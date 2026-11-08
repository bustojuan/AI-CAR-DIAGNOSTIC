import hmac
import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.responses import JSONResponse

from app.core.logging import request_id_context

logger = logging.getLogger(__name__)


class RequestMiddleware:
    """Bound real body bytes (also without Content-Length); attach safe correlation IDs."""

    def __init__(self, app, max_bytes: int, upload_max_bytes=None, admin_token=None):
        self.app, self.max_bytes = app, max_bytes
        self.upload_max_bytes, self.admin_token = upload_max_bytes, admin_token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        limit = self.max_bytes
        if (
            scope.get("path") == "/api/v1/documents/upload"
            and self.admin_token
            and hmac.compare_digest(headers.get(b"x-admin-token", b""), self.admin_token.encode())
        ):
            limit = self.upload_max_bytes
        supplied_id = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = (
            supplied_id if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied_id) else str(uuid4())
        )
        scope.setdefault("state", {})["request_id"] = request_id
        request_id_context.set(request_id)
        started = perf_counter()
        response_started = False

        async def send_response(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ] + [(b"x-request-id", request_id.encode())]
                if scope.get("path", "").startswith("/api/v1/parts/"):
                    message["headers"] = [
                        (key, value)
                        for key, value in message["headers"]
                        if key.lower() not in (b"cache-control", b"pragma")
                    ] + [(b"cache-control", b"no-store"), (b"pragma", b"no-cache")]
                logger.info(
                    "request_id=%s method=%s status=%s duration_ms=%.1f",
                    request_id,
                    scope["method"],
                    message["status"],
                    (perf_counter() - started) * 1000,
                )
            await send(message)

        async def reject(status, code, message):
            await JSONResponse(
                status_code=status,
                content={
                    "error": {
                        "code": code,
                        "message": message,
                        "request_id": request_id,
                    }
                },
            )(scope, receive, send_response)

        if b"content-length" in headers:
            try:
                size = int(headers[b"content-length"])
                if size < 0:
                    raise ValueError
            except ValueError:
                return await reject(400, "invalid_content_length", "Invalid Content-Length header.")
            if size > limit:
                return await reject(413, "request_too_large", "Request body exceeds size limit.")
        body = bytearray()
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            body.extend(event.get("body", b""))
            if len(body) > limit:
                return await reject(413, "request_too_large", "Request body exceeds size limit.")
            if not event.get("more_body", False):
                break
        consumed = False

        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        try:
            await self.app(scope, replay, send_response)
        except Exception as exc:
            # Consume unexpected failures here so the server does not log raw provider payloads.
            logger.error(
                "unexpected_error request_id=%s category=%s", request_id, type(exc).__name__
            )
            if response_started:
                raise RuntimeError("Response interrupted.") from None
            await reject(500, "internal_error", "An unexpected server error occurred.")
