import re
from typing import Any, Dict, List, Optional, Tuple


_CONFIRM_WORDS = {"确认", "确定", "执行", "运行", "好的", "ok", "OK", "yes", "YES"}


def _extract_ips(text: str) -> List[str]:
    return re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text or "")


def _extract_backtick(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"`([^`]+)`", text)
    if m:
        return m.group(1).strip()
    return None


def _extract_after_keywords(text: str, keywords: List[str]) -> Optional[str]:
    if not text:
        return None
    for k in keywords:
        idx = text.find(k)
        if idx >= 0:
            rest = text[idx + len(k):].strip()
            return rest or None
    return None


def _extract_service(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"重启\s*([a-zA-Z0-9._-]+)\s*服务", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"服务\s*([a-zA-Z0-9._-]+)", text)
    if m and "重启" in text:
        return m.group(1).strip()
    return None


def _extract_command(text: str) -> Optional[str]:
    cmd = _extract_backtick(text)
    if cmd:
        return cmd
    rest = _extract_after_keywords(text, ["执行", "运行", "run", "cmd", "命令"])
    if rest:
        return rest.strip()
    return None


def _normalize_targets(ip_list: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in ip_list or []:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _missing_for_tool(name: str, args: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    if name in {"ops.exec_script", "ops.restart_service", "inspection.run"}:
        targets = args.get("targets")
        if not targets:
            missing.append("targets")
    if name == "ops.exec_script" and not (args.get("command") or "").strip():
        missing.append("command")
    if name == "ops.restart_service" and not (args.get("service") or "").strip():
        missing.append("service")
    if name == "inspection.run" and not (args.get("scope") or "").strip():
        missing.append("scope")
    return missing


def _help_text() -> str:
    return (
        "支持的能力：\n"
        "1) 备份统计：例如“备份统计/备份情况”\n"
        "2) 搜索主机：例如“搜索主机 10.0.0.10”\n"
        "3) 执行命令：例如“在 10.0.0.10 执行 `uptime`”（需要确认）\n"
        "4) 重启服务：例如“在 10.0.0.10 重启 nginx 服务”（需要确认）\n"
        "5) 巡检：例如“对 10.0.0.10 巡检”（需要确认）"
    )


def plan_next(user_text: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    text = (user_text or "").strip()
    state = session_state or {}
    pending = state.get("pending")

    if not text:
        return {"reply": _help_text()}

    if text in {"帮助", "help", "?", "？"}:
        return {"reply": _help_text()}

    if pending and isinstance(pending, dict):
        name = pending.get("name")
        args = dict(pending.get("args") or {})
        if name == "ops.exec_script":
            ips = _extract_ips(text)
            if ips:
                args["targets"] = _normalize_targets(ips)
            cmd = _extract_command(text)
            if cmd:
                args["command"] = cmd
        elif name == "ops.restart_service":
            ips = _extract_ips(text)
            if ips:
                args["targets"] = _normalize_targets(ips)
            svc = _extract_service(text)
            if svc:
                args["service"] = svc
        elif name == "inspection.run":
            ips = _extract_ips(text)
            if ips:
                args["targets"] = _normalize_targets(ips)
        missing = _missing_for_tool(name, args) if name else []
        if missing:
            return {"reply": f"还缺少参数：{', '.join(missing)}", "pending": {"name": name, "args": args}}
        return {"reply": "已补全参数，等待确认执行。", "tool_call": {"name": name, "args": args}, "requires_confirm": True}

    if "备份" in text and any(k in text for k in ["统计", "概况", "情况", "stats"]):
        return {
            "reply": "已获取备份统计。",
            "tool_call": {"name": "backup.stats", "args": {}},
            "requires_confirm": False
        }

    if any(k in text for k in ["搜索主机", "查主机", "查找主机"]):
        q = _extract_after_keywords(text, ["搜索主机", "查主机", "查找主机"]) or ""
        q = q.strip()
        if not q:
            return {"reply": "请输入要搜索的关键字（IP/主机名）。"}
        return {
            "reply": f"已搜索主机：{q}",
            "tool_call": {"name": "host.search", "args": {"q": q}},
            "requires_confirm": False
        }

    if "巡检" in text:
        targets = _normalize_targets(_extract_ips(text))
        args = {"scope": "server", "targets": targets}
        if not targets:
            return {"reply": "请提供要巡检的主机 IP（支持多个）。", "pending": {"name": "inspection.run", "args": args}}
        return {
            "reply": f"将对 {', '.join(targets)} 触发巡检，确认执行吗？",
            "tool_call": {"name": "inspection.run", "args": args},
            "requires_confirm": True
        }

    if "重启" in text and "服务" in text:
        targets = _normalize_targets(_extract_ips(text))
        service = _extract_service(text)
        args = {"targets": targets, "service": service or ""}
        missing = _missing_for_tool("ops.restart_service", args)
        if missing:
            return {"reply": f"请补充参数：{', '.join(missing)}（例如：在 10.0.0.10 重启 nginx 服务）", "pending": {"name": "ops.restart_service", "args": args}}
        return {
            "reply": f"将对 {', '.join(targets)} 重启服务 {service}，确认执行吗？",
            "tool_call": {"name": "ops.restart_service", "args": args},
            "requires_confirm": True
        }

    if any(k in text for k in ["执行", "运行", "run", "cmd", "命令"]):
        targets = _normalize_targets(_extract_ips(text))
        command = _extract_command(text) or ""
        args = {"targets": targets, "command": command}
        missing = _missing_for_tool("ops.exec_script", args)
        if missing:
            return {"reply": f"请补充参数：{', '.join(missing)}（例如：在 10.0.0.10 执行 `uptime`）", "pending": {"name": "ops.exec_script", "args": args}}
        return {
            "reply": f"将对 {', '.join(targets)} 执行命令：{command}，确认执行吗？",
            "tool_call": {"name": "ops.exec_script", "args": args},
            "requires_confirm": True
        }

    return {"reply": _help_text()}


def is_confirm_text(text: str) -> bool:
    t = (text or "").strip()
    return t in _CONFIRM_WORDS
