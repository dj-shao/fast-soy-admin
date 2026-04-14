# pyright: reportIncompatibleVariableOverride=false
from tortoise import fields

from app.core.base_model import BaseModel


class RadarRequest(BaseModel):
    id = fields.IntField(primary_key=True)
    x_request_id = fields.CharField(max_length=64, unique=True, description="请求ID")
    method = fields.CharField(max_length=10, description="请求方法")
    path = fields.CharField(max_length=500, description="请求路径")
    client_ip = fields.CharField(max_length=45, null=True, description="客户端IP")
    user_id = fields.IntField(null=True, description="操作人ID")
    user_name = fields.CharField(max_length=255, null=True, description="操作人用户名")
    query_params = fields.TextField(null=True, description="查询参数")
    request_headers = fields.JSONField(null=True, description="请求头")
    request_body = fields.TextField(null=True, description="请求体")
    response_status = fields.IntField(null=True, description="HTTP状态码")
    response_headers = fields.JSONField(null=True, description="响应头")
    response_body = fields.TextField(null=True, description="响应体")
    duration_ms = fields.FloatField(null=True, description="总耗时(ms)")
    error_type = fields.CharField(max_length=200, null=True, description="异常类型")
    error_message = fields.TextField(null=True, description="异常消息")
    error_traceback = fields.TextField(null=True, description="异常堆栈")
    resolved = fields.BooleanField(default=False, description="是否已处理")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "radar_requests"
        table_description = "Radar请求记录"
        indexes = [("x_request_id",), ("path",), ("created_at",)]


class RadarQuery(BaseModel):
    id = fields.IntField(primary_key=True)
    request_id: int
    request = fields.ForeignKeyField("app_system.RadarRequest", related_name="queries", on_delete=fields.CASCADE, description="关联请求")
    sql_text = fields.TextField(description="SQL语句")
    params = fields.TextField(null=True, description="绑定参数")
    operation = fields.CharField(max_length=20, null=True, description="操作类型")
    duration_ms = fields.FloatField(description="查询耗时(ms)")
    connection_name = fields.CharField(max_length=100, null=True, description="连接名称")
    start_offset_ms = fields.FloatField(null=True, description="相对请求起始偏移(ms)")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "radar_queries"
        table_description = "Radar SQL查询记录"
        indexes = [("duration_ms",)]


class RadarUserLog(BaseModel):
    id = fields.IntField(primary_key=True)
    request_id: int | None
    request = fields.ForeignKeyField("app_system.RadarRequest", related_name="user_logs", on_delete=fields.CASCADE, null=True, description="关联请求")
    level = fields.CharField(max_length=10, default="INFO", description="日志级别")
    message = fields.TextField(description="日志消息")
    data = fields.TextField(null=True, description="附加数据(JSON)")
    source = fields.CharField(max_length=200, null=True, description="调用来源")
    offset_ms = fields.FloatField(null=True, description="相对请求起始偏移(ms)")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "radar_user_logs"
        table_description = "Radar开发者手动日志"
