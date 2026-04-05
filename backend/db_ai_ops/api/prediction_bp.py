import datetime
from datetime import timedelta
from collections import defaultdict

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, Host, Middleware, MetricHistory, Prediction

prediction_bp = Blueprint('prediction_bp', __name__)


@prediction_bp.route('/prediction/targets', methods=['GET'])
def get_prediction_targets():
    """获取可预测的目标"""
    target_type = request.args.get('type')

    targets = []
    if not target_type or target_type == 'database':
        databases = Database.query.filter_by(enabled=True).all()
        for d in databases:
            targets.append({
                'type': 'database',
                'id': d.id,
                'name': d.name,
                'db_type': d.db_type.value if d.db_type else None
            })

    if not target_type or target_type == 'host':
        hosts = Host.query.filter_by(enabled=True).all()
        for h in hosts:
            targets.append({
                'type': 'host',
                'id': h.id,
                'name': h.name
            })

    return jsonify({'targets': targets})


@prediction_bp.route('/prediction/metrics', methods=['GET'])
def get_prediction_metrics():
    """获取可预测的指标类型"""
    return jsonify({
        'metrics': [
            {'value': 'disk', 'label': '磁盘使用率', 'unit': '%', 'threshold': 80},
            {'value': 'connections', 'label': '连接数', 'unit': '个', 'threshold': 80},
            {'value': 'capacity', 'label': '数据库容量', 'unit': 'GB', 'threshold': 85}
        ]
    })


@prediction_bp.route('/prediction', methods=['GET'])
def get_predictions():
    """获取预测结果列表"""
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id', type=int)
    metric_type = request.args.get('metric_type')

    query = Prediction.query
    if target_type:
        query = query.filter_by(target_type=target_type)
    if target_id:
        query = query.filter_by(target_id=target_id)
    if metric_type:
        query = query.filter_by(metric_type=metric_type)

    predictions = query.order_by(Prediction.threshold_day.asc()).all()

    # 补充目标名称
    for p in predictions:
        p.target_name = get_target_name(p.target_type, p.target_id)

    return jsonify({
        'predictions': [p.to_dict() for p in predictions]
    })


@prediction_bp.route('/prediction', methods=['POST'])
def run_prediction():
    """运行预测分析"""
    data = request.get_json()
    target_type = data.get('target_type')  # database/host
    target_id = data.get('target_id')
    metric_type = data.get('metric_type')  # disk/connections/capacity

    if not all([target_type, target_id, metric_type]):
        return jsonify({'error': 'target_type, target_id, metric_type are required'}), 400

    # 获取历史数据（最近30天）
    since = datetime.datetime.utcnow() - timedelta(days=30)
    metrics = MetricHistory.query.filter(
        MetricHistory.target_type == target_type,
        MetricHistory.target_id == target_id,
        MetricHistory.metric_type == metric_type,
        MetricHistory.timestamp >= since
    ).order_by(MetricHistory.timestamp.asc()).all()

    # 如果没有历史数据，使用模拟数据
    if len(metrics) < 3:
        # 生成模拟历史数据用于演示
        result = generate_demo_prediction(target_type, target_id, metric_type)
        return jsonify(result)

    # 使用线性回归进行预测
    result = calculate_prediction(target_type, target_id, metric_type, metrics)
    return jsonify(result)


@prediction_bp.route('/prediction/batch', methods=['POST'])
def batch_prediction():
    """批量预测所有目标"""
    data = request.get_json()
    metric_type = data.get('metric_type', 'disk')

    results = []

    # 预测所有数据库
    databases = Database.query.filter_by(enabled=True).all()
    for db_obj in databases:
        try:
            since = datetime.datetime.utcnow() - timedelta(days=30)
            metrics = MetricHistory.query.filter(
                MetricHistory.target_type == 'database',
                MetricHistory.target_id == db_obj.id,
                MetricHistory.metric_type == metric_type,
                MetricHistory.timestamp >= since
            ).order_by(MetricHistory.timestamp.asc()).all()

            if metrics:
                result = calculate_prediction('database', db_obj.id, metric_type, metrics)
                results.append(result)
            else:
                result = generate_demo_prediction('database', db_obj.id, metric_type)
                results.append(result)
        except Exception:
            pass

    return jsonify({'predictions': results})


def get_target_name(target_type, target_id):
    """获取目标名称"""
    if target_type == 'database':
        obj = Database.query.get(target_id)
        return obj.name if obj else str(target_id)
    elif target_type == 'host':
        obj = Host.query.get(target_id)
        return obj.name if obj else str(target_id)
    return str(target_id)


def calculate_prediction(target_type, target_id, metric_type, metrics):
    """使用线性回归计算预测"""
    # 准备数据点
    points = [(m.timestamp.timestamp(), m.value) for m in metrics]
    if len(points) < 2:
        return generate_demo_prediction(target_type, target_id, metric_type)

    # 简单线性回归
    n = len(points)
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_xx = sum(p[0] * p[0] for p in points)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    intercept = (sum_y - slope * sum_x) / n

    # 预测7天后的值
    future_time = (datetime.datetime.utcnow() + timedelta(days=7)).timestamp()
    predicted_value = slope * future_time + intercept

    # 获取阈值
    thresholds = {'disk': 80, 'connections': 80, 'capacity': 85}
    threshold = thresholds.get(metric_type, 80)

    # 计算到达阈值的天数
    if slope > 0:
        days_to_threshold = (threshold - intercept) / slope / 86400
        days_to_threshold -= (datetime.datetime.utcnow().timestamp())
        days_to_threshold = days_to_threshold / 86400
    else:
        days_to_threshold = 999  # 不会到达阈值

    # 置信度（基于数据点数量和数据分布）
    confidence = min(0.95, 0.5 + len(metrics) * 0.02)

    # 保存预测结果
    prediction = Prediction(
        target_type=target_type,
        target_id=target_id,
        metric_type=metric_type,
        predicted_value=round(predicted_value, 2),
        predicted_at=datetime.datetime.utcnow() + timedelta(days=7),
        threshold_value=threshold,
        threshold_day=int(days_to_threshold) if days_to_threshold > 0 else 0,
        confidence=round(confidence, 2)
    )
    db.session.add(prediction)
    db.session.commit()

    target_name = get_target_name(target_type, target_id)

    return {
        'target_type': target_type,
        'target_id': target_id,
        'target_name': target_name,
        'metric_type': metric_type,
        'current_value': round(metrics[-1].value, 2) if metrics else 0,
        'predicted_value': round(predicted_value, 2),
        'threshold': threshold,
        'days_to_threshold': int(days_to_threshold) if days_to_threshold > 0 else 0,
        'confidence': round(confidence, 2),
        'trend': 'up' if slope > 0 else 'down',
        'prediction_date': (datetime.datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
    }


def generate_demo_prediction(target_type, target_id, metric_type):
    """生成演示预测数据"""
    thresholds = {'disk': 80, 'connections': 80, 'capacity': 85}
    threshold = thresholds.get(metric_type, 80)

    # 模拟当前值和预测
    current_values = {'disk': 65, 'connections': 45, 'capacity': 50}
    current = current_values.get(metric_type, 50)
    predicted = current + 5 + (hash(str(target_id)) % 10)

    days_to_threshold = max(1, int((threshold - current) / 2))

    target_name = get_target_name(target_type, target_id)

    # 保存预测
    prediction = Prediction(
        target_type=target_type,
        target_id=target_id,
        metric_type=metric_type,
        predicted_value=predicted,
        predicted_at=datetime.datetime.utcnow() + timedelta(days=7),
        threshold_value=threshold,
        threshold_day=days_to_threshold,
        confidence=0.65
    )
    db.session.add(prediction)
    db.session.commit()

    return {
        'target_type': target_type,
        'target_id': target_id,
        'target_name': target_name,
        'metric_type': metric_type,
        'current_value': current,
        'predicted_value': predicted,
        'threshold': threshold,
        'days_to_threshold': days_to_threshold,
        'confidence': 0.65,
        'trend': 'up',
        'prediction_date': (datetime.datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d'),
        'demo': True
    }


@prediction_bp.route('/prediction/<int:pred_id>', methods=['DELETE'])
def delete_prediction(pred_id):
    """删除预测记录"""
    pred = Prediction.query.get_or_404(pred_id)
    db.session.delete(pred)
    db.session.commit()
    return jsonify({'message': 'Deleted'})