"""Unit tests for the Resource Estimation engine."""

from app.models import WorkloadType
from app.scheduler.estimator import estimate_resources


def test_estimate_image_processing(app):
    wt = WorkloadType(
        name='Image Processing',
        docker_image='cloud-workload-image',
        command_template='dummy',
        est_cpu_cores=1,
        est_memory_mb=256,
        est_time_seconds=30,
        cpu_scale_factor=1.0,
        memory_scale_factor=1.5,
        time_scale_factor=1.2,
    )

    # Base size 512
    est_base = estimate_resources(wt, {'size': 512, 'operation': 'blur'})
    assert est_base['cpu_cores'] >= 1
    assert est_base['memory_mb'] == int(256 * 1.5)  # 384 MB
    assert est_base['time_seconds'] == int(30 * 1.2)  # 36s

    # Scaled size 1024 (size_factor = 4)
    est_scaled = estimate_resources(wt, {'size': 1024, 'operation': 'blur'})
    assert est_scaled['cpu_cores'] == 4
    assert est_scaled['memory_mb'] > est_base['memory_mb']
    assert est_scaled['time_seconds'] > est_base['time_seconds']


def test_estimate_data_analysis(app):
    wt = WorkloadType(
        name='Data Analysis',
        docker_image='cloud-workload-data',
        command_template='dummy',
        est_cpu_cores=1,
        est_memory_mb=128,
        est_time_seconds=15,
        cpu_scale_factor=1.0,
        memory_scale_factor=2.0,
        time_scale_factor=1.0,
    )

    # 1000 rows (baseline)
    est_base = estimate_resources(wt, {'rows': 1000})
    assert est_base['memory_mb'] == 256  # 128 * 2.0
    assert est_base['time_seconds'] == 15

    # 5000 rows (factor = 5)
    est_large = estimate_resources(wt, {'rows': 5000})
    assert est_large['cpu_cores'] == 5
    assert est_large['memory_mb'] == 1280  # 128 * 2.0 * 5
    assert est_large['time_seconds'] == 75  # 15 * 5


def test_estimate_file_processing(app):
    wt = WorkloadType(
        name='File Processing',
        docker_image='cloud-workload-file',
        command_template='dummy',
        est_cpu_cores=1,
        est_memory_mb=128,
        est_time_seconds=10,
        cpu_scale_factor=0.5,
        memory_scale_factor=1.0,
        time_scale_factor=0.8,
    )

    est = estimate_resources(wt, {'size_kb': 200})
    assert est['cpu_cores'] >= 1
    assert est['memory_mb'] == 256
    assert est['time_seconds'] == 16
