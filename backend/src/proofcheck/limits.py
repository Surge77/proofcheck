"""Hard limits on what one request may send, enforced before any parsing happens.

Two jobs:
1. Refuse oversized bodies early (Content-Length) and while streaming (chunked
   uploads have no Content-Length), so a huge upload can't exhaust memory.
2. Keep every uploaded file in memory. Starlette spools file parts over 1 MB to
   a temporary file on disk; for bank statements and payment screenshots that
   would break the promise that nothing is written to disk.
"""

from fastapi import HTTPException
from starlette.formparsers import MultiPartParser
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 60 screenshots of ~1.5 MB plus a statement fits comfortably; real batches are far smaller.
MAX_REQUEST_BYTES = 100 * 1024 * 1024


class InMemoryMultiPartParser(MultiPartParser):
    # The body itself is capped at MAX_REQUEST_BYTES, so no single part can grow past
    # this threshold, and SpooledTemporaryFile therefore never rolls over to disk.
    spool_max_size = MAX_REQUEST_BYTES


def _too_large() -> HTTPException:
    return HTTPException(413, f"Upload is larger than {MAX_REQUEST_BYTES // (1024 * 1024)} MB.")


class BodySizeLimit:
    """ASGI middleware: 413 for request bodies over MAX_REQUEST_BYTES."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = MAX_REQUEST_BYTES  # read per request so tests can lower it
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _reject(send)
            return
        received = 0

        async def counted_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > limit:
                # Raised inside the route, so FastAPI turns it into a normal 413 response.
                raise _too_large()
            return message

        await self.app(scope, counted_receive, send)


async def _reject(send: Send) -> None:
    body = b'{"detail":"Upload is too large."}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", b"%d" % len(body)),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
