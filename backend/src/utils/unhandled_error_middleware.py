import logging

import sentry_sdk
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class UnhandledErrorMiddleware:
    """Превращает необработанное исключение в JSON-ответ 500.

    Должен стоять внутри CORSMiddleware: ответ ServerErrorMiddleware не получает CORS-заголовков, и браузер
    скрыл бы от frontend статус ошибки.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.exception("Необработанное исключение при обработке запроса")
            sentry_sdk.capture_exception(exc)
            if response_started:
                raise
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
            await response(scope, receive, send)
