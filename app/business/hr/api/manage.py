"""
HR 管理接口 — 部门/标签/员工的 CRUD (需要系统权限)。
"""

from fastapi import APIRouter, Request

from app.business.hr.controllers import department_controller, employee_controller, skill_controller
from app.business.hr.schemas import (
    DepartmentCreate,
    DepartmentSearch,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeSearch,
    EmployeeTransition,
    EmployeeUpdate,
    SkillCreate,
    SkillSearch,
    SkillUpdate,
)
from app.business.hr.services import create_employee, get_department_stats, list_employees_with_relations, transition_employee, update_employee
from app.utils import (
    CTX_USER_ID,
    CRUDRouter,
    DependPermission,
    SearchFieldConfig,
    Success,
    SuccessExtra,
    require_buttons,
)

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(contains_fields=["name", "code"], exact_fields=["status"]),
    summary_prefix="部门",
    soft_delete=True,
    tree_endpoint=True,
)

skill_crud = CRUDRouter(
    prefix="/skills",
    controller=skill_controller,
    create_schema=SkillCreate,
    update_schema=SkillUpdate,
    list_schema=SkillSearch,
    search_fields=SearchFieldConfig(contains_fields=["name"], exact_fields=["category"]),
    summary_prefix="标签",
)

# 员工的列表/创建/更新均走自定义逻辑
emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    list_schema=EmployeeSearch,
    summary_prefix="员工",
    soft_delete=True,
)


@emp_crud.override("get")
async def _get_employee(item_id: int):
    emp = await employee_controller.get(id=item_id)
    await emp.fetch_related("department", "skills")
    record = await emp.to_dict()
    record["departmentName"] = emp.department.name
    record["skillIds"] = [s.id for s in emp.skills]
    record["skillNames"] = [s.name for s in emp.skills]
    return Success(data=record)


@emp_crud.override("list")
async def _list_employees(obj_in: EmployeeSearch, request: Request):
    total, records = await list_employees_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


router = APIRouter(prefix="/hr", tags=["HR管理"], dependencies=[DependPermission])


# 将具体路径定义在参数化路由（{item_id}）之前，以避免路由匹配冲突
@router.get("/departments/stats", summary="部门统计")
async def dept_stats(request: Request):
    """部门统计 — 结果缓存在 Redis 中（5 分钟 TTL），员工数据变更时自动失效。"""
    stats = await get_department_stats(redis=request.app.state.redis)
    return Success(data=stats)


router.include_router(dept_crud.router)
router.include_router(skill_crud.router)
router.include_router(emp_crud.router)


# ---- 员工创建/更新：独立走 service 层，依赖 B_HR_CREATE 按钮权限 ----


@router.post(
    "/employees",
    summary="创建员工",
    dependencies=[require_buttons("B_HR_CREATE")],
)
async def create_emp(emp_in: EmployeeCreate, request: Request):
    """
    超级管理员：须指定 department_id
    部门主管（B_HR_CREATE）：department 自动继承
    共同逻辑：自动创建系统用户（R_USER，must_change_password=True），密码随机生成并返回给前端
    """
    current_emp = await employee_controller.get_or_none(user_id=CTX_USER_ID.get())
    return await create_employee(emp_in, current_emp, request.app.state.redis)


@router.patch("/employees/{emp_id}", summary="更新员工")
async def update_emp(emp_id: int, emp_in: EmployeeUpdate):
    return await update_employee(emp_id, emp_in)


@router.post("/employees/{emp_id}/transition", summary="员工状态流转")
async def transition_emp(emp_id: int, body: EmployeeTransition):
    """状态流转: pending → onboarding → active → resigned"""
    return await transition_employee(emp_id, body.to_state)
