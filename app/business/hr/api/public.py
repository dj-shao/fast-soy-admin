"""
HR 公开接口（常量路由数据展示页）— 无需登录即可访问，仅返回聚合统计。

⚠️ 这些接口不经过 DependAuth / DependPermission，**不要**在这里暴露任何敏感字段
（手机号、邮箱、工号、user_id 等）。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.business.hr.models import Department, Employee, EmployeeStatus, Tag
from app.utils import Success

router = APIRouter(prefix="/hr/public", tags=["HR公开展示"])


@router.get("/showcase", summary="[公开] HR 数据展示总览")
async def showcase_overview():
    """返回部门 / 员工 / 标签的公开聚合统计，用于常量路由展示页。"""
    dept_total = await Department.all().count()
    emp_total = await Employee.all().count()
    tag_total = await Tag.all().count()

    status_counts: dict[str, int] = {}
    for status in EmployeeStatus:
        status_counts[status.value] = await Employee.filter(status=status).count()

    departments = await Department.all().order_by("id")
    dept_rows: list[dict] = []
    for dept in departments:
        emp_count = await Employee.filter(department_id=dept.id).count()
        dept_rows.append({
            "name": dept.name,
            "code": dept.code,
            "employeeCount": emp_count,
        })

    return Success(
        data={
            "totals": {
                "department": dept_total,
                "employee": emp_total,
                "tag": tag_total,
            },
            "employeeStatus": status_counts,
            "departments": dept_rows,
        }
    )
