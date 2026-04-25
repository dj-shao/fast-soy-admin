"""
HR 管理接口 — 部门/标签/员工的 CRUD (需要系统权限)。
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile

from app.business.hr.controllers import department_controller, employee_controller, tag_controller
from app.business.hr.schemas import (
    DepartmentCreate,
    DepartmentSearch,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeSearch,
    EmployeeTransition,
    EmployeeUpdate,
    TagCreate,
    TagSearch,
    TagUpdate,
)
from app.business.hr.services import create_employee, get_department_stats, list_employees_with_relations, transition_employee, update_employee
from app.core.config import APP_SETTINGS
from app.core.sqids import encode_id
from app.utils import (
    CRUDRouter,
    DependPermission,
    Fail,
    SearchFieldConfig,
    SqidPath,
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
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
    action_dependencies={
        "create": [require_buttons("B_HR_DEPT_CREATE")],
        "update": [require_buttons("B_HR_DEPT_EDIT")],
        "delete": [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)

tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(contains_fields=["name"], exact_fields=["category"]),
    summary_prefix="标签",
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
    action_dependencies={
        "create": [require_buttons("B_HR_TAG_CREATE")],
        "update": [require_buttons("B_HR_TAG_EDIT")],
        "delete": [require_buttons("B_HR_TAG_DELETE")],
        "batch_delete": [require_buttons("B_HR_TAG_DELETE")],
    },
)

# 员工的列表/创建/更新均走自定义逻辑（见下方 router 上的手写路由），
# CRUDRouter 仅生成 GET/DELETE 与 batch_delete；create/update 因未传 schema 不注册。
emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    list_schema=EmployeeSearch,
    summary_prefix="员工",
    soft_delete=True,
    action_dependencies={
        "delete": [require_buttons("B_HR_EMP_DELETE")],
        "batch_delete": [require_buttons("B_HR_EMP_DELETE")],
    },
)


@emp_crud.override("get")
async def _get_employee(item_id: SqidPath):
    emp = await employee_controller.get(id=item_id)
    await emp.fetch_related("department", "tags")
    record = await emp.to_dict()
    record["departmentName"] = emp.department.name
    record["tagIds"] = [encode_id(t.id) for t in emp.tags]
    record["tagNames"] = [t.name for t in emp.tags]
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
router.include_router(tag_crud.router)
router.include_router(emp_crud.router)


# ---- 员工创建/更新/状态流转：独立走 service 层，按按钮权限隔离 ----


@router.post(
    "/employees",
    summary="创建员工",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(emp_in: EmployeeCreate, request: Request):
    """HR 管理员视角：必须指定 department_id；自动创建系统用户。

    部门主管创建下属请走 ``POST /hr/team/employees``。
    """
    return await create_employee(emp_in, request.app.state.redis)


@router.patch(
    "/employees/{emp_id}",
    summary="更新员工",
    dependencies=[require_buttons("B_HR_EMP_EDIT")],
)
async def update_emp(emp_id: SqidPath, emp_in: EmployeeUpdate):
    return await update_employee(emp_id, emp_in)


@router.post(
    "/employees/{emp_id}/transition",
    summary="员工状态流转",
    dependencies=[require_buttons("B_HR_EMP_TRANSITION")],
)
async def transition_emp(emp_id: SqidPath, body: EmployeeTransition):
    """状态流转: pending → onboarding → active → resigned"""
    return await transition_employee(emp_id, body.to_state)


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


@router.post(
    "/employees/{emp_id}/avatar",
    summary="上传员工头像",
    dependencies=[require_buttons("B_HR_EMP_EDIT")],
)
async def upload_avatar(emp_id: SqidPath, file: UploadFile):
    """上传员工头像图片，保存到 static/avatars/，返回访问 URL。"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return Fail(msg="仅支持 JPEG/PNG/GIF/WebP 格式的图片")

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        return Fail(msg="图片大小不能超过 2MB")

    ext = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = APP_SETTINGS.STATIC_ROOT / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filepath = upload_dir / filename
    filepath.write_bytes(content)

    avatar_url = f"/static/avatars/{filename}"

    # 更新员工头像字段
    await employee_controller.update(id=emp_id, obj_in={"avatar": avatar_url})
    return Success(msg="头像上传成功", data={"avatarUrl": avatar_url})
