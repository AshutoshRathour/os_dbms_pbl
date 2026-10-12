"""Database seeder — creates tables and populates initial data.

Seeds:
- 4 workload types with Docker image names and estimation rules
- 3 simulated computing nodes
- 4 scheduling algorithm configurations
- 1 default admin user

Run with: python init_db.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import (
    User, WorkloadType, ComputingNode, SchedulingConfig,
)


def wait_for_db(app, retries=30, delay=2):
    """Wait for MySQL to become available and accept queries."""
    print(f'Waiting for MySQL to become ready (max {retries} retries, interval {delay}s)...', flush=True)
    for i in range(retries):
        try:
            with app.app_context():
                with db.engine.connect() as conn:
                    conn.execute(db.text("SELECT 1"))
                print('Database connection established successfully.', flush=True)
                return True
        except Exception as e:
            try:
                db.engine.dispose()
            except Exception:
                pass
            print(f'Waiting for database... ({i + 1}/{retries}): {e}', flush=True)
            time.sleep(delay)
    print('ERROR: Could not connect to database after maximum retries.', file=sys.stderr, flush=True)
    return False


def seed():
    app = create_app(os.environ.get('FLASK_ENV', 'development'))

    if not wait_for_db(app):
        print('FATAL: Database readiness check failed. Exiting.', file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        with app.app_context():
            db.create_all()
            print('Tables created.', flush=True)

            # --- Workload Types ---
            if WorkloadType.query.count() == 0:
                workloads = [
                    WorkloadType(
                        name='Image Processing',
                        docker_image='cloud-workload-image',
                        command_template='python process.py --operation blur --size 512',
                        est_cpu_cores=1,
                        est_memory_mb=256,
                        est_time_seconds=30,
                        description='Generates and processes images with filters (blur, sharpen, grayscale, resize, edge detection).',
                        cpu_scale_factor=1.0,
                        memory_scale_factor=1.5,
                        time_scale_factor=1.2,
                    ),
                    WorkloadType(
                        name='Data Analysis',
                        docker_image='cloud-workload-data',
                        command_template='python analyze.py --rows 1000',
                        est_cpu_cores=1,
                        est_memory_mb=128,
                        est_time_seconds=15,
                        description='Statistical analysis on generated datasets — mean, median, stdev, correlations.',
                        cpu_scale_factor=1.0,
                        memory_scale_factor=2.0,
                        time_scale_factor=1.0,
                    ),
                    WorkloadType(
                        name='File Processing',
                        docker_image='cloud-workload-file',
                        command_template='python process.py --size-kb 100',
                        est_cpu_cores=1,
                        est_memory_mb=128,
                        est_time_seconds=10,
                        description='Text generation and analysis — word count, character frequency, sentence statistics.',
                        cpu_scale_factor=0.5,
                        memory_scale_factor=1.0,
                        time_scale_factor=0.8,
                    ),
                    WorkloadType(
                        name='Video Conversion',
                        docker_image='cloud-workload-video',
                        command_template='python convert.py --duration 5',
                        est_cpu_cores=2,
                        est_memory_mb=512,
                        est_time_seconds=60,
                        description='Frame generation and compression — compute-intensive encoding simulation.',
                        cpu_scale_factor=1.5,
                        memory_scale_factor=1.0,
                        time_scale_factor=2.0,
                    ),
                ]
                db.session.add_all(workloads)
                print(f'Seeded {len(workloads)} workload types.', flush=True)

            # --- Computing Nodes (simulated) ---
            if ComputingNode.query.count() == 0:
                nodes = [
                    ComputingNode(
                        name='node-alpha',
                        total_cpu_cores=4,
                        total_memory_mb=2048,
                        status='active',
                        is_simulated=True,
                    ),
                    ComputingNode(
                        name='node-beta',
                        total_cpu_cores=4,
                        total_memory_mb=4096,
                        status='active',
                        is_simulated=True,
                    ),
                    ComputingNode(
                        name='node-gamma',
                        total_cpu_cores=2,
                        total_memory_mb=1024,
                        status='active',
                        is_simulated=True,
                    ),
                ]
                db.session.add_all(nodes)
                print(f'Seeded {len(nodes)} computing nodes (simulated).', flush=True)

            # --- Scheduling Configs ---
            if SchedulingConfig.query.count() == 0:
                configs = [
                    SchedulingConfig(algorithm='FCFS', time_quantum_ms=0, is_active=True),
                    SchedulingConfig(algorithm='SJF', time_quantum_ms=0, is_active=True),
                    SchedulingConfig(algorithm='Priority', time_quantum_ms=0, is_active=True),
                    SchedulingConfig(algorithm='RoundRobin', time_quantum_ms=100, is_active=True),
                ]
                db.session.add_all(configs)
                print(f'Seeded {len(configs)} scheduling configurations.', flush=True)

            # --- Default Admin User ---
            if User.query.count() == 0:
                admin = User(username='admin', email='admin@cloudscheduler.local')
                admin.set_password('admin123')
                db.session.add(admin)
                print('Created default admin user (admin / admin123).', flush=True)

            db.session.commit()
            print('Database seeding complete.', flush=True)
    except Exception as e:
        print(f'ERROR during database initialization: {e}', file=sys.stderr, flush=True)
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass
        sys.exit(1)


if __name__ == '__main__':
    seed()
