from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from core.exceptions import AuthenticationError
from tests.fakes import FixedClock
from utils.jwt_tokens import JwtTokenService

SECRET = "x" * 32
USER_ID = uuid4()


def make_service(clock: FixedClock | None = None) -> JwtTokenService:
    return JwtTokenService(
        secret=SECRET,
        clock=clock or FixedClock(),
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=30),
    )


def test_issue_and_verify_access() -> None:
    service = make_service()

    token = service.issue_access(USER_ID)
    claims = service.verify_access(token)

    assert claims.user_id == USER_ID


def test_issue_and_verify_refresh_carries_version() -> None:
    service = make_service()

    token = service.issue_refresh(USER_ID, version=3)
    claims = service.verify_refresh(token)

    assert claims.user_id == USER_ID
    assert claims.version == 3


def test_access_expires_by_clock() -> None:
    clock = FixedClock()
    service = make_service(clock)
    token = service.issue_access(USER_ID)

    clock.advance(timedelta(minutes=15, seconds=1))

    with pytest.raises(AuthenticationError):
        service.verify_access(token)


def test_access_valid_just_before_expiry() -> None:
    clock = FixedClock()
    service = make_service(clock)
    token = service.issue_access(USER_ID)

    clock.advance(timedelta(minutes=14, seconds=59))

    service.verify_access(token)  # не бросает


def test_refresh_token_rejected_as_access() -> None:
    service = make_service()
    token = service.issue_refresh(USER_ID, version=0)

    with pytest.raises(AuthenticationError):
        service.verify_access(token)


def test_access_token_rejected_as_refresh() -> None:
    service = make_service()
    token = service.issue_access(USER_ID)

    with pytest.raises(AuthenticationError):
        service.verify_refresh(token)


def test_tampered_signature_rejected() -> None:
    service = make_service()
    token = service.issue_access(USER_ID)

    with pytest.raises(AuthenticationError):
        JwtTokenService(
            secret="y" * 32, clock=FixedClock(), access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=30)
        ).verify_access(token)


def test_garbage_token_rejected() -> None:
    service = make_service()

    with pytest.raises(AuthenticationError):
        service.verify_access("not-a-jwt")


def test_alg_none_token_rejected() -> None:
    service = make_service()
    forged = jwt.encode(
        {"sub": str(USER_ID), "token_type": "access", "iat": 0, "exp": 9_999_999_999},
        key="",
        algorithm="none",
    )

    with pytest.raises(AuthenticationError):
        service.verify_access(forged)


def test_missing_required_claim_rejected() -> None:
    service = make_service()
    token = jwt.encode({"sub": str(USER_ID), "iat": 0, "exp": 9_999_999_999}, SECRET, algorithm="HS256")

    with pytest.raises(AuthenticationError):
        service.verify_access(token)


def test_refresh_without_version_rejected() -> None:
    service = make_service()
    token = jwt.encode(
        {"sub": str(USER_ID), "token_type": "refresh", "iat": 0, "exp": 9_999_999_999}, SECRET, algorithm="HS256"
    )

    with pytest.raises(AuthenticationError):
        service.verify_refresh(token)


def test_non_uuid_subject_rejected() -> None:
    service = make_service()
    token = jwt.encode(
        {"sub": "not-a-uuid", "token_type": "access", "iat": 0, "exp": 9_999_999_999}, SECRET, algorithm="HS256"
    )

    with pytest.raises(AuthenticationError):
        service.verify_access(token)
