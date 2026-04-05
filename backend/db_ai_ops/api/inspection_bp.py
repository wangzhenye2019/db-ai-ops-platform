from flask import Blueprint, jsonify, request, g, make_response

from db_ai_ops.extensions import db
from db_ai_ops.models import InspectionReport, InspectionReportStatus
from db_ai_ops.tasks.ops_tasks import run_inspection_report

inspection_bp = Blueprint('inspection_bp', __name__)


@inspection_bp.route('/inspection/run', methods=['POST'])
def run_inspection():
    data = request.get_json() or {}
    scope = (data.get('scope') or '').strip()
    if not scope:
        return jsonify({'error': 'scope 不能为空'}), 400

    target_ids = data.get('target_ids') or []
    summary = f"{scope}:{len(target_ids)}"

    r = InspectionReport(
        scope=scope,
        target_summary=summary,
        status=InspectionReportStatus.PENDING,
        created_by=getattr(g, 'current_user', None)
    )
    db.session.add(r)
    db.session.commit()

    try:
        run_inspection_report.delay(r.id, data)
    except Exception:
        run_inspection_report.apply(args=[r.id, data])
    return jsonify(r.to_dict()), 201


@inspection_bp.route('/inspection/reports', methods=['GET'])
def list_reports():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = InspectionReport.query.order_by(InspectionReport.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@inspection_bp.route('/inspection/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    r = InspectionReport.query.get_or_404(report_id)
    return jsonify(r.to_dict())


@inspection_bp.route('/inspection/reports/<int:report_id>/export', methods=['GET'])
def export_report(report_id):
    """导出巡检报告"""
    fmt = request.args.get('format', 'json')  # json/markdown/html
    r = InspectionReport.query.get_or_404(report_id)

    if r.status != InspectionReportStatus.READY:
        return jsonify({'error': 'Report not ready'}), 400

    result = r.result or {}

    if fmt == 'json':
        response = make_response(jsonify(result))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_id}.json'
        return response

    elif fmt == 'markdown':
        content = generate_markdown(r, result)
        response = make_response(content)
        response.headers['Content-Type'] = 'text/markdown'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_id}.md'
        return response

    elif fmt == 'html':
        content = generate_html(r, result)
        response = make_response(content)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_id}.html'
        return response

    return jsonify({'error': 'Unsupported format'}), 400


@inspection_bp.route('/inspection/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    r = InspectionReport.query.get_or_404(report_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


def generate_markdown(report, result):
    """生成Markdown格式报告"""
    md = f"""# 巡检报告

## 基本信息
- 巡检范围: {report.scope}
- 目标: {report.target_summary}
- 状态: {report.status.value}
- 创建人: {report.created_by or '-'}
- 创建时间: {report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else '-'}
- 完成时间: {report.completed_at.strftime('%Y-%m-%d %H:%M:%S') if report.completed_at else '-'}

## 巡检结果

"""
    # 解析result中的检查项
    items = result.get('items', [])
    if not items:
        md += "暂无详细结果\n"
    else:
        for item in items:
            status = item.get('status', 'unknown')
            icon = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}.get(status, '❓')
            md += f"### {icon} {item.get('name', 'Unknown')}\n"
            md += f"- 检查项: {item.get('check', '-')}\n"
            md += f"- 结果: {item.get('message', '-')}\n"
            md += f"- 详情: {item.get('detail', '-')}\n\n"

    return md


def generate_html(report, result):
    """生成HTML格式报告"""
    items = result.get('items', [])
    rows = ""
    for item in items:
        status = item.get('status', 'unknown')
        icon = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}.get(status, '❓')
        rows += f"""
        <tr>
            <td>{icon} {item.get('name', 'Unknown')}</td>
            <td>{item.get('check', '-')}</td>
            <td>{item.get('message', '-')}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>巡检报告 - {report.scope}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; }}
        h1 {{ color: #1a1a1a; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
    </style>
</head>
<body>
    <h1>巡检报告</h1>
    <p><strong>巡检范围:</strong> {report.scope}</p>
    <p><strong>目标:</strong> {report.target_summary}</p>
    <p><strong>状态:</strong> {report.status.value}</p>
    <p><strong>创建时间:</strong> {report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else '-'}</p>

    <h2>巡检结果</h2>
    <table>
        <thead>
            <tr>
                <th>检查项</th>
                <th>项目</th>
                <th>结果</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>"""
    return html
