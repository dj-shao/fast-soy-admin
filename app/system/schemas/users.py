from pydantic import Field, model_validator

from app.core.base_schema import PageQueryBase, SchemaBase
from app.core.code import Code
from app.core.exceptions import SchemaValidationError
from app.system.models import GenderType, StatusType


class UserBase(SchemaBase):
    user_name: str | None = Field(None, title="用户名")
    password: str | None = Field(None, title="密码")
    user_email: str | None = Field(None, title="邮箱")
    user_gender: GenderType | None = Field(None, title="性别")
    nick_name: str | None = Field(None, title="昵称")
    user_phone: str | None = Field(None, title="手机号")
    status_type: StatusType | None = Field(None, title="用户状态")
    by_user_role_code_list: list[str] | None = Field(None, title="用户角色编码列表")


class UserSearch(UserBase, PageQueryBase):
    pass


class UserCreate(UserBase):
    @model_validator(mode="after")
    def validate_create(self):
        if not self.user_name:
            raise SchemaValidationError(code=Code.USERNAME_REQUIRED, msg="用户名不能为空")
        if not self.password:
            raise SchemaValidationError(code=Code.PASSWORD_REQUIRED, msg="密码不能为空")
        if not self.user_email:
            raise SchemaValidationError(code=Code.USER_EMAIL_REQUIRED, msg="用户邮箱不能为空")
        if not self.by_user_role_code_list:
            raise SchemaValidationError(code=Code.USER_ROLE_REQUIRED, msg="用户至少需要一个角色")
        if not self.nick_name:
            self.nick_name = self.user_name
        return self


class UserUpdate(UserBase):
    @model_validator(mode="after")
    def validate_update(self):
        if not self.by_user_role_code_list:
            raise SchemaValidationError(code=Code.USER_ROLE_REQUIRED, msg="用户至少需要一个角色")
        return self


class UpdatePassword(SchemaBase):
    old_password: str = Field(title="旧密码")
    new_password: str = Field(title="新密码")


class UserRegister(SchemaBase):
    user_name: str | None = Field(None, title="用户名")
    password: str = Field(title="密码")
    user_email: str | None = Field(None, title="邮箱")
    user_gender: GenderType | None = Field(None, title="性别")
    nick_name: str | None = Field(None, title="昵称")
    user_phone: str | None = Field(None, title="手机号")


__all__ = ["UserBase", "UserSearch", "UserCreate", "UserUpdate", "UpdatePassword", "UserRegister"]
