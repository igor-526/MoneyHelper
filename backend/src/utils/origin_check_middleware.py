import json

from starlette.types import ASGIApp, Receive, Scope, Send

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_FORBIDDEN_BODY = json.dumps({"detail": "Недопустимый источник запроса"}).encode("utf-8")


class OriginCheckMiddleware:
    """CSRF: для небезопасных методов заголовок Origin, если он есть, должен входить в allowed_origins.

    Запрос без Origin (не браузерный клиент) допускается — CSRF без браузера невозможен. Пустой список
    allowed_origins означает, что все такие запросы с Origin отклоняются (закрыто по умолчанию).

    Должен добавляться *до* CORSMiddleware (то есть оказаться внутри него): тогда preflight OPTIONS
    обрабатывает сам CORS-слой, а отказ 403 не получает CORS-заголовков для чужого origin.
    """

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self._allowed_origins = set(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return

        origin = _get_header(scope, b"origin")
        if origin is not None and origin not in self._allowed_origins:
            await _send_forbidden(send)
            return

        await self.app(scope, receive, send)


def _get_header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


async def _send_forbidden(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": _FORBIDDEN_BODY})
