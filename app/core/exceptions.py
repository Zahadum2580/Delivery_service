import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Обработка ошибок валидации Pydantic.
    Возвращает JSON с детальной информацией об ошибках.
    """
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Глобальная обработка неожиданных ошибок.
    Логирует ошибку и возвращает общий ответ 500.
    """
    logger.exception("Unexpected error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Централизованная обработка HTTPException
    """
    logger.warning("HTTP error %s: %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    handlers = {
        RequestValidationError: validation_exception_handler,
        StarletteHTTPException: http_exception_handler,
        Exception: global_exception_handler,
    }
    for exc_class, handler in handlers.items():
        app.add_exception_handler(exc_class, handler)
