import hashlib
import re
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import Database, SlowQuery

slowsql_bp = Blueprint('slowsql_bp', __name__)


@slowsql_bp.route('/slowsql/queries', methods=['GET'])
def list_slow_queries():
    """获取慢SQL列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    database_id = request.args.get('database_id', type=int)
    min_time = request.args.get('min_time', 1.0, type=float)
    digest = request.args.get('digest')

    query = SlowQuery.query
    if database_id:
        query = query.filter_by(database_id=database_id)
    if digest:
        query = query.filter_by(digest=digest)
    if min_time:
        query = query.filter(SlowQuery.execute_time >= min_time)

    query = query.order_by(SlowQuery.timestamp.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'queries': [q.to_dict() for q in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@slowsql_bp.route('/slowsql/queries/<int:query_id>', methods=['GET'])
def get_slow_query(query_id):
    """获取慢SQL详情"""
    query = SlowQuery.query.get_or_404(query_id)
    return jsonify(query.to_dict())


@slowsql_bp.route('/slowsql/queries', methods=['POST'])
def record_slow_query():
    """记录慢SQL"""
    data = request.get_json()
    database_id = data.get('database_id')
    sql_text = data.get('sql_text')
    execute_time = data.get('execute_time', 0)
    rows_sent = data.get('rows_sent', 0)
    rows_examined = data.get('rows_examined', 0)
    user = data.get('user')
    client = data.get('client')

    if not sql_text:
        return jsonify({'error': 'sql_text is required'}), 400

    # 计算SQL摘要
    digest = hashlib.md5(sql_text.encode()).hexdigest()[:16]

    query = SlowQuery(
        database_id=database_id,
        sql_text=sql_text,
        execute_time=float(execute_time),
        rows_sent=rows_sent,
        rows_examined=rows_examined,
        user=user,
        client=client,
        digest=digest,
        analysis={},
        suggestion=''
    )
    db.session.add(query)
    db.session.commit()

    # 自动分析
    analysis = analyze_slow_query(sql_text, execute_time, rows_sent, rows_examined)
    query.analysis = analysis
    query.suggestion = generate_suggestion(analysis)
    db.session.commit()

    return jsonify(query.to_dict()), 201


@slowsql_bp.route('/slowsql/queries/<int:query_id>/analyze', methods=['POST'])
def analyze_slow_query_endpoint(query_id):
    """手动触发分析"""
    query = SlowQuery.query.get_or_404(query_id)

    analysis = analyze_slow_query(
        query.sql_text,
        query.execute_time,
        query.rows_sent,
        query.rows_examined
    )
    query.analysis = analysis
    query.suggestion = generate_suggestion(analysis)
    db.session.commit()

    return jsonify(query.to_dict())


@slowsql_bp.route('/slowsql/stats', methods=['GET'])
def get_slow_sql_stats():
    """获取慢SQL统计"""
    database_id = request.args.get('database_id', type=int)
    days = request.args.get('days', 7, type=int)

    since = datetime.utcnow() - timedelta(days=days)

    query = SlowQuery.query.filter(SlowQuery.timestamp >= since)
    if database_id:
        query = query.filter_by(database_id=database_id)

    total = query.count()
    avg_time = db.session.query(db.func.avg(SlowQuery.execute_time)).filter(
        SlowQuery.timestamp >= since
    ).scalar() or 0

    # 按SQL摘要分组统计
    digest_stats = db.session.query(
        SlowQuery.digest,
        db.func.count(SlowQuery.id).label('count'),
        db.func.avg(SlowQuery.execute_time).label('avg_time'),
        db.func.max(SlowQuery.execute_time).label('max_time')
    ).filter(SlowQuery.timestamp >= since).group_by(SlowQuery.digest).order_by(
        db.desc('count')
    ).limit(10).all()

    top_queries = []
    for d in digest_stats:
        first = SlowQuery.query.filter_by(digest=d.digest).first()
        top_queries.append({
            'digest': d.digest,
            'sql_text': first.sql_text[:200] if first else '',
            'count': d.count,
            'avg_time': round(d.avg_time, 3),
            'max_time': round(d.max_time, 3)
        })

    return jsonify({
        'total': total,
        'avg_time': round(avg_time, 3),
        'top_queries': top_queries
    })


@slowsql_bp.route('/slowsql/queries/<int:query_id>', methods=['DELETE'])
def delete_slow_query(query_id):
    """删除慢SQL记录"""
    query = SlowQuery.query.get_or_404(query_id)
    db.session.delete(query)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


# ==================== Analysis Functions ====================

def analyze_slow_query(sql_text, execute_time, rows_sent, rows_examined):
    """分析SQL语句，返回诊断结果"""
    analysis = {
        'risks': [],
        'patterns': [],
        'score': 100  # 初始分数
    }

    sql_lower = sql_text.lower()

    # 检查全表扫描
    if 'where' not in sql_lower and 'join' in sql_lower:
        analysis['risks'].append('可能存在全表扫描')
        analysis['score'] -= 20

    # 检查SELECT *
    if sql_lower.strip().startswith('select *'):
        analysis['patterns'].append('使用SELECT *')
        analysis['score'] -= 10

    # 检查子查询
    if 'select' in sql_lower and ' from (' in sql_lower:
        analysis['patterns'].append('使用子查询')
        analysis['score'] -= 15

    # 检查JOIN类型
    if ' join ' in sql_lower:
        if ' left join ' in sql_lower or ' right join ' in sql_lower:
            analysis['patterns'].append('使用OUTER JOIN')
            analysis['score'] -= 10
        if ' cross join ' in sql_lower:
            analysis['risks'].append('使用CROSS JOIN可能导致笛卡尔积')
            analysis['score'] -= 25

    # 检查缺失索引的WHERE
    where_match = re.search(r'where\s+(\w+)\s*=', sql_lower)
    if where_match:
        col = where_match.group(1)
        if 'index' not in sql_lower and col not in ['id', 'created_at']:
            analysis['risks'].append(f'WHERE条件字段 {col} 可能缺少索引')

    # 检查ORDER BY
    if 'order by' in sql_lower:
        order_col = re.search(r'order\s+by\s+(\w+)', sql_lower)
        if order_col:
            analysis['patterns'].append(f'排序字段: {order_col.group(1)}')

    # 检查GROUP BY
    if 'group by' in sql_lower:
        analysis['patterns'].append('使用GROUP BY')

    # 检查LIMIT
    if 'limit' not in sql_lower:
        analysis['risks'].append('未使用LIMIT限制结果集')
        analysis['score'] -= 10
    else:
        limit_match = re.search(r'limit\s+(\d+)', sql_lower)
        if limit_match and int(limit_match.group(1)) > 1000:
            analysis['patterns'].append(f'LIMIT值较大: {limit_match.group(1)}')

    # 检查OR条件
    if ' or ' in sql_lower.replace(' or ', ''):
        analysis['risks'].append('使用OR条件可能导致索引失效')
        analysis['score'] -= 15

    # 检查NOT IN
    if 'not in' in sql_lower:
        analysis['risks'].append('NOT IN可能导致性能问题，建议用NOT EXISTS替代')
        analysis['score'] -= 15

    # 扫描行数分析
    if rows_examined > 100000 and rows_sent < rows_examined * 0.01:
        analysis['patterns'].append(f'扫描{rows_examined}行但只返回{rows_sent}行，效率低')
        analysis['score'] -= 20

    # 执行时间分析
    if execute_time > 5:
        analysis['risks'].append(f'执行时间较长: {execute_time}秒')
        analysis['score'] -= 15
    elif execute_time > 1:
        analysis['patterns'].append(f'执行时间: {execute_time}秒')

    analysis['score'] = max(0, analysis['score'])
    return analysis


def generate_suggestion(analysis):
    """根据分析结果生成优化建议"""
    suggestions = []

    if not analysis.get('risks') and not analysis.get('patterns'):
        return 'SQL语句看起来正常，未发现明显性能问题。'

    for risk in analysis.get('risks', []):
        suggestions.append(f'⚠️ {risk}')

    for pattern in analysis.get('patterns', []):
        suggestions.append(f'💡 {pattern}')

    # 根据分数给出总体建议
    score = analysis.get('score', 100)
    if score >= 80:
        suggestions.append('✅ 整体评分良好，建议继续观察。')
    elif score >= 60:
        suggestions.append('⚠️ 存在一定风险，建议优化。')
    else:
        suggestions.append('❌ 建议优先优化，问题较严重。')

    return '\n'.join(suggestions)