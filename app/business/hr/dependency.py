"""
Business dependencies — 员工身份解析 & 主管权限。

Usage:
    @router.get("/my/profile", dependencies=[DependAuth])
    async def my_profile(emp: Employee = DependEmployee):
        ...

    @router.patch("/department/employees/{id}/skills")
    async def edit_skills(emp: Employee = DependManager):
        ...
"""

from __future__ import annotations

from fastapi import Depends

from app.business.hr.ctx import set_department_id
from app.business.hr.models import Department, Employee
from app.core.code import Code
from app.core.dependency import AuthControl
from app.core.exceptions import BizError
from app.system.models import User


async def get_current_employee(user: User = Depends(AuthControl.is_authed)) -> Employee:
    """解析当前用户对应的员工，并将部门 ID 写入上下文"""
    emp = await Employee.filter(user_id=user.id).select_related("department").first()
    if not emp:
        raise BizError(code=Code.HR_USER_NOT_EMPLOYEE, msg="当前用户未关联员工信息")
    set_department_id(emp.department_id)
    return emp


async def get_department_manager(emp: Employee = Depends(get_current_employee)) -> Employee:
    """校验当前员工是否为部门主管"""
    is_mgr = await Department.filter(id=emp.department_id, manager_id=emp.id).exists()
    if not is_mgr:
        raise BizError(code=Code.HR_MANAGER_ONLY, msg="仅部门主管可执行此操作")
    return emp


DependEmployee = Depends(get_current_employee)
DependManager = Depends(get_department_manager)
