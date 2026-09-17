from __future__ import annotations

import abc
import uuid
from collections.abc import Callable
from typing import Any

from pulse.contracts.models import PropertyRecord, RequestTrace, RunTrace


class SourceFetchError(Exception):
    """Raised when an adapter fails to fetch data from the upstream source."""


class SourceParseError(Exception):
    """Raised when an adapter fails to parse the upstream response payload."""


TransportFunc = Callable[[str, dict[str, Any], dict[str, str]], RequestTrace]


class BaseAdapter(abc.ABC):
    """Base interface for source-specific web data adapters."""

    def __init__(self, transport: TransportFunc | None = None) -> None:
        self.transport = transport

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Name of the source, e.g. 'nextimmo'."""

    @abc.abstractmethod
    def fetch_page(self, page: int, params: dict[str, Any] | None = None) -> RequestTrace:
        """Fetch a single page, capturing network trace."""

    @abc.abstractmethod
    def extract_raw_records(self, payload: str) -> list[dict[str, Any]]:
        """Extract unnormalized record dictionaries from page payload."""

    @abc.abstractmethod
    def normalize_record(self, raw: dict[str, Any]) -> PropertyRecord:
        """Transform unnormalized raw record into canonical PropertyRecord."""

    def run(self, limit: int = 50, start_page: int = 1) -> RunTrace:
        """Execute extraction run up to the requested limit."""
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        requests: list[RequestTrace] = []
        records: list[PropertyRecord] = []
        current_page = start_page

        while len(records) < limit:
            trace = self.fetch_page(current_page)
            requests.append(trace)

            if not trace.raw_payload:
                break

            raw_items = self.extract_raw_records(trace.raw_payload)
            if not raw_items:
                break

            for raw in raw_items:
                record = self.normalize_record(raw)
                records.append(record)
                if len(records) >= limit:
                    break

            current_page += 1

        return RunTrace(
            run_id=run_id,
            source=self.source_name,
            requested_limit=limit,
            requests=requests,
            records=records,
        )
