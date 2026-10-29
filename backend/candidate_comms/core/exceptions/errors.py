from .codes import ErrorCode


class ApplicationError(Exception):
    """A business-rule failure raised by services; the API renders it in the error envelope."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        status_code: int = 400,
        fields: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.fields = fields or {}
