"""
HR 团队接口 — 部门主管对本部门下属的管理（搜索/创建/编辑/标签/状态流转/统计）。

所有路径均带 ``/hr/team`` 前缀；调用方必须为本部门主管（``DependManager``）。
具体写操作再叠加按钮码控制，便于前端按按钮显隐。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from app.business.hr.controllers import employee_controller
from app.business.hr.dependency import DependManager
from app.business.hr.schemas import (
    EmployeeCreate,
    EmployeeSearch,
    EmployeeTransition,
    EmployeeUpdate,
    TagIds,
)
from app.business.hr.services import (
    create_subordinate_employee,
    edit_subordinate_tags,
    get_team_overview,
    list_employees_with_relations,
    transition_subordinate,
    update_subordinate_employee,
)
from app.utils import Fail, SqidPath, Success, SuccessExtra, require_buttons

if TYPE_CHECKING:
    from app.business.hr.models import Employee

router = APIRouter(prefix="/hr", tags=["HR团队"])


@router.post("/team/employees/search", summary="[主管] 下属分页搜索")
async def team_employees_search(obj_in: EmployeeSearch, request: Request, mgr: Employee = DependManager):
    obj_in.department_id = mgr.department_id  # type: ignore[attr-defined]
    total, records = await list_employees_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


@router.get("/team/stats", summary="[主管] 部门概览")
async def team_stats(mgr: Employee = DependManager):
    data = await get_team_overview(mgr)
    return Success(data=data)


@router.post(
    "/team/employees",
    summary="[主管] 创建下属",
    dependencies=[require_buttons("B_HR_TEAM_EMP_CREATE")],
)
async def team_create_employee(emp_in: EmployeeCreate, request: Request, mgr: Employee = DependManager):
    return await create_subordinate_employee(emp_in, mgr, request.app.state.redis)


@router.patch(
    "/team/employees/{emp_id}",
    summary="[主管] 编辑下属",
    dependencies=[require_buttons("B_HR_TEAM_EMP_EDIT")],
)
async def team_update_employee(emp_id: SqidPath, emp_in: EmployeeUpdate, mgr: Employee = DependManager):
    return await update_subordinate_employee(mgr, emp_id, emp_in)


@router.patch(
    "/team/employees/{emp_id}/tags",
    summary="[主管] 编辑下属标签",
    dependencies=[require_buttons("B_HR_TEAM_TAG_EDIT")],
)
async def team_edit_subordinate_tags(emp_id: SqidPath, body: TagIds, mgr: Employee = DependManager):
    return await edit_subordinate_tags(mgr, emp_id, body.tag_ids)


@router.post(
    "/team/employees/{emp_id}/transition",
    summary="[主管] 推进下属状态",
    dependencies=[require_buttons("B_HR_TEAM_EMP_TRANSITION")],
)
async def team_transition_employee(emp_id: SqidPath, body: EmployeeTransition, mgr: Employee = DependManager):
    target = await employee_controller.get_or_none(id=emp_id, department_id=mgr.department_id)  # type: ignore[attr-defined]
    if not target:
        from app.core.code import Code

        return Fail(code=Code.HR_EMPLOYEE_NOT_IN_DEPT, msg="该员工不在您的部门中")
    return await transition_subordinate(emp_id, body.to_state)
