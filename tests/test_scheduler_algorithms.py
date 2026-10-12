"""Unit tests for OS Scheduling Algorithms (FCFS, SJF, Priority, Round Robin)."""

from app.scheduler.algorithms import run_fcfs, run_sjf, run_priority, run_round_robin


def test_fcfs_scheduling():
    processes = [
        {'job_id': 1, 'arrival_time': 0, 'burst_time': 10, 'priority': 5},
        {'job_id': 2, 'arrival_time': 2, 'burst_time': 5, 'priority': 2},
    ]

    res = run_fcfs(processes)
    order = res['execution_order']
    metrics = res['metrics']

    assert len(order) == 2
    assert order[0]['job_id'] == 1
    assert order[0]['start'] == 0
    assert order[0]['end'] == 10

    assert order[1]['job_id'] == 2
    assert order[1]['start'] == 10
    assert order[1]['end'] == 15

    # Job 2 arrived at 2, waited until 10 => waiting_time = 8
    job2_metrics = next(p for p in metrics['per_job'] if p['job_id'] == 2)
    assert job2_metrics['waiting_time'] == 8
    assert job2_metrics['turnaround_time'] == 13


def test_sjf_scheduling():
    processes = [
        {'job_id': 1, 'arrival_time': 0, 'burst_time': 20, 'priority': 5},
        {'job_id': 2, 'arrival_time': 0, 'burst_time': 5, 'priority': 3},
        {'job_id': 3, 'arrival_time': 0, 'burst_time': 10, 'priority': 1},
    ]

    res = run_sjf(processes)
    order = res['execution_order']

    # Shortest first: 2 (burst 5), then 3 (burst 10), then 1 (burst 20)
    assert [step['job_id'] for step in order] == [2, 3, 1]


def test_priority_scheduling():
    processes = [
        {'job_id': 1, 'arrival_time': 0, 'burst_time': 10, 'priority': 5},
        {'job_id': 2, 'arrival_time': 0, 'burst_time': 10, 'priority': 1},  # Highest priority
        {'job_id': 3, 'arrival_time': 0, 'burst_time': 10, 'priority': 3},
    ]

    res = run_priority(processes)
    order = res['execution_order']

    # Priority order: 2 (P1), then 3 (P3), then 1 (P5)
    assert [step['job_id'] for step in order] == [2, 3, 1]


def test_round_robin_scheduling():
    processes = [
        {'job_id': 1, 'arrival_time': 0, 'burst_time': 25, 'priority': 5},
        {'job_id': 2, 'arrival_time': 0, 'burst_time': 10, 'priority': 5},
    ]

    # Quantum 10
    res = run_round_robin(processes, time_quantum=10)
    order = res['execution_order']

    # Step 1: Job 1 runs 10 (remaining: 15)
    assert order[0]['job_id'] == 1
    assert order[0]['burst'] == 10
    assert order[0]['remaining'] == 15

    # Step 2: Job 2 runs 10 (remaining: 0, finishes)
    assert order[1]['job_id'] == 2
    assert order[1]['burst'] == 10
    assert order[1]['remaining'] == 0

    # Step 3: Job 1 runs 10 (remaining: 5)
    assert order[2]['job_id'] == 1
    assert order[2]['burst'] == 10

    # Step 4: Job 1 runs 5 (remaining: 0, finishes)
    assert order[3]['job_id'] == 1
    assert order[3]['burst'] == 5
    assert order[3]['remaining'] == 0

    metrics = res['metrics']
    assert metrics['total_completion_time'] == 35
