from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.exceptions import AppError


def _serializable_errors(errors: list[Any]) -> list[Any]:
    """Контекст ошибки может содержать исключения — приводим их к строкам, чтобы ответ сериализовался."""
    result = []
    for error in errors:
        ctx = error.get("ctx")
        if ctx:
            error = {
                **error,
                "ctx": {key: str(value) if isinstance(value, Exception) else value for key, value in ctx.items()},
            }
        result.append(error)
    return jsonable_encoder(result)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": _serializable_errors(list(exc.errors()))})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
