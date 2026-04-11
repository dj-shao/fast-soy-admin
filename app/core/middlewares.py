import os
import re
import sys
from datetime import datetime
from io import StringIO
from uuid import uuid4

import pretty_errors
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.bgtask import BgTasks
from app.core.config import APP_SETTINGS
from app.core.ctx import CTX_X_REQUEST_ID
from app.core.exceptions import BaseHandle


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.handle_http(scope, receive, send)

    async def handle_http(self, scope, receive, send) -> None:
        request = Request(scope, receive)
        response = await self.before_request(request) or self.app

        async def send_wrapper(_response):
            await self.after_request(request, _response)
            await send(_response)

        await response(scope, receive, send_wrapper)

    async def before_request(self, request: Request) -> ASGIApp | None: ...

    async def after_request(self, request: Request, response: dict): ...


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request: Request) -> ASGIApp | None:
        await BgTasks.init_bg_tasks_obj()
        return self.app

    async def after_request(self, request: Request, response: dict) -> None:
        await BgTasks.execute_tasks()


class RequestIDMiddleware(SimpleBaseMiddleware):
    """为每个请求生成 x-request-id 并注入到上下文和响应头中。"""

    async def before_request(self, request: Request) -> ASGIApp | None:
        x_request_id = uuid4().hex
        CTX_X_REQUEST_ID.set(x_request_id)
        request.state.x_request_id = x_request_id
        return None

    async def after_request(self, request: Request, response: dict) -> None:
        if response.get("type") == "http.response.start" and hasattr(request.state, "x_request_id"):
            response["headers"].append((b"x-request-id", request.state.x_request_id.encode()))


class PrettyErrorsMiddleware(BaseHTTPMiddleware):
    """
    异常捕获中间件，使用 pretty_errors 格式化异常信息并记录到日志文件。
    """

    class _ExceptionWriter(pretty_errors.ExceptionWriter):
        def __init__(self, buffer: StringIO):
            super().__init__()
            self.buffer = buffer

        def output_text(self, texts):
            if not isinstance(texts, (list, tuple)):
                texts = [texts]
            count = 0
            for text in texts:
                _text = str(text)
                self.buffer.write(_text)
                count += self.visible_length(_text)
            line_length = self.get_line_length()
            if count == 0 or count % line_length != 0 or self.config.full_line_newline:  # type: ignore[union-attr]
                self.buffer.write("\n")
            self.buffer.write(pretty_errors.RESET_COLOR)

    def __init__(self, app, **pretty_errors_config):
        super().__init__(app)
        self.error_buffer = StringIO()
        pretty_errors.configure(**pretty_errors_config)
        pretty_errors.exception_writer = self._ExceptionWriter(self.error_buffer)
        # Hide framework dispatch layers (noisy, no diagnostic value)
        # Keeps: project code + third-party library internals (e.g. tortoise, pydantic)
        self._setup_blacklist()

    @staticmethod
    def _setup_blacklist():
        """Blacklist framework dispatch layers that add noise to tracebacks."""
        site_pkg = next((p for p in sys.path if "site-packages" in p), "")
        stdlib = os.path.dirname(os.__file__)

        paths = [
            os.path.join(site_pkg, "starlette"),
            os.path.join(site_pkg, "uvicorn"),
            os.path.join(site_pkg, "anyio"),
            os.path.join(site_pkg, "fastapi"),
            os.path.join(stdlib, "asyncio"),
            str(APP_SETTINGS.PROJECT_ROOT / "radar" / "middleware.py"),
            str(APP_SETTINGS.PROJECT_ROOT / "core" / "middlewares.py"),
        ]
        pretty_errors.blacklist(*[p for p in paths if os.path.exists(p)])

    async def dispatch(self, request: Request, call_next):
        self.error_buffer.seek(0)
        self.error_buffer.truncate(0)
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            pretty_errors.excepthook(*sys.exc_info())
            output = self.error_buffer.getvalue()

            msg = f"服务器内部错误, path: {request.url.path}, query: {dict(request.query_params)}"

            # Write colored output to error log file (preserve ANSI colors)
            error_dir = APP_SETTINGS.LOGS_ROOT / "uncaught"
            error_dir.mkdir(parents=True, exist_ok=True)
            error_file = error_dir / f"{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')}.log"
            error_file.write_text(f"{msg}\n{output}", encoding="utf-8")

            # Print colored traceback directly to stderr (preserves ANSI colors)
            sys.stderr.write(f"{msg}\n{output}\n")
            sys.stderr.flush()

            # Return plain-text output in debug mode (strip ANSI escape codes)
            if APP_SETTINGS.APP_DEBUG:
                ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
                details: str | None = ansi_escape.sub("", f"{msg}\n{output}")
            else:
                details: str | None = None

            return await BaseHandle(request, exc, Exception, "5001", f"服务器内部错误: {exc.__class__.__name__}", 200, details=details)
