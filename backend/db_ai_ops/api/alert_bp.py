"""
告警管理 API
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from ..models import AlertRule, AlertChannel, AlertHistory, AlertLevel, AlertStatus
from ..models import db
from ..tasks.alert_check import check_alerts_task

alert_bp = Blueprint('alert', __name__, url_prefix='/alerts')


def get_current_user_id():
    """获取当前用户ID，默认为1（管理员）"""
    try:
        return getattr(g, 'user', None) and g.user.id or 1
    except:
        return 1


def api_success(data=None, message='success'):
    """统一成功响应"""
    resp = {'success': True, 'message': message}
    if data:
        resp['data'] = data
    return jsonify(resp)


def api_error(message, code=400):
    """统一错误响应"""
    return jsonify({'success': False, 'message': message}), code


# ============ 告警规则管理 ============

@alert_bp.route('/rules', methods=['GET'])
def list_rules():
    """获取告警规则列表"""
    target_type = request.args.get('target_type')
    enabled = request.args.get('enabled')

    query = AlertRule.query

    if target_type:
        query = query.filter_by(target_type=target_type)
    if enabled is not None:
        query = query.filter_by(enabled=enabled == 'true')

    rules = query.order_by(AlertRule.created_at.desc()).all()
    return api_success({'rules': [r.to_dict() for r in rules]})


@alert_bp.route('/rules', methods=['POST'])

def create_rule():
    """创建告警规则"""
    data = request.get_json()

    # 验证必填字段
    required = ['name', 'target_type', 'metric', 'operator', 'threshold']
    for field in required:
        if not data.get(field):
            return api_error(f'缺少必填字段: {field}')

    # 验证运算符
    if data['operator'] not in ['>', '<', '>=', '<=', '==', '!=']:
        return api_error('无效的运算符')

    rule = AlertRule(
        name=data['name'],
        enabled=data.get('enabled', True),
        target_type=data['target_type'],
        target_id=data.get('target_id'),
        metric=data['metric'],
        aggregator=data.get('aggregator', 'avg'),
        period_seconds=data.get('period_seconds', 300),
        operator=data['operator'],
        threshold=float(data['threshold']),
        consecutive_count=data.get('consecutive_count', 1),
        level=data.get('level', AlertLevel.P2),
        channel_ids=data.get('channel_ids', []),
        notify_on_resolve=data.get('notify_on_resolve', True),
        suppression_duration=data.get('suppression_duration', 300),
        created_by=1  # 默认管理员
    )

    db.session.add(rule)
    db.session.commit()

    return api_success({'rule': rule.to_dict()}, '创建成功')


@alert_bp.route('/rules/<int:id>', methods=['GET'])

def get_rule(id):
    """获取告警规则详情"""
    rule = AlertRule.query.get_or_404(id)
    return api_success({'rule': rule.to_dict()})


@alert_bp.route('/rules/<int:id>', methods=['PUT'])

def update_rule(id):
    """更新告警规则"""
    rule = AlertRule.query.get_or_404(id)
    data = request.get_json()

    updatable_fields = [
        'name', 'enabled', 'target_type', 'target_id', 'metric',
        'aggregator', 'period_seconds', 'operator', 'threshold',
        'consecutive_count', 'level', 'channel_ids', 'notify_on_resolve',
        'suppression_duration'
    ]

    for field in updatable_fields:
        if field in data:
            if field == 'threshold':
                setattr(rule, field, float(data[field]))
            else:
                setattr(rule, field, data[field])

    rule.updated_at = datetime.utcnow()
    db.session.commit()

    return api_success({'rule': rule.to_dict()}, '更新成功')


@alert_bp.route('/rules/<int:id>', methods=['DELETE'])

def delete_rule(id):
    """删除告警规则"""
    rule = AlertRule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return api_success(message='删除成功')


@alert_bp.route('/rules/<int:id>/toggle', methods=['POST'])

def toggle_rule(id):
    """启用/禁用告警规则"""
    rule = AlertRule.query.get_or_404(id)
    rule.enabled = not rule.enabled
    rule.updated_at = datetime.utcnow()
    db.session.commit()
    return api_success({'enabled': rule.enabled}, '操作成功')


# ============ 通知渠道管理 ============

@alert_bp.route('/channels', methods=['GET'])

def list_channels():
    """获取通知渠道列表"""
    channels = AlertChannel.query.order_by(AlertChannel.created_at.desc()).all()
    return api_success({'channels': [c.to_dict() for c in channels]})


@alert_bp.route('/channels', methods=['POST'])

def create_channel():
    """创建通知渠道"""
    data = request.get_json()

    if not data.get('name') or not data.get('channel_type'):
        return api_error('名称和类型不能为空')

    if data['channel_type'] not in ['webhook', 'email', 'wechat', 'dingtalk', 'feishu']:
        return api_error('无效的通知渠道类型')

    channel = AlertChannel(
        name=data['name'],
        channel_type=data['channel_type'],
        enabled=data.get('enabled', True),
        config=data.get('config', {})
    )

    db.session.add(channel)
    db.session.commit()

    return api_success({'channel': channel.to_dict()}, '创建成功')


@alert_bp.route('/channels/<int:id>', methods=['GET'])

def get_channel(id):
    """获取通知渠道详情"""
    channel = AlertChannel.query.get_or_404(id)
    return api_success({'channel': channel.to_dict()})


@alert_bp.route('/channels/<int:id>', methods=['PUT'])

def update_channel(id):
    """更新通知渠道"""
    channel = AlertChannel.query.get_or_404(id)
    data = request.get_json()

    if 'name' in data:
        channel.name = data['name']
    if 'enabled' in data:
        channel.enabled = data['enabled']
    if 'config' in data:
        channel.config = data['config']

    channel.updated_at = datetime.utcnow()
    db.session.commit()

    return api_success({'channel': channel.to_dict()}, '更新成功')


@alert_bp.route('/channels/<int:id>', methods=['DELETE'])

def delete_channel(id):
    """删除通知渠道"""
    channel = AlertChannel.query.get_or_404(id)
    db.session.delete(channel)
    db.session.commit()
    return api_success(message='删除成功')


@alert_bp.route('/channels/<int:id>/test', methods=['POST'])

def test_channel(id):
    """测试通知渠道"""
    from ..utils.notification import send_test_notification

    channel = AlertChannel.query.get_or_404(id)
    success, error = send_test_notification(channel.to_dict_with_secret())

    if success:
        return api_success(message='测试消息发送成功')
    else:
        return api_error(f'发送失败: {error}')


# ============ 告警历史管理 ============

@alert_bp.route('/history', methods=['GET'])

def list_history():
    """获取告警历史"""
    status = request.args.get('status')
    level = request.args.get('level')
    target_type = request.args.get('target_type')
    rule_id = request.args.get('rule_id', type=int)
    hours = request.args.get('hours', type=int, default=24)

    query = AlertHistory.query

    if status:
        query = query.filter_by(status=status)
    if level:
        query = query.filter_by(level=level)
    if target_type:
        query = query.filter_by(target_type=target_type)
    if rule_id:
        query = query.filter_by(rule_id=rule_id)
    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(AlertHistory.triggered_at >= since)

    alerts = query.order_by(AlertHistory.triggered_at.desc()).limit(500).all()
    return api_success({'alerts': [a.to_dict() for a in alerts]})


@alert_bp.route('/history/stats', methods=['GET'])

def history_stats():
    """获取告警统计"""
    hours = request.args.get('hours', type=int, default=24)
    since = datetime.utcnow() - timedelta(hours=hours)

    # 按级别统计
    level_stats = db.session.query(
        AlertHistory.level,
        db.func.count(AlertHistory.id)
    ).filter(
        AlertHistory.triggered_at >= since
    ).group_by(AlertHistory.level).all()

    # 按状态统计
    status_stats = db.session.query(
        AlertHistory.status,
        db.func.count(AlertHistory.id)
    ).filter(
        AlertHistory.triggered_at >= since
    ).group_by(AlertHistory.status).all()

    # Top 10 告警规则
    top_rules = db.session.query(
        AlertHistory.rule_name,
        db.func.count(AlertHistory.id).label('count')
    ).filter(
        AlertHistory.triggered_at >= since
    ).group_by(AlertHistory.rule_name).order_by(
        db.desc('count')
    ).limit(10).all()

    return api_success({
        'by_level': {level: count for level, count in level_stats},
        'by_status': {status: count for status, count in status_stats},
        'top_rules': [{'name': name, 'count': count} for name, count in top_rules]
    })


@alert_bp.route('/history/<int:id>/ack', methods=['POST'])

def ack_alert(id):
    """确认告警"""
    data = request.get_json() or {}
    alert = AlertHistory.query.get_or_404(id)

    if alert.status == AlertStatus.RESOLVED:
        return api_error('告警已恢复，无需确认')

    alert.status = AlertStatus.ACKED
    alert.acked_at = datetime.utcnow()
    alert.acked_by = get_current_user_id()
    alert.ack_comment = data.get('comment', '')

    db.session.commit()
    return api_success({'alert': alert.to_dict()}, '确认成功')


@alert_bp.route('/history/<int:id>/resolve', methods=['POST'])

def resolve_alert(id):
    """手动解决告警"""
    data = request.get_json() or {}
    alert = AlertHistory.query.get_or_404(id)

    if alert.status == AlertStatus.RESOLVED:
        return api_error('告警已恢复')

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.resolved_reason = data.get('reason', '手动解决')

    db.session.commit()
    return api_success({'alert': alert.to_dict()}, '标记已恢复')


# ============ 指标数据 ============

@alert_bp.route('/metrics', methods=['GET'])

def list_metrics():
    """获取支持的监控指标"""
    metrics = {
        'database': [
            {'value': 'connections', 'label': '连接数', 'unit': '个'},
            {'value': 'connections_usage', 'label': '连接使用率', 'unit': '%'},
            {'value': 'qps', 'label': 'QPS', 'unit': '/s'},
            {'value': 'tps', 'label': 'TPS', 'unit': '/s'},
            {'value': 'slow_queries', 'label': '慢查询数', 'unit': '个/分'},
            {'value': 'replication_lag', 'label': '复制延迟', 'unit': '秒'},
            {'value': 'disk_usage', 'label': '磁盘使用率', 'unit': '%'},
            {'value': 'memory_usage', 'label': '内存使用率', 'unit': '%'}
        ],
        'host': [
            {'value': 'cpu_usage', 'label': 'CPU使用率', 'unit': '%'},
            {'value': 'memory_usage', 'label': '内存使用率', 'unit': '%'},
            {'value': 'disk_usage', 'label': '磁盘使用率', 'unit': '%'},
            {'value': 'load_avg_1m', 'label': '1分钟负载', 'unit': ''},
            {'value': 'network_in', 'label': '网络入流量', 'unit': 'MB/s'},
            {'value': 'network_out', 'label': '网络出流量', 'unit': 'MB/s'}
        ],
        'middleware': [
            {'value': 'connections', 'label': '连接数', 'unit': '个'},
            {'value': 'memory_usage', 'label': '内存使用率', 'unit': '%'},
            {'value': 'hit_ratio', 'label': '缓存命中率', 'unit': '%'}
        ]
    }
    return api_success({'metrics': metrics})


@alert_bp.route('/check', methods=['POST'])

def trigger_check():
    """手动触发告警检查（调试用）"""
    result = check_alerts_task.delay()
    return api_success({'task_id': result.id}, '告警检查任务已触发')
