"""Resource estimation engine.

Uses database-driven rules from WorkloadType to estimate CPU, memory,
and execution time based on input parameters and scaling factors.
"""

import math


def estimate_resources(workload_type, input_params):
    """Estimate resource requirements for a job.

    Args:
        workload_type: WorkloadType model instance with base estimates and scale factors.
        input_params: dict of user-supplied job parameters.

    Returns:
        dict with keys: cpu_cores, memory_mb, time_seconds
    """
    base_cpu = workload_type.est_cpu_cores
    base_mem = workload_type.est_memory_mb
    base_time = workload_type.est_time_seconds
    cpu_sf = workload_type.cpu_scale_factor or 1.0
    mem_sf = workload_type.memory_scale_factor or 1.0
    time_sf = workload_type.time_scale_factor or 1.0

    # Determine a normalized "input size" factor from the params
    size_factor = _compute_size_factor(workload_type.name, input_params)

    est_cpu = max(1, math.ceil(base_cpu * cpu_sf * size_factor))
    est_mem = max(64, math.ceil(base_mem * mem_sf * size_factor))
    est_time = max(5, math.ceil(base_time * time_sf * size_factor))

    return {
        'cpu_cores': est_cpu,
        'memory_mb': est_mem,
        'time_seconds': est_time,
    }


def _compute_size_factor(workload_name, params):
    """Compute a scale multiplier based on workload-specific parameters.

    Returns a float >= 1.0 that represents how much larger the job is
    compared to the baseline defined in the workload type.
    """
    if workload_name == 'Image Processing':
        size = params.get('size', 512)
        # Baseline is 512×512; scale quadratically with image dimension
        return max(1.0, (size / 512) ** 2)

    elif workload_name == 'Data Analysis':
        rows = params.get('rows', 1000)
        # Baseline is 1000 rows; scale linearly
        return max(1.0, rows / 1000)

    elif workload_name == 'File Processing':
        size_kb = params.get('size_kb', 100)
        # Baseline is 100 KB; scale linearly
        return max(1.0, size_kb / 100)

    elif workload_name == 'Video Conversion':
        duration = params.get('duration_seconds', 5)
        # Baseline is 5 seconds; scale linearly
        return max(1.0, duration / 5)

    return 1.0
