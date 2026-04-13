from __future__ import annotations

import inspect
import json
import time

from app.core.log import log
from app.system.radar.ctx import CTX_RADAR

_LOG_DISPATCH = {
    "DEBUG": log.debug,
    "INFO": log.info,
    "WARNING": log.warning,
    "ERROR": log.error,
    "CRITICAL": log.critical,
}


def radar_log(message: str, *, level: str = "INFO", data: dict | None = None, log_to_file: bool = True) -> None:
    """向当前请求的 Radar 时间线插入一条手动日志，并可同时输出到文件日志。

    用法：
        from app.system.radar.developer import radar_log

        radar_log("订单开始处理", data={"order_id": 123})
        radar_log("支付失败", level="ERROR", data={"reason": "timeout"})
        radar_log("仅 radar 记录", log_to_file=False)
    """
    level = level.upper()

    if log_to_file:
        log_func = _LOG_DISPATCH.get(level, log.info)
        if data:
            log_func(f"{message} | {json.dumps(data, ensure_ascii=False, default=str)}")
        else:
            log_func(message)

    radar_ctx = CTX_RADAR.get()
    if radar_ctx is None:
        return

    frame = inspect.currentframe()
    source = None
    if frame and frame.f_back:
        caller = frame.f_back
        module = caller.f_globals.get("__name__", "unknown")
        func_name = caller.f_code.co_name
        source = f"{module}.{func_name}:{caller.f_lineno}"

    radar_ctx.user_logs.append({
        "level": level,
        "message": message,
        "data": json.dumps(data, ensure_ascii=False, default=str) if data else None,
        "source": source,
        "offset_ms": round((time.monotonic() - radar_ctx.start_mono) * 1000, 3),
    })
