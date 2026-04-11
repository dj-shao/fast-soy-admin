from __future__ import annotations

import asyncio
import sys
import time
from uuid import uuid4

from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.ctx import CTX_X_REQUEST_ID
from app.system.radar.config import RADAR_SETTINGS
from app.system.radar.ctx import CTX_RADAR, RadarRequestContext
from app.system.radar.db import flush_request_data
from app.system.radar.exceptions import format_exception_pretty


def _serialize_headers(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    result: dict[str, str] = {}
    sensitive_keys = {"authorization", "cookie", "x-api-key", "x-auth-token", "x-csrf-token"}
    for key_bytes, val_bytes in headers:
        key = key_bytes.decode("latin-1", errors="replace").lower()
        val = val_bytes.decode("latin-1", errors="replace")
        if key in sensitive_keys:
            val = "[REDACTED]"
        result[key] = val
    return result


def _truncate_body(body: str | None, max_size: int) -> str | None:
    if body is None:
        return None
    if len(body) <= max_size:
        return body
    return body[:max_size] + f"... [truncated {len(body) - max_size} chars]"


class RadarMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        is_included = any(path.startswith(inc) for inc in RADAR_SETTINGS.RADAR_INCLUDE_PATHS)
        is_excluded = any(path.startswith(exc) for exc in RADAR_SETTINGS.RADAR_EXCLUDE_PATHS)

        if is_excluded and not is_included:
            # 被排除的路径仍然设置上下文，以便 radar_log 可用
            # 请求结束后仅在有 user_logs 时才落库
            await self._handle_http(scope, receive, send, flush_only_if_logged=True)
        else:
            await self._handle_http(scope, receive, send, flush_only_if_logged=False)

    async def _handle_http(self, scope: Scope, receive: Receive, send: Send, *, flush_only_if_logged: bool = False) -> None:
        x_request_id = CTX_X_REQUEST_ID.get("")
        if not x_request_id:
            x_request_id = uuid4().hex

        # 获取客户端 IP
        client_ip = None
        client_info = scope.get("client")
        if client_info:
            client_ip = client_info[0]
        # 优先取请求头中的 X-Forwarded-For / X-Real-IP
        for key_bytes, val_bytes in scope.get("headers", []):
            key = key_bytes.decode("latin-1", errors="replace").lower()
            if key == "x-forwarded-for":
                client_ip = val_bytes.decode("latin-1", errors="replace").split(",")[0].strip()
                break
            if key == "x-real-ip":
                client_ip = val_bytes.decode("latin-1", errors="replace").strip()

        radar_ctx = RadarRequestContext(
            x_request_id=x_request_id,
            start_mono=time.monotonic(),
            method=scope.get("method", ""),
            path=scope.get("path", ""),
            client_ip=client_ip,
            query_params=scope.get("query_string", b"").decode("latin-1") or None,
            request_headers=_serialize_headers(scope.get("headers", [])),
        )

        # 缓冲请求体
        body_chunks: list[bytes] = []
        receive_complete = False

        async def buffered_receive() -> Message:
            nonlocal receive_complete
            message = await receive()
            if message.get("type") == "http.request":
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    receive_complete = True
            return message

        # 捕获响应
        response_headers_raw: list[tuple[bytes, bytes]] = []
        response_body_chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                radar_ctx.response_status = message.get("status")
                response_headers_raw.extend(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body_chunks.append(message.get("body", b""))
            await send(message)

        token = CTX_RADAR.set(radar_ctx)
        try:
            await self.app(scope, buffered_receive, send_wrapper)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            radar_ctx.exception_info = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value),
                "traceback": format_exception_pretty(exc_type, exc_value, exc_tb),
            }
            raise
        finally:
            # 被排除的路径：仅在有 radar_log 日志时才落库
            should_flush = not flush_only_if_logged or bool(radar_ctx.user_logs)

            if should_flush:
                # 整理请求体
                if body_chunks:
                    raw_body = b"".join(body_chunks)
                    try:
                        radar_ctx.request_body = _truncate_body(raw_body.decode("utf-8", errors="replace"), RADAR_SETTINGS.RADAR_MAX_BODY_SIZE)
                    except Exception:
                        radar_ctx.request_body = f"[binary {len(raw_body)} bytes]"

                # 整理响应数据
                if response_headers_raw:
                    radar_ctx.response_headers = _serialize_headers(response_headers_raw)

                if RADAR_SETTINGS.RADAR_CAPTURE_RESPONSE_BODY and response_body_chunks:
                    raw_resp = b"".join(response_body_chunks)
                    try:
                        radar_ctx.response_body = _truncate_body(raw_resp.decode("utf-8", errors="replace"), RADAR_SETTINGS.RADAR_MAX_BODY_SIZE)
                    except Exception:
                        radar_ctx.response_body = f"[binary {len(raw_resp)} bytes]"

                # 异步写入 Radar 数据库
                asyncio.create_task(_safe_flush(radar_ctx))

            CTX_RADAR.reset(token)


async def _safe_flush(ctx: RadarRequestContext) -> None:
    try:
        await flush_request_data(ctx)
    except Exception:
        logger.exception("Radar: failed to flush request data")
