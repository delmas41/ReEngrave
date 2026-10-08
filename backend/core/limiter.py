"""
Shared slowapi rate limiter instance.

The key is the client address. Behind a reverse proxy the socket address is
the proxy's, so every client would share one budget; with
`settings.trust_proxy_headers` (TRUST_PROXY_HEADERS) the first
`X-Forwarded-For` hop is used instead. It is off by default because the
header is client-controlled wherever no proxy sits in front of the app.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from core.config import settings


def client_key(request: Request) -> str:
    if settings.trust_proxy_headers:
        first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


limiter = Limiter(key_func=client_key)


def setting_limit(name: str):
    """A slowapi limit that reads `settings.<name>` on every request."""
    return lambda: getattr(settings, name)
