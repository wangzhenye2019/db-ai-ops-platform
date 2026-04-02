import json

from flask import Blueprint, jsonify, request, g

from db_ai_ops.agent_planner import is_confirm_text, plan_next
from db_ai_ops.agent_tools import execute_tool, is_readonly, list_tools
from db_ai_ops.extensions import db
from db_ai_ops.models import AgentMessage, AgentRole, AgentSession


agent_bp = Blueprint('agent_bp', __name__)


@agent_bp.route('/agent/tools', methods=['GET'])
def agent_tools():
    return jsonify({'tools': list_tools()})


@agent_bp.route('/agent/sessions', methods=['POST'])
def create_session():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip() or '新会话'
    s = AgentSession(title=title, state={}, created_by=getattr(g, 'current_user', None))
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@agent_bp.route('/agent/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    s = AgentSession.query.get_or_404(session_id)
    return jsonify(s.to_dict())


@agent_bp.route('/agent/sessions/<int:session_id>/messages', methods=['GET'])
def list_messages(session_id):
    s = AgentSession.query.get_or_404(session_id)
    msgs = AgentMessage.query.filter_by(session_id=s.id).order_by(AgentMessage.created_at.asc()).all()
    return jsonify({'session': s.to_dict(), 'messages': [m.to_dict() for m in msgs]})


def _add_message(session_id, role: AgentRole, content: str, meta=None):
    m = AgentMessage(session_id=session_id, role=role, content=content, meta=meta or {})
    db.session.add(m)
    db.session.commit()
    return m


@agent_bp.route('/agent/sessions/<int:session_id>/messages', methods=['POST'])
def post_message(session_id):
    s = AgentSession.query.get_or_404(session_id)
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    confirm = bool(data.get('confirm')) or is_confirm_text(content)
    cancel = bool(data.get('cancel')) or content in {'取消', '算了', '停止'}

    emitted = []

    if content:
        emitted.append(_add_message(s.id, AgentRole.USER, content).to_dict())

    state = s.state or {}

    if cancel and state.get('pending'):
        state.pop('pending', None)
        s.state = state
        db.session.commit()
        assistant = _add_message(s.id, AgentRole.ASSISTANT, "已取消待执行操作。").to_dict()
        emitted.append(assistant)
        return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': None}), 200

    if confirm and state.get('pending'):
        pending = state.get('pending') or {}
        tool_name = pending.get('name')
        tool_args = pending.get('args') or {}
        if not tool_name:
            return jsonify({'error': 'pending tool is invalid'}), 400
        if is_readonly(tool_name):
            state.pop('pending', None)
            s.state = state
            db.session.commit()
        try:
            result = execute_tool(tool_name, tool_args, created_by=getattr(g, 'current_user', None))
        except Exception as e:
            assistant = _add_message(s.id, AgentRole.ASSISTANT, f"执行失败：{str(e)}", meta={'tool': tool_name}).to_dict()
            emitted.append(assistant)
            return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': state.get('pending')}), 200

        state.pop('pending', None)
        s.state = state
        db.session.commit()

        tool_msg = _add_message(
            s.id,
            AgentRole.TOOL,
            json.dumps(result, ensure_ascii=False, indent=2),
            meta={'tool': tool_name, 'args': tool_args, 'result': result}
        ).to_dict()
        emitted.append(tool_msg)

        summary = "已执行。"
        if isinstance(result, dict):
            if 'task' in result:
                summary = f"已创建运维任务：{result['task'].get('id')}"
            if 'report' in result:
                summary = f"已创建巡检报告：{result['report'].get('id')}"
        assistant = _add_message(s.id, AgentRole.ASSISTANT, summary, meta={'tool': tool_name}).to_dict()
        emitted.append(assistant)
        return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': None}), 200

    plan = plan_next(content, state)
    reply = plan.get('reply') or ''
    pending = plan.get('pending')
    tool_call = plan.get('tool_call')
    requires_confirm = bool(plan.get('requires_confirm'))

    if pending and isinstance(pending, dict):
        state['pending'] = pending
        s.state = state
        db.session.commit()

    if tool_call and isinstance(tool_call, dict) and tool_call.get('name'):
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('args') or {}
        if requires_confirm:
            state['pending'] = {'name': tool_name, 'args': tool_args}
            s.state = state
            db.session.commit()
            assistant = _add_message(
                s.id,
                AgentRole.ASSISTANT,
                reply or "需要确认执行。",
                meta={'pending': state['pending']}
            ).to_dict()
            emitted.append(assistant)
            return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': state.get('pending')}), 200

        try:
            result = execute_tool(tool_name, tool_args, created_by=getattr(g, 'current_user', None))
        except Exception as e:
            assistant = _add_message(s.id, AgentRole.ASSISTANT, f"执行失败：{str(e)}", meta={'tool': tool_name}).to_dict()
            emitted.append(assistant)
            return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': state.get('pending')}), 200

        tool_msg = _add_message(
            s.id,
            AgentRole.TOOL,
            json.dumps(result, ensure_ascii=False, indent=2),
            meta={'tool': tool_name, 'args': tool_args, 'result': result}
        ).to_dict()
        emitted.append(tool_msg)

    assistant = _add_message(s.id, AgentRole.ASSISTANT, reply, meta={'pending': state.get('pending')}).to_dict()
    emitted.append(assistant)
    return jsonify({'session': s.to_dict(), 'messages': emitted, 'pending': state.get('pending')}), 200
