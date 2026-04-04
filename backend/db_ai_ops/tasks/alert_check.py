"""
告警检查任务
周期性执行，检查所有启用的告警规则
"""
from datetime import datetime, timedelta
from celery import shared_task
from ..models import db
from ..models import AlertRule, AlertChannel, AlertHistory, AlertStatus, AlertLevel
from ..models import Database, Host
from ..utils.notification import send_notification
import random


@shared_task(bind=True, max_retries=3)
def check_alerts_task(self):
    """执行告警检查"""
    print(f"[Alert Check] Starting at {datetime.utcnow()}")

    # 获取所有启用的规则
    rules = AlertRule.query.filter_by(enabled=True).all()
    print(f"[Alert Check] Checking {len(rules)} rules")

    for rule in rules:
        try:
            check_single_rule(rule)
        except Exception as e:
            print(f"[Alert Check] Error checking rule {rule.id}: {e}")
            continue

    print(f"[Alert Check] Finished at {datetime.utcnow()}")
    return {'checked': len(rules)}


def check_single_rule(rule):
    """检查单个告警规则"""
    # 确定监控目标
    targets = get_targets(rule.target_type, rule.target_id)

    for target in targets:
        # 获取指标值（实际应从监控系统获取）
        metric_value = get_metric_value(
            rule.target_type,
            target['id'],
            rule.metric,
            rule.aggregator,
            rule.period_seconds
        )

        if metric_value is None:
            continue

        # 判断是否触发告警
        triggered = evaluate_condition(
            metric_value,
            rule.operator,
            rule.threshold
        )

        if triggered:
            handle_triggered_alert(rule, target, metric_value)
        else:
            handle_resolved_alert(rule, target)


def get_targets(target_type, target_id):
    """获取监控目标列表"""
    if target_id:
        # 单个目标
        if target_type == 'database':
            db_obj = Database.query.get(target_id)
            if db_obj:
                return [{'id': db_obj.id, 'name': db_obj.name, 'obj': db_obj}]
        elif target_type == 'host':
            host = Host.query.get(target_id)
            if host:
                return [{'id': host.id, 'name': host.name, 'obj': host}]
        return []
    else:
        # 全部目标
        if target_type == 'database':
            dbs = Database.query.filter_by(enabled=True).all()
            return [{'id': d.id, 'name': d.name, 'obj': d} for d in dbs]
        elif target_type == 'host':
            hosts = Host.query.filter_by(enabled=True).all()
            return [{'id': h.id, 'name': h.name, 'obj': h} for h in hosts]
        return []


def get_metric_value(target_type, target_id, metric, aggregator, period):
    """
    获取指标值
    实际实现应从 Prometheus/Zabbix 等监控系统获取
    这里使用模拟数据
    """
    # TODO: 接入真实监控系统
    # 模拟数据用于演示
    if metric == 'cpu_usage':
        return random.uniform(20, 95)
    elif metric == 'memory_usage':
        return random.uniform(30, 90)
    elif metric == 'disk_usage':
        return random.uniform(40, 85)
    elif metric == 'connections':
        return random.randint(10, 200)
    elif metric == 'qps':
        return random.randint(100, 5000)
    elif metric == 'slow_queries':
        return random.randint(0, 20)
    else:
        return random.uniform(0, 100)


def evaluate_condition(value, operator, threshold):
    """评估告警条件"""
    operators = {
        '>': lambda v, t: v > t,
        '<': lambda v, t: v < t,
        '>=': lambda v, t: v >= t,
        '<=': lambda v, t: v <= t,
        '==': lambda v, t: v == t,
        '!=': lambda v, t: v != t
    }

    op_func = operators.get(operator)
    if not op_func:
        return False

    return op_func(value, threshold)


def handle_triggered_alert(rule, target, metric_value):
    """处理触发的告警"""
    # 检查是否已存在活跃的告警
    existing = AlertHistory.query.filter_by(
        rule_id=rule.id,
        target_id=target['id'],
        status=AlertStatus.ACTIVE
    ).first()

    if existing:
        # 更新告警值
        existing.metric_value = metric_value
        db.session.commit()
        return

    # 检查抑制期
    suppressed = AlertHistory.query.filter(
        AlertHistory.rule_id == rule.id,
        AlertHistory.target_id == target['id'],
        AlertHistory.resolved_at >= datetime.utcnow() - timedelta(seconds=rule.suppression_duration)
    ).first()

    if suppressed:
        return

    # 创建新告警
    message = f"{rule.metric} 当前值 {metric_value:.2f}，{rule.operator} 阈值 {rule.threshold}"

    alert = AlertHistory(
        rule_id=rule.id,
        rule_name=rule.name,
        alert_name=rule.name,
        level=rule.level,
        status=AlertStatus.ACTIVE,
        target_type=rule.target_type,
        target_id=target['id'],
        target_name=target['name'],
        metric=rule.metric,
        metric_value=metric_value,
        threshold=rule.threshold,
        operator=rule.operator,
        message=message
    )

    db.session.add(alert)
    db.session.commit()

    # 发送通知
    send_alert_notifications(rule, alert)


def handle_resolved_alert(rule, target):
    """处理恢复的告警"""
    existing = AlertHistory.query.filter_by(
        rule_id=rule.id,
        target_id=target['id'],
        status=AlertStatus.ACTIVE
    ).first()

    if not existing:
        return

    # 标记为已恢复
    existing.status = AlertStatus.RESOLVED
    existing.resolved_at = datetime.utcnow()
    existing.resolved_reason = '自动恢复'
    db.session.commit()

    # 发送恢复通知
    if rule.notify_on_resolve:
        send_resolve_notifications(rule, existing)


def send_alert_notifications(rule, alert):
    """发送告警通知"""
    channels = AlertChannel.query.filter(
        AlertChannel.id.in_(rule.channel_ids),
        AlertChannel.enabled == True
    ).all()

    message = {
        'title': f"【告警】{alert.alert_name}",
        'content': alert.message,
        'level': alert.level,
        'target_name': alert.target_name,
        'metric': alert.metric,
        'metric_value': alert.metric_value,
        'threshold': alert.threshold,
        'time': alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if alert.triggered_at else 'N/A'
    }

    notifications = []
    for channel in channels:
        success, error = send_notification(channel.to_dict_with_secret(), message)
        notifications.append({
            'channel_id': channel.id,
            'channel_name': channel.name,
            'sent_at': datetime.utcnow().isoformat(),
            'success': success,
            'error': error
        })

    alert.notifications_sent = notifications
    db.session.commit()


def send_resolve_notifications(rule, alert):
    """发送恢复通知"""
    channels = AlertChannel.query.filter(
        AlertChannel.id.in_(rule.channel_ids),
        AlertChannel.enabled == True
    ).all()

    message = {
        'title': f"【恢复】{alert.alert_name}",
        'content': f"告警已恢复，持续时间 {alert._get_duration() // 60} 分钟",
        'level': alert.level,
        'target_name': alert.target_name,
        'metric': alert.metric,
        'metric_value': alert.metric_value,
        'threshold': alert.threshold,
        'time': alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else 'N/A'
    }

    for channel in channels:
        send_notification(channel.to_dict_with_secret(), message)
