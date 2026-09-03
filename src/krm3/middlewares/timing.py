# middleware.py
import inspect  # Built-in replacement for asyncio's inspection methods
from collections.abc import Awaitable, Callable

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import sync_and_async_middleware

from krm3.utils.context import request_ctx

type SyncGetResponse = Callable[[HttpRequest], HttpResponse]
type AsyncGetResponse = Callable[[HttpRequest], Awaitable[HttpResponse]]


@sync_and_async_middleware
def TimingMiddleware(  # noqa: N802
    get_response: SyncGetResponse | AsyncGetResponse,
) -> SyncGetResponse | AsyncGetResponse:
    """
    Core Django middleware providing cross-compatible thread/task local isolation.

    Guarantees automatic cleanup for both synchronous WSGI and asynchronous ASGI requests.
    """
    # 1. Asynchronous Execution Path (ASGI)
    # Using inspect.iscoroutinefunction avoids the Python 3.12+ deprecation warning
    if inspect.iscoroutinefunction(get_response):
        async def middleware(request: HttpRequest) -> HttpResponse:
            try:
                request_ctx.timing = {}
                return await get_response(request)
            finally:
                if hasattr(request_ctx, "timing"):
                    del request_ctx.timing

        return middleware

    # 2. Synchronous Execution Path (WSGI)
    def middleware(request: HttpRequest) -> HttpResponse:
        try:
            request_ctx.timing = {}
            return get_response(request)
        finally:
            if hasattr(request_ctx, "timing"):
                del request_ctx.timing

    return middleware
