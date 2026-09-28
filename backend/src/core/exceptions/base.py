class AppError(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ClientError(AppError):
    status_code = 400


class AuthenticationError(ClientError):
    status_code = 401


class PermissionDeniedError(ClientError):
    status_code = 403


class NotFoundError(ClientError):
    status_code = 404


class AlreadyExistsError(ClientError):
    status_code = 409
