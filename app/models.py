"""SQLAlchemy ORM models for the Cloud Scheduler system."""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager


def utcnow():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_active_user = db.Column(db.Boolean, default=True)

    jobs = db.relationship('Job', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Workload Type
# ---------------------------------------------------------------------------
class WorkloadType(db.Model):
    __tablename__ = 'workload_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    docker_image = db.Column(db.String(255), nullable=False)
    command_template = db.Column(db.String(500), nullable=False)
    est_cpu_cores = db.Column(db.Integer, default=1)
    est_memory_mb = db.Column(db.Integer, default=256)
    est_time_seconds = db.Column(db.Integer, default=60)
    description = db.Column(db.Text)

    # Scaling factors: multiply by input_size to estimate resources
    cpu_scale_factor = db.Column(db.Float, default=1.0)
    memory_scale_factor = db.Column(db.Float, default=1.0)
    time_scale_factor = db.Column(db.Float, default=1.0)

    jobs = db.relationship('Job', backref='workload_type', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'docker_image': self.docker_image,
            'command_template': self.command_template,
            'est_cpu_cores': self.est_cpu_cores,
            'est_memory_mb': self.est_memory_mb,
            'est_time_seconds': self.est_time_seconds,
            'description': self.description,
            'cpu_scale_factor': self.cpu_scale_factor,
            'memory_scale_factor': self.memory_scale_factor,
            'time_scale_factor': self.time_scale_factor,
        }


# ---------------------------------------------------------------------------
# Computing Node
# ---------------------------------------------------------------------------
class ComputingNode(db.Model):
    __tablename__ = 'computing_nodes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    total_cpu_cores = db.Column(db.Integer, nullable=False)
    total_memory_mb = db.Column(db.Integer, nullable=False)
    allocated_cpu_cores = db.Column(db.Integer, default=0)
    allocated_memory_mb = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # active, maintenance, offline
    last_heartbeat = db.Column(db.DateTime, default=utcnow)
    is_simulated = db.Column(db.Boolean, default=True)

    assignments = db.relationship('JobAssignment', backref='node', lazy='dynamic')

    @property
    def available_cpu(self):
        return self.total_cpu_cores - self.allocated_cpu_cores

    @property
    def available_memory(self):
        return self.total_memory_mb - self.allocated_memory_mb

    @property
    def cpu_utilization(self):
        if self.total_cpu_cores == 0:
            return 0.0
        return round((self.allocated_cpu_cores / self.total_cpu_cores) * 100, 1)

    @property
    def memory_utilization(self):
        if self.total_memory_mb == 0:
            return 0.0
        return round((self.allocated_memory_mb / self.total_memory_mb) * 100, 1)

    def has_capacity(self, cpu_cores, memory_mb):
        return self.available_cpu >= cpu_cores and self.available_memory >= memory_mb

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'total_cpu_cores': self.total_cpu_cores,
            'total_memory_mb': self.total_memory_mb,
            'allocated_cpu_cores': self.allocated_cpu_cores,
            'allocated_memory_mb': self.allocated_memory_mb,
            'available_cpu': self.available_cpu,
            'available_memory': self.available_memory,
            'cpu_utilization': self.cpu_utilization,
            'memory_utilization': self.memory_utilization,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'is_simulated': self.is_simulated,
        }


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
class Job(db.Model):
    __tablename__ = 'jobs'

    STATUS_QUEUED = 'queued'
    STATUS_ASSIGNED = 'assigned'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    VALID_STATUSES = [STATUS_QUEUED, STATUS_ASSIGNED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    workload_type_id = db.Column(db.Integer, db.ForeignKey('workload_types.id'), nullable=False)
    status = db.Column(db.String(20), default=STATUS_QUEUED, nullable=False, index=True)
    input_params = db.Column(db.JSON)
    est_cpu_cores = db.Column(db.Integer)
    est_memory_mb = db.Column(db.Integer)
    est_time_seconds = db.Column(db.Integer)
    priority = db.Column(db.Integer, default=5)  # 1=highest, 10=lowest
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    assignment = db.relationship('JobAssignment', backref='job', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'workload_type_id': self.workload_type_id,
            'workload_name': self.workload_type.name if self.workload_type else None,
            'status': self.status,
            'input_params': self.input_params,
            'est_cpu_cores': self.est_cpu_cores,
            'est_memory_mb': self.est_memory_mb,
            'est_time_seconds': self.est_time_seconds,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assignment': self.assignment.to_dict() if self.assignment else None,
        }


# ---------------------------------------------------------------------------
# Job Assignment
# ---------------------------------------------------------------------------
class JobAssignment(db.Model):
    __tablename__ = 'job_assignments'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), unique=True, nullable=False, index=True)
    node_id = db.Column(db.Integer, db.ForeignKey('computing_nodes.id'), nullable=False, index=True)
    container_id = db.Column(db.String(100))
    assigned_at = db.Column(db.DateTime, default=utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    exit_code = db.Column(db.Integer)
    stdout = db.Column(db.Text)
    stderr = db.Column(db.Text)
    actual_cpu_used = db.Column(db.Integer)
    actual_memory_used_mb = db.Column(db.Integer)
    actual_duration_seconds = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'node_id': self.node_id,
            'node_name': self.node.name if self.node else None,
            'container_id': self.container_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'exit_code': self.exit_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'actual_cpu_used': self.actual_cpu_used,
            'actual_memory_used_mb': self.actual_memory_used_mb,
            'actual_duration_seconds': self.actual_duration_seconds,
        }


# ---------------------------------------------------------------------------
# Scheduling Config
# ---------------------------------------------------------------------------
class SchedulingConfig(db.Model):
    __tablename__ = 'scheduling_configs'

    id = db.Column(db.Integer, primary_key=True)
    algorithm = db.Column(db.String(50), nullable=False)  # FCFS, SJF, Priority, RoundRobin
    time_quantum_ms = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    results = db.relationship('SchedulingResult', backref='config', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'algorithm': self.algorithm,
            'time_quantum_ms': self.time_quantum_ms,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Scheduling Result (simulated comparison metrics)
# ---------------------------------------------------------------------------
class SchedulingResult(db.Model):
    __tablename__ = 'scheduling_results'

    id = db.Column(db.Integer, primary_key=True)
    scheduling_config_id = db.Column(db.Integer, db.ForeignKey('scheduling_configs.id'), nullable=False)
    job_ids = db.Column(db.JSON)          # List of job IDs included in simulation
    execution_order = db.Column(db.JSON)  # Ordered list of job execution steps
    metrics = db.Column(db.JSON)          # {avg_wait, avg_turnaround, per_job: [...]}
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'scheduling_config_id': self.scheduling_config_id,
            'algorithm': self.config.algorithm if self.config else None,
            'time_quantum_ms': self.config.time_quantum_ms if self.config else None,
            'job_ids': self.job_ids,
            'execution_order': self.execution_order,
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
