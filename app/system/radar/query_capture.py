from __future__ import annotations

import contextvars
import json
import time
from functools import wraps
from typing import Any

from tortoise.backends.sqlite.client import SqliteClient, SqliteTransactionWrapper

from app.system.radar.ctx import CTX_RADAR

# 递归防护：Radar 自身写入 DB 时设为 True，避免捕获自身产生的 SQL
CTX_RADAR_WRITING: contextvars.ContextVar[bool] = contextvars.ContextVar("radar_writing", default=False)

_originals: dict[str, Any] = {}


def _serialize_params(values: Any) -> str | None:
    if values is None:
        return None
    try:
        if isinstance(values, (list, tuple)) and len(values) > 100:
            values = list(values[:100])
        return json.dumps(values, ensure_ascii=False, default=str)
    except Exception:
        return str(values)[:2000]


def _detect_operation(query: str) -> str:
    q = query.strip()
    if not q:
        return "UNKNOWN"
    first_word = q.split(maxsplit=1)[0].upper()
    if first_word in ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "PRAGMA"):
        return first_word
    return "OTHER"


def _make_patched(original: Any) -> Any:
    @wraps(original)
    async def patched(self: Any, query: str, values: Any = None) -> Any:
        radar_ctx = CTX_RADAR.get()
        if radar_ctx is None or CTX_RADAR_WRITING.get():
            return await original(self, query, values)

        start = time.monotonic()
        try:
            return await original(self, query, values)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            radar_ctx.queries.append({
                "sql": query[:5000],
                "params": _serialize_params(values),
                "operation": _detect_operation(query),
                "duration_ms": round(duration_ms, 3),
                "connection_name": getattr(self, "connection_name", "default"),
                "start_offset_ms": round((start - radar_ctx.start_mono) * 1000, 3),
            })

    return patched


def _make_patched_many(original: Any) -> Any:
    @wraps(original)
    async def patched(self: Any, query: str, values_list: list | None = None) -> Any:
        radar_ctx = CTX_RADAR.get()
        if radar_ctx is None or CTX_RADAR_WRITING.get():
            return await original(self, query, values_list)

        start = time.monotonic()
        try:
            return await original(self, query, values_list)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            radar_ctx.queries.append({
                "sql": query[:5000],
                "params": f"[{len(values_list or [])} rows]",
                "operation": _detect_operation(query),
                "duration_ms": round(duration_ms, 3),
                "connection_name": getattr(self, "connection_name", "default"),
                "start_offset_ms": round((start - radar_ctx.start_mono) * 1000, 3),
            })

    return patched


def install_query_capture() -> None:
    if _originals:
        return  # 已安装，跳过

    for cls in (SqliteClient, SqliteTransactionWrapper):
        cls_name = cls.__name__
        for method_name in ("execute_query", "execute_insert", "execute_query_dict"):
            original = getattr(cls, method_name, None)
            if original is None:
                continue
            _originals[f"{cls_name}.{method_name}"] = original
            setattr(cls, method_name, _make_patched(original))

        original_many = getattr(cls, "execute_many", None)
        if original_many:
            _originals[f"{cls_name}.execute_many"] = original_many
            cls.execute_many = _make_patched_many(original_many)


def uninstall_query_capture() -> None:
    for cls in (SqliteClient, SqliteTransactionWrapper):
        cls_name = cls.__name__
        for method_name in ("execute_query", "execute_insert", "execute_query_dict", "execute_many"):
            key = f"{cls_name}.{method_name}"
            if key in _originals:
                setattr(cls, method_name, _originals[key])

    _originals.clear()
