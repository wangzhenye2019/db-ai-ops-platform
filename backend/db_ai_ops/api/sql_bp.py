"""
SQL审核 API
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
import re
import time
from ..models import db, SqlOrder, SqlOrderStatus, SqlAuditRule, Database, Backup, BackupStatus
from ..tasks.sql_execute import execute_sql_order_task

sql_bp = Blueprint('sql', __name__, url_prefix='/sql')


def api_success(data=None, message='success'):
    resp = {'success': True, 'message': message}
    if data:
        resp['data'] = data
    return jsonify(resp)


def api_error(message, code=400):
    return jsonify({'success': False, 'message': message}), code


# ============ SQL工单管理 ============

@sql_bp.route('/orders', methods=['GET'])
def list_orders():
    """获取SQL工单列表"""
    status = request.args.get('status')
    database_id = request.args.get('database_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = SqlOrder.query

    if status:
        query = query.filter_by(status=status)
    if database_id:
        query = query.filter_by(database_id=database_id)

    query = query.order_by(SqlOrder.created_at.desc())

    # 分页
    total = query.count()
    orders = query.offset((page - 1) * per_page).limit(per_page).all()

    return api_success({
        'orders': [o.to_dict() for o in orders],
        'total': total,
        'page': page,
        'per_page': per_page
    })


@sql_bp.route('/orders', methods=['POST'])
def create_order():
    """创建SQL工单"""
    data = request.get_json()

    if not data.get('title') or not data.get('sql_content'):
        return api_error('标题和SQL内容不能为空')

    if not data.get('database_id'):
        return api_error('请选择数据库')

    # 检查数据库是否存在
    db_obj = Database.query.get(data['database_id'])
    if not db_obj:
        return api_error('数据库不存在')

    # 解析SQL类型
    sql_type = detect_sql_type(data['sql_content'])

    # 风险评估
    risk_level = assess_risk(data['sql_content'], sql_type)
    if risk_level == 'high' and sql_type in ['UPDATE', 'DELETE', 'DROP', 'TRUNCATE']:
        # 高风险操作需要备份
        data['auto_backup'] = True

    # 创建工单
    order = SqlOrder(
        title=data['title'],
        description=data.get('description', ''),
        database_id=data['database_id'],
        sql_content=data['sql_content'],
        sql_type=sql_type,
        status=SqlOrderStatus.PENDING,
        creator_id=1  # 默认管理员
    )

    db.session.add(order)
    db.session.commit()

    return api_success({'order': order.to_dict()}, '工单创建成功')


@sql_bp.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    """获取工单详情"""
    order = SqlOrder.query.get_or_404(id)
    return api_success({'order': order.to_dict()})


@sql_bp.route('/orders/<int:id>/audit', methods=['POST'])
def audit_order(id):
    """审核工单"""
    data = request.get_json()
    order = SqlOrder.query.get_or_404(id)

    if order.status != SqlOrderStatus.PENDING:
        return api_error('工单状态不允许审核')

    action = data.get('action')  # approve, reject

    if action == 'approve':
        order.status = SqlOrderStatus.APPROVED
        order.review_comment = data.get('comment', '审核通过')
    elif action == 'reject':
        order.status = SqlOrderStatus.REJECTED
        order.review_comment = data.get('comment', '审核拒绝')
    else:
        return api_error('无效的审核操作')

    order.reviewer_id = 1
    order.reviewed_at = datetime.utcnow()
    db.session.commit()

    return api_success({'order': order.to_dict()}, '审核完成')


@sql_bp.route('/orders/<int:id>/execute', methods=['POST'])
def execute_order(id):
    """执行工单"""
    order = SqlOrder.query.get_or_404(id)

    if order.status != SqlOrderStatus.APPROVED:
        return api_error('只有已审核通过的工单才能执行')

    # 更新状态为执行中
    order.status = SqlOrderStatus.EXECUTING
    order.executor_id = 1
    order.executed_at = datetime.utcnow()
    db.session.commit()

    # 触发异步执行任务
    result = execute_sql_order_task.delay(order.id)

    return api_success({'order': order.to_dict(), 'task_id': result.id}, '执行任务已启动')


@sql_bp.route('/orders/<int:id>/rollback', methods=['POST'])
def rollback_order(id):
    """回滚工单"""
    order = SqlOrder.query.get_or_404(id)

    if order.status != SqlOrderStatus.EXECUTED:
        return api_error('只有已执行的工单才能回滚')

    if not order.rollback_sql:
        return api_error('该工单无可用回滚SQL')

    # 创建回滚工单
    rollback_order = SqlOrder(
        title=f'回滚: {order.title}',
        description=f'回滚原工单 #{order.id}',
        database_id=order.database_id,
        sql_content=order.rollback_sql,
        sql_type=detect_sql_type(order.rollback_sql),
        status=SqlOrderStatus.PENDING,
        creator_id=1
    )

    db.session.add(rollback_order)

    # 更新原工单状态
    order.status = SqlOrderStatus.ROLLED_BACK
    order.rolled_back_at = datetime.utcnow()

    db.session.commit()

    return api_success({'order': rollback_order.to_dict()}, '回滚工单已创建')


# ============ SQL语法检查 ============

@sql_bp.route('/audit', methods=['POST'])
def audit_sql():
    """SQL语法和风险检查"""
    data = request.get_json()
    sql = data.get('sql', '')
    database_id = data.get('database_id')

    if not sql:
        return api_error('SQL内容不能为空')

    # 语法检查
    syntax_result = check_syntax(sql)

    # 风险评估
    risk_result = assess_risk_full(sql)

    # 规则检查
    rule_results = check_audit_rules(sql)

    return api_success({
        'syntax': syntax_result,
        'risk': risk_result,
        'rules': rule_results
    })


# ============ 审核规则管理 ============

@sql_bp.route('/rules', methods=['GET'])
def list_rules():
    """获取审核规则列表"""
    rules = SqlAuditRule.query.order_by(SqlAuditRule.created_at.desc()).all()
    return api_success({'rules': [r.to_dict() for r in rules]})


@sql_bp.route('/rules', methods=['POST'])
def create_rule():
    """创建审核规则"""
    data = request.get_json()

    if not data.get('name') or not data.get('rule_type'):
        return api_error('名称和规则类型不能为空')

    rule = SqlAuditRule(
        name=data['name'],
        enabled=data.get('enabled', True),
        rule_type=data['rule_type'],
        pattern=data.get('pattern'),
        keywords=data.get('keywords'),
        severity=data.get('severity', 'warning'),
        message=data.get('message', ''),
        suggestion=data.get('suggestion')
    )

    db.session.add(rule)
    db.session.commit()

    return api_success({'rule': rule.to_dict()}, '创建成功')


@sql_bp.route('/rules/<int:id>', methods=['PUT'])
def update_rule(id):
    """更新审核规则"""
    rule = SqlAuditRule.query.get_or_404(id)
    data = request.get_json()

    for field in ['name', 'enabled', 'rule_type', 'pattern', 'keywords', 'severity', 'message', 'suggestion']:
        if field in data:
            setattr(rule, field, data[field])

    rule.updated_at = datetime.utcnow()
    db.session.commit()

    return api_success({'rule': rule.to_dict()}, '更新成功')


@sql_bp.route('/rules/<int:id>', methods=['DELETE'])
def delete_rule(id):
    """删除审核规则"""
    rule = SqlAuditRule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return api_success(message='删除成功')


# ============ 辅助函数 ============

def detect_sql_type(sql):
    """检测SQL类型"""
    sql = sql.strip().upper()
    if sql.startswith('SELECT'):
        return 'SELECT'
    elif sql.startswith('INSERT'):
        return 'INSERT'
    elif sql.startswith('UPDATE'):
        return 'UPDATE'
    elif sql.startswith('DELETE'):
        return 'DELETE'
    elif sql.startswith('CREATE'):
        return 'CREATE'
    elif sql.startswith('ALTER'):
        return 'ALTER'
    elif sql.startswith('DROP'):
        return 'DROP'
    elif sql.startswith('TRUNCATE'):
        return 'TRUNCATE'
    return 'OTHER'


def assess_risk(sql, sql_type):
    """快速风险评估"""
    high_risk_keywords = ['DROP', 'TRUNCATE', 'DELETE FROM', 'ALTER TABLE.*DROP',
                          'GRANT', 'REVOKE', 'EXECUTE']
    medium_risk_keywords = ['UPDATE', 'CREATE TABLE', 'ALTER TABLE']

    sql_upper = sql.upper()

    for kw in high_risk_keywords:
        if re.search(kw, sql_upper):
            return 'high'

    for kw in medium_risk_keywords:
        if re.search(kw, sql_upper):
            return 'medium'

    return 'low'


def assess_risk_full(sql):
    """完整风险评估"""
    sql_upper = sql.upper()

    risks = []

    # 高风险检查
    if re.search(r'\bDROP\b', sql_upper):
        risks.append({'level': 'high', 'message': '包含 DROP 操作，可能导致数据丢失'})
    if re.search(r'\bTRUNCATE\b', sql_upper):
        risks.append({'level': 'high', 'message': '包含 TRUNCATE 操作，将清空表数据'})
    if re.search(r'\bDELETE\s+FROM\s+\w+\s*;?\s*$', sql_upper, re.MULTILINE):
        risks.append({'level': 'high', 'message': '包含全表 DELETE 操作'})

    # 中风险检查
    if re.search(r'\bUPDATE\s+\w+\s+SET\b', sql_upper):
        risks.append({'level': 'medium', 'message': '包含 UPDATE 操作'})
    if re.search(r'\bALTER\s+TABLE\b', sql_upper):
        risks.append({'level': 'medium', 'message': '包含表结构变更'})

    # 低风险检查
    if not re.search(r'\bWHERE\b', sql_upper) and sql_type in ['UPDATE', 'DELETE']:
        risks.append({'level': 'high', 'message': '缺少 WHERE 条件，可能影响全表'})

    return {
        'level': 'high' if any(r['level'] == 'high' for r in risks) else 'medium' if risks else 'low',
        'items': risks
    }


def check_syntax(sql):
    """简单语法检查（实际生产应使用 sqlparse）"""
    errors = []

    # 括号匹配检查
    if sql.count('(') != sql.count(')'):
        errors.append('括号不匹配')

    # 引号匹配检查
    if sql.count("'") % 2 != 0:
        errors.append('单引号不匹配')

    # 关键字检查
    if not re.match(r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|SHOW|USE)', sql, re.IGNORECASE):
        errors.append('未识别的SQL语句类型')

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def check_audit_rules(sql):
    """根据规则检查SQL"""
    rules = SqlAuditRule.query.filter_by(enabled=True).all()
    results = []

    for rule in rules:
        matched = False

        # 关键词匹配
        if rule.keywords:
            keywords = rule.keywords.split(',')
            for kw in keywords:
                if kw.strip().lower() in sql.lower():
                    matched = True
                    break

        # 正则匹配
        if rule.pattern and not matched:
            try:
                if re.search(rule.pattern, sql, re.IGNORECASE):
                    matched = True
            except:
                pass

        if matched:
            results.append({
                'rule_id': rule.id,
                'rule_name': rule.name,
                'severity': rule.severity,
                'message': rule.message,
                'suggestion': rule.suggestion
            })

    return results