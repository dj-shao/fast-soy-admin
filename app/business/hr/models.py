# pyright: reportIncompatibleVariableOverride=false
"""
Business model example — 员工、部门、标签。

启用: 去掉文件名 _ 前缀，运行 tortoise makemigrations && tortoise migrate
"""

from tortoise import fields

from app.utils import AuditMixin, BaseModel, StatusType


class Department(BaseModel, AuditMixin):
    """部门"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="部门名称")
    code = fields.CharField(max_length=50, unique=True, description="部门编码")
    description = fields.CharField(max_length=500, null=True, blank=True, description="部门描述")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    # 部门主管 → Employee (用 IntField 避免循环 FK)
    manager_id = fields.IntField(null=True, description="部门主管员工ID")

    class Meta:
        table = "biz_department"


class Skill(BaseModel, AuditMixin):
    """标签"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="标签名称")
    category = fields.CharField(max_length=50, description="标签分类")
    description = fields.CharField(max_length=500, null=True, blank=True, description="标签描述")

    class Meta:
        table = "biz_skill"


class Employee(BaseModel, AuditMixin):
    """员工"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, description="员工姓名")
    employee_no = fields.CharField(max_length=20, unique=True, description="工号")
    email = fields.CharField(max_length=100, null=True, blank=True, description="邮箱")
    phone = fields.CharField(max_length=20, null=True, blank=True, description="电话")
    position = fields.CharField(max_length=50, null=True, blank=True, description="职位")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    # FK: 员工 → 系统用户 (一对一)
    user: fields.ForeignKeyNullableRelation = fields.ForeignKeyField("app_system.User", null=True, unique=True, on_delete=fields.SET_NULL, related_name="employee", description="关联系统用户")
    # FK: 员工 → 部门
    department: fields.ForeignKeyRelation[Department] = fields.ForeignKeyField("app_system.Department", related_name="employees", description="所属部门")
    # M2M: 员工 ↔ 标签
    skills: fields.ManyToManyRelation[Skill] = fields.ManyToManyField("app_system.Skill", related_name="employees", description="标签列表")

    class Meta:
        table = "biz_employee"
