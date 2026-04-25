import orjson
from fastapi.exceptions import (
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError

from app.core.code import Code
from app.core.ctx import CTX_X_REQUEST_ID


class SettingNotFound(Exception):
    pass


class BizError(Exception):
    """基础业务异常——可在任意层（服务层、控制器、Schema、API）抛出。

    由全局异常处理器统一捕获，并返回 Fail(code=..., msg=...)。
    """

    def __init__(self, code: int | str, msg: str) -> None:
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"{self.code}: {self.msg}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(code={self.code!r}, msg={self.msg!r})"


class SchemaValidationError(BizError):
    """在 Pydantic Schema 校验器中抛出。

    不继承 ValueError，因此 Pydantic 不会捕获它，会直接透传至 BizError 处理器。
    """


async def BaseHandle(req: Request, exc: Exception, handle_exc, code: int | str, msg: str | dict, status_code: int = 500, **kwargs) -> JSONResponse:
    x_request_id = CTX_X_REQUEST_ID.get() or ""
    try:
        request_body_raw = await req.body()
    except RuntimeError:
        request_body_raw = b""
    try:
        request_body = orjson.loads(request_body_raw) if request_body_raw else {}
    except (orjson.JSONDecodeError, UnicodeDecodeError):
        request_body = {}

    request_input = {"path": req.url.path, "query": req.query_params._dict, "body": request_body, "headers": dict(req.headers)}

    # 1xxx 系统内部异常视为非预期 → ERROR；其余（认证/授权/业务/校验等）属于预期失败 → WARNING。
    code_str = str(code)
    log_level = "ERROR" if code_str.startswith("1") else "WARNING"

    try:
        from app.system.radar.developer import radar_log

        radar_log(
            f"异常响应: code={code} msg={msg}",
            level=log_level,
            data={"xRequestId": x_request_id, "input": request_input, **kwargs},
        )
    except Exception:
        pass

    if isinstance(exc, handle_exc):
        return JSONResponse(content={"code": str(code), "msg": msg, "data": None}, status_code=status_code)
    else:
        return JSONResponse(content={"code": str(code), "msg": f"Exception handler Error, exc: {exc}", "data": None}, status_code=status_code)


async def DoesNotExistHandle(req: Request, exc: Exception) -> JSONResponse:
    return await BaseHandle(req, exc, DoesNotExist, Code.NOT_FOUND, f"Object has not found, exc: {exc}, path: {req.path_params}, query: {req.query_params}", 200)


async def IntegrityHandle(req: Request, exc: Exception) -> JSONResponse:
    return await BaseHandle(req, exc, IntegrityError, Code.INTEGRITY_ERROR, f"IntegrityError，{exc}, path: {req.path_params}, query: {req.query_params}", 200)


async def BizErrorHandle(req: Request, exc: BizError) -> JSONResponse:
    return await BaseHandle(req, exc, BizError, exc.code, exc.msg, 200)


# Pydantic v2 错误类型 → 中文消息模板。{xxx} 占位符来自 err["ctx"]。
_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "必填字段缺失",
    "string_type": "必须是字符串",
    "string_too_long": "字符长度不能超过 {max_length}",
    "string_too_short": "字符长度不能少于 {min_length}",
    "string_pattern_mismatch": "格式不正确",
    "int_type": "必须是整数",
    "int_parsing": "无法解析为整数",
    "float_type": "必须是数字",
    "float_parsing": "无法解析为数字",
    "bool_type": "必须是布尔值",
    "bool_parsing": "无法解析为布尔值",
    "decimal_type": "必须是小数",
    "decimal_parsing": "无法解析为小数",
    "decimal_max_digits": "总位数不能超过 {max_digits}",
    "decimal_max_places": "小数位数不能超过 {decimal_places}",
    "datetime_type": "必须是日期时间",
    "datetime_parsing": "日期时间格式无效",
    "date_type": "必须是日期",
    "date_parsing": "日期格式无效",
    "time_parsing": "时间格式无效",
    "uuid_parsing": "UUID 格式无效",
    "json_invalid": "JSON 格式无效",
    "greater_than": "必须大于 {gt}",
    "greater_than_equal": "必须大于等于 {ge}",
    "less_than": "必须小于 {lt}",
    "less_than_equal": "必须小于等于 {le}",
    "enum": "只能是 {expected} 之一",
    "literal_error": "只能是 {expected} 之一",
    "list_type": "必须是数组",
    "dict_type": "必须是对象",
    "too_short": "元素数量不能少于 {min_length}",
    "too_long": "元素数量不能超过 {max_length}",
    "value_error": "值不合法",
}


def _format_validation_error(err: dict) -> dict:
    """将一条 Pydantic 错误转成 {field, message, type}。"""
    loc = [str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path")]
    field = ".".join(loc)
    err_type = err.get("type", "")
    ctx = err.get("ctx") or {}
    template = _VALIDATION_MESSAGES.get(err_type)
    if template:
        try:
            message = template.format(**{k: v for k, v in ctx.items() if not isinstance(v, Exception)})
        except (KeyError, IndexError, ValueError):
            message = err.get("msg", "")
    else:
        message = err.get("msg", "")
    return {"field": field, "message": message, "type": err_type}


async def RequestValidationHandle(req: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [_format_validation_error(e) for e in exc.errors()]
    if errors:
        first = errors[0]
        msg = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    else:
        msg = "请求参数校验失败"
    return await BaseHandle(req, exc, RequestValidationError, Code.REQUEST_VALIDATION, msg, 200, errors=errors, detail=exc.errors())


async def ResponseValidationHandle(req: Request, exc: ResponseValidationError) -> JSONResponse:
    return await BaseHandle(req, exc, ResponseValidationError, Code.RESPONSE_VALIDATION, "ResponseValidationError", 200, detail=exc.errors())
