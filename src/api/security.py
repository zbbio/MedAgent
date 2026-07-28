"""Shared-password authentication with signed, expiring cookies."""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import Request

from ..config import config


COOKIE_NAME = "medagent_session"


def verify_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode("utf-8"), config.ACCESS_PASSWORD.encode("utf-8"))


def issue_session_token(now: int | None = None) -> str:
    timestamp = str(now or int(time.time()))
    signature = hmac.new(
        config.SESSION_SECRET.encode("utf-8"),
        timestamp.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{timestamp}.{signature}"


def is_valid_session_token(token: str | None, now: int | None = None) -> bool:
    if not token or "." not in token:
        return False
    timestamp_text, signature = token.split(".", 1)
    try:
        timestamp = int(timestamp_text)
    except ValueError:
        return False

    current_time = now or int(time.time())
    age = current_time - timestamp
    if age < -60 or age > config.SESSION_TTL_SECONDS:
        return False

    expected = hmac.new(
        config.SESSION_SECRET.encode("utf-8"),
        timestamp_text.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def is_authenticated(request: Request) -> bool:
    return is_valid_session_token(request.cookies.get(COOKIE_NAME))
