import os
from uuid import uuid4


def _client():
    os.environ['ADMIN_USERNAME'] = 'admin'
    os.environ['ADMIN_PASSWORD'] = 'admin'
    os.environ['CELERY_ALWAYS_EAGER'] = '1'
    from db_ai_ops import create_app

    app = create_app()
    return app.test_client()


def _login(client):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert response.status_code == 200
    return response.get_json()['token']


def _create_host_and_credential(client, headers):
    suffix = uuid4().hex[:8]
    credential_response = client.post('/api/credentials', json={
        'name': f'mysql-init-{suffix}',
        'cred_type': 'db_password',
        'username': 'admin',
        'secret': 'Strong-Mysql-Password_42!'
    }, headers=headers)
    assert credential_response.status_code == 201

    host_response = client.post('/api/hosts', json={
        'name': f'mysql-target-{suffix}',
        'host': '192.0.2.20',
        'port': 22,
        'os_type': 'linux',
        'username': 'root',
        'password': 'Strong-SSH-Password_42!',
        'enabled': True
    }, headers=headers)
    assert host_response.status_code == 201
    return host_response.get_json()['id'], credential_response.get_json()['id']


def test_mysql_deployment_options_and_dry_run():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}
    host_id, credential_id = _create_host_and_credential(client, headers)

    options = client.get('/api/ops/deployments/mysql/options', headers=headers)
    assert options.status_code == 200
    assert {item['value'] for item in options.get_json()['topologies']} == {'single-node', 'master-slave', 'mgr'}

    response = client.post('/api/ops/tasks', json={
        'category': 'database',
        'action': 'mysql-deploy',
        'payload': {
            'topology': 'single-node',
            'target_ids': [host_id],
            'mysql_version': '8.4.6',
            'mysql_port': 3306,
            'server_specs': 'auto',
            'mysql_data_dir_base': '/database/mysql',
            'mysql_admin_user': 'admin',
            'initial_credential_id': credential_id,
            'confirmed': True,
            'dry_run': True
        }
    }, headers=headers)
    assert response.status_code == 201
    task = response.get_json()

    detail = client.get(f"/api/ops/tasks/{task['id']}", headers=headers)
    assert detail.status_code == 200
    result = detail.get_json()
    assert result['status'] == 'success'
    assert result['result']['mode'] == 'dry-run'
    assert result['result']['preview']['host_key_checking'] is True
    assert result['result']['preview']['host_hardening'] == 'disabled'
    assert 'Strong-Mysql-Password_42!' not in str(result)
    assert 'Strong-SSH-Password_42!' not in str(result)


def test_mysql_deployment_rejects_plaintext_password_fields():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    response = client.post('/api/ops/tasks', json={
        'category': 'database',
        'action': 'mysql-deploy',
        'payload': {
            'password': 'not-allowed',
            'topology': 'single-node',
            'target_ids': [1],
            'initial_credential_id': 1,
            'confirmed': True,
            'dry_run': True
        }
    }, headers=headers)
    assert response.status_code == 400
    assert '明文密码' in response.get_json()['error']


def test_mysql_deployment_apply_requires_known_hosts_and_redacts_output(monkeypatch, tmp_path):
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}
    host_id, credential_id = _create_host_and_credential(client, headers)

    known_hosts = tmp_path / 'known_hosts'
    known_hosts.write_text('192.0.2.20 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestOnly\n', encoding='utf-8')
    monkeypatch.setenv('DEPLOYMENT_KNOWN_HOSTS_PATH', str(known_hosts))

    captured = {}

    class Completed:
        returncode = 0
        stdout = 'connected with Strong-SSH-Password_42! and Strong-Mysql-Password_42!'
        stderr = ''

    def fake_run(command, **kwargs):
        captured['command'] = command
        captured['env'] = kwargs['env']
        return Completed()

    import db_ai_ops.deployment.mysql_runner as runner
    monkeypatch.setattr(runner.subprocess, 'run', fake_run)

    with client.application.app_context():
        result = runner.run_mysql_deployment({
            'topology': 'single-node',
            'target_ids': [host_id],
            'mysql_version': '8.4.6',
            'mysql_port': 3306,
            'server_specs': 'auto',
            'mysql_data_dir_base': '/database/mysql',
            'mysql_admin_user': 'admin',
            'initial_credential_id': credential_id,
            'confirmed': True,
            'dry_run': False
        })

    assert captured['command'][0] == 'ansible-playbook'
    assert captured['env']['ANSIBLE_HOST_KEY_CHECKING'] == 'True'
    assert result['mode'] == 'apply'
    assert 'Strong-SSH-Password_42!' not in result['stdout']
    assert 'Strong-Mysql-Password_42!' not in result['stdout']
    assert result['stdout'].count('***REDACTED***') == 2
