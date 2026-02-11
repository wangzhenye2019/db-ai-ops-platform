from flask import Blueprint, jsonify, request
from app import db
from app.models import Schedule

schedule_bp = Blueprint('schedule_bp', __name__)


@schedule_bp.route('/schedules', methods=['GET'])
def list_schedules():
    """List all schedules"""
    schedules = Schedule.query.order_by(Schedule.created_at.desc()).all()
    return jsonify({
        'schedules': [schedule.to_dict() for schedule in schedules]
    })


@schedule_bp.route('/schedules', methods=['POST'])
def create_schedule():
    """Create a new backup schedule"""
    data = request.get_json()

    required_fields = ['database_id', 'cron_expression']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    # Validate cron expression (basic format check)
    cron_parts = data['cron_expression'].split()
    if len(cron_parts) != 5:
        return jsonify({'error': 'Invalid cron expression. Format: "min hour day month weekday"'}), 400

    schedule = Schedule(
        database_id=data['database_id'],
        cron_expression=data['cron_expression'],
        enabled=data.get('enabled', True)
    )

    db.session.add(schedule)
    db.session.commit()

    return jsonify(schedule.to_dict()), 201


@schedule_bp.route('/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Get schedule details"""
    schedule = Schedule.query.get_or_404(schedule_id)
    return jsonify(schedule.to_dict())


@schedule_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Update schedule"""
    schedule = Schedule.query.get_or_404(schedule_id)
    data = request.get_json()

    for field in ['cron_expression', 'enabled']:
        if field in data:
            setattr(schedule, field, data[field])

    db.session.commit()
    return jsonify(schedule.to_dict())


@schedule_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete schedule"""
    schedule = Schedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()

    return jsonify({'message': 'Schedule deleted'})


@schedule_bp.route('/schedules/<int:schedule_id>/toggle', methods=['POST'])
def toggle_schedule(schedule_id):
    """Enable/disable schedule"""
    schedule = Schedule.query.get_or_404(schedule_id)
    schedule.enabled = not schedule.enabled
    db.session.commit()

    return jsonify({
        'message': f'Schedule {"enabled" if schedule.enabled else "disabled"}',
        'enabled': schedule.enabled
    })


@schedule_bp.route('/schedules/cron-help', methods=['GET'])
def cron_help():
    """Get cron expression help"""
    return jsonify({
        'description': 'Cron expression format: minute hour day month weekday',
        'examples': [
            {'expression': '0 2 * * *', 'description': 'Every day at 2:00 AM'},
            {'expression': '0 */6 * * *', 'description': 'Every 6 hours'},
            {'expression': '0 0 * * 0', 'description': 'Every Sunday at midnight'},
            {'expression': '30 2 * * *', 'description': 'Every day at 2:30 AM'},
            {'expression': '0 3 * * 1', 'description': 'Every Monday at 3:00 AM'}
        ],
        'fields': [
            {'name': 'minute', 'range': '0-59', 'description': 'Minute of the hour'},
            {'name': 'hour', 'range': '0-23', 'description': 'Hour of the day'},
            {'name': 'day', 'range': '1-31', 'description': 'Day of the month'},
            {'name': 'month', 'range': '1-12', 'description': 'Month of the year'},
            {'name': 'weekday', 'range': '0-6', 'description': 'Day of the week (0=Sunday)'}
        ]
    })
