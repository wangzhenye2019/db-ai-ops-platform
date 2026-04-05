import datetime
from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, Host, Middleware

diagnosis_bp = Blueprint('diagnosis_bp', __name__)


# 诊断规则库
DIAGNOSIS_RULES = {
    'high_cpu': {
        'symptom': 'CPU使用率过高',
        'causes': ['慢查询', '连接数过多', '表锁竞争', '复杂计算'],
        'checks': [
            '检查慢SQL查询',
            '查看连接数状态',
            '检查是否有锁等待',
            '查看进程列表'
        ],
        'suggestions': [
            '优化慢SQL查询',
            '增加连接池大小',
            '添加索引',
            '考虑读写分离'
        ]
    },
    'high_memory': {
        'symptom': '内存使用率过高',
        'causes': ['缓冲池过大', '连接泄漏', '查询结果集过大', '排序内存不足'],
        'checks': [
            '检查缓冲池配置',
            '查看连接状态',
            '检查慢查询',
            '查看内存分配'
        ],
        'suggestions': [
            '调整缓冲池大小',
            '检查连接泄漏',
            '限制查询返回行数',
            '优化排序操作'
        ]
    },
    'high_connections': {
        'symptom': '连接数过高',
        'causes': ['连接池配置不当', '慢查询阻塞', '连接未释放', '并发过高'],
        'checks': [
            '查看当前连接数',
            '检查慢查询',
            '查看连接状态',
            '检查连接池配置'
        ],
        'suggestions': [
            '增加连接池最大连接数',
            '优化慢查询',
            '检查应用连接泄漏',
            '考虑连接复用'
        ]
    },
    'disk_full': {
        'symptom': '磁盘空间不足',
        'causes': ['数据文件过大', '日志文件过多', '备份文件堆积', '临时文件'],
        'checks': [
            '查看磁盘使用率',
            '检查数据目录大小',
            '查看日志文件',
            '检查备份目录'
        ],
        'suggestions': [
            '清理历史数据',
            '归档旧日志',
            '清理过期备份',
            '扩展磁盘空间'
        ]
    },
    'slow_query': {
        'symptom': '查询响应慢',
        'causes': ['缺少索引', '统计信息过期', 'SQL写法不佳', '资源不足'],
        'checks': [
            '查看执行计划',
            '检查索引',
            '分析SQL',
            '查看资源状态'
        ],
        'suggestions': [
            '添加适当索引',
            '更新统计信息',
            '优化SQL写法',
            '增加资源'
        ]
    },
    'replication_lag': {
        'symptom': '主从延迟过高',
        'causes': ['主库压力大', '网络延迟', '从库性能差', '大事务'],
        'checks': [
            '查看延迟时间',
            '检查主库压力',
            '检查网络状态',
            '查看从库状态'
        ],
        'suggestions': [
            '优化主库写入',
            '检查网络',
            '提升从库配置',
            '拆分大事务'
        ]
    },
    'lock_wait': {
        'symptom': '锁等待超时',
        'causes': ['长事务', '未提交事务', '锁竞争', '不当锁顺序'],
        'checks': [
            '查看锁等待',
            '检查活跃事务',
            '查看锁信息',
            '分析事务日志'
        ],
        'suggestions': [
            '缩短事务时间',
            '及时提交事务',
            '优化锁顺序',
            '使用低隔离级别'
        ]
    },
    'table_corrupt': {
        'symptom': '表损坏',
        'causes': ['硬件故障', '异常关机', '磁盘错误', '软件bug'],
        'checks': [
            '检查表状态',
            '查看错误日志',
            '检查磁盘',
            '验证数据完整性'
        ],
        'suggestions': [
            '修复表',
            '恢复备份',
            '检查硬件',
            '检查文件系统'
        ]
    }
}


@diagnosis_bp.route('/diagnosis/rules', methods=['GET'])
def get_diagnosis_rules():
    """获取诊断规则列表"""
    rules = []
    for key, rule in DIAGNOSIS_RULES.items():
        rules.append({
            'code': key,
            'symptom': rule['symptom'],
            'causes': rule['causes'],
            'suggestions': rule['suggestions']
        })
    return jsonify({'rules': rules})


@diagnosis_bp.route('/diagnosis/targets', methods=['GET'])
def get_diagnosis_targets():
    """获取可诊断的目标"""
    target_type = request.args.get('type')

    targets = []
    if not target_type or target_type == 'database':
        databases = Database.query.filter_by(enabled=True).all()
        for d in databases:
            targets.append({
                'type': 'database',
                'id': d.id,
                'name': d.name,
                'db_type': d.db_type.value if d.db_type else None,
                'host': d.host
            })

    if not target_type or target_type == 'host':
        hosts = Host.query.filter_by(enabled=True).all()
        for h in hosts:
            targets.append({
                'type': 'host',
                'id': h.id,
                'name': h.name,
                'host': h.host
            })

    if not target_type or target_type == 'middleware':
        middlewares = Middleware.query.filter_by(enabled=True).all()
        for m in middlewares:
            targets.append({
                'type': 'middleware',
                'id': m.id,
                'name': m.name,
                'mw_type': m.mw_type.value if m.mw_type else None
            })

    return jsonify({'targets': targets})


@diagnosis_bp.route('/diagnosis', methods=['POST'])
def run_diagnosis():
    """执行智能诊断"""
    data = request.get_json()
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    symptoms = data.get('symptoms', [])  # 如 ['high_cpu', 'slow_query']

    if not target_type or not target_id:
        return jsonify({'error': 'target_type and target_id are required'}), 400

    # 获取目标信息
    target = None
    if target_type == 'database':
        target = Database.query.get(target_id)
    elif target_type == 'host':
        target = Host.query.get(target_id)
    elif target_type == 'middleware':
        target = Middleware.query.get(target_id)

    if not target:
        return jsonify({'error': 'Target not found'}), 404

    # 执行诊断
    results = run_intelligent_diagnosis(target_type, target, symptoms)

    return jsonify({
        'target_type': target_type,
        'target_id': target_id,
        'target_name': target.name if hasattr(target, 'name') else str(target),
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'results': results
    })


@diagnosis_bp.route('/diagnosis/history', methods=['GET'])
def get_diagnosis_history():
    """获取诊断历史（模拟）"""
    # 这里可以扩展为存储到数据库
    return jsonify({
        'history': []
    })


def run_intelligent_diagnosis(target_type, target, symptoms):
    """根据症状进行智能诊断"""
    results = []

    # 如果没有指定症状，进行全面检查
    if not symptoms:
        symptoms = list(DIAGNOSIS_RULES.keys())

    for symptom in symptoms:
        if symptom not in DIAGNOSIS_RULES:
            continue

        rule = DIAGNOSIS_RULES[symptom]

        # 根据目标类型和症状生成诊断结果
        diagnosis = {
            'symptom': rule['symptom'],
            'severity': determine_severity(symptom, target),
            'causes': rule['causes'],
            'checks': rule['checks'],
            'suggestions': rule['suggestions'],
            'confidence': calculate_confidence(symptom, target)
        }

        results.append(diagnosis)

    # 按严重程度排序
    results.sort(key=lambda x: {'critical': 0, 'warning': 1, 'info': 2}.get(x['severity'], 3))

    return results


def determine_severity(symptom, target):
    """根据症状和目标确定严重程度"""
    # 这里可以根据实际情况返回不同严重程度
    severity_map = {
        'table_corrupt': 'critical',
        'disk_full': 'critical',
        'lock_wait': 'warning',
        'replication_lag': 'warning',
        'high_cpu': 'warning',
        'high_memory': 'warning',
        'high_connections': 'warning',
        'slow_query': 'info'
    }
    return severity_map.get(symptom, 'info')


def calculate_confidence(symptom, target):
    """计算诊断置信度"""
    # 简单模拟：根据症状类型返回不同置信度
    confidence_map = {
        'slow_query': 0.85,
        'high_cpu': 0.80,
        'high_memory': 0.75,
        'high_connections': 0.70,
        'disk_full': 0.90,
        'replication_lag': 0.65,
        'lock_wait': 0.70,
        'table_corrupt': 0.95
    }
    return confidence_map.get(symptom, 0.60)