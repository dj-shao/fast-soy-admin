from fastapi import Request
from tortoise.transactions import in_transaction

from app.core.base_schema import Fail, Success
from app.core.cache import load_role_permissions
from app.core.code import Code
from app.core.constants import SUPER_ADMIN_ROLE
from app.core.crud import get_db_conn
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers import menu_controller, role_controller
from app.system.models import Api, Button, Role
from app.system.schemas.admin import RoleCreate, RoleSearch, RoleUpdate, RoleUpdateAuthrization

# 标准 CRUD 路由：list(POST /search), get, delete, batch_delete, create, update
# create / update 使用 override 注入 Redis 缓存刷新
crud = CRUDRouter(
    prefix="/roles",
    controller=role_controller,
    create_schema=RoleCreate,
    update_schema=RoleUpdate,
    list_schema=RoleSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["role_name", "role_code"],
        exact_fields=["status_type"],
    ),
    summary_prefix="角色",
)
router = crud.router


# ---- 覆盖 create：需要刷新 Redis 权限缓存 ----


@crud.override("create")
async def _create_role(role_in: RoleCreate, request: Request):
    if await role_controller.exists(role_code=role_in.role_code):
        return Fail(code=Code.DUPLICATE_ROLE_CODE, msg="该角色编码已存在")

    new_role = await role_controller.create(obj_in=role_in)
    await load_role_permissions(request.app.state.redis, role_code=new_role.role_code)
    return Success(msg="创建成功", data={"createdId": encode_id(new_role.id)})


# ---- 覆盖 update：同上 ----


@crud.override("update")
async def _update_role(item_id: SqidPath, obj_in: RoleUpdate, request: Request):
    role_obj = await role_controller.update(id=item_id, obj_in=obj_in)
    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


# ---- 扩展：角色菜单管理 ----


@router.get("/roles/{role_id}/menus", summary="查看角色菜单")
async def _(role_id: SqidPath):
    role_obj = await Role.get(id=role_id).prefetch_related("by_role_home")
    if role_obj.role_code == SUPER_ADMIN_ROLE:
        menu_objs = await menu_controller.model.filter(constant=False)
    else:
        menu_objs = await role_obj.by_role_menus
    return Success(data={"byRoleHomeId": role_obj.by_role_home.id, "byRoleMenuIds": [m.id for m in menu_objs]})


@router.patch("/roles/{role_id}/menus", summary="更新角色菜单")
async def _(role_id: SqidPath, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_home_id:
        async with in_transaction(get_db_conn(Role)):
            role_obj = await role_controller.update(id=role_id, obj_in=dict(by_role_home_id=role_in.by_role_home_id))
            if role_in.by_role_menu_ids:
                menu_objs = await menu_controller.get_by_id_list(id_list=role_in.by_role_menu_ids)
                if not menu_objs:
                    return Success(msg="获取角色菜单对象失败", code=2000)

                await role_obj.by_role_menus.clear()
                while len(menu_objs) > 0:
                    menu_obj = menu_objs.pop()
                    await role_obj.by_role_menus.add(menu_obj)
                    if menu_obj.parent_id != 0:
                        menu_objs.append(await menu_controller.get(id=menu_obj.parent_id))
            else:
                await role_obj.by_role_menus.clear()

        await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)

    return Success(
        msg="更新成功",
        data={"byRoleMenuIds": role_in.by_role_menu_ids, "byRoleHomeId": role_in.by_role_home_id},
    )


# ---- 扩展：角色按钮管理 ----


@router.get("/roles/{role_id}/buttons", summary="查看角色按钮")
async def _(role_id: SqidPath):
    role_obj = await role_controller.get(id=role_id)
    if role_obj.role_code == SUPER_ADMIN_ROLE:
        button_objs = await Button.all()
    else:
        button_objs = await role_obj.by_role_buttons

    return Success(data={"byRoleButtonIds": [b.id for b in button_objs]})


@router.patch("/roles/{role_id}/buttons", summary="更新角色按钮")
async def _(role_id: SqidPath, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_button_ids is not None:
        async with in_transaction(get_db_conn(Role)):
            await role_obj.by_role_buttons.clear()
            for button_id in role_in.by_role_button_ids:
                button_obj = await Button.get(id=button_id)
                await role_obj.by_role_buttons.add(button_obj)

    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"byRoleButtonIds": role_in.by_role_button_ids})


# ---- 扩展：角色 API 管理 ----


@router.get("/roles/{role_id}/apis", summary="查看角色API")
async def _(role_id: SqidPath):
    role_obj = await role_controller.get(id=role_id)
    if role_obj.role_code == SUPER_ADMIN_ROLE:
        api_objs = await Api.all()
    else:
        api_objs = await role_obj.by_role_apis

    return Success(data={"byRoleApiIds": [a.id for a in api_objs]})


@router.patch("/roles/{role_id}/apis", summary="更新角色API")
async def _(role_id: SqidPath, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_api_ids is not None:
        async with in_transaction(get_db_conn(Role)):
            await role_obj.by_role_apis.clear()
            for api_id in role_in.by_role_api_ids:
                api_obj = await Api.get(id=api_id)
                await role_obj.by_role_apis.add(api_obj)

    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"byRoleApiIds": role_in.by_role_api_ids})
