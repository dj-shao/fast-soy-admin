"""
验证码服务 — 发送与验证。

目前为占位实现（内存存储 + 日志输出），生产环境需替换为真实 SMS/邮件服务。

替换指南:
    1. send_captcha() 中接入短信服务商 SDK（如阿里云 SMS、腾讯云 SMS）
    2. 将 _store 替换为 Redis 存储（带 TTL）
    3. 可选：增加发送频率限制（如 60s 内只能发送一次）
"""

import random

from redis.asyncio import Redis

from app.system.radar.developer import radar_log

# Redis key 前缀和过期时间
_CAPTCHA_PREFIX = "captcha:"
_CAPTCHA_EXPIRE = 300  # 5 分钟


def _generate_code(length: int = 6) -> str:
    """生成随机数字验证码"""
    return "".join(str(random.randint(0, 9)) for _ in range(length))


async def send_captcha(redis: Redis, phone: str) -> bool:
    """
    发送验证码到手机号。

    TODO: 替换为真实短信服务
        - 接入阿里云 SMS / 腾讯云 SMS / 其他短信服务商
        - 增加频率限制（如 60s 冷却）
        - 增加每日发送上限

    Args:
        redis: Redis 实例
        phone: 手机号

    Returns:
        是否发送成功
    """
    code = _generate_code()

    # 存储到 Redis，带过期时间
    await redis.set(f"{_CAPTCHA_PREFIX}{phone}", code, ex=_CAPTCHA_EXPIRE)

    # ========== 占位：打印到日志，生产环境替换为真实发送 ==========
    radar_log("验证码已生成 (开发模式，未真实发送)", data={"phone": phone, "code": code})
    # ==========================================================

    return True


async def verify_captcha(redis: Redis, phone: str, code: str) -> bool:
    """
    验证手机验证码。

    Args:
        redis: Redis 实例
        phone: 手机号
        code: 用户输入的验证码

    Returns:
        验证码是否正确
    """
    key = f"{_CAPTCHA_PREFIX}{phone}"
    stored_code = await redis.get(key)

    if not stored_code:
        return False

    if stored_code.decode() != code:
        return False

    # 验证成功后删除，防止重复使用
    await redis.delete(key)
    return True
