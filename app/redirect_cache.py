from __future__ import annotations

from app.extensions import cache

_KEY_FMT = "redirect:v1:{short_code}"


def redirect_cache_key(short_code: str) -> str:
    return _KEY_FMT.format(short_code=short_code)


def get_redirect_target(short_code: str) -> str | None:
    return cache.get(redirect_cache_key(short_code))


def set_redirect_target(short_code: str, original_url: str) -> None:
    cache.set(redirect_cache_key(short_code), original_url)


def invalidate_redirect(short_code: str) -> None:
    cache.delete(redirect_cache_key(short_code))
