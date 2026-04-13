from fastapi import APIRouter, Query, Request

from app.core.base_schema import Success
from app.core.cache import get_constant_routes, get_role_menu_ids, get_user_role_home
from app.core.constants import SUPER_ADMIN_ROLE
from app.core.ctx import CTX_ROLE_CODES, get_current_user_id
from app.core.dependency import DependAuth
from app.system.controllers import menu_controller
from app.system.models import IconType, Menu

router = APIRouter()


async def build_route_tree(menus: list[Menu], parent_id: int = 0, simple: bool = False) -> list[dict]:
    """
    递归生成路由树。

    参数：
        menus: 菜单对象列表
        parent_id: 父菜单 ID，默认为 0（顶层）
        simple: 是否返回简化格式的路由数据
    """
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = await build_route_tree(menus, menu.id, simple)
            await menu.fetch_related("active_menu")
            if simple:
                menu_dict = {
                    "name": menu.route_name,
                    "path": menu.route_path,
                    "component": menu.component,
                    "meta": {
                        "title": menu.menu_name,
                        "i18nKey": menu.i18n_key,
                        "order": menu.order,
                        "keepAlive": menu.keep_alive,
                        "icon": menu.icon,
                        "iconType": menu.icon_type,
                        "href": menu.href,
                        "activeMenu": menu.active_menu.route_name if menu.active_menu else None,
                        "multiTab": menu.multi_tab,
                        "fixedIndexInTab": menu.fixed_index_in_tab,
                    },
                }
                if menu.icon_type == IconType.local:
                    menu_dict["meta"]["localIcon"] = menu.icon
                    menu_dict["meta"].pop("icon")
                if menu.redirect:
                    menu_dict["redirect"] = menu.redirect
                if menu.component:
                    menu_dict["meta"]["layout"] = menu.component.split("$", maxsplit=1)[0]
                if menu.hide_in_menu and not menu.constant:
                    menu_dict["meta"]["hideInMenu"] = menu.hide_in_menu
            else:
                menu_dict = await menu.to_dict()
            if children:
                menu_dict["children"] = children
            tree.append(menu_dict)
    return tree


@router.get("/constant-routes", summary="查看常量路由(公共路由)")
async def _(request: Request):
    """从 Redis 获取常量路由"""
    redis = request.app.state.redis
    data = await get_constant_routes(redis)
    return Success(data=data)


@router.get("/user-routes", summary="查看用户路由菜单", dependencies=[DependAuth])
async def _(request: Request):
    """
    查看用户路由菜单
    - 超级管理员返回所有菜单
    - 普通用户从 Redis 读取角色菜单 ID，再构建路由树
    """
    redis = request.app.state.redis
    role_codes = CTX_ROLE_CODES.get()
    role_home = await get_user_role_home(redis, get_current_user_id())
    is_super = SUPER_ADMIN_ROLE in role_codes

    if is_super:
        role_routes: list[Menu] = await Menu.filter(constant=False)
    else:
        # 从 Redis 汇总所有角色的菜单 ID
        all_menu_ids: set[int] = set()
        for role_code in role_codes:
            menu_ids = await get_role_menu_ids(redis, role_code)
            all_menu_ids.update(menu_ids)

        if all_menu_ids:
            role_routes = await Menu.filter(id__in=list(all_menu_ids))
            # 补全父级菜单
            menu_objs = role_routes.copy()
            while len(menu_objs) > 0:
                menu = menu_objs.pop()
                if menu.parent_id != 0:
                    parent = await Menu.filter(id=menu.parent_id).first()
                    if parent and parent not in role_routes:
                        menu_objs.append(parent)
                        role_routes.append(parent)
        else:
            role_routes = []

    role_routes = list(set(role_routes))
    menu_tree = await build_route_tree(role_routes, simple=True)
    data = {"home": role_home, "routes": menu_tree}
    return Success(data=data)


@router.get("/exists", summary="路由是否存在", dependencies=[DependAuth])
async def _(name: str = Query(..., description="路由名称")):
    is_exists = await menu_controller.model.exists(route_name=name)
    return Success(data=is_exists)
