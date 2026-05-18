from types import TracebackType
from typing import Self

from django.test.utils import CaptureQueriesContext
from flags.state import flag_enabled

from krm3.utils.context import request_ctx

class SqlPerfMonitor(CaptureQueriesContext):
    def __enter__(self) -> Self:
        self.enabled = flag_enabled('SQL_PERF_MONITOR_ENABLED')
        if self.enabled:
            super().__enter__()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if not self.enabled:
            return
        super().__exit__(exc_type, exc_value, exc_tb)
        if exc_type is None:
            request_ctx.timing.setdefault('sql', []).extend(self.captured_queries)
