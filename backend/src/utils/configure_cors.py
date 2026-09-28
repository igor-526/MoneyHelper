from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


def configure_cors(app: FastAPI, origins: list[str]) -> None:
    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
