import os

import pytest

from db_ai_ops.security import open_private_output, run_argv
from db_ai_ops.tasks.backup_tasks import _validate_identifier
from db_ai_ops.tasks.ops_tasks import _ssh_exec


def test_run_argv_never_invokes_shell(monkeypatch):
    captured = {}

    class Completed:
        returncode = 0

    def fake_run(argv, **kwargs):
        captured['argv'] = argv
        captured['kwargs'] = kwargs
        return Completed()

    import db_ai_ops.security as security
    monkeypatch.setattr(security.subprocess, 'run', fake_run)

    run_argv(['echo', 'value; touch /tmp/should-not-run'], timeout=5)

    assert captured['argv'] == ['echo', 'value; touch /tmp/should-not-run']
    assert captured['kwargs']['shell'] is False
    assert captured['kwargs']['check'] is True


def test_open_private_output_sets_owner_only_permissions(tmp_path):
    output = tmp_path / 'backup.sql'
    with open_private_output(output) as handle:
        handle.write(b'backup')

    assert output.read_bytes() == b'backup'
    assert os.stat(output).st_mode & 0o777 == 0o600


@pytest.mark.parametrize('value', ['db;drop', 'db name', 'db\nname', "db'--"])
def test_backup_identifier_rejects_command_control(value):
    with pytest.raises(ValueError):
        _validate_identifier(value)


def test_ssh_requires_known_hosts_before_connecting(monkeypatch):
    monkeypatch.setenv('SSH_KNOWN_HOSTS_PATH', '/tmp/does-not-exist-for-dbops-test')

    class Host:
        username = 'root'
        password = 'not-used'
        credential_id = None
        host = '192.0.2.10'
        port = 22

    with pytest.raises(Exception, match='known_hosts'):
        _ssh_exec(Host(), 'hostname')
