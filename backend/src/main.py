from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.auth import router as auth_router
from api.errors import register_error_handlers
from settings import settings
from utils.configure_cors import configure_cors
from utils.configure_sentry import configure_sentry
from utils.database import close_database
from utils.origin_check_middleware import OriginCheckMiddleware
from utils.unhandled_error_middleware import UnhandledErrorMiddleware

configure_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_database()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_title, debug=settings.debug, lifespan=lifespan)

    @application.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(auth_router)

    register_error_handlers(application)
    # Порядок важен: последний добавленный middleware — самый внешний. Обработчик 500 и проверка Origin
    # должны быть внутри CORS, иначе их ответы не получат CORS-заголовков.
    application.add_middleware(UnhandledErrorMiddleware)
    application.add_middleware(OriginCheckMiddleware, allowed_origins=settings.cors_origins)
    configure_cors(application, settings.cors_origins)
    return application


app = create_app()
