"""``RequestContextMiddleware``: each request's user, client, start and tenant bound for what it writes (ADA-02).

Atlas's ``AtlasAuthenticationFilter`` fills its ``RequestContext`` for each request; this binds the core's request
context inside the authentication, so the admin audits a change writes name its user and client.
"""

import time

from aurelius_atlas_core.request_context import RequestContext, bound
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from aurelius_atlas_server.authentication import acting_user


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Binds the request's context while the request is served."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """The authenticated user, the client's address, the time now and the tenant (TEN-08), bound around the rest
        of the request.
        """  # noqa: D205 - one sentence
        context = RequestContext(
            user=acting_user(request),
            client_ip_address=None if request.client is None else request.client.host,
            request_time=int(time.time() * 1000),
            tenant=getattr(request.state, "tenant", None),
        )
        with bound(context):
            return await call_next(request)
