from tortoise.expressions import Q

from app.core.autodiscover import discover_business_module_names
from app.core.base_schema import Fail, Success, SuccessExtra
from app.core.code import Code
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers import menu_controller
from app.system.models import IconType, Menu
from app.system.schemas.admin import MenuCreate, MenuSearch, MenuUpdate

# 标准 CRUD：get, delete, batch_delete（默认启用）
# list/create/update 使用 override 注入树结构和按钮关联
crud = CRUDRouter(
    prefix="/menus",
    controller=menu_controller,
    create_schema=MenuCreate,
    update_schema=MenuUpdate,
    list_schema=MenuSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["menu_name"],
        exact_fields=["menu_type", "status_type"],
    ),
    summary_prefix="菜单",
)
router = crud.router


async def build_menu_tree(menus: list[Menu], parent_id: int = 0, simple: bool = False) -> list[dict]:
    """递归生成菜单树"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = await build_menu_tree(menus, menu.id, simple)
            if simple:
                menu_dict = {"id": menu.id, "label": menu.menu_name, "pId": menu.parent_id}
            else:
                menu_dict = await menu.to_dict()
                if menu.icon_type == IconType.local:
                    menu_dict["localIcon"] = menu.icon
                    menu_dict.pop("icon")
                menu_dict["buttons"] = [await button.to_dict() for button in await menu.by_menu_buttons]
            if children:
                menu_dict["children"] = children
            tree.append(menu_dict)
    return tree


# ---- 覆盖 list：返回树结构 ----


async def _collect_business_menu_ids() -> set[int]:
    """收集所有挂在业务模块根路由下的菜单 ID（含子树）。"""
    biz_names = discover_business_module_names()
    if not biz_names:
        return set()
    roots = await Menu.filter(parent_id=0, route_name__in=biz_names).only("id")
    if not roots:
        return set()
    collected: set[int] = {m.id for m in roots}
    frontier: set[int] = set(collected)
    while frontier:
        children = await Menu.filter(parent_id__in=list(frontier)).only("id")
        new_ids = {c.id for c in children} - collected
        if not new_ids:
            break
        collected |= new_ids
        frontier = new_ids
    return collected


@crud.override("list")
async def _list_menus(obj_in: MenuSearch):
    # 三个开关语义：菜单属于某类别时，只要对应开关开启即显示；
    # 不属于任何特殊类别的"普通菜单"始终显示。
    biz_ids = list(await _collect_business_menu_ids())

    # 普通菜单：非常量、非隐藏、非业务
    regular = Q(constant=False) & Q(hide_in_menu=False)
    if biz_ids:
        regular &= ~Q(id__in=biz_ids)
    combined = regular

    if obj_in.include_constant:
        combined |= Q(constant=True)
    if obj_in.include_hidden:
        combined |= Q(hide_in_menu=True)
    if obj_in.include_business and biz_ids:
        combined |= Q(id__in=biz_ids)

    # 菜单为树结构，按扁平记录分页会让子树看不到；此处一次性返回全部匹配项
    menus = await Menu.filter(combined).order_by("id").prefetch_related("by_menu_buttons")
    menu_tree = await build_menu_tree(menus, simple=False)
    total = len(menus)
    return SuccessExtra(data={"records": menu_tree}, total=total, current=1, size=total or 1)


# ---- 覆盖 create/update：按钮关联 + active_menu 处理 ----


@crud.override("create")
async def _create_menu(menu_in: MenuCreate):
    if await menu_controller.exists(route_path=menu_in.route_path):
        return Fail(code=Code.DUPLICATE_MENU_ROUTE, msg=f"路由路径 {menu_in.route_path} 已存在")

    if menu_in.active_menu:
        active_menu_obj = await menu_controller.get(menu_name=menu_in.active_menu)
        obj_dict = menu_in.model_dump(exclude_unset=True, exclude_none=True, exclude={"buttons", "active_menu"})
        obj_dict["active_menu_id"] = active_menu_obj.id
        new_menu = await menu_controller.create(obj_in=obj_dict)
    else:
        new_menu = await menu_controller.create(obj_in=menu_in, exclude={"buttons"})
    if new_menu and menu_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(new_menu, menu_in.by_menu_buttons)
    return Success(msg="创建成功", data={"createdId": encode_id(new_menu.id)})


@crud.override("update")
async def _update_menu(item_id: SqidPath, obj_in: MenuUpdate):
    menu_obj = await menu_controller.update(id=item_id, obj_in=obj_in, exclude={"buttons"})
    if menu_obj and obj_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(menu_obj, obj_in.by_menu_buttons)
    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


# ---- 扩展：菜单树（简化）/ 页面列表 / 按钮树 ----


@router.get("/menus/tree", summary="查看菜单树")
async def _():
    menus = await Menu.filter(constant=False)
    return Success(data=await build_menu_tree(menus, simple=True))


@router.get("/menus/pages", summary="查看一级菜单")
async def _():
    menus = await Menu.filter(parent_id=0, constant=False)
    return Success(data=[{"key": m.menu_name, "value": m.id} for m in menus])


@router.get("/menus/buttons/tree", summary="查看菜单按钮树")
async def _():
    all_menus = await Menu.filter(constant=False)
    if not all_menus:
        return Success(data=[])

    menu_button_map: dict[int, list[dict]] = {}
    for menu in all_menus:
        buttons = await menu.by_menu_buttons.all()
        if buttons:
            menu_button_map[menu.id] = [{"id": b.id, "label": b.button_code, "pId": menu.id} for b in buttons]

    if not menu_button_map:
        return Success(data=[])

    menu_map = {m.id: m for m in all_menus}
    needed_ids: set[int] = set()
    for mid in menu_button_map:
        cur = mid
        while cur in menu_map and cur not in needed_ids:
            needed_ids.add(cur)
            cur = menu_map[cur].parent_id

    menu_objs = [m for m in all_menus if m.id in needed_ids]

    def build_tree(parent_id: int = 0) -> list[dict]:
        result = []
        for menu in menu_objs:
            if menu.parent_id == parent_id:
                children = build_tree(menu.id)
                btns = menu_button_map.get(menu.id, [])
                node: dict = {"id": f"parent${menu.id}", "label": menu.menu_name, "pId": menu.parent_id}
                combined = children + btns
                if combined:
                    node["children"] = combined
                result.append(node)
        return result

    return Success(data=build_tree())
