"""
业务开发者的统一导入入口。

本模块重新导出常用类和函数，业务代码可从单一稳定位置导入，
无需深入引用 app.core.* 或 app.system.* 等内部模块：

    from app.utils import CRUDBase, CRUDRouter, Success, radar_log
"""

# ---- ORM 基类 & 枚举 ----
from app.core.base_model import AuditMixin as AuditMixin
from app.core.base_model import BaseModel as BaseModel
from app.core.base_model import IntEnum as IntEnum
from app.core.base_model import StatusType as StatusType
from app.core.base_model import StrEnum as StrEnum
from app.core.base_model import TreeMixin as TreeMixin

# ---- Schema 基类 ----
from app.core.base_schema import CommonIds as CommonIds
from app.core.base_schema import Custom as Custom
from app.core.base_schema import Fail as Fail
from app.core.base_schema import OfflineByRoleRequest as OfflineByRoleRequest
from app.core.base_schema import PageQueryBase as PageQueryBase
from app.core.base_schema import PageResponseModel as PageResponseModel
from app.core.base_schema import ResponseModel as ResponseModel
from app.core.base_schema import SchemaBase as SchemaBase
from app.core.base_schema import Success as Success
from app.core.base_schema import SuccessExtra as SuccessExtra
from app.core.base_schema import make_optional as make_optional

# ---- 业务错误码 ----
from app.core.code import Code as Code

# ---- 配置 ----
from app.core.config import APP_SETTINGS as APP_SETTINGS

# ---- 常量 ----
from app.core.constants import SUPER_ADMIN_ROLE as SUPER_ADMIN_ROLE

# ---- CRUD 操作 ----
from app.core.crud import CRUDBase as CRUDBase
from app.core.crud import get_db_conn as get_db_conn

# ---- 上下文 & 鉴权 ----
from app.core.ctx import CTX_USER_ID as CTX_USER_ID
from app.core.ctx import get_current_user as get_current_user
from app.core.ctx import get_current_user_id as get_current_user_id
from app.core.ctx import has_button_code as has_button_code
from app.core.ctx import has_role_code as has_role_code
from app.core.ctx import is_super_admin as is_super_admin

# ---- 数据权限 ----
from app.core.data_scope import DataScopeType as DataScopeType
from app.core.data_scope import build_scope_filter as build_scope_filter
from app.core.dependency import DependAuth as DependAuth
from app.core.dependency import DependPermission as DependPermission
from app.core.dependency import require_buttons as require_buttons
from app.core.dependency import require_roles as require_roles

# ---- 事件总线 ----
from app.core.events import emit as emit
from app.core.events import on as on
from app.core.exceptions import BizError as BizError
from app.core.exceptions import SchemaValidationError as SchemaValidationError

# ---- 日志 & 监控 ----
from app.core.log import log as log
from app.core.router import CRUDRouter as CRUDRouter
from app.core.router import SearchFieldConfig as SearchFieldConfig
from app.core.soft_delete import SoftDeleteMixin as SoftDeleteMixin

# ---- 状态机 ----
from app.core.state_machine import StateMachine as StateMachine

# ---- 数据工具 ----
from app.core.tools import camel_case_convert as camel_case_convert
from app.core.tools import orjson_dumps as orjson_dumps
from app.core.tools import snake_case_convert as snake_case_convert
from app.core.tools import time_to_timestamp as time_to_timestamp
from app.core.tools import timestamp_to_time as timestamp_to_time
from app.core.tools import to_camel_case as to_camel_case
from app.core.tools import to_lower_camel_case as to_lower_camel_case
from app.core.tools import to_snake_case as to_snake_case
from app.core.tools import to_upper_camel_case as to_upper_camel_case
from app.system.radar.developer import radar_log as radar_log

# ---- 安全 ----
from app.system.security import create_access_token as create_access_token
from app.system.security import get_password_hash as get_password_hash
from app.system.security import verify_password as verify_password
