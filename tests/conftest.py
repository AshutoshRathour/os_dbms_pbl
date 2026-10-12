"""Pytest configuration and shared fixtures."""

import pytest
from app import create_app
from app.extensions import db
from app.models import User, WorkloadType, ComputingNode, SchedulingConfig, Job


@pytest.fixture
def app():
    """Create application in testing mode with in-memory SQLite database."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()

        # Seed essential workload types
        workloads = [
            WorkloadType(
                name='Image Processing',
                docker_image='cloud-workload-image',
                command_template='python process.py --operation blur --size 512',
                est_cpu_cores=1,
                est_memory_mb=256,
                est_time_seconds=30,
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
                cpu_scale_factor=1.5,
                memory_scale_factor=1.0,
                time_scale_factor=2.0,
            ),
        ]
        db.session.add_all(workloads)

        # Seed nodes
        nodes = [
            ComputingNode(name='test-node-1', total_cpu_cores=4, total_memory_mb=2048, status='active'),
            ComputingNode(name='test-node-2', total_cpu_cores=8, total_memory_mb=4096, status='active'),
        ]
        db.session.add_all(nodes)

        # Seed test user
        user = User(username='testuser', email='test@test.local')
        user.set_password('password123')
        db.session.add(user)

        # Seed scheduling configs
        configs = [
            SchedulingConfig(algorithm='FCFS', time_quantum_ms=0, is_active=True),
            SchedulingConfig(algorithm='SJF', time_quantum_ms=0, is_active=True),
            SchedulingConfig(algorithm='Priority', time_quantum_ms=0, is_active=True),
            SchedulingConfig(algorithm='RoundRobin', time_quantum_ms=100, is_active=True),
        ]
        db.session.add_all(configs)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client, app):
    """Client with test user logged in."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
    return client
