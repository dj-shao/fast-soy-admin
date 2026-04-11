"""
业务模块配置。

从 .env 文件加载业务专属配置。
使用方式：
    from app.business.hr.config import BIZ_SETTINGS

    prefix = BIZ_SETTINGS.EMPLOYEE_NO_PREFIX  # "EMP"

在 .env 中覆盖：
    EMPLOYEE_NO_PREFIX=STAFF
    MAX_SKILLS_PER_EMPLOYEE=20
"""

from pydantic_settings import BaseSettings


class BusinessSettings(BaseSettings):
    EMPLOYEE_NO_PREFIX: str = "EMP"
    MAX_SKILLS_PER_EMPLOYEE: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}


BIZ_SETTINGS = BusinessSettings()
