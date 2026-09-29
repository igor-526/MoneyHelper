from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Response, status

from api.cookies import REFRESH_COOKIE_NAME, clear_session_cookies, set_session_cookies
from api.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, UserOut
from core.exceptions import AuthenticationError
from core.services.auth import INVALID_OR_EXPIRED_TOKEN_MESSAGE, AuthService
from depends.auth import get_auth_service, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    user = await auth_service.register(email=data.email, password=data.password)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
async def login(
    data: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    user, tokens = await auth_service.login(email=data.email, password=data.password)
    set_session_cookies(response, tokens.access_token, tokens.refresh_token)
    return UserOut.model_validate(user)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh(
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> None:
    if refresh_token is None:
        raise AuthenticationError(INVALID_OR_EXPIRED_TOKEN_MESSAGE)
    tokens = await auth_service.refresh(refresh_token)
    set_session_cookies(response, tokens.access_token, tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> None:
    # Не бросает ошибку без сессии/с недействительным refresh: logout всегда 204 и очищает cookies.
    await auth_service.logout(refresh_token)
    clear_session_cookies(response)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    response: Response,
    user_id: Annotated[UUID, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    tokens = await auth_service.change_password(user_id, data.current_password, data.new_password)
    set_session_cookies(response, tokens.access_token, tokens.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(
    user_id: Annotated[UUID, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    user = await auth_service.get_user(user_id)
    return UserOut.model_validate(user)
