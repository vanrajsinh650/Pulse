from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from pulse.adapters.base import BaseAdapter, TransportFunc
from pulse.contracts.models import RequestTrace, RunTrace
from pulse.replay.recorder import load_run_trace


class ReplayEngine:
    """Offline deterministic replay engine using recorded RunTraces."""

    def __init__(self, trace: RunTrace) -> None:
        self.trace = trace
        # Index request traces by page and by URL
        self.page_index: Dict[int, RequestTrace] = {req.page: req for req in trace.requests}
        self.url_index: Dict[str, RequestTrace] = {req.url: req for req in trace.requests}

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> ReplayEngine:
        trace = load_run_trace(path)
        return cls(trace)

    def as_transport(self) -> TransportFunc:
        """Returns a transport function that matches adapter calls to recorded traces."""
        def transport(url: str, params: Dict[str, Any], headers: Dict[str, str]) -> RequestTrace:
            # First match exact URL
            if url in self.url_index:
                return self.url_index[url]

            # Next match by page extracted from URL if possible
            for req in self.trace.requests:
                if f"/page/{req.page}" in url or f"page={req.page}" in url:
                    return req

            # Fallback to matching request order if index exists
            if self.trace.requests:
                return self.trace.requests[0]

            raise RuntimeError(f"No recorded request found for URL: {url}")

        return transport

    def replay_adapter(self, adapter_cls: type[BaseAdapter], limit: Optional[int] = None) -> RunTrace:
        """Replay an adapter through the recorded requests offline."""
        effective_limit = limit if limit is not None else (self.trace.requested_limit or 50)
        adapter = adapter_cls(transport=self.as_transport())
        return adapter.run(limit=effective_limit)
