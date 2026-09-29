from fastapi import Response

from settings import settings

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_COOKIE_PATH = "/"
# Отдельный путь: refresh не уходит на прочие эндпоинты API, только на /api/auth/*.
REFRESH_COOKIE_PATH = "/api/auth"


def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Единственное место, ставящее cookies сессии. Токены в тело ответа не попадают."""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.access_token_ttl_minutes * 60,
        path=ACCESS_COOKIE_PATH,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure_resolved,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure_resolved,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path=ACCESS_COOKIE_PATH,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure_resolved,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure_resolved,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
