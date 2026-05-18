# middleware.py
import inspect  # Built-in replacement for asyncio's inspection methods
from django.utils.decorators import sync_and_async_middleware
from krm3.utils.context import request_ctx


@sync_and_async_middleware
def TimingMiddleware(get_response):
    """
    Core Django middleware providing cross-compatible thread/task local isolation.
    Guarantees automatic cleanup for both synchronous WSGI and asynchronous ASGI requests.
    """

    # 1. Asynchronous Execution Path (ASGI)
    # Using inspect.iscoroutinefunction avoids the Python 3.12+ deprecation warning
    if inspect.iscoroutinefunction(get_response):
        async def middleware(request):
            try:
                request_ctx.timing = {}
                return await get_response(request)
            finally:
                if hasattr(request_ctx, "timing"):
                    del request_ctx.timing

        return middleware

    # 2. Synchronous Execution Path (WSGI)
    else:
        def middleware(request):
            try:
                request_ctx.timing = {}
                return get_response(request)
            finally:
                if hasattr(request_ctx, "timing"):
                    del request_ctx.timing

        return middleware
