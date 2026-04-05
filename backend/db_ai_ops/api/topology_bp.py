from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, Host, Middleware

topology_bp = Blueprint('topology_bp', __name__)


@topology_bp.route('/topology', methods=['GET'])
def get_topology():
    """获取完整拓扑图数据"""
    system_id = request.args.get('system_id', type=int)

    # 查询所有主机（作为核心节点）
    host_query = Host.query.filter_by(enabled=True)
    if system_id:
        host_query = host_query.filter_by(business_system_id=system_id)
    hosts = host_query.all()

    # 查询所有数据库
    db_query = Database.query.filter_by(enabled=True)
    if system_id:
        db_query = db_query.filter_by(business_system_id=system_id)
    databases = db_query.all()

    # 查询所有中间件
    mw_query = Middleware.query.filter_by(enabled=True)
    if system_id:
        mw_query = mw_query.filter_by(business_system_id=system_id)
    middlewares = mw_query.all()

    # 构建节点
    nodes = []

    # 添加主机节点
    for h in hosts:
        nodes.append({
            'id': f'host_{h.id}',
            'type': 'host',
            'name': h.name,
            'host': h.host,
            'os_type': h.os_type.value if h.os_type else 'linux',
            'idc': h.idc,
            'business_system': h.business_system.name if h.business_system else None,
            'icon': 'Monitor'
        })

    # 添加数据库节点
    for d in databases:
        nodes.append({
            'id': f'db_{d.id}',
            'type': 'database',
            'name': d.name,
            'host': d.host,
            'db_type': d.db_type.value,
            'business_system': d.business_system.name if d.business_system else None,
            'icon': 'Grid'
        })

    # 添加中间件节点
    for m in middlewares:
        nodes.append({
            'id': f'mw_{m.id}',
            'type': 'middleware',
            'name': m.name,
            'host': m.host,
            'mw_type': m.mw_type.value if m.mw_type else 'other',
            'business_system': m.business_system.name if m.business_system else None,
            'icon': 'Connection'
        })

    # 构建边（根据host字段匹配）
    edges = []
    host_ips = {h.host: f'host_{h.id}' for h in hosts}

    for d in databases:
        if d.host in host_ips:
            edges.append({
                'source': host_ips[d.host],
                'target': f'db_{d.id}',
                'label': 'contains'
            })

    for m in middlewares:
        if m.host in host_ips:
            edges.append({
                'source': host_ips[m.host],
                'target': f'mw_{m.id}',
                'label': 'contains'
            })

    return jsonify({
        'nodes': nodes,
        'edges': edges
    })


@topology_bp.route('/topology/by-system/<int:system_id>', methods=['GET'])
def get_topology_by_system(system_id):
    """按业务系统获取拓扑图"""
    return get_topology()


@topology_bp.route('/topology/node/<node_type>/<int:node_id>', methods=['GET'])
def get_node_detail(node_type, node_id):
    """获取节点详情"""
    if node_type == 'host':
        node = Host.query.get(node_id)
        if node:
            return jsonify({
                'id': node.id,
                'name': node.name,
                'type': 'host',
                'host': node.host,
                'port': node.port,
                'os_type': node.os_type.value if node.os_type else None,
                'hostname': node.hostname,
                'os_version': node.os_version,
                'idc': node.idc,
                'owner': node.owner,
                'env': node.env,
                'remark': node.remark,
                'business_system': node.business_system.name if node.business_system else None
            })
    elif node_type == 'database':
        node = Database.query.get(node_id)
        if node:
            return jsonify({
                'id': node.id,
                'name': node.name,
                'type': 'database',
                'host': node.host,
                'port': node.port,
                'db_type': node.db_type.value,
                'version': node.version,
                'owner': node.env,
                'env': node.env,
                'remark': node.remark,
                'business_system': node.business_system.name if node.business_system else None
            })
    elif node_type == 'middleware':
        node = Middleware.query.get(node_id)
        if node:
            return jsonify({
                'id': node.id,
                'name': node.name,
                'type': 'middleware',
                'host': node.host,
                'port': node.port,
                'mw_type': node.mw_type.value if node.mw_type else None,
                'version': node.version,
                'owner': node.owner,
                'env': node.env,
                'remark': node.remark,
                'business_system': node.business_system.name if node.business_system else None
            })

    return jsonify({'error': 'Node not found'}), 404