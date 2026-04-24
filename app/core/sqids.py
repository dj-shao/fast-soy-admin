"""Sqids 编解码 — 对外暴露的 ID 统一走这一层。

字母表顺序由 ``APP_SETTINGS.SECRET_KEY`` 派生（SHA-256 → 种子 → 确定性 shuffle），
因此：

- 同一个 ``SECRET_KEY`` 在任意部署下产出的 sqid 一致；
- 轮换 ``SECRET_KEY`` 会使历史 sqid 全部失效，语义与 JWT 签名密钥轮换一致。
"""

import hashlib
import random

from sqids import Sqids  # type: ignore[attr-defined]

from app.core.config import APP_SETTINGS

_DEFAULT_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_MIN_LENGTH = 8


def _derive_alphabet(secret: str) -> str:
    seed = int.from_bytes(hashlib.sha256(secret.encode()).digest(), "big")
    chars = list(_DEFAULT_ALPHABET)
    random.Random(seed).shuffle(chars)
    return "".join(chars)


_sqids = Sqids(alphabet=_derive_alphabet(APP_SETTINGS.SECRET_KEY), min_length=_MIN_LENGTH)


def encode_id(v: int) -> str:
    """int 主键 → sqid 字符串。"""
    return _sqids.encode([v])


def decode_id(s: str) -> int:
    """sqid 字符串 → int。"""
    nums = _sqids.decode(s)
    if len(nums) != 1:
        raise ValueError(f"invalid sqid: {s!r}")
    return nums[0]


__all__ = ["encode_id", "decode_id"]
