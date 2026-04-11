"""
业务响应码分类定义。

码段说明：
  0000        — 成功
  1000-1999   — 系统内部错误（异常捕获）
  2000-2999   — 业务逻辑错误（认证、权限、资源等）
  3000-3999   — 内部保留
  4000-9999   — 用户自定义业务码（框架不使用）

前端 .env 映射：
  VITE_SERVICE_SUCCESS_CODE=0000
  VITE_SERVICE_LOGOUT_CODES=2100,2101
  VITE_SERVICE_MODAL_LOGOUT_CODES=2102
  VITE_SERVICE_EXPIRED_TOKEN_CODES=2103
"""


class Code:
    """全应用统一响应码分类定义。"""

    # ---- 0000 成功 ----
    SUCCESS = "0000"

    # ==== 1xxx 系统内部错误 ====

    # 10xx — 服务器错误
    INTERNAL_ERROR = "1000"  # 通用/未处理异常

    # 11xx — 数据库错误
    INTEGRITY_ERROR = "1100"  # 约束冲突（唯一键、外键等）
    NOT_FOUND = "1101"  # 记录不存在

    # 12xx — 数据校验错误
    REQUEST_VALIDATION = "1200"  # 请求参数/请求体校验失败
    RESPONSE_VALIDATION = "1201"  # 响应序列化失败

    # ==== 2xxx 业务逻辑错误 ====

    # 21xx — 认证
    INVALID_TOKEN = "2100"  # Token 缺失/解码失败/无效
    INVALID_SESSION = "2101"  # Token 类型错误/用户不存在
    ACCOUNT_DISABLED = "2102"  # 用户账号已被禁用
    TOKEN_EXPIRED = "2103"  # 访问/刷新 Token 已过期

    # 22xx — 授权
    API_DISABLED = "2200"  # API 接口已被禁用
    PERMISSION_DENIED = "2201"  # RBAC 权限不足

    # 23xx — 资源冲突
    DUPLICATE_RESOURCE = "2300"  # 资源重复（用户名、角色编码等）

    # 24xx — 通用业务失败
    FAIL = "2400"  # 通用业务逻辑失败

    # 25xx — 限流/安全
    RATE_LIMITED = "2500"  # 请求过于频繁
    IP_BANNED = "2501"  # IP 已被临时封禁
    ACCESS_DENIED = "2502"  # 被安全策略拦截

    # ==== 3xxx 内部保留 ====
    # （暂未使用，为未来框架扩展预留）

    # ==== 4000-9999 用户自定义业务码 ====
    # （框架不使用——供项目专属业务逻辑使用）
