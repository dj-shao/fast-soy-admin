"""
业务模块上下文变量。

业务专属上下文，可由中间件或依赖注入函数写入。
使用方式：
    from app.business.hr.ctx import get_department_id, set_department_id

    # 在依赖或中间件中设置
    set_department_id(dept_id)

    # 在业务逻辑中读取
    dept_id = get_department_id()
"""

from __future__ import annotations

import contextvars

# 当前操作的部门 ID（可用于部门范围的数据隔离）
CTX_DEPARTMENT_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("biz_department_id", default=None)


def get_department_id() -> int | None:
    """获取当前上下文中的部门 ID"""
    return CTX_DEPARTMENT_ID.get()


def set_department_id(dept_id: int | None) -> None:
    """设置当前上下文中的部门 ID"""
    CTX_DEPARTMENT_ID.set(dept_id)
