from flask import Blueprint, jsonify, request

from db_ai_ops.extensions import db
from db_ai_ops.models import KnowledgeArticle, KnowledgeScope

kb_bp = Blueprint('kb_bp', __name__)


@kb_bp.route('/kb/articles', methods=['GET'])
def list_articles():
    scope = request.args.get('scope')
    query = KnowledgeArticle.query
    if scope:
        try:
            query = query.filter_by(scope=KnowledgeScope(scope))
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400
    items = query.order_by(KnowledgeArticle.created_at.desc()).all()
    return jsonify({'articles': [a.to_dict() for a in items]})


@kb_bp.route('/kb/articles', methods=['POST'])
def create_article():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title 不能为空'}), 400

    scope_raw = (data.get('scope') or 'general').lower()
    try:
        scope = KnowledgeScope(scope_raw)
    except ValueError:
        return jsonify({'error': f'Invalid scope. Must be one of: {[e.value for e in KnowledgeScope]}'}), 400

    a = KnowledgeArticle(
        scope=scope,
        title=title,
        category=(data.get('category') or '').strip() or None,
        tags=data.get('tags') or [],
        content=data.get('content') or ''
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict()), 201


@kb_bp.route('/kb/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    a = KnowledgeArticle.query.get_or_404(article_id)
    return jsonify(a.to_dict())


@kb_bp.route('/kb/articles/<int:article_id>', methods=['PUT'])
def update_article(article_id):
    a = KnowledgeArticle.query.get_or_404(article_id)
    data = request.get_json() or {}

    for field in ['title', 'category', 'content']:
        if field in data:
            setattr(a, field, data[field])

    if 'scope' in data:
        scope_raw = (data.get('scope') or '').lower()
        try:
            a.scope = KnowledgeScope(scope_raw)
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400

    if 'tags' in data:
        a.tags = data.get('tags') or []

    db.session.commit()
    return jsonify(a.to_dict())


@kb_bp.route('/kb/articles/<int:article_id>', methods=['DELETE'])
def delete_article(article_id):
    a = KnowledgeArticle.query.get_or_404(article_id)
    db.session.delete(a)
    db.session.commit()
    return jsonify({'message': 'Article deleted'})


@kb_bp.route('/kb/scopes', methods=['GET'])
def kb_scopes():
    return jsonify({
        'scopes': [{'value': e.value, 'label': e.value.upper()} for e in KnowledgeScope]
    })
