from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.analytics import router as analytics_router
from api.auth import router as auth_router
from api.balances import wallet_balances_router
from api.categories import router as categories_router
from api.currencies import router as currencies_router
from api.errors import register_error_handlers
from api.icons import router as icons_router
from api.transactions import router as transactions_router
from api.transfers import router as transfers_router
from api.wallets import router as wallets_router
from api.workspaces import router as workspaces_router
from seeds import SEED_DEFINITIONS
from settings import settings
from utils.configure_cors import configure_cors
from utils.configure_sentry import configure_sentry
from utils.database import close_database, engine
from utils.origin_check_middleware import OriginCheckMiddleware
from utils.seeding import run_seeding
from utils.unhandled_error_middleware import UnhandledErrorMiddleware

configure_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.seeding_enabled:
        await run_seeding(engine, SEED_DEFINITIONS)
    yield
    await close_database()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_title, debug=settings.debug, lifespan=lifespan)

    @application.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(analytics_router)
    application.include_router(auth_router)
    application.include_router(categories_router)
    application.include_router(currencies_router)
    application.include_router(icons_router)
    application.include_router(transactions_router)
    application.include_router(transfers_router)
    application.include_router(wallet_balances_router)
    application.include_router(wallets_router)
    application.include_router(workspaces_router)

    register_error_handlers(application)
    # Порядок важен: последний добавленный middleware — самый внешний. Обработчик 500 и проверка Origin
    # должны быть внутри CORS, иначе их ответы не получат CORS-заголовков.
    application.add_middleware(UnhandledErrorMiddleware)
    application.add_middleware(OriginCheckMiddleware, allowed_origins=settings.cors_origins)
    configure_cors(application, settings.cors_origins)
    return application


app = create_app()
