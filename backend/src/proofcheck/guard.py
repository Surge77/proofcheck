"""Only pages served by ProofCheck itself may call its API.

CORS alone isn't enough: it stops other sites *reading* responses, but a
multipart POST is a "simple" request, so any website the user visits could
fire uploads at 127.0.0.1 and burn their GPU. And with DNS rebinding, a site
can even become same-origin. Checking Host and Origin closes both doors.
"""

from starlette.types import ASGIApp, Receive, Scope, Send

from proofcheck.config import Settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def allowed_origins(settings: Settings, dev_origins: list[str]) -> set[str]:
    own = {f"http://{host}:{settings.port}" for host in ("127.0.0.1", "localhost")}
    return own | set(dev_origins)


class OriginGuard:
    """403 for state-changing requests whose Origin is another website."""

    def __init__(self, app: ASGIApp, origins: set[str]) -> None:
        self.app = app
        self.origins = origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in SAFE_METHODS:
            origin = dict(scope["headers"]).get(b"origin")
            if origin is not None and origin.decode("latin-1") not in self.origins:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send({"type": "http.response.body", "body": b'{"detail":"Forbidden"}'})
                return
        await self.app(scope, receive, send)


def host_guard_hosts(settings: Settings) -> list[str]:
    # A rebinding attack reaches 127.0.0.1 but keeps sending its own hostname.
    return ["*"] if settings.allow_lan else ["127.0.0.1", "localhost"]
