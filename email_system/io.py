from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import EmailRecord


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _get(obj: Dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def _normalize_address(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("address") or value.get("email") or value.get("name") or ""
    if isinstance(value, str):
        return value
    return ""


def _normalize_address_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [addr for addr in (_normalize_address(v) for v in value) if addr]
    if isinstance(value, str):
        return [value]
    return []


def _normalize_attachments(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        names = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("filename") or item.get("fileName")
                if name:
                    names.append(name)
        return names
    return []


def _record_from_json(obj: Dict[str, Any]) -> EmailRecord:
    message_id = _get(obj, ["message_id", "messageId", "id"], "")
    conversation_id = _get(obj, ["conversation_id", "conversationId", "thread_id", "threadId"], "")
    subject = _get(obj, ["subject", "Subject"], "")
    body = _get(obj, ["body", "Body", "content", "Content"], "")
    sender = _normalize_address(_get(obj, ["from", "sender", "Sender"], ""))
    to_list = _normalize_address_list(_get(obj, ["to", "toRecipients", "To"], []))
    cc_list = _normalize_address_list(_get(obj, ["cc", "ccRecipients", "Cc"], []))
    attachments = _normalize_attachments(_get(obj, ["attachments", "attachmentNames"], []))
    date_val = _get(obj, ["date", "sentDateTime", "receivedDateTime"], None)
    date = _parse_date(date_val)
    raw = obj
    if not conversation_id:
        conversation_id = message_id or subject.lower().strip()
    if not message_id:
        message_id = f"msg_{hash(subject + body)}"
    return EmailRecord(
        message_id=message_id,
        conversation_id=conversation_id,
        subject=subject,
        body=body,
        sender=sender,
        to=to_list,
        cc=cc_list,
        date=date,
        attachments=attachments,
        raw=raw,
    )


def _load_json_file(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    return [data]


def load_emails(path: str | Path) -> List[EmailRecord]:
    path = Path(path)
    records: List[EmailRecord] = []
    if path.is_dir():
        for file in sorted(path.glob("*.json")):
            for obj in _load_json_file(file):
                records.append(_record_from_json(obj))
        return records
    for obj in _load_json_file(path):
        records.append(_record_from_json(obj))
    return records


def save_output(path: str | Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

