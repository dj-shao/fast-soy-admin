# pyright: reportIncompatibleVariableOverride=false
from tortoise import fields

from app.core.base_model import AuditMixin, BaseModel, GenderType, IconType, MenuType, MethodType, StatusType
from app.core.data_scope import DataScopeType


class User(BaseModel, AuditMixin):
    id = fields.IntField(primary_key=True, description="用户id")
    user_name = fields.CharField(max_length=20, unique=True, description="用户名称")
    password = fields.CharField(max_length=128, description="密码")
    nick_name = fields.CharField(max_length=30, null=True, description="昵称")
    user_gender = fields.CharEnumField(enum_type=GenderType, default=GenderType.unknow, description="性别")
    user_email = fields.CharField(max_length=255, unique=True, null=True, description="邮箱")
    user_phone = fields.CharField(max_length=20, null=True, description="电话")
    last_login = fields.DatetimeField(null=True, description="最后登录时间")
    status_type = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
    token_version = fields.IntField(default=0, description="令牌版本号，递增后使已签发token失效")
    must_change_password = fields.BooleanField(default=False, description="首次登录需修改密码")

    by_user_roles: fields.ManyToManyRelation["Role"] = fields.ManyToManyField("app_system.Role", related_name="by_role_users")

    class Meta:
        table = "users"
        table_description = "用户表"
        indexes = [
            ("user_name",),
            ("nick_name",),
            ("user_gender",),
            ("user_email",),
            ("user_phone",),
            ("status_type",),
        ]


class Role(BaseModel, AuditMixin):
    id = fields.IntField(primary_key=True, description="角色id")
    role_name = fields.CharField(max_length=20, unique=True, description="角色名称")
    role_code = fields.CharField(max_length=20, unique=True, description="角色编码")
    role_desc = fields.CharField(max_length=500, null=True, blank=True, description="角色描述")
    data_scope = fields.CharEnumField(enum_type=DataScopeType, default=DataScopeType.all, description="数据权限范围")
    by_role_home_id: int
    by_role_home: fields.ForeignKeyRelation["Menu"] = fields.ForeignKeyField("app_system.Menu", related_name=None, description="角色首页")
    status_type = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    by_role_menus: fields.ManyToManyRelation["Menu"] = fields.ManyToManyField("app_system.Menu", related_name="by_menu_roles")
    by_role_apis: fields.ManyToManyRelation["Api"] = fields.ManyToManyField("app_system.Api", related_name="by_api_roles")
    by_role_buttons: fields.ManyToManyRelation["Button"] = fields.ManyToManyField("app_system.Button", related_name="by_button_roles")
    by_role_users: fields.ReverseRelation["User"]

    class Meta:
        table = "roles"
        table_description = "角色表"
        indexes = [
            ("role_name",),
            ("role_code",),
            ("status_type",),
        ]


class Api(BaseModel, AuditMixin):
    id = fields.IntField(primary_key=True, description="API id")
    api_path = fields.CharField(max_length=500, description="API路径")
    api_method = fields.CharEnumField(MethodType, description="请求方法")
    summary = fields.CharField(max_length=500, null=True, description="请求简介")
    tags = fields.JSONField(max_length=500, null=True, description="API标签")
    status_type = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
    is_system = fields.BooleanField(default=False, description="是否为系统自动注册的API")

    by_api_roles: fields.ReverseRelation["Role"]

    class Meta:
        table = "apis"
        table_description = "API表"
        indexes = [
            ("api_path",),
            ("api_method",),
            ("summary",),
        ]


class Menu(BaseModel, AuditMixin):
    id = fields.IntField(primary_key=True, description="菜单id")
    menu_name = fields.CharField(max_length=100, description="菜单名称")
    menu_type = fields.CharEnumField(MenuType, description="菜单类型")
    route_name = fields.CharField(unique=True, max_length=100, description="路由名称")
    route_path = fields.CharField(unique=True, max_length=200, description="路由路径")

    path_param = fields.CharField(null=True, max_length=200, description="路径参数")
    route_param = fields.JSONField(null=True, description="路由参数, List[dict]")
    order = fields.IntField(default=0, description="菜单顺序")
    component = fields.CharField(null=True, max_length=100, description="路由组件")
    parent_id = fields.IntField(default=0, max_length=10, description="父菜单ID")
    i18n_key = fields.CharField(null=True, max_length=100, description="用于国际化的展示文本，优先级高于title")
    icon = fields.CharField(null=True, max_length=100, description="图标名称")
    icon_type = fields.CharEnumField(IconType, null=True, description="图标类型")
    href = fields.CharField(null=True, max_length=200, description="外链")
    multi_tab = fields.BooleanField(default=False, description="是否支持多页签")
    keep_alive = fields.BooleanField(default=False, description="是否缓存")
    hide_in_menu = fields.BooleanField(default=False, description="是否在菜单隐藏")
    active_menu_id: int | None
    active_menu: fields.ForeignKeyNullableRelation["Menu"] = fields.ForeignKeyField(to="app_system.Menu", related_name=None, null=True, description="隐藏的路由需要激活的菜单")
    fixed_index_in_tab = fields.IntField(null=True, max_length=10, description="固定在页签的序号")
    status_type = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="菜单状态")
    redirect = fields.CharField(null=True, max_length=200, description="重定向路径")
    props = fields.BooleanField(default=False, description="是否为首路由")
    constant = fields.BooleanField(default=False, description="是否为公共路由")

    by_menu_buttons: fields.ManyToManyRelation["Button"] = fields.ManyToManyField("app_system.Button", related_name="by_button_menus")
    by_menu_roles: fields.ReverseRelation["Role"]

    class Meta:
        table = "menus"
        table_description = "菜单表"


class Button(BaseModel, AuditMixin):
    id = fields.IntField(primary_key=True, description="按钮id")
    button_code = fields.CharField(max_length=200, description="按钮编码", db_index=True)
    button_desc = fields.CharField(max_length=200, description="按钮描述")
    status_type = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    by_button_menus: fields.ReverseRelation["Menu"]
    by_button_roles: fields.ReverseRelation["Role"]

    class Meta:
        table = "buttons"


__all__ = ["User", "Role", "Api", "Menu", "Button"]
