# pyright: reportIncompatibleVariableOverride=false
from typing import Any

from pydantic import Field, model_validator

from app.core.base_schema import PageQueryBase, SchemaBase
from app.core.code import Code
from app.core.data_scope import DataScopeType
from app.core.exceptions import SchemaValidationError
from app.system.models import IconType, MenuType, StatusType

# ============================================================
# 角色 Schema
# ============================================================


class RoleBase(SchemaBase):
    role_name: str | None = Field(None, title="角色名称")
    role_code: str | None = Field(None, title="角色编码")
    role_desc: str | None = Field(None, title="角色描述")
    data_scope: DataScopeType | None = Field(None, title="数据权限范围")
    by_role_home_id: int | None = Field(None, title="角色首页")
    status_type: StatusType | None = Field(None, title="角色状态")


class RoleSearch(RoleBase, PageQueryBase):
    pass


class RoleCreate(RoleBase):
    role_name: str = Field(title="角色名称")
    role_code: str = Field(title="角色编码")

    @model_validator(mode="after")
    def validate_create(self):
        if not self.role_name.strip():
            raise SchemaValidationError(code=Code.ROLE_NAME_REQUIRED, msg="角色名称不能为空")
        if not self.role_code.strip():
            raise SchemaValidationError(code=Code.ROLE_CODE_REQUIRED, msg="角色编码不能为空")
        return self


class RoleUpdate(RoleBase): ...


class RoleUpdateAuthrization(SchemaBase):
    by_role_home_id: int | None = Field(None, title="角色首页菜单id")
    by_role_menu_ids: list[int] | None = Field(None, title="角色菜单列表")
    by_role_api_ids: list[int] | None = Field(None, title="角色API列表")
    by_role_button_ids: list[int] | None = Field(None, title="角色按钮列表")


# ============================================================
# API Schema
# ============================================================


class BaseApi(SchemaBase):
    api_path: str | None = Field(None, title="请求路径", description="/api/v1/auth/login")
    api_method: str | None = Field(None, title="请求方法", description="GET")
    summary: str | None = Field(None, title="API简介")
    tags: list[str] | None = Field(None, title="API标签")
    status_type: StatusType | None = Field(None, title="API状态")


class ApiSearch(BaseApi, PageQueryBase):
    pass


class ApiCreate(BaseApi):
    api_path: str = Field(title="请求路径", description="/api/v1/auth/login")
    api_method: str = Field(title="请求方法", description="GET")


class ApiUpdate(BaseApi): ...


# ============================================================
# 菜单 Schema
# ============================================================


class ButtonBase(SchemaBase):
    button_code: str | None = Field(None, title="按钮编码")
    button_desc: str | None = Field(None, title="按钮描述")


class MenuBase(SchemaBase):
    menu_name: str | None = Field(None, max_length=200, title="菜单名称")
    menu_type: MenuType | None = Field(None, max_length=200, title="菜单类型")
    route_name: str | None = Field(None, max_length=200, title="路由名称")
    route_path: str | None = Field(None, max_length=200, title="路由路径")

    path_param: str | None = Field(None, max_length=200, description="路径参数")
    route_param: list[dict[str, Any]] = Field(default_factory=list, alias="query", description="路由参数列表")
    by_menu_buttons: list[ButtonBase] = Field(default_factory=list, description="按钮列表")
    order: int | None = Field(None, description="菜单顺序")
    component: str | None = Field(None, description="路由组件")

    parent_id: int | None = Field(None, description="父菜单ID")
    i18n_key: str | None = Field(None, description="用于国际化的展示文本，优先级高于title")

    icon: str | None = Field(None, description="图标名称")
    icon_type: IconType | None = Field(None, description="图标类型")

    href: str | None = Field(None, description="外链")
    multi_tab: bool | None = Field(None, description="是否支持多页签")
    keep_alive: bool | None = Field(None, description="是否缓存")
    hide_in_menu: bool | None = Field(None, description="是否在菜单隐藏")
    active_menu: str | None = Field(None, description="隐藏的路由需要激活的菜单")
    fixed_index_in_tab: int | None = Field(None, description="固定在页签的序号")
    status: str | None = Field(None, description="状态")

    redirect: str | None = Field(None, description="重定向路径")
    props: bool | None = Field(None, description="是否为首路由")
    constant: bool | None = Field(None, description="是否为公共路由")


class MenuSearch(PageQueryBase):
    menu_name: str | None = Field(None, title="菜单名称")
    menu_type: MenuType | None = Field(None, title="菜单类型")
    status_type: StatusType | None = Field(None, title="状态")


class MenuCreate(MenuBase):
    menu_name: str = Field(max_length=200, title="菜单名称")
    menu_type: MenuType = Field(max_length=200, title="菜单类型")
    route_name: str = Field(max_length=200, title="路由名称")
    route_path: str = Field(max_length=200, title="路由路径")

    @model_validator(mode="after")
    def validate_create(self):
        if not self.route_name.strip():
            raise SchemaValidationError(code=Code.ROUTE_NAME_REQUIRED, msg="路由名称不能为空")
        if not self.route_path.strip():
            raise SchemaValidationError(code=Code.ROUTE_PATH_REQUIRED, msg="路由路径不能为空")
        return self


class MenuUpdate(MenuBase): ...


__all__ = [
    "RoleBase",
    "RoleSearch",
    "RoleCreate",
    "RoleUpdate",
    "RoleUpdateAuthrization",
    "BaseApi",
    "ApiSearch",
    "ApiCreate",
    "ApiUpdate",
    "ButtonBase",
    "MenuBase",
    "MenuSearch",
    "MenuCreate",
    "MenuUpdate",
]
