"""
HR 模块事件处理器。

所有处理器使用 radar_log 模拟副作用（审计记录、通知等）。
此模块需要被导入才能注册处理器 — 在 HR ``__init__.py`` 中导入。
"""

from app.core.events import on
from app.utils import radar_log


@on("employee.created")
async def _on_employee_created(employee_id: int, employee_no: str, **kwargs):
    radar_log("HR事件: 员工已创建", data={"employeeId": employee_id, "employeeNo": employee_no})


@on("employee.updated")
async def _on_employee_updated(employee_id: int, **kwargs):
    radar_log("HR事件: 员工信息已更新", data={"employeeId": employee_id})


@on("employee.deleted")
async def _on_employee_deleted(employee_ids: list[int], **kwargs):
    radar_log("HR事件: 员工已删除（软删除）", data={"employeeIds": employee_ids})


@on("employee.status_changed")
async def _on_status_changed(employee_id: int, from_state: str, to_state: str, **kwargs):
    radar_log("HR事件: 员工状态变更", data={"employeeId": employee_id, "fromState": from_state, "toState": to_state})
