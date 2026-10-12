"""Integration tests for Flask REST APIs and Auth endpoints."""

import json
from app.models import Job, WorkloadType


def test_auth_registration_and_login(client, app):
    # Register new user
    res = client.post('/auth/register', data={
        'username': 'bob',
        'email': 'bob@cloud.local',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert res.status_code == 200

    # Log in
    res_login = client.post('/auth/login', data={
        'username': 'bob',
        'password': 'password123'
    }, follow_redirects=True)
    assert res_login.status_code == 200


def test_api_list_workload_types(authenticated_client):
    res = authenticated_client.get('/api/jobs/workload-types')
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) >= 4
    names = [wt['name'] for wt in data]
    assert 'Image Processing' in names
    assert 'Data Analysis' in names


def test_api_create_job_valid_and_invalid(authenticated_client, app):
    with app.app_context():
        wt = WorkloadType.query.filter_by(name='Image Processing').first()
        wt_id = wt.id

    # 1. Invalid priority
    res_bad_pri = authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'operation': 'blur', 'size': 512},
        'priority': 99
    })
    assert res_bad_pri.status_code == 400

    # 2. Invalid parameter (unknown operation)
    res_bad_param = authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'operation': 'invalid_op', 'size': 512},
        'priority': 5
    })
    assert res_bad_param.status_code == 400

    # 3. Valid job submission
    res_valid = authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'operation': 'blur', 'size': 512},
        'priority': 3
    })
    assert res_valid.status_code == 201
    job = res_valid.get_json()
    assert job['id'] is not None
    assert job['status'] == Job.STATUS_QUEUED
    assert job['est_cpu_cores'] >= 1
    assert job['est_memory_mb'] >= 256


def test_api_job_lifecycle_and_cancellation(authenticated_client, app):
    with app.app_context():
        wt = WorkloadType.query.filter_by(name='Data Analysis').first()
        wt_id = wt.id

    # Create job
    res_create = authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'rows': 2000},
        'priority': 4
    })
    job_id = res_create.get_json()['id']

    # Get single job
    res_get = authenticated_client.get(f'/api/jobs/{job_id}')
    assert res_get.status_code == 200
    assert res_get.get_json()['id'] == job_id

    # Cancel job
    res_cancel = authenticated_client.delete(f'/api/jobs/{job_id}')
    assert res_cancel.status_code == 200
    assert res_cancel.get_json()['job']['status'] == Job.STATUS_FAILED


def test_api_dashboard_and_nodes(authenticated_client):
    # Dashboard endpoint
    res_dash = authenticated_client.get('/api/dashboard')
    assert res_dash.status_code == 200
    dash_data = res_dash.get_json()
    assert 'job_stats' in dash_data
    assert 'node_stats' in dash_data
    assert 'recent_jobs' in dash_data

    # Node summary endpoint
    res_nodes = authenticated_client.get('/api/nodes/summary')
    assert res_nodes.status_code == 200
    nodes_data = res_nodes.get_json()
    assert 'total_nodes' in nodes_data
    assert 'total_cpu_cores' in nodes_data


def test_api_scheduling_simulation(authenticated_client, app):
    # Submit 2 jobs to have simulation data
    with app.app_context():
        wt = WorkloadType.query.first()
        wt_id = wt.id

    authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'operation': 'blur', 'size': 512},
        'priority': 2
    })
    authenticated_client.post('/api/jobs', json={
        'workload_type_id': wt_id,
        'input_params': {'operation': 'blur', 'size': 1024},
        'priority': 5
    })

    # Trigger simulation
    res_sim = authenticated_client.post('/api/scheduling/simulate', json={
        'time_quantum': 50
    })
    assert res_sim.status_code == 200
    sim_data = res_sim.get_json()
    assert 'algorithms' in sim_data
    assert 'RoundRobin' in sim_data['algorithms']
    assert 'FCFS' in sim_data['algorithms']
    assert 'SJF' in sim_data['algorithms']
    assert 'Priority' in sim_data['algorithms']
