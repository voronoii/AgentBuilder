from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    # Knowledge
    KNOWLEDGE_NOT_FOUND = "KNOWLEDGE_NOT_FOUND"
    KNOWLEDGE_DUPLICATE_NAME = "KNOWLEDGE_DUPLICATE_NAME"
    KNOWLEDGE_INVALID_INPUT = "KNOWLEDGE_INVALID_INPUT"
    KNOWLEDGE_UNSUPPORTED_FILE = "KNOWLEDGE_UNSUPPORTED_FILE"
    KNOWLEDGE_FILE_TOO_LARGE = "KNOWLEDGE_FILE_TOO_LARGE"
    KNOWLEDGE_PARSER_FAILED = "KNOWLEDGE_PARSER_FAILED"
    KNOWLEDGE_EMBEDDING_FAILED = "KNOWLEDGE_EMBEDDING_FAILED"
    KNOWLEDGE_QDRANT_UNAVAILABLE = "KNOWLEDGE_QDRANT_UNAVAILABLE"
    # MCP
    MCP_NOT_FOUND = "MCP_NOT_FOUND"
    MCP_DUPLICATE_NAME = "MCP_DUPLICATE_NAME"
    MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"
    MCP_DISCOVERY_FAILED = "MCP_DISCOVERY_FAILED"
    # Workflow
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
    WORKFLOW_DUPLICATE_NAME = "WORKFLOW_DUPLICATE_NAME"
    # Run
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    RUN_ALREADY_FINISHED = "RUN_ALREADY_FINISHED"
    RUN_CANCEL_FAILED = "RUN_CANCEL_FAILED"
    COMPILATION_FAILED = "COMPILATION_FAILED"
    # Settings
    SETTING_NOT_FOUND = "SETTING_NOT_FOUND"
    # App (Publishing)
    APP_NOT_FOUND = "APP_NOT_FOUND"
    APP_INACTIVE = "APP_INACTIVE"
    APP_ALREADY_EXISTS = "APP_ALREADY_EXISTS"
    INVALID_API_KEY = "INVALID_API_KEY"
    # Conversation
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    CONVERSATION_NOT_OWNED = "CONVERSATION_NOT_OWNED"
    # Cross-cutting
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INTERNAL_UNEXPECTED = "INTERNAL_UNEXPECTED"


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: ErrorCode,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail)


def _envelope(
    *, detail: str, code: str, request_id: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"detail": detail, "code": code, "request_id": request_id}
    if extra:
        body["extra"] = extra
    return body


def _request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get("x-request-id", "")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                detail=exc.detail,
                code=str(exc.code),
                request_id=rid,
                extra=exc.extra,
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=422,
            content=_envelope(
                detail="요청 데이터가 올바르지 않습니다.",
                code=ErrorCode.VALIDATION_FAILED,
                request_id=rid,
                extra={"errors": exc.errors()},
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=500,
            content=_envelope(
                detail="서버 내부 오류가 발생했습니다.",
                code=ErrorCode.INTERNAL_UNEXPECTED,
                request_id=rid,
            ),
            headers={"X-Request-ID": rid},
        )
