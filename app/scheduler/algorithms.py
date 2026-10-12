"""OS CPU Scheduling Algorithm Simulator.

Implements FCFS, SJF, Priority, and Round Robin scheduling algorithms
for *simulation and comparison* purposes.

IMPORTANT DISTINCTION:
  These algorithms simulate theoretical CPU scheduling to compute
  waiting time, turnaround time, and execution order. They do NOT
  control actual Docker container execution — that is handled by
  the worker service using real process management.

Each algorithm accepts a list of process dicts:
  {
      'job_id': int,
      'arrival_time': int,
      'burst_time': int,
      'priority': int,   # 1 = highest priority
  }

Each returns:
  {
      'execution_order': list of step dicts,
      'metrics': {
          'avg_waiting_time': float,
          'avg_turnaround_time': float,
          'total_completion_time': int,
          'per_job': list of per-job metric dicts,
      }
  }
"""

from copy import deepcopy


def run_fcfs(processes, **kwargs):
    """First Come First Served — non-preemptive, ordered by arrival time."""
    procs = sorted(deepcopy(processes), key=lambda p: p['arrival_time'])
    current_time = 0
    execution_order = []
    per_job = []

    for proc in procs:
        start = max(current_time, proc['arrival_time'])
        end = start + proc['burst_time']
        waiting = start - proc['arrival_time']
        turnaround = end - proc['arrival_time']

        execution_order.append({
            'job_id': proc['job_id'],
            'start': start,
            'end': end,
            'burst': proc['burst_time'],
        })
        per_job.append({
            'job_id': proc['job_id'],
            'waiting_time': waiting,
            'turnaround_time': turnaround,
            'completion_time': end,
        })
        current_time = end

    return _build_result(execution_order, per_job)


def run_sjf(processes, **kwargs):
    """Shortest Job First — non-preemptive."""
    procs = deepcopy(processes)
    n = len(procs)
    completed = [False] * n
    current_time = 0
    execution_order = []
    per_job = []
    done = 0

    while done < n:
        # Find eligible processes (arrived and not completed)
        eligible = [
            (i, p) for i, p in enumerate(procs)
            if not completed[i] and p['arrival_time'] <= current_time
        ]

        if not eligible:
            # Advance time to next arrival
            future = [p['arrival_time'] for i, p in enumerate(procs) if not completed[i]]
            current_time = min(future)
            continue

        # Pick the one with shortest burst
        eligible.sort(key=lambda x: (x[1]['burst_time'], x[1]['arrival_time']))
        idx, proc = eligible[0]

        start = current_time
        end = start + proc['burst_time']
        waiting = start - proc['arrival_time']
        turnaround = end - proc['arrival_time']

        execution_order.append({
            'job_id': proc['job_id'],
            'start': start,
            'end': end,
            'burst': proc['burst_time'],
        })
        per_job.append({
            'job_id': proc['job_id'],
            'waiting_time': waiting,
            'turnaround_time': turnaround,
            'completion_time': end,
        })

        completed[idx] = True
        current_time = end
        done += 1

    return _build_result(execution_order, per_job)


def run_priority(processes, **kwargs):
    """Priority Scheduling — non-preemptive, lower number = higher priority."""
    procs = deepcopy(processes)
    n = len(procs)
    completed = [False] * n
    current_time = 0
    execution_order = []
    per_job = []
    done = 0

    while done < n:
        eligible = [
            (i, p) for i, p in enumerate(procs)
            if not completed[i] and p['arrival_time'] <= current_time
        ]

        if not eligible:
            future = [p['arrival_time'] for i, p in enumerate(procs) if not completed[i]]
            current_time = min(future)
            continue

        # Lower priority number = higher priority; tie-break by arrival
        eligible.sort(key=lambda x: (x[1]['priority'], x[1]['arrival_time']))
        idx, proc = eligible[0]

        start = current_time
        end = start + proc['burst_time']
        waiting = start - proc['arrival_time']
        turnaround = end - proc['arrival_time']

        execution_order.append({
            'job_id': proc['job_id'],
            'start': start,
            'end': end,
            'burst': proc['burst_time'],
        })
        per_job.append({
            'job_id': proc['job_id'],
            'waiting_time': waiting,
            'turnaround_time': turnaround,
            'completion_time': end,
        })

        completed[idx] = True
        current_time = end
        done += 1

    return _build_result(execution_order, per_job)


def run_round_robin(processes, time_quantum=100, **kwargs):
    """Round Robin — preemptive with configurable time quantum.

    Maintains a ready queue. Processes execute for at most `time_quantum`
    units before being preempted and moved to the back of the queue.
    """
    procs = deepcopy(processes)
    procs.sort(key=lambda p: p['arrival_time'])
    n = len(procs)

    remaining = {p['job_id']: p['burst_time'] for p in procs}
    arrival = {p['job_id']: p['arrival_time'] for p in procs}

    current_time = 0
    execution_order = []
    completion = {}
    ready_queue = []
    arrived = set()
    idx = 0  # pointer into sorted procs

    # Enqueue processes arriving at time 0
    while idx < n and procs[idx]['arrival_time'] <= current_time:
        ready_queue.append(procs[idx]['job_id'])
        arrived.add(procs[idx]['job_id'])
        idx += 1

    while ready_queue or idx < n:
        if not ready_queue:
            # Jump to next arrival
            current_time = procs[idx]['arrival_time']
            while idx < n and procs[idx]['arrival_time'] <= current_time:
                if procs[idx]['job_id'] not in arrived:
                    ready_queue.append(procs[idx]['job_id'])
                    arrived.add(procs[idx]['job_id'])
                idx += 1
            continue

        job_id = ready_queue.pop(0)
        exec_time = min(time_quantum, remaining[job_id])
        start = current_time
        current_time += exec_time
        remaining[job_id] -= exec_time

        execution_order.append({
            'job_id': job_id,
            'start': start,
            'end': current_time,
            'burst': exec_time,
            'remaining': remaining[job_id],
        })

        # Check for new arrivals during this quantum
        while idx < n and procs[idx]['arrival_time'] <= current_time:
            if procs[idx]['job_id'] not in arrived:
                ready_queue.append(procs[idx]['job_id'])
                arrived.add(procs[idx]['job_id'])
            idx += 1

        if remaining[job_id] > 0:
            # Preempted — re-enqueue at the back
            ready_queue.append(job_id)
        else:
            # Completed
            completion[job_id] = current_time

    # Compute per-job metrics
    per_job = []
    for p in procs:
        jid = p['job_id']
        ct = completion.get(jid, current_time)
        tat = ct - arrival[jid]
        wt = tat - p['burst_time']
        per_job.append({
            'job_id': jid,
            'waiting_time': max(0, wt),
            'turnaround_time': tat,
            'completion_time': ct,
        })

    return _build_result(execution_order, per_job)


def _build_result(execution_order, per_job):
    """Assemble the standard result dict."""
    n = len(per_job)
    avg_wt = sum(p['waiting_time'] for p in per_job) / n if n else 0
    avg_tat = sum(p['turnaround_time'] for p in per_job) / n if n else 0
    total_ct = max((p['completion_time'] for p in per_job), default=0)

    return {
        'execution_order': execution_order,
        'metrics': {
            'avg_waiting_time': round(avg_wt, 2),
            'avg_turnaround_time': round(avg_tat, 2),
            'total_completion_time': total_ct,
            'per_job': per_job,
        },
    }
