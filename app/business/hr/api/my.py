"""
HR 个人接口 — 任何已绑定员工身份的登录用户都能访问的"我的工作台"接口。
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, UploadFile

from app.business.hr.controllers import employee_controller
from app.business.hr.dependency import DependEmployee
from app.business.hr.schemas import MyProfileUpdate, TagIds
from app.business.hr.services import get_employee_profile, list_department_employees, update_employee_tags
from app.core.config import APP_SETTINGS
from app.utils import DependAuth, Fail, Success, require_buttons

if TYPE_CHECKING:
    from app.business.hr.models import Employee

router = APIRouter(prefix="/hr", tags=["HR个人"], dependencies=[DependAuth])


@router.get("/my/profile", summary="我的信息")
async def my_profile(emp: Employee = DependEmployee):
    record = await get_employee_profile(emp)
    return Success(data=record)


@router.patch("/my/profile", summary="编辑我的资料")
async def update_my_profile(body: MyProfileUpdate, emp: Employee = DependEmployee):
    """员工自助维护：仅允许电话、邮箱。部门 / 职位 / 状态需主管或 HR 操作。"""
    await employee_controller.update(id=emp.id, obj_in=body, exclude={"tag_ids"})
    return Success(msg="更新成功")


@router.patch(
    "/my/tags",
    summary="编辑我的标签",
    dependencies=[require_buttons("B_HR_MY_TAG_EDIT")],
)
async def my_tags(body: TagIds, emp: Employee = DependEmployee):
    return await update_employee_tags(emp, body.tag_ids, log_label="编辑个人标签")


@router.get("/my/department", summary="同部门同事")
async def my_department(emp: Employee = DependEmployee):
    """查看同部门同事（脱敏：不返回手机/邮箱）"""
    records = await list_department_employees(emp.department_id, exclude_fields=["phone", "email"])  # type: ignore[attr-defined]
    return Success(data=records)


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


@router.post(
    "/my/avatar",
    summary="上传我的头像",
    dependencies=[require_buttons("B_HR_MY_AVATAR_EDIT")],
)
async def upload_my_avatar(file: UploadFile, emp: Employee = DependEmployee):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return Fail(msg="仅支持 JPEG/PNG/GIF/WebP 格式的图片")
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        return Fail(msg="图片大小不能超过 2MB")

    ext = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = APP_SETTINGS.STATIC_ROOT / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(content)

    avatar_url = f"/static/avatars/{filename}"
    await employee_controller.update(id=emp.id, obj_in={"avatar": avatar_url})
    return Success(msg="头像上传成功", data={"avatarUrl": avatar_url})
