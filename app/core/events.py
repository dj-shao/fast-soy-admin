"""
轻量级同进程事件总线 — 跨模块通信。

业务模块之间不允许反向导入（system → 不知道 business），
但有些场景需要跨模块联动（如删除用户时联动处理员工）。
通过事件总线实现：发送方只管 ``emit``，接收方通过 ``@on`` 注册处理器。

用法::

    # 注册事件处理器（通常在模块的 events.py 顶层）
    from app.core.events import on

    @on("employee.created")
    async def _notify_on_create(employee_id: int, **kwargs):
        radar_log("员工创建事件", data={"employeeId": employee_id})

    # 触发事件（在服务层）
    from app.core.events import emit

    await emit("employee.created", employee_id=new_emp.id)

注意：
    - 仅限进程内使用，不做跨进程/跨服务投递。
    - 处理器在 ``emit`` 中顺序执行（异步处理器 await），异常被捕获并 log，不中断后续处理器。
    - 处理器在模块导入时注册，因此包含 ``@on`` 的模块必须被导入（通常在 ``__init__.py`` 中 import）。
"""

from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any, Callable

_handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)


def on(event: str) -> Callable:
    """装饰器：将函数注册为指定事件的处理器。

    处理器签名应接受 ``**kwargs``，以便事件触发方自由传参::

        @on("employee.created")
        async def handler(employee_id: int, **kwargs): ...
    """

    def decorator(fn: Callable) -> Callable:
        _handlers[event].append(fn)
        return fn

    return decorator


async def emit(event: str, **kwargs: Any) -> None:
    """触发事件，顺序执行所有已注册的处理器。

    处理器抛出的异常被捕获并通过 ``log.exception`` 输出，不中断其他处理器。
    """
    from app.core.log import log

    handlers = _handlers.get(event, [])
    for handler in handlers:
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(**kwargs)
            else:
                handler(**kwargs)
        except Exception:
            log.exception(f"Event handler error: {event} / {handler.__qualname__}")
