"""认证服务。

提供密码哈希、token 签发/校验与鉴权依赖 get_current_user。
采用 Python 标准库实现（hashlib.pbkdf2_hmac + hmac 签名 token），
避免引入 passlib/jose 等重依赖，满足 PRD 不引入未约定依赖的约束。

token 结构：payload 与签名以 '.' 分隔，形如 {base64(payload)}.{base64(signature)}。
签名 = HMAC-SHA256(secret, base64(payload))，校验时重算比对（compare_digest 防时序攻击）。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

# Python <3.11 不提供 datetime.UTC，用 timezone.utc 兼容（3.11+ 等价）
UTC = timezone.utc

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Bearer token 鉴权方案
_bearer_scheme = HTTPBearer(auto_error=False)

# token 有效期
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 天


def hash_password(password: str) -> str:
    """使用 PBKDF2-HMAC-SHA256 生成带随机盐的密码哈希。

    返回格式：pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>。
    """
    salt = secrets.token_bytes(16)
    iterations = 100_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(iterations),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码是否匹配存储的哈希（格式不合法返回 False）。"""
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2])
        expected = base64.b64decode(parts[3])
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _make_signature(payload_b64: str) -> str:
    """基于 token 密钥对 payload 计算 HMAC 签名。"""
    message = payload_b64.encode("ascii")
    digest = hmac.new(
        settings.token_secret.encode("utf-8"), message, hashlib.sha256
    ).digest()
    return _b64url_encode(digest)


def create_token(user_id: int) -> str:
    """为指定用户签发签名 token（含过期时间）。"""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "exp": int((now + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp()),
        "iat": int(now.timestamp()),
    }
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signature = _make_signature(payload_b64)
    return f"{payload_b64}.{signature}"


def _decode_token(token: str) -> dict:
    """解析并校验 token，失败抛出 HTTPException(401)。"""
    try:
        payload_b64, signature = token.split(".", 1)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if not hmac.compare_digest(_make_signature(payload_b64), signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证已失效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(UTC).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：解析 Bearer token 并返回当前登录用户。

    未携带或非法 token 时抛出 401。
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.get(User, user_id_int)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """可选鉴权依赖：有合法 Bearer token 时返回用户，否则返回 None。

    用于 history/favorites 等匿名/登录双维度的接口，未登录零改动。
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        # 非法/过期 token 视为匿名，不阻断请求
        return None
