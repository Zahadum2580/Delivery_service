import logging
import time

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        start_time = time.time()

        # Пропускаем Swagger/OpenAPI
        if request.url.path.startswith(
            ("/docs", "/openapi.json", "/redoc", "/swagger")
        ):
            await self.app(scope, receive, send)
            return

        response_status = None

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except HTTPException as he:
            logger.warning("HTTP error %s: %s", he.status_code, he.detail)
            response = JSONResponse(
                status_code=he.status_code,
                content={"error": "HTTPException", "details": he.detail},
            )
            await response(scope, receive, send)
            response_status = he.status_code
        except Exception as e:
            logger.exception("Unexpected error: %s", e)
            response = JSONResponse(
                status_code=500,
                content={"error": "InternalServerError", "details": str(e)},
            )
            await response(scope, receive, send)
            response_status = 500
        finally:
            process_time = time.time() - start_time
            logger.info(
                "Completed %s %s with status %s in %.3f sec",
                request.method,
                request.url.path,
                response_status,
                process_time,
            )
