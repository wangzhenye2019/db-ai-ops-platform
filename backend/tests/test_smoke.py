import io
import os


def _client():
    os.environ['ADMIN_USERNAME'] = 'admin'
    os.environ['ADMIN_PASSWORD'] = 'admin'
    os.environ['CELERY_ALWAYS_EAGER'] = '1'
    from db_ai_ops import create_app

    app = create_app()
    return app.test_client()


def _login(client):
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200
    data = r.get_json()
    assert 'token' in data
    return data['token']


def test_auth_and_core_endpoints():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    for path in [
        '/api/auth/me',
        '/api/databases',
        '/api/hosts',
        '/api/middlewares',
        '/api/systems',
        '/api/credentials',
        '/api/ips',
        '/api/dict/idcs',
        '/api/dict/tags',
        '/api/kb/articles',
        '/api/ops/tasks',
        '/api/inspection/reports',
        '/api/audit/logs?limit=5'
    ]:
        r = client.get(path, headers=headers)
        assert r.status_code == 200


def test_import_hosts_dry_run():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    csv_content = (
        'name,host,port,os_type,username,password,enabled,tags\n'
        'web1,10.0.0.10,22,linux,root,,1,prod\n'
    ).encode('utf-8')
    data = {'file': (io.BytesIO(csv_content), 'hosts.csv')}
    r = client.post(
        '/api/import/hosts?dry_run=1&mode=insert',
        data=data,
        headers=headers,
        content_type='multipart/form-data'
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body['dry_run'] is True
    assert body['created'] == 1
    assert len(body.get('preview') or []) >= 1


def test_asset_groups_and_members():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    r = client.post('/api/assets/groups', json={'name': 'g1', 'description': 'demo'}, headers=headers)
    assert r.status_code in (201, 400)

    groups = client.get('/api/assets/groups', headers=headers)
    assert groups.status_code == 200
    gid = (groups.get_json().get('groups') or [])[0]['id']

    h = client.post('/api/hosts', json={'name': 'h-asset', 'host': '10.10.10.10', 'port': 22, 'os_type': 'linux'}, headers=headers)
    assert h.status_code in (201, 400)
    hosts = client.get('/api/hosts', headers=headers).get_json().get('hosts') or []
    hid = hosts[0]['id']

    r2 = client.post(f'/api/assets/groups/{gid}/members', json={'add': [{'type': 'host', 'id': hid}]}, headers=headers)
    assert r2.status_code == 200

    members = client.get(f'/api/assets/groups/{gid}/members', headers=headers)
    assert members.status_code == 200

    assets = client.get(f'/api/assets?group_id={gid}', headers=headers)
    assert assets.status_code == 200


def test_business_systems_crud_smoke():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    r = client.post('/api/systems', json={'name': 'order-center', 'owner': '张三', 'enabled': True}, headers=headers)
    assert r.status_code in (201, 400)

    r2 = client.get('/api/systems', headers=headers)
    assert r2.status_code == 200

    systems = r2.get_json().get('systems') or []
    sid = systems[0]['id']
    c = client.post(f'/api/systems/{sid}/contacts', json={'name': '李四', 'role': '运维'}, headers=headers)
    assert c.status_code in (201, 400)

    h = client.post('/api/hosts', json={'name': 'h-link', 'host': '10.10.20.10', 'port': 22, 'os_type': 'linux'}, headers=headers)
    assert h.status_code in (201, 400)
    hosts = client.get('/api/hosts', headers=headers).get_json().get('hosts') or []
    hid = hosts[0]['id']

    link = client.post(f'/api/systems/{sid}/links', json={'add': [{'type': 'host', 'id': hid}]}, headers=headers)
    assert link.status_code == 200

    links = client.get(f'/api/systems/{sid}/links', headers=headers)
    assert links.status_code == 200


def test_credentials_admin_smoke():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    r = client.post('/api/credentials', json={'name': 'ssh-root', 'cred_type': 'ssh_password', 'username': 'root', 'secret': 'pwd'}, headers=headers)
    assert r.status_code in (201, 400)

    lst = client.get('/api/credentials', headers=headers)
    assert lst.status_code == 200


def test_ip_assets_smoke():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    r = client.post('/api/ips', json={'ip': '10.255.0.1', 'cidr': 24, 'version': 'ipv4', 'status': 'free'}, headers=headers)
    assert r.status_code in (201, 400)
    lst = client.get('/api/ips', headers=headers)
    assert lst.status_code == 200


def test_agent_chatops_smoke():
    client = _client()
    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    tools = client.get('/api/agent/tools', headers=headers)
    assert tools.status_code == 200
    assert isinstance(tools.get_json().get('tools'), list)

    s = client.post('/api/agent/sessions', json={'title': 't'}, headers=headers)
    assert s.status_code == 201
    sid = s.get_json()['id']

    r1 = client.post(f'/api/agent/sessions/{sid}/messages', json={'content': '备份统计'}, headers=headers)
    assert r1.status_code == 200
    body = r1.get_json()
    assert 'messages' in body

    r2 = client.post(f'/api/agent/sessions/{sid}/messages', json={'content': '在 10.0.0.10 执行 `uptime`'}, headers=headers)
    assert r2.status_code == 200
    body2 = r2.get_json()
    assert body2.get('pending') is not None

    r3 = client.post(f'/api/agent/sessions/{sid}/messages', json={'content': '取消', 'cancel': True}, headers=headers)
    assert r3.status_code == 200
    body3 = r3.get_json()
    assert body3.get('pending') is None
