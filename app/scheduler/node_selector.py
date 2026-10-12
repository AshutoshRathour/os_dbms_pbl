"""Node selection with resource-aware scheduling and row-level locking.

Selects a computing node that has sufficient available capacity for the
requested CPU and memory. Uses SELECT ... FOR UPDATE to prevent
concurrent over-allocation.
"""

from sqlalchemy import text
from app.extensions import db
from app.models import ComputingNode


def select_node(cpu_cores, memory_mb):
    """Find and atomically allocate resources on a suitable node.

    Uses a best-fit strategy: picks the active node with the smallest
    available resources that still satisfies the request, reducing
    fragmentation.

    Args:
        cpu_cores: Required CPU cores.
        memory_mb: Required memory in MB.

    Returns:
        ComputingNode instance with resources already allocated, or None.
    """
    # Row-level lock on active nodes to prevent concurrent over-allocation
    nodes = (
        ComputingNode.query
        .filter_by(status='active')
        .with_for_update()
        .all()
    )

    # Filter nodes with sufficient capacity
    eligible = [
        n for n in nodes
        if n.has_capacity(cpu_cores, memory_mb)
    ]

    if not eligible:
        return None

    # Best-fit: sort by smallest remaining capacity after allocation
    eligible.sort(key=lambda n: (n.available_cpu - cpu_cores) + (n.available_memory - memory_mb))

    chosen = eligible[0]
    chosen.allocated_cpu_cores += cpu_cores
    chosen.allocated_memory_mb += memory_mb

    # Do NOT commit here — the caller manages the transaction
    return chosen


def release_node_resources(node_id, cpu_cores, memory_mb):
    """Release allocated resources back to a node.

    Args:
        node_id: ComputingNode ID.
        cpu_cores: CPU cores to release.
        memory_mb: Memory MB to release.
    """
    node = (
        ComputingNode.query
        .filter_by(id=node_id)
        .with_for_update()
        .first()
    )
    if node:
        node.allocated_cpu_cores = max(0, node.allocated_cpu_cores - cpu_cores)
        node.allocated_memory_mb = max(0, node.allocated_memory_mb - memory_mb)
    # Caller commits the transaction
