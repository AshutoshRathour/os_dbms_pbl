"""Scheduling Simulator REST API.

Runs FCFS, SJF, Priority, and Round Robin scheduling simulations
on a given set of jobs and persists results for comparison.

IMPORTANT: These are *simulated* OS-level CPU scheduling algorithms
that compute theoretical waiting/turnaround times. They are
completely separate from the actual Docker container execution.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models import Job, SchedulingConfig, SchedulingResult
from app.scheduler.algorithms import run_fcfs, run_sjf, run_priority, run_round_robin

scheduling_bp = Blueprint('scheduling_api', __name__, url_prefix='/api/scheduling')


@scheduling_bp.route('/configs', methods=['GET'])
@login_required
def list_configs():
    """List all scheduling algorithm configurations."""
    configs = SchedulingConfig.query.all()
    return jsonify([c.to_dict() for c in configs])


@scheduling_bp.route('/simulate', methods=['POST'])
@login_required
def simulate():
    """Run all scheduling algorithms on specified jobs and compare.

    Request body:
        job_ids: list[int]  — IDs of jobs to include (uses est_time_seconds as burst)
        time_quantum: int   — quantum for Round Robin (ms), default 100
    """
    data = request.get_json(silent=True) or {}
    job_ids = data.get('job_ids', [])
    time_quantum = data.get('time_quantum', 100)

    if not job_ids:
        # Default: use all jobs
        jobs = Job.query.order_by(Job.created_at).all()
    else:
        jobs = Job.query.filter(Job.id.in_(job_ids)).order_by(Job.created_at).all()

    if not jobs:
        return jsonify({'error': 'No jobs found'}), 400

    if not isinstance(time_quantum, int) or time_quantum < 1:
        return jsonify({'error': 'time_quantum must be a positive integer'}), 400

    # Build process list for the simulator
    processes = []
    for i, job in enumerate(jobs):
        processes.append({
            'job_id': job.id,
            'arrival_time': i,  # Simplification: arrival order = submission order
            'burst_time': max(job.est_time_seconds or 1, 1),
            'priority': job.priority or 5,
        })

    actual_job_ids = [p['job_id'] for p in processes]

    # Run all four algorithms
    results_map = {}

    for algo_name, algo_func, extra_kwargs in [
        ('FCFS', run_fcfs, {}),
        ('SJF', run_sjf, {}),
        ('Priority', run_priority, {}),
        ('RoundRobin', run_round_robin, {'time_quantum': time_quantum}),
    ]:
        result = algo_func(processes, **extra_kwargs)

        # Persist result
        config = SchedulingConfig.query.filter_by(algorithm=algo_name).first()
        if not config:
            config = SchedulingConfig(
                algorithm=algo_name,
                time_quantum_ms=time_quantum if algo_name == 'RoundRobin' else 0,
                is_active=True,
            )
            db.session.add(config)
            db.session.flush()

        sr = SchedulingResult(
            scheduling_config_id=config.id,
            job_ids=actual_job_ids,
            execution_order=result['execution_order'],
            metrics=result['metrics'],
        )
        db.session.add(sr)
        results_map[algo_name] = {
            'execution_order': result['execution_order'],
            'metrics': result['metrics'],
        }

    db.session.commit()

    return jsonify({
        'job_ids': actual_job_ids,
        'time_quantum': time_quantum,
        'algorithms': results_map,
        'note': 'These are SIMULATED scheduling metrics for comparison. '
                'Actual Docker execution uses the worker service.',
    })


@scheduling_bp.route('/results', methods=['GET'])
@login_required
def list_results():
    """List recent scheduling simulation results."""
    results = (
        SchedulingResult.query
        .order_by(SchedulingResult.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([r.to_dict() for r in results])
