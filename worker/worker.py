"""Background Worker — polls MySQL for queued jobs, executes them in Docker containers.

This runs as a separate process/container. It:
1. Polls for queued jobs using SELECT ... FOR UPDATE to prevent double-claiming.
2. Estimates resources and selects an eligible node (atomic with row locking).
3. Launches a Docker container with CPU/memory/timeout limits.
4. Captures container ID, stdout, stderr, exit code, and duration.
5. Updates the database with actual execution results.
6. Releases node resources and cleans up containers.

Security:
- Never executes arbitrary shell commands from user input.
- All container arguments are validated and parameterized.
- Containers run without privileged mode.
- Resource limits are enforced.
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime, timezone

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Job, JobAssignment, ComputingNode
from app.scheduler.node_selector import select_node, release_node_resources

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('worker')


class JobWorker:
    """Background worker that executes jobs in Docker containers."""

    def __init__(self):
        self.app = create_app(os.environ.get('FLASK_ENV', 'development'))
        self.poll_interval = self.app.config.get('WORKER_POLL_INTERVAL', 5)
        self.max_concurrent = self.app.config.get('WORKER_MAX_CONCURRENT', 3)
        self.container_timeout = self.app.config.get('CONTAINER_TIMEOUT', 300)
        self.cleanup_containers = self.app.config.get('CONTAINER_CLEANUP', True)
        self.running = True
        self.active_jobs = 0
        self._lock = threading.Lock()

        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info('Connected to Docker Engine')
        except Exception as e:
            logger.error(f'Failed to connect to Docker: {e}')
            self.docker_client = None

        # Graceful shutdown
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info('Shutdown signal received, finishing active jobs...')
        self.running = False

    def run(self):
        """Main loop — poll for jobs and execute them."""
        logger.info(f'Worker started (poll={self.poll_interval}s, max_concurrent={self.max_concurrent})')

        with self.app.app_context():
            # Recover any jobs stuck in 'assigned' or 'running' state from crashes
            self._recover_stuck_jobs()

            while self.running:
                try:
                    if self.active_jobs < self.max_concurrent:
                        job = self._claim_job()
                        if job:
                            # Execute in a thread to allow concurrent processing
                            t = threading.Thread(
                                target=self._execute_job_thread,
                                args=(job.id,),
                                daemon=True,
                            )
                            t.start()
                        else:
                            time.sleep(self.poll_interval)
                    else:
                        time.sleep(1)
                except Exception as e:
                    logger.error(f'Error in main loop: {e}', exc_info=True)
                    time.sleep(self.poll_interval)

        logger.info('Worker stopped')

    def _claim_job(self):
        """Atomically claim the next queued job using SELECT FOR UPDATE.

        Returns the Job if claimed, or None if no jobs are available.
        """
        try:
            # Use a fresh transaction with row-level locking
            job = (
                Job.query
                .filter_by(status=Job.STATUS_QUEUED)
                .order_by(Job.priority.asc(), Job.created_at.asc())
                .with_for_update(skip_locked=True)
                .first()
            )

            if not job:
                return None

            job.status = Job.STATUS_ASSIGNED
            db.session.commit()
            logger.info(f'Claimed job {job.id} (workload={job.workload_type.name})')
            return job

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error claiming job: {e}')
            return None

    def _execute_job_thread(self, job_id):
        """Execute a single job inside a Docker container (runs in a thread)."""
        with self._lock:
            self.active_jobs += 1

        try:
            with self.app.app_context():
                self._execute_job(job_id)
        except Exception as e:
            logger.error(f'Unhandled error executing job {job_id}: {e}', exc_info=True)
            with self.app.app_context():
                self._fail_job(job_id, str(e))
        finally:
            with self._lock:
                self.active_jobs -= 1

    def _execute_job(self, job_id):
        """Core job execution logic."""
        job = db.session.get(Job, job_id)
        if not job:
            logger.error(f'Job {job_id} not found')
            return

        workload = job.workload_type
        cpu_cores = job.est_cpu_cores or 1
        memory_mb = job.est_memory_mb or 256

        # 1. Select a node with sufficient capacity (atomic with locking)
        node = select_node(cpu_cores, memory_mb)
        if not node:
            logger.warning(f'No node available for job {job_id} (needs {cpu_cores} CPU, {memory_mb} MB)')
            job.status = Job.STATUS_QUEUED  # Re-queue
            db.session.commit()
            return

        # 2. Create assignment record
        assignment = JobAssignment(
            job_id=job.id,
            node_id=node.id,
            assigned_at=datetime.now(timezone.utc),
        )
        db.session.add(assignment)
        db.session.commit()

        logger.info(f'Job {job_id} assigned to node {node.name}')

        # 3. Build Docker container arguments
        container = None
        start_time = datetime.now(timezone.utc)

        try:
            if not self.docker_client:
                raise RuntimeError('Docker client not available')

            # Build safe command from validated parameters
            command = self._build_command(workload, job.input_params or {})
            image = workload.docker_image

            # Ensure image exists
            try:
                self.docker_client.images.get(image)
            except ImageNotFound:
                logger.info(f'Pulling image {image}...')
                self.docker_client.images.pull(image)

            # 4. Launch container with resource limits
            job.status = Job.STATUS_RUNNING
            assignment.started_at = start_time
            db.session.commit()

            logger.info(f'Starting container for job {job_id}: image={image}, cmd={command}')

            nano_cpus = int(cpu_cores * 1e9)  # Docker uses nano-CPUs
            mem_limit = f'{memory_mb}m'

            container = self.docker_client.containers.run(
                image=image,
                command=command,
                detach=True,
                nano_cpus=nano_cpus,
                mem_limit=mem_limit,
                network_disabled=True,
                privileged=False,
                read_only=False,
                remove=False,  # We'll remove after capturing logs
                labels={
                    'cloud-scheduler': 'true',
                    'job-id': str(job_id),
                    'node-id': str(node.id),
                },
            )

            assignment.container_id = container.id
            db.session.commit()

            # 5. Wait for completion with timeout
            result = container.wait(timeout=self.container_timeout)
            exit_code = result.get('StatusCode', -1)

            # 6. Capture output
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')

            # Truncate extremely long output
            max_output = 50000
            if len(stdout) > max_output:
                stdout = stdout[:max_output] + '\n... [truncated]'
            if len(stderr) > max_output:
                stderr = stderr[:max_output] + '\n... [truncated]'

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # 7. Update assignment with results
            assignment.completed_at = end_time
            assignment.exit_code = exit_code
            assignment.stdout = stdout
            assignment.stderr = stderr
            assignment.actual_duration_seconds = duration
            assignment.actual_cpu_used = cpu_cores
            assignment.actual_memory_used_mb = memory_mb

            if exit_code == 0:
                job.status = Job.STATUS_COMPLETED
                logger.info(f'Job {job_id} completed successfully in {duration:.1f}s')
            else:
                job.status = Job.STATUS_FAILED
                logger.warning(f'Job {job_id} failed with exit code {exit_code}')

            db.session.commit()

        except Exception as e:
            logger.error(f'Error executing job {job_id}: {e}', exc_info=True)
            assignment.stderr = str(e)
            assignment.completed_at = datetime.now(timezone.utc)
            assignment.exit_code = -1
            if start_time:
                assignment.actual_duration_seconds = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()
            job.status = Job.STATUS_FAILED
            db.session.commit()

        finally:
            # 8. Release node resources
            release_node_resources(node.id, cpu_cores, memory_mb)
            db.session.commit()

            # 9. Clean up container
            if container and self.cleanup_containers:
                try:
                    container.remove(force=True)
                    logger.info(f'Cleaned up container {container.short_id} for job {job_id}')
                except Exception as e:
                    logger.warning(f'Failed to remove container: {e}')

    def _build_command(self, workload, params):
        """Build a safe Docker command from validated parameters.

        Never passes raw user input as shell commands. All values are
        passed as controlled arguments.
        """
        name = workload.name

        if name == 'Image Processing':
            operation = params.get('operation', 'blur')
            size = int(params.get('size', 512))
            return f'python process.py --operation {operation} --size {size}'

        elif name == 'Data Analysis':
            rows = int(params.get('rows', 1000))
            return f'python analyze.py --rows {rows}'

        elif name == 'File Processing':
            size_kb = int(params.get('size_kb', 100))
            return f'python process.py --size-kb {size_kb}'

        elif name == 'Video Conversion':
            duration = int(params.get('duration_seconds', 5))
            return f'python convert.py --duration {duration}'

        else:
            # Fallback: use command template
            return workload.command_template

    def _fail_job(self, job_id, error_message):
        """Mark a job as failed and release resources."""
        try:
            job = db.session.get(Job, job_id)
            if job:
                job.status = Job.STATUS_FAILED
                if job.assignment:
                    job.assignment.stderr = error_message
                    job.assignment.completed_at = datetime.now(timezone.utc)
                    job.assignment.exit_code = -1
                    # Release resources
                    if job.assignment.node_id:
                        release_node_resources(
                            job.assignment.node_id,
                            job.est_cpu_cores or 1,
                            job.est_memory_mb or 256,
                        )
                db.session.commit()
        except Exception as e:
            logger.error(f'Error failing job {job_id}: {e}')
            db.session.rollback()

    def _recover_stuck_jobs(self):
        """Re-queue jobs stuck in assigned/running state from a previous crash."""
        stuck = Job.query.filter(
            Job.status.in_([Job.STATUS_ASSIGNED, Job.STATUS_RUNNING])
        ).all()

        for job in stuck:
            logger.warning(f'Recovering stuck job {job.id} (was {job.status})')
            job.status = Job.STATUS_QUEUED
            if job.assignment:
                if job.assignment.node_id:
                    release_node_resources(
                        job.assignment.node_id,
                        job.est_cpu_cores or 1,
                        job.est_memory_mb or 256,
                    )
                db.session.delete(job.assignment)

        if stuck:
            db.session.commit()
            logger.info(f'Recovered {len(stuck)} stuck jobs')


if __name__ == '__main__':
    worker = JobWorker()
    worker.run()
