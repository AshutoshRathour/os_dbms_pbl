"""Dashboard REST API — aggregated metrics for the monitoring dashboard."""

from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func
from app.extensions import db
from app.models import Job, JobAssignment, ComputingNode

dashboard_bp = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('', methods=['GET'])
@login_required
def get_dashboard():
    """Return all dashboard metrics in a single call."""
    return jsonify({
        'job_stats': _job_stats(),
        'node_stats': _node_stats(),
        'recent_jobs': _recent_jobs(),
        'resource_usage': _resource_usage(),
    })


@dashboard_bp.route('/job-stats', methods=['GET'])
@login_required
def job_stats():
    return jsonify(_job_stats())


@dashboard_bp.route('/recent-jobs', methods=['GET'])
@login_required
def recent_jobs():
    return jsonify(_recent_jobs())


def _job_stats():
    """Count jobs by status."""
    counts = (
        db.session.query(Job.status, func.count(Job.id))
        .group_by(Job.status)
        .all()
    )
    stats = {s: 0 for s in Job.VALID_STATUSES}
    for status, count in counts:
        stats[status] = count
    stats['total'] = sum(stats.values())

    # Average metrics from completed assignments
    avg_metrics = (
        db.session.query(
            func.avg(JobAssignment.actual_duration_seconds),
            func.avg(JobAssignment.actual_memory_used_mb),
        )
        .filter(JobAssignment.exit_code.isnot(None))
        .first()
    )
    stats['avg_duration'] = round(avg_metrics[0], 2) if avg_metrics[0] else 0
    stats['avg_memory_mb'] = round(avg_metrics[1], 1) if avg_metrics[1] else 0

    return stats


def _node_stats():
    """Node resource summary."""
    nodes = ComputingNode.query.all()
    return {
        'total': len(nodes),
        'active': sum(1 for n in nodes if n.status == 'active'),
        'total_cpu': sum(n.total_cpu_cores for n in nodes),
        'allocated_cpu': sum(n.allocated_cpu_cores for n in nodes),
        'total_memory': sum(n.total_memory_mb for n in nodes),
        'allocated_memory': sum(n.allocated_memory_mb for n in nodes),
        'nodes': [n.to_dict() for n in nodes],
    }


def _recent_jobs():
    """Last 15 jobs with assignment info."""
    jobs = (
        Job.query
        .order_by(Job.created_at.desc())
        .limit(15)
        .all()
    )
    return [j.to_dict() for j in jobs]


def _resource_usage():
    """Per-node resource bar data."""
    nodes = ComputingNode.query.filter_by(status='active').all()
    return [{
        'name': n.name,
        'cpu_total': n.total_cpu_cores,
        'cpu_used': n.allocated_cpu_cores,
        'cpu_pct': n.cpu_utilization,
        'mem_total': n.total_memory_mb,
        'mem_used': n.allocated_memory_mb,
        'mem_pct': n.memory_utilization,
    } for n in nodes]
