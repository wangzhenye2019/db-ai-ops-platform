"""Secure adapter that runs the vendored dbops MySQL Ansible playbooks.

Secrets are resolved only while a task is running.  They are written to a
0600 temporary inventory, redacted from output, and removed with the task
workspace.  The adapter purposely requires an operator-provided known_hosts
file instead of accepting unknown SSH host keys.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml
from flask import current_app

from db_ai_ops.crypto import decrypt_text
from db_ai_ops.models import Credential, CredentialType, Host


SUPPORTED_TOPOLOGIES = {"single-node", "master-slave", "mgr"}
SUPPORTED_VERSION = re.compile(r"^(5\.7|8\.0|8\.4)\.\d{1,3}$")
SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,31}$")
SAFE_DATA_DIR = re.compile(r"^/[A-Za-z0-9_./-]{1,220}$")
SAFE_SERVER_SPECS = re.compile(r"^(auto|[1-9]\d{0,2}c[1-9]\d{0,3}g)$")


class DeploymentValidationError(ValueError):
    """Raised when a deployment request cannot be safely executed."""


def _deployment_root() -> Path:
    configured = os.getenv("DEPLOYMENT_DBOPS_ROOT")
    candidates = [
        Path(configured) if configured else None,
        Path("/app/deployments/dbops_mysql"),
        Path(__file__).resolve().parents[3] / "deployments" / "dbops_mysql",
    ]
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate
    raise DeploymentValidationError(
        "找不到 dbops MySQL 自动化资产。请设置 DEPLOYMENT_DBOPS_ROOT。"
    )


def _read_credential_secret(credential_id: Any) -> tuple[Credential, str]:
    try:
        credential_id = int(credential_id)
    except (TypeError, ValueError) as exc:
        raise DeploymentValidationError("凭据 ID 必须是整数") from exc

    credential = Credential.query.get(credential_id)
    if not credential or not credential.enabled:
        raise DeploymentValidationError("部署凭据不存在或已禁用")
    if not credential.secret_encrypted:
        raise DeploymentValidationError("部署凭据没有保存密钥内容")

    secret = decrypt_text(credential.secret_encrypted, current_app.config["SECRET_KEY"])
    if not secret:
        raise DeploymentValidationError("无法读取部署凭据")
    return credential, secret


def _passwords_from_credential(credential_id: Any, admin_username: str) -> tuple[dict[str, str], list[str]]:
    credential, raw_secret = _read_credential_secret(credential_id)
    if credential.cred_type not in {CredentialType.DB_PASSWORD, CredentialType.GENERIC}:
        raise DeploymentValidationError("初始化凭据必须是 DB_PASSWORD 或 GENERIC 类型")

    try:
        parsed = json.loads(raw_secret)
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    if parsed and not isinstance(parsed, dict):
        raise DeploymentValidationError("GENERIC 初始化凭据必须为密码文本或 JSON 对象")

    primary_password = str(parsed.get("mysql_admin_password") if parsed else raw_secret).strip()
    if not primary_password:
        raise DeploymentValidationError("初始化凭据中缺少 mysql_admin_password")
    if len(primary_password) < 8:
        raise DeploymentValidationError("MySQL 管理员密码至少需要 8 个字符")

    def _get(name: str, fallback: str | None = None) -> str:
        value = str(parsed.get(name, "")).strip() if parsed else ""
        return value or fallback or secrets.token_urlsafe(24)

    # Only mysql_admin_password is required from the credential.  The other
    # account passwords are random, task-local values and never emitted.
    values = {
        "mysql_admin_user": admin_username,
        "mysql_admin_password": primary_password,
        "mysql_admin_127_password": _get("mysql_admin_127_password", primary_password),
        "mysql_user_password": _get("mysql_user_password"),
        "mysql_rple_password": _get("mysql_rple_password"),
        "mysql_mha_password": _get("mysql_mha_password"),
        "mysql_backup_password": _get("mysql_backup_password"),
        "mysql_mgr_password": _get("mysql_mgr_password"),
        "mysql_monitor_password": _get("mysql_monitor_password"),
        "mysql_kha_password": _get("mysql_kha_password"),
    }
    return values, [value for value in values.values() if value]


def _resolve_host(host_id: Any) -> tuple[Host, dict[str, Any], list[str]]:
    try:
        host_id = int(host_id)
    except (TypeError, ValueError) as exc:
        raise DeploymentValidationError("target_ids 必须是主机 ID 数组") from exc

    host = Host.query.get(host_id)
    if not host or not host.enabled:
        raise DeploymentValidationError(f"主机 {host_id} 不存在或已禁用")
    if not host.username:
        raise DeploymentValidationError(f"主机 {host.name} 未配置 SSH 用户名")

    try:
        address = str(ipaddress.ip_address(host.host))
    except ValueError as exc:
        raise DeploymentValidationError(
            f"主机 {host.name} 的地址必须是 IPv4 或 IPv6，当前不接受域名"
        ) from exc

    password = host.password or ""
    if not password and host.credential_id:
        ssh_credential, password = _read_credential_secret(host.credential_id)
        if ssh_credential.cred_type not in {CredentialType.SSH_PASSWORD, CredentialType.GENERIC}:
            raise DeploymentValidationError(f"主机 {host.name} 绑定的凭据不是 SSH 凭据")
    if not password:
        raise DeploymentValidationError(f"主机 {host.name} 未配置 SSH 密码或凭据")

    inventory_name = f"host_{host.id}"
    return host, {
        "ansible_host": address,
        "ansible_port": int(host.port or 22),
        "ansible_user": host.username,
        "ansible_password": password,
        "ansible_connection": "paramiko",
        "ansible_become": True,
        "ansible_become_method": "sudo",
    }, [password]


def _validate_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DeploymentValidationError("部署载荷必须是 JSON 对象")

    topology = str(payload.get("topology") or "").strip().lower()
    if topology not in SUPPORTED_TOPOLOGIES:
        raise DeploymentValidationError("topology 仅支持 single-node、master-slave 或 mgr")

    target_ids = payload.get("target_ids") or []
    if not isinstance(target_ids, list) or not target_ids:
        raise DeploymentValidationError("target_ids 至少需要指定一台启用的主机")
    if len(target_ids) != len(set(map(str, target_ids))):
        raise DeploymentValidationError("target_ids 不能包含重复主机")
    if topology == "single-node" and len(target_ids) != 1:
        raise DeploymentValidationError("single-node 必须且只能选择一台主机")
    if topology == "master-slave" and len(target_ids) < 2:
        raise DeploymentValidationError("master-slave 至少需要一台主库和一台从库")
    if topology == "mgr" and not 3 <= len(target_ids) <= 9:
        raise DeploymentValidationError("mgr 必须选择 3 至 9 台主机")

    version = str(payload.get("mysql_version") or "8.4.6").strip()
    if not SUPPORTED_VERSION.fullmatch(version):
        raise DeploymentValidationError("mysql_version 仅支持 5.7.x、8.0.x 或 8.4.x")

    try:
        mysql_port = int(payload.get("mysql_port", 3306))
    except (TypeError, ValueError) as exc:
        raise DeploymentValidationError("mysql_port 必须是整数") from exc
    if not 1024 <= mysql_port <= 65535:
        raise DeploymentValidationError("mysql_port 必须在 1024 到 65535 之间")

    server_specs = str(payload.get("server_specs") or "auto").strip().lower()
    if not SAFE_SERVER_SPECS.fullmatch(server_specs):
        raise DeploymentValidationError("server_specs 必须为 auto 或如 4c8g 的规格")

    mysql_admin_user = str(payload.get("mysql_admin_user") or "admin").strip()
    if not SAFE_NAME.fullmatch(mysql_admin_user):
        raise DeploymentValidationError("mysql_admin_user 只能使用字母、数字和下划线")

    mysql_data_dir_base = str(payload.get("mysql_data_dir_base") or "/database/mysql").strip()
    if not SAFE_DATA_DIR.fullmatch(mysql_data_dir_base) or ".." in mysql_data_dir_base.split("/"):
        raise DeploymentValidationError("mysql_data_dir_base 必须是安全的绝对 Linux 路径")

    if not payload.get("initial_credential_id"):
        raise DeploymentValidationError("必须指定 initial_credential_id，且不得在任务载荷中传入明文密码")

    if not payload.get("confirmed"):
        raise DeploymentValidationError("部署会修改远端主机；请在复核参数后将 confirmed 设为 true")

    try:
        timeout_seconds = int(payload.get("timeout_seconds", 3600))
    except (TypeError, ValueError) as exc:
        raise DeploymentValidationError("timeout_seconds 必须是整数") from exc

    return {
        "topology": topology,
        "target_ids": target_ids,
        "mysql_version": version,
        "mysql_port": mysql_port,
        "server_specs": server_specs,
        "mysql_admin_user": mysql_admin_user,
        "mysql_data_dir_base": mysql_data_dir_base.rstrip("/"),
        "initial_credential_id": payload.get("initial_credential_id"),
        "replication_grant_hosts": str(payload.get("replication_grant_hosts") or "%").strip(),
        "dry_run": bool(payload.get("dry_run", False)),
        "timeout_seconds": min(max(timeout_seconds, 60), 14400),
    }


def _runtime_variables(request: dict[str, Any], passwords: dict[str, str], host_addresses: list[str]) -> tuple[dict[str, Any], str]:
    port = request["mysql_port"]
    version = request["mysql_version"]
    variables = {
        "mysql_version": version,
        "mysql_port": port,
        "server_specs": request["server_specs"],
        "db_type": "mysql",
        "mysql_packages_dir": "../downloads/",
        "mysql_user": "mysql",
        "mysql_group": "mysql",
        "mysql_data_dir_base": request["mysql_data_dir_base"],
        "mysql_software_dir": f"/database/mysql/base/{version}",
        "mysql_service_name": f"mysql{port}",
        "mysql_rple_user": "repl",
        "mysql_mha_user": "mha",
        "mysql_backup_user": "backup",
        "mysql_mgr_user": "repl",
        "mysql_monitor_user": "monitor",
        "mysql_kha_user": "kha",
        "mysql_binlog_format": "row",
        "mysql_innodb_log_buffer_size": "64M",
        "mysql_innodb_open_files": 65535,
        "mysql_max_connections": 1000,
        "mysql_thread_cache_size": 256,
        "mysql_character_set_server": "utf8mb4",
        "mysql_transaction_isolation": "READ-COMMITTED",
        "mysql_default_time_zone": "+8:00",
        "mysql57_innodb_log_files_in_group": 16,
        "mysql57_innodb_log_file_size": "256M",
        "fcs_skip_db_mount_verification": True,
        "fcs_skip_check_ntpd_or_chrony_running": True,
        "fcs_auto_download_mysql": True,
        "fcs_auto_download": False,
        "fcs_create_mysql_fast_login": True,
        "fcs_backup_script_create_backup_user": False,
        "fcs_role_mysqld_exporter_create_monitor_user": False,
        "fcs_mysql_use_jemalloc": False,
        "fcs_use_greatsql_ha": False,
        "fcs_mysql_fast_login_have_prompt": False,
        "fcs_create_mysql_fast_login_name": f"db{port}",
        **passwords,
    }

    topology = request["topology"]
    if topology == "single-node":
        return variables, "db_ai_safe_single_node.yml"
    if topology == "master-slave":
        variables.update({
            "master_ip": host_addresses[0],
            "slave_ips": host_addresses[1:],
            "sub_nets": request["replication_grant_hosts"],
        })
        return variables, "db_ai_safe_master_slave.yml"
    variables.update({
        "mysql_mgr_hosts": host_addresses,
        "mysql_mgr_port": port * 10 + 1,
        "sub_nets": request["replication_grant_hosts"],
        "mgr_use_random_uuid": 1,
    })
    return variables, "db_ai_safe_mgr.yml"


def _safe_advanced_variables() -> dict[str, str]:
    return {
        "mycnf_dir": "{{ mysql_data_dir_base }}/etc/{{ mysql_port }}",
        "datadir": "{{ mysql_data_dir_base }}/data/{{ mysql_port }}",
        "tmpdir": "{{ mysql_data_dir_base }}/tmp/{{ mysql_port }}",
        "binlog_dir": "{{ mysql_data_dir_base }}/log/binlog/{{ mysql_port }}",
        "relaylog_dir": "{{ mysql_data_dir_base }}/log/relaylog/{{ mysql_port }}",
        "redolog_dir": "{{ mysql_data_dir_base }}/log/redolog/{{ mysql_port }}",
        "socket_dir": "{{ datadir }}",
        "mysqlx_socket_dir": "{{ datadir }}",
        "auditlog_dir": "{{ datadir }}",
        "slowlog_dir": "{{ datadir }}",
        "errlog_dir": "{{ datadir }}",
        "generallog_dir": "{{ datadir }}",
        "socket": "{{ socket_dir }}/mysql.sock",
        "mysqlx_socket": "{{ mysqlx_socket_dir }}/mysqlx.sock",
        "mysql_package": "{{ 'mysql-' + mysql_version + '-linux-' + ('glibc2.12' if mysql_version.startswith('5.') else 'glibc2.17') + '-x86_64' + ('.tar.gz' if mysql_version.startswith('5.') else '-minimal.tar.xz') }}",
    }


def _write_yaml(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(value, stream, allow_unicode=True, default_flow_style=False, sort_keys=False)
    os.chmod(path, mode)


def _redact(text: str, secrets_to_redact: list[str]) -> str:
    clean = text or ""
    for secret in sorted(set(secrets_to_redact), key=len, reverse=True):
        if secret and len(secret) >= 4:
            clean = clean.replace(secret, "***REDACTED***")
    return clean


def _prepare_workspace(request: dict[str, Any]) -> tuple[Path, dict[str, Any], list[str], str]:
    root = _deployment_root()
    work_base = os.getenv("DEPLOYMENT_WORK_DIR") or None
    work_dir = Path(tempfile.mkdtemp(prefix="db-ai-mysql-", dir=work_base))
    playbook_root = work_dir / "dbops_mysql"
    shutil.copytree(root, playbook_root)

    hosts: dict[str, Any] = {}
    addresses: list[str] = []
    sensitive: list[str] = []
    for host_id in request["target_ids"]:
        host, host_variables, host_secrets = _resolve_host(host_id)
        hosts[f"host_{host.id}"] = host_variables
        addresses.append(host_variables["ansible_host"])
        sensitive.extend(host_secrets)

    passwords, password_secrets = _passwords_from_credential(
        request["initial_credential_id"], request["mysql_admin_user"]
    )
    sensitive.extend(password_secrets)
    variables, playbook_name = _runtime_variables(request, passwords, addresses)

    inventory = {"all": {"children": {"dbops_mysql": {"hosts": hosts}}}}
    _write_yaml(work_dir / "inventory.yml", inventory)
    _write_yaml(playbook_root / "playbooks" / "common_config.yml", variables)
    _write_yaml(playbook_root / "playbooks" / "advanced_config.yml", _safe_advanced_variables())

    vars_dir = playbook_root / "playbooks" / "vars"
    if request["topology"] == "master-slave":
        _write_yaml(vars_dir / "var_master_slave.yml", {
            "master_ip": addresses[0],
            "slave_ips": addresses[1:],
            "sub_nets": request["replication_grant_hosts"],
        })
    elif request["topology"] == "mgr":
        _write_yaml(vars_dir / "var_mgr.yml", {
            "mysql_mgr_hosts": addresses,
            "mysql_mgr_port": request["mysql_port"] * 10 + 1,
            "sub_nets": request["replication_grant_hosts"],
        })

    ansible_config = """[defaults]\nhost_key_checking = True\ninterpreter_python = auto_silent\nforks = 5\ntimeout = 15\nretry_files_enabled = False\ndisplay_args_to_stdout = False\nstdout_callback = default\n[ssh_connection]\npipelining = True\n"""
    config_path = work_dir / "ansible.cfg"
    config_path.write_text(ansible_config, encoding="utf-8")
    os.chmod(config_path, 0o600)

    return work_dir, {
        "playbook_root": playbook_root,
        "inventory": work_dir / "inventory.yml",
        "config": config_path,
        "playbook": playbook_root / "playbooks" / playbook_name,
        "addresses": addresses,
    }, sensitive, playbook_name


def run_mysql_deployment(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate, plan and optionally run one MySQL deployment request."""
    request = _validate_request(payload)
    workspace: Path | None = None
    try:
        workspace, paths, sensitive, playbook_name = _prepare_workspace(request)
        preview = {
            "topology": request["topology"],
            "mysql_version": request["mysql_version"],
            "mysql_port": request["mysql_port"],
            "server_specs": request["server_specs"],
            "target_count": len(request["target_ids"]),
            "target_addresses": paths["addresses"],
            "playbook": playbook_name,
            "host_key_checking": True,
            "host_hardening": "disabled",
        }
        if request["dry_run"]:
            return {"mode": "dry-run", "preview": preview, "exit_code": 0, "stdout": "", "stderr": ""}

        known_hosts = os.getenv("DEPLOYMENT_KNOWN_HOSTS_PATH", "").strip()
        if not known_hosts or not Path(known_hosts).is_file():
            raise DeploymentValidationError(
                "生产部署需要 DEPLOYMENT_KNOWN_HOSTS_PATH 指向已审核的 known_hosts 文件"
            )
        ssh_dir = workspace / ".ssh"
        ssh_dir.mkdir(mode=0o700)
        shutil.copy2(known_hosts, ssh_dir / "known_hosts")
        os.chmod(ssh_dir / "known_hosts", 0o600)

        command = [
            "ansible-playbook",
            "--inventory", str(paths["inventory"]),
            str(paths["playbook"]),
        ]
        env = os.environ.copy()
        env.update({
            "ANSIBLE_CONFIG": str(paths["config"]),
            "ANSIBLE_HOST_KEY_CHECKING": "True",
            "HOME": str(workspace),
            "PYTHONUNBUFFERED": "1",
        })
        completed = subprocess.run(
            command,
            cwd=str(paths["playbook_root"] / "playbooks"),
            env=env,
            capture_output=True,
            text=True,
            timeout=request["timeout_seconds"],
            check=False,
        )
        return {
            "mode": "apply",
            "preview": preview,
            "exit_code": completed.returncode,
            "stdout": _redact(completed.stdout, sensitive),
            "stderr": _redact(completed.stderr, sensitive),
        }
    except subprocess.TimeoutExpired as exc:
        raise DeploymentValidationError(f"部署执行超时：{request['timeout_seconds']} 秒") from exc
    finally:
        if workspace:
            shutil.rmtree(workspace, ignore_errors=True)
