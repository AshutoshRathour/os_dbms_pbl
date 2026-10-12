"""Jobs REST API — CRUD and status management."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Job, WorkloadType
from app.scheduler.estimator import estimate_resources

jobs_bp = Blueprint('jobs_api', __name__, url_prefix='/api/jobs')


@jobs_bp.route('', methods=['GET'])
@login_required
def list_jobs():
    """List jobs for the current user, with optional status filter."""
    status = request.args.get('status')
    query = Job.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(Job.created_at.desc())

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'jobs': [j.to_dict() for j in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@jobs_bp.route('/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """Get a single job by ID."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())


@jobs_bp.route('', methods=['POST'])
@login_required
def create_job():
    """Submit a new job."""
    data = request.get_json(silent=True) or {}

    workload_type_id = data.get('workload_type_id')
    if not workload_type_id:
        return jsonify({'error': 'workload_type_id is required'}), 400

    workload_type = db.session.get(WorkloadType, workload_type_id)
    if not workload_type:
        return jsonify({'error': 'Invalid workload type'}), 400

    input_params = data.get('input_params', {})
    priority = data.get('priority', 5)

    if not isinstance(priority, int) or priority < 1 or priority > 10:
        return jsonify({'error': 'Priority must be 1-10'}), 400

    # Validate input_params based on workload type
    validation_error = _validate_input_params(workload_type.name, input_params)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    # Estimate resources
    est = estimate_resources(workload_type, input_params)

    job = Job(
        user_id=current_user.id,
        workload_type_id=workload_type_id,
        status=Job.STATUS_QUEUED,
        input_params=input_params,
        est_cpu_cores=est['cpu_cores'],
        est_memory_mb=est['memory_mb'],
        est_time_seconds=est['time_seconds'],
        priority=priority,
    )
    db.session.add(job)
    db.session.commit()

    return jsonify(job.to_dict()), 201


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@login_required
def cancel_job(job_id):
    """Cancel a queued job."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job.status != Job.STATUS_QUEUED:
        return jsonify({'error': 'Only queued jobs can be cancelled'}), 400

    job.status = Job.STATUS_FAILED
    db.session.commit()
    return jsonify({'message': 'Job cancelled', 'job': job.to_dict()})


@jobs_bp.route('/workload-types', methods=['GET'])
@login_required
def list_workload_types():
    """List all available workload types."""
    types = WorkloadType.query.all()
    return jsonify([wt.to_dict() for wt in types])


def _validate_input_params(workload_name, params):
    """Validate input parameters for a given workload type.

    Returns an error string if invalid, None if valid.
    """
    if not isinstance(params, dict):
        return 'input_params must be a JSON object'

    validators = {
        'Image Processing': _validate_image_params,
        'Data Analysis': _validate_data_params,
        'File Processing': _validate_file_params,
        'Video Conversion': _validate_video_params,
    }

    validator = validators.get(workload_name)
    if validator:
        return validator(params)
    return None


def _validate_image_params(params):
    valid_ops = ['blur', 'sharpen', 'grayscale', 'resize', 'edge_detect']
    operation = params.get('operation', 'blur')
    if operation not in valid_ops:
        return f'Invalid operation. Choose from: {valid_ops}'
    size = params.get('size', 512)
    if not isinstance(size, int) or size < 64 or size > 4096:
        return 'Image size must be 64-4096'
    return None


def _validate_data_params(params):
    rows = params.get('rows', 1000)
    if not isinstance(rows, int) or rows < 10 or rows > 1000000:
        return 'Rows must be 10-1000000'
    return None


def _validate_file_params(params):
    size_kb = params.get('size_kb', 100)
    if not isinstance(size_kb, int) or size_kb < 1 or size_kb > 10240:
        return 'File size must be 1-10240 KB'
    return None


def _validate_video_params(params):
    duration = params.get('duration_seconds', 5)
    if not isinstance(duration, int) or duration < 1 or duration > 60:
        return 'Duration must be 1-60 seconds'
    return None
