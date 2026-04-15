from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.core.base_schema import SchemaBase


class CredentialsSchema(SchemaBase):
    user_name: Annotated[str, Field(max_length=20)] | None = Field(None, title="用户名")
    password: Annotated[str, Field(max_length=128)] | None = Field(None, title="密码")


class JWTOut(SchemaBase):
    token: str | None = Field(None, title="请求token")
    refresh_token: str | None = Field(None, title="刷新token")


class JWTPayload(BaseModel):
    data: dict
    iat: datetime
    exp: datetime


class CaptchaRequest(SchemaBase):
    phone: Annotated[str, Field(max_length=20)] = Field(title="手机号")


class CodeLoginSchema(SchemaBase):
    phone: Annotated[str, Field(max_length=20)] = Field(title="手机号")
    code: Annotated[str, Field(max_length=10)] = Field(title="验证码")


class RegisterSchema(SchemaBase):
    phone: Annotated[str, Field(max_length=20)] = Field(title="手机号")
    code: Annotated[str, Field(max_length=10)] = Field(title="验证码")
    password: Annotated[str, Field(max_length=128)] = Field(title="密码")
    user_name: Annotated[str, Field(max_length=20)] | None = Field(None, title="用户名")


__all__ = ["CredentialsSchema", "JWTOut", "JWTPayload", "CaptchaRequest", "CodeLoginSchema", "RegisterSchema"]
