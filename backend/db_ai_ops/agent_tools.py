import re
from typing import Any, Dict, List, Optional, Tuple

from db_ai_ops.extensions import db
from db_ai_ops.models import Backup, BackupStatus, Host, InspectionReport, InspectionReportStatus, OperationTask, OperationTaskStatus
from db_ai_ops.tasks.ops_tasks import run_inspection_report, run_operation_task


def _is_readonly_tool(name: str) -> bool:
    return name in {"backup.stats", "host.search"}


def _resolve_host_ids(targets: List[Any]) -> Tuple[List[int], List[str]]:
    ids: List[int] = []
    missing: List[str] = []
    for t in (targets or []):
        if t is None:
            continue
        if isinstance(t, int):
            h = Host.query.get(t)
            if h and h.enabled:
                ids.append(h.id)
            else:
                missing.append(str(t))
            continue
        s = str(t).strip()
        if not s:
            continue
        if re.fullmatch(r"\d+", s):
            h = Host.query.get(int(s))
            if h and h.enabled:
                ids.append(h.id)
            else:
                missing.append(s)
            continue
        h = Host.query.filter(Host.enabled.is_(True)).filter((Host.host == s) | (Host.name == s)).first()
        if h:
            ids.append(h.id)
        else:
            missing.append(s)
    uniq = []
    seen = set()
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        uniq.append(i)
    return uniq, missing


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "backup.stats",
            "description": "查询备份统计信息（只读）",
            "readonly": True,
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
        },
        {
            "name": "host.search",
            "description": "按关键字搜索主机（只读）",
            "readonly": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "关键字（IP/主机名/备注等）"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}
                },
                "required": ["q"],
                "additionalProperties": False
            }
        },
        {
            "name": "ops.exec_script",
            "description": "在目标主机上执行 SSH 命令（需要确认）",
            "readonly": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {"type": "array", "items": {"type": ["integer", "string"]}},
                    "command": {"type": "string"}
                },
                "required": ["targets", "command"],
                "additionalProperties": False
            }
        },
        {
            "name": "ops.restart_service",
            "description": "在目标主机上重启 systemd 服务（需要确认）",
            "readonly": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {"type": "array", "items": {"type": ["integer", "string"]}},
                    "service": {"type": "string"}
                },
                "required": ["targets", "service"],
                "additionalProperties": False
            }
        },
        {
            "name": "inspection.run",
            "description": "触发巡检并生成报告（需要确认）",
            "readonly": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["server", "middleware", "database"], "default": "server"},
                    "targets": {"type": "array", "items": {"type": ["integer", "string"]}}
                },
                "required": ["scope", "targets"],
                "additionalProperties": False
            }
        }
    ]


def execute_tool(name: str, args: Dict[str, Any], *, created_by: Optional[str] = None) -> Dict[str, Any]:
    if name == "backup.stats":
        from db_ai_ops.models import Database

        total_databases = Database.query.filter_by(enabled=True).count()
        total_backups = Backup.query.count()
        successful_backups = Backup.query.filter_by(status=BackupStatus.SUCCESS).count()
        failed_backups = Backup.query.filter_by(status=BackupStatus.FAILED).count()
        total_size = db.session.query(db.func.sum(Backup.file_size)).scalar() or 0
        return {
            "total_databases": total_databases,
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "failed_backups": failed_backups,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

    if name == "host.search":
        q = (args.get("q") or "").strip()
        if not q:
            raise ValueError("q 不能为空")
        limit = int(args.get("limit") or 20)
        limit = max(1, min(limit, 50))
        like = f"%{q}%"
        rows = (
            Host.query.filter(Host.enabled.is_(True))
            .filter((Host.host.like(like)) | (Host.name.like(like)) | (Host.remark.like(like)) | (Host.owner.like(like)))
            .order_by(Host.updated_at.desc())
            .limit(limit)
            .all()
        )
        return {"hosts": [h.to_dict() for h in rows]}

    if name in {"ops.exec_script", "ops.restart_service"}:
        targets = args.get("targets") or []
        target_ids, missing = _resolve_host_ids(targets)
        if missing:
            raise ValueError(f"未找到主机: {', '.join(missing[:10])}")
        if not target_ids:
            raise ValueError("targets 不能为空")

        payload: Dict[str, Any] = {"target_ids": target_ids}
        if name == "ops.exec_script":
            command = (args.get("command") or "").strip()
            if not command:
                raise ValueError("command 不能为空")
            payload["command"] = command
            action = "exec-script"
        else:
            service = (args.get("service") or "").strip()
            if not service:
                raise ValueError("service 不能为空")
            payload["service"] = service
            action = "restart-service"

        t = OperationTask(
            category="server",
            action=action,
            payload=payload,
            status=OperationTaskStatus.PENDING,
            created_by=created_by
        )
        db.session.add(t)
        db.session.commit()
        try:
            run_operation_task.delay(t.id)
        except Exception:
            run_operation_task.apply(args=[t.id])
        return {"task": t.to_dict()}

    if name == "inspection.run":
        scope = (args.get("scope") or "server").strip()
        targets = args.get("targets") or []
        target_ids, missing = _resolve_host_ids(targets) if scope == "server" else ([], [])
        if scope == "server":
            if missing:
                raise ValueError(f"未找到主机: {', '.join(missing[:10])}")
            if not target_ids:
                raise ValueError("targets 不能为空")
        r = InspectionReport(
            scope=scope,
            target_summary=f"{scope}:{len(target_ids)}",
            status=InspectionReportStatus.PENDING,
            created_by=created_by
        )
        db.session.add(r)
        db.session.commit()
        try:
            run_inspection_report.delay(r.id, {"target_ids": target_ids})
        except Exception:
            run_inspection_report.apply(args=[r.id, {"target_ids": target_ids}])
        return {"report": r.to_dict()}

    raise ValueError("unknown tool")


def is_readonly(name: str) -> bool:
    return _is_readonly_tool(name)

