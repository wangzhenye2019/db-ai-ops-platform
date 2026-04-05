from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, Host, Middleware, MetricHistory, MetricType

metrics_bp = Blueprint('metrics_bp', __name__)


@metrics_bp.route('/metrics/types', methods=['GET'])
def get_metric_types():
    """获取支持的指标类型"""
    return jsonify({
        'types': [
            {'value': 'cpu', 'label': 'CPU使用率', 'unit': '%'},
            {'value': 'memory', 'label': '内存使用率', 'unit': '%'},
            {'value': 'disk', 'label': '磁盘使用率', 'unit': '%'},
            {'value': 'connections', 'label': '连接数', 'unit': '个'},
            {'value': 'qps', 'label': 'QPS', 'unit': '次/秒'},
            {'value': 'tps', 'label': 'TPS', 'unit': '次/秒'},
            {'value': 'slow_queries', 'label': '慢查询数', 'unit': '个'},
            {'value': 'threads', 'label': '线程数', 'unit': '个'}
        ]
    })


@metrics_bp.route('/metrics/targets', methods=['GET'])
def get_metric_targets():
    """获取可监控的目标列表"""
    target_type = request.args.get('type')

    targets = []
    if not target_type or target_type == 'host':
        hosts = Host.query.filter_by(enabled=True).all()
        for h in hosts:
            targets.append({
                'type': 'host',
                'id': h.id,
                'name': h.name,
                'host': h.host
            })

    if not target_type or target_type == 'database':
        databases = Database.query.filter_by(enabled=True).all()
        for d in databases:
            targets.append({
                'type': 'database',
                'id': d.id,
                'name': d.name,
                'host': d.host
            })

    if not target_type or target_type == 'middleware':
        middlewares = Middleware.query.filter_by(enabled=True).all()
        for m in middlewares:
            targets.append({
                'type': 'middleware',
                'id': m.id,
                'name': m.name,
                'host': m.host
            })

    return jsonify({'targets': targets})


@metrics_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """获取指标数据"""
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id', type=int)
    metric_type = request.args.get('metric_type')
    time_range = request.args.get('time_range', '24h')  # 1h, 6h, 24h, 7d, 30d

    # Parse time range
    now = datetime.utcnow()
    if time_range == '1h':
        since = now - timedelta(hours=1)
    elif time_range == '6h':
        since = now - timedelta(hours=6)
    elif time_range == '24h':
        since = now - timedelta(hours=24)
    elif time_range == '7d':
        since = now - timedelta(days=7)
    elif time_range == '30d':
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(hours=24)

    # Build query
    query = MetricHistory.query.filter(MetricHistory.timestamp >= since)
    if target_type:
        query = query.filter_by(target_type=target_type)
    if target_id:
        query = query.filter_by(target_id=target_id)
    if metric_type:
        query = query.filter_by(metric_type=metric_type)

    metrics = query.order_by(MetricHistory.timestamp.asc()).all()

    # Generate demo data if no real data
    if not metrics:
        return jsonify({
            'metrics': generate_demo_data(target_type, target_id, metric_type, since, now)
        })

    return jsonify({
        'metrics': [m.to_dict() for m in metrics]
    })


@metrics_bp.route('/metrics/latest', methods=['GET'])
def get_latest_metrics():
    """获取最新指标值"""
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id', type=int)

    query = db.session.query(
        MetricHistory.metric_type,
        db.func.max(MetricHistory.timestamp).label('timestamp'),
        MetricHistory.value,
        MetricHistory.unit
    ).group_by(MetricHistory.metric_type, MetricHistory.value, MetricHistory.unit)

    if target_type:
        query = query.filter(MetricHistory.target_type == target_type)
    if target_id:
        query = query.filter(MetricHistory.target_id == target_id)

    results = query.all()

    if not results:
        # Return demo data
        return jsonify({
            'metrics': [
                {'metric_type': 'cpu', 'value': 45.2, 'unit': '%', 'timestamp': datetime.utcnow().isoformat()},
                {'metric_type': 'memory', 'value': 62.8, 'unit': '%', 'timestamp': datetime.utcnow().isoformat()},
                {'metric_type': 'disk', 'value': 35.5, 'unit': '%', 'timestamp': datetime.utcnow().isoformat()},
                {'metric_type': 'connections', 'value': 128, 'unit': '个', 'timestamp': datetime.utcnow().isoformat()},
                {'metric_type': 'qps', 'value': 1500, 'unit': '次/秒', 'timestamp': datetime.utcnow().isoformat()},
                {'metric_type': 'tps', 'value': 320, 'unit': '次/秒', 'timestamp': datetime.utcnow().isoformat()}
            ]
        })

    return jsonify({
        'metrics': [
            {
                'metric_type': r.metric_type,
                'value': r.value,
                'unit': r.unit,
                'timestamp': r.timestamp.isoformat()
            }
            for r in results
        ]
    })


@metrics_bp.route('/metrics', methods=['POST'])
def record_metric():
    """记录指标数据"""
    data = request.get_json()
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    metric_type = data.get('metric_type')
    value = data.get('value')
    unit = data.get('unit')

    if not all([target_type, target_id, metric_type, value is not None]):
        return jsonify({'error': 'Missing required fields'}), 400

    metric = MetricHistory(
        target_type=target_type,
        target_id=target_id,
        metric_type=metric_type,
        value=float(value),
        unit=unit
    )
    db.session.add(metric)
    db.session.commit()

    return jsonify({'message': 'Metric recorded', 'id': metric.id}), 201


def generate_demo_data(target_type, target_id, metric_type, since, now):
    """生成演示数据"""
    import random
    data = []

    # Determine which metrics to show
    metrics_to_show = [metric_type] if metric_type else ['cpu', 'memory', 'connections', 'qps']

    for metric in metrics_to_show:
        # Generate 24 points over the time range
        num_points = 24
        delta = (now - since) / num_points

        base_values = {
            'cpu': 40,
            'memory': 55,
            'disk': 30,
            'connections': 100,
            'qps': 1200,
            'tps': 250,
            'slow_queries': 5,
            'threads': 50
        }

        base = base_values.get(metric, 50)

        for i in range(num_points):
            # Add some variation
            variation = random.uniform(-10, 10)
            value = max(0, base + variation)

            data.append({
                'target_type': target_type or 'database',
                'target_id': target_id or 1,
                'metric_type': metric,
                'value': round(value, 2),
                'unit': get_unit(metric),
                'timestamp': (since + delta * i).isoformat()
            })

    return data


def get_unit(metric_type):
    units = {
        'cpu': '%',
        'memory': '%',
        'disk': '%',
        'connections': '个',
        'qps': '次/秒',
        'tps': '次/秒',
        'slow_queries': '个',
        'threads': '个'
    }
    return units.get(metric_type, '')