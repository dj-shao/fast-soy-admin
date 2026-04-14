"""
HR 个人接口 — 查看/编辑自己的信息和标签 (需要员工身份)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from app.business.hr.dependency import DependEmployee
from app.business.hr.schemas import TagIds

if TYPE_CHECKING:
    from app.business.hr.models import Employee
from app.business.hr.services import get_employee_profile, list_department_employees, update_employee_skills
from app.utils import DependAuth, Success

router = APIRouter(prefix="/hr", tags=["HR个人"], dependencies=[DependAuth])


@router.get("/my/profile", summary="我的信息")
async def my_profile(emp: Employee = DependEmployee):
    """查看自己的信息和标签"""
    record = await get_employee_profile(emp)
    return Success(data=record)


@router.patch("/my/tags", summary="编辑我的标签")
async def my_tags(body: TagIds, emp: Employee = DependEmployee):
    """编辑自己的标签列表"""
    return await update_employee_skills(emp, body.tag_ids, log_label="编辑个人标签")


@router.get("/my/department", summary="同部门同事")
async def my_department(emp: Employee = DependEmployee):
    """查看同部门同事及其标签"""
    records = await list_department_employees(emp.department_id, exclude_fields=["phone", "email"])  # type: ignore[attr-defined]
    return Success(data=records)
