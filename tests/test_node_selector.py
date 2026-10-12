"""Unit tests for resource-aware Node Selector and release mechanisms."""

from app.models import ComputingNode
from app.scheduler.node_selector import select_node, release_node_resources
from app.extensions import db


def test_select_node_best_fit(app):
    with app.app_context():
        # Clean nodes and insert known sizes
        ComputingNode.query.delete()
        n1 = ComputingNode(name='small-node', total_cpu_cores=2, total_memory_mb=1024, status='active')
        n2 = ComputingNode(name='large-node', total_cpu_cores=8, total_memory_mb=8192, status='active')
        db.session.add_all([n1, n2])
        db.session.commit()

        # Request 1 CPU, 512 MB. Best fit should choose n1 (small-node)
        chosen = select_node(1, 512)
        assert chosen is not None
        assert chosen.name == 'small-node'
        assert chosen.allocated_cpu_cores == 1
        assert chosen.allocated_memory_mb == 512
        db.session.commit()

        # Request 4 CPU, 2048 MB. Only large-node can fit
        chosen2 = select_node(4, 2048)
        assert chosen2 is not None
        assert chosen2.name == 'large-node'
        assert chosen2.allocated_cpu_cores == 4
        db.session.commit()


def test_select_node_insufficient_capacity(app):
    with app.app_context():
        # Request more CPU than any single node has
        chosen = select_node(64, 1024)
        assert chosen is None


def test_release_node_resources(app):
    with app.app_context():
        node = ComputingNode.query.filter_by(status='active').first()
        initial_alloc = node.allocated_cpu_cores
        initial_mem = node.allocated_memory_mb

        # Allocate
        node.allocated_cpu_cores += 2
        node.allocated_memory_mb += 512
        db.session.commit()

        # Release
        release_node_resources(node.id, 2, 512)
        db.session.commit()

        updated = db.session.get(ComputingNode, node.id)
        assert updated.allocated_cpu_cores == initial_alloc
        assert updated.allocated_memory_mb == initial_mem
