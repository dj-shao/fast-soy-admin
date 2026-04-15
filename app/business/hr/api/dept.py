"""
HR 主管接口 — 查看/编辑部门员工 (需要主管身份)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from app.business.hr.dependency import DependManager
from app.business.hr.schemas import TagIds

if TYPE_CHECKING:
    from app.business.hr.models import Employee
from app.business.hr.services import edit_subordinate_tags, list_department_employees
from app.utils import SqidPath, Success

router = APIRouter(prefix="/hr", tags=["HR主管"])


@router.get("/department/employees", summary="[主管] 查看部门员工")
async def dept_employees(mgr: Employee = DependManager):
    """主管查看自己部门所有员工详细信息"""
    records = await list_department_employees(mgr.department_id)  # type: ignore[attr-defined]
    return Success(data=records)


@router.patch("/department/employees/{emp_id}/tags", summary="[主管] 编辑下属标签")
async def edit_employee_tags(emp_id: SqidPath, body: TagIds, mgr: Employee = DependManager):
    """主管编辑同部门下属的标签"""
    return await edit_subordinate_tags(mgr, emp_id, body.tag_ids)
