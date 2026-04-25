"""
HR service — 员工创建、标签管理、部门查询、状态流转的核心业务逻辑。
"""

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.controllers import employee_controller, tag_controller
from app.business.hr.ctx import get_department_id
from app.business.hr.models import Department, Employee
from app.business.hr.schemas import EmployeeCreate, EmployeeSearch, EmployeeUpdate
from app.core.code import Code
from app.core.data_scope import build_scope_filter, get_current_data_scope
from app.core.events import emit
from app.core.sqids import encode_id
from app.core.state_machine import StateMachine
from app.system.services import create_system_user
from app.utils import CTX_USER_ID, Fail, Success, get_current_user_id, get_db_conn, radar_log

# ---- 员工状态机 ----

EMPLOYEE_FSM = StateMachine(
    transitions={
        "pending": ["onboarding"],
        "onboarding": ["active"],
        "active": ["resigned"],
        "resigned": [],  # 终态
    }
)


async def generate_employee_no() -> str:
    """生成工号: 前缀 + 自增序号"""
    count = await employee_controller.model.all().count()
    return f"{BIZ_SETTINGS.EMPLOYEE_NO_PREFIX}{count + 1:04d}"


async def _create_employee_core(emp_in: EmployeeCreate, redis):
    """创建系统用户 + 员工 + 标签关联（事务）。调用方需自行校验权限/部门。"""
    if emp_in.tag_ids and len(emp_in.tag_ids) > BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE:
        return Fail(code=Code.HR_TAGS_EXCEED_LIMIT, msg=f"标签数量不能超过 {BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE}")

    employee_no = await generate_employee_no()

    async with in_transaction(get_db_conn(Employee)):
        try:
            result = await create_system_user(
                redis,
                user_name=emp_in.user_name,
                nick_name=emp_in.name,
                user_email=emp_in.email,
                user_gender=emp_in.user_gender,
                user_phone=emp_in.phone,
            )
        except ValueError as e:
            return Fail(msg=str(e))

        emp_data = emp_in.model_dump(exclude_unset=True, exclude_none=True, exclude={"tag_ids", "password", "email", "user_name", "user_gender"})
        emp_data.update(employee_no=employee_no, email=emp_in.email, user_id=result.user.id)
        new_emp = await employee_controller.create(obj_in=emp_data)

        if emp_in.tag_ids:
            for tid in emp_in.tag_ids:
                tag = await tag_controller.get(id=tid)
                await new_emp.tags.add(tag)

    radar_log("创建员工", data={"employeeId": new_emp.id, "employeeNo": employee_no, "userId": result.user.id})
    await emit("employee.created", employee_id=new_emp.id, employee_no=employee_no)
    return Success(
        msg="创建成功",
        data={
            "employee_id": new_emp.id,
            "employee_no": employee_no,
            "user_id": result.user.id,
            "raw_password": result.raw_password,
        },
    )


async def create_employee(emp_in: EmployeeCreate, redis):
    """HR 管理员视角创建员工 — 必须显式指定部门。"""
    if not emp_in.department_id:
        return Fail(code=Code.HR_DEPARTMENT_REQUIRED, msg="创建员工需要指定部门")
    return await _create_employee_core(emp_in, redis)


async def create_subordinate_employee(emp_in: EmployeeCreate, mgr: Employee, redis):
    """部门主管视角创建下属 — 部门强制继承自主管所在部门。"""
    emp_in.department_id = mgr.department_id  # type: ignore[attr-defined]
    return await _create_employee_core(emp_in, redis)


async def list_employees_with_relations(search_in: EmployeeSearch, redis=None):
    """员工分页列表 — 使用 select_related/prefetch_related 优化 N+1 查询 + 行级数据权限。"""
    q = employee_controller.build_search(search_in, contains_fields=["name", "email"], exact_fields=["status"], range_fields=["created_at"])
    if search_in.department_id:
        q &= Q(department_id=search_in.department_id)

    # 行级数据权限过滤
    scope = await get_current_data_scope(redis)
    scope_q = build_scope_filter(scope=scope, user_id=CTX_USER_ID.get(), department_id=get_department_id())
    q &= scope_q
    total, employees = await employee_controller.list(
        page=search_in.current,
        page_size=search_in.size,
        search=q,
        order=["id"],
        select_related=["department"],
        prefetch_related=["tags"],
    )
    records = []
    for emp in employees:
        record = await emp.to_dict()
        record["departmentName"] = emp.department.name
        record["tagIds"] = [encode_id(t.id) for t in emp.tags]
        record["tagNames"] = [t.name for t in emp.tags]
        records.append(record)
    return total, records


async def update_employee(emp_id: int, emp_in: EmployeeUpdate):
    """更新员工信息 — 含标签关联更新"""
    if emp_in.tag_ids and len(emp_in.tag_ids) > BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE:
        return Fail(code=Code.HR_TAGS_EXCEED_LIMIT, msg=f"标签数量不能超过 {BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE}")
    async with in_transaction(get_db_conn(Employee)):
        emp = await employee_controller.update(id=emp_id, obj_in=emp_in, exclude={"tag_ids"})
        if emp_in.tag_ids is not None:
            await emp.tags.clear()
            for sid in emp_in.tag_ids:
                await emp.tags.add(await tag_controller.get(id=sid))
    radar_log("编辑员工", data={"employeeId": emp_id})
    await emit("employee.updated", employee_id=emp_id)
    return Success(msg="更新成功", data={"updated_id": emp_id})


async def update_employee_tags(emp: Employee, tag_ids: list[int], *, log_label: str = "编辑标签", extra_log: dict[str, object] | None = None):
    """通用标签更新 — 校验上限 + 清除重建 + 日志"""
    if len(tag_ids) > BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE:
        return Fail(code=Code.HR_TAGS_EXCEED_LIMIT, msg=f"标签数量不能超过 {BIZ_SETTINGS.MAX_TAGS_PER_EMPLOYEE}")
    await emp.tags.clear()
    for tid in tag_ids:
        await emp.tags.add(await tag_controller.get(id=tid))
    log_data: dict[str, object] = {"employeeId": emp.id, "tagIds": tag_ids}
    if extra_log:
        log_data.update(extra_log)
    radar_log(log_label, data=log_data)
    return Success(msg="标签更新成功")


async def get_employee_profile(emp: Employee):
    """获取员工完整信息 — 含部门和标签"""
    await emp.fetch_related("department", "tags")
    record = await emp.to_dict()
    record["departmentName"] = emp.department.name
    record["tags"] = [await t.to_dict() for t in emp.tags]
    return record


async def list_department_employees(department_id: int, exclude_fields: list[str] | None = None):
    """部门员工列表 — prefetch_related 加载标签"""
    employees = await employee_controller.model.filter(department_id=department_id).prefetch_related("tags")
    records = []
    for emp in employees:
        record = await emp.to_dict(exclude_fields=exclude_fields)
        record["tagNames"] = [t.name for t in emp.tags]
        records.append(record)
    return records


async def edit_subordinate_tags(mgr: Employee, emp_id: int, tag_ids: list[int]):
    """主管编辑下属标签"""
    target = await employee_controller.get_or_none(id=emp_id, department_id=mgr.department_id)  # type: ignore[attr-defined]
    if not target:
        return Fail(code=Code.HR_EMPLOYEE_NOT_IN_DEPT, msg="该员工不在您的部门中")
    return await update_employee_tags(target, tag_ids, log_label="主管编辑下属标签", extra_log={"managerId": mgr.id})


async def update_subordinate_employee(mgr: Employee, emp_id: int, emp_in: EmployeeUpdate):
    """主管编辑下属基础信息 — 校验目标必须在本部门。"""
    target = await employee_controller.get_or_none(id=emp_id, department_id=mgr.department_id)  # type: ignore[attr-defined]
    if not target:
        return Fail(code=Code.HR_EMPLOYEE_NOT_IN_DEPT, msg="该员工不在您的部门中")
    return await update_employee(emp_id, emp_in)


async def transition_subordinate(emp_id: int, to_state: str):
    """主管推进下属状态 — 调用方需先校验下属归属（在 team router 中完成）。"""
    return await transition_employee(emp_id, to_state)


async def get_team_overview(mgr: Employee):
    """主管视角的部门概览 — 状态分布 + 总人数 + 部门信息。"""
    dept = await Department.get(id=mgr.department_id)  # type: ignore[attr-defined]
    qs = Employee.filter(department_id=mgr.department_id)  # type: ignore[attr-defined]
    total = await qs.count()
    status_counts: dict[str, int] = {}
    from app.business.hr.models import EmployeeStatus

    for status in EmployeeStatus:
        status_counts[status.value] = await qs.filter(status=status).count()
    return {
        "department": {"id": dept.id, "name": dept.name, "code": dept.code},
        "total": total,
        "statusCounts": status_counts,
    }


async def transition_employee(emp_id: int, to_state: str):
    """员工状态流转 — 使用状态机校验合法性 + 审计日志 + 事件通知。"""
    emp = await employee_controller.get(id=emp_id)
    from_state = emp.status.value if hasattr(emp.status, "value") else str(emp.status)
    await EMPLOYEE_FSM.transition(
        obj=emp,
        to_state=to_state,
        state_field="status",
        actor_id=get_current_user_id(),
        log_fn=radar_log,
    )
    await emit("employee.status_changed", employee_id=emp_id, from_state=from_state, to_state=to_state)
    return Success(msg="状态更新成功", data={"employeeId": emp_id, "newState": to_state})
