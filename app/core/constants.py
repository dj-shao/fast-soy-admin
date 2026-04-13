"""框架级常量定义。

业务代码应从 ``app.utils`` 导入，而非直接引用本模块。
"""

# 超级管理员角色编码 — 在 RBAC 校验中用于判断是否跳过权限检查
SUPER_ADMIN_ROLE = "R_SUPER"
