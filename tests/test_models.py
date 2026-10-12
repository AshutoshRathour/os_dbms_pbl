"""Unit tests for SQLAlchemy models."""

from app.models import User, ComputingNode, Job, WorkloadType, JobAssignment


def test_user_password_hashing(app):
    user = User(username='alice', email='alice@example.com')
    user.set_password('supersecret')
    assert user.password_hash != 'supersecret'
    assert user.check_password('supersecret') is True
    assert user.check_password('wrongpass') is False


def test_computing_node_capacities(app):
    node = ComputingNode(
        name='node-test',
        total_cpu_cores=4,
        total_memory_mb=2048,
        allocated_cpu_cores=1,
        allocated_memory_mb=512,
        status='active'
    )
    assert node.available_cpu == 3
    assert node.available_memory == 1536
    assert node.cpu_utilization == 25.0
    assert node.memory_utilization == 25.0

    # Capacity check
    assert node.has_capacity(2, 1024) is True
    assert node.has_capacity(4, 512) is False  # Exceeds available CPU
    assert node.has_capacity(1, 2048) is False  # Exceeds available RAM


def test_job_and_assignment_lifecycle(app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        wt = WorkloadType.query.first()
        node = ComputingNode.query.first()

        job = Job(
            user_id=user.id,
            workload_type_id=wt.id,
            status=Job.STATUS_QUEUED,
            input_params={'operation': 'blur', 'size': 512},
            est_cpu_cores=1,
            est_memory_mb=256,
            est_time_seconds=30,
            priority=3
        )
        from app.extensions import db
        db.session.add(job)
        db.session.commit()

        assert job.id is not None
        assert job.status == Job.STATUS_QUEUED

        # Add assignment
        assignment = JobAssignment(
            job_id=job.id,
            node_id=node.id,
            container_id='docker-fake-123'
        )
        db.session.add(assignment)
        job.status = Job.STATUS_RUNNING
        db.session.commit()

        assert job.assignment is not None
        assert job.assignment.container_id == 'docker-fake-123'
        assert job.status == Job.STATUS_RUNNING
