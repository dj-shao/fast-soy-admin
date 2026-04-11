import jwt
from passlib.context import CryptContext

from app.core.config import APP_SETTINGS
from app.system.schemas.login import JWTPayload

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def create_access_token(*, data: JWTPayload):
    """生成 JWT access token。"""
    payload = data.model_dump().copy()
    encoded_jwt = jwt.encode(payload, APP_SETTINGS.SECRET_KEY, algorithm=APP_SETTINGS.JWT_ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对明文密码进行哈希处理并返回哈希值。"""
    return pwd_context.hash(password)
