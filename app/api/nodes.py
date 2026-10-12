"""Computing Nodes REST API."""

from flask import Blueprint, jsonify
from flask_login import login_required
from app.models import ComputingNode

nodes_bp = Blueprint('nodes_api', __name__, url_prefix='/api/nodes')


@nodes_bp.route('', methods=['GET'])
@login_required
def list_nodes():
    """List all computing nodes with their current status."""
    nodes = ComputingNode.query.order_by(ComputingNode.name).all()
    return jsonify([n.to_dict() for n in nodes])


@nodes_bp.route('/<int:node_id>', methods=['GET'])
@login_required
def get_node(node_id):
    """Get a single node's details."""
    from app.extensions import db
    node = db.session.get(ComputingNode, node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    return jsonify(node.to_dict())


@nodes_bp.route('/summary', methods=['GET'])
@login_required
def nodes_summary():
    """Aggregate resource summary across all nodes."""
    nodes = ComputingNode.query.all()
    total_cpu = sum(n.total_cpu_cores for n in nodes)
    allocated_cpu = sum(n.allocated_cpu_cores for n in nodes)
    total_mem = sum(n.total_memory_mb for n in nodes)
    allocated_mem = sum(n.allocated_memory_mb for n in nodes)

    active = sum(1 for n in nodes if n.status == 'active')
    maintenance = sum(1 for n in nodes if n.status == 'maintenance')
    offline = sum(1 for n in nodes if n.status == 'offline')

    return jsonify({
        'total_nodes': len(nodes),
        'active': active,
        'maintenance': maintenance,
        'offline': offline,
        'total_cpu_cores': total_cpu,
        'allocated_cpu_cores': allocated_cpu,
        'available_cpu_cores': total_cpu - allocated_cpu,
        'total_memory_mb': total_mem,
        'allocated_memory_mb': allocated_mem,
        'available_memory_mb': total_mem - allocated_mem,
        'cpu_utilization': round((allocated_cpu / total_cpu * 100), 1) if total_cpu else 0,
        'memory_utilization': round((allocated_mem / total_mem * 100), 1) if total_mem else 0,
    })
