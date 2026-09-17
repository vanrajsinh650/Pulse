from __future__ import annotations

from typing import Dict, List, Set
from pulse.contracts.models import InvariantResult, InvariantType, RunTrace


def check_pagination_continuity(trace: RunTrace) -> InvariantResult:
    """Verify that pagination progresses and does not repeat previously fetched pages."""
    if trace.total_requests <= 1:
        return InvariantResult(
            invariant=InvariantType.PAGINATION_CONTINUITY,
            passed=True,
            expected="pagination progress",
            observed=f"{trace.total_requests} page fetched (single page run)",
            evidence=["single request run; no pagination loop possible"],
        )

    # Check overall duplicate records
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []
    for record in trace.records:
        if record.source_listing_id in seen_ids:
            duplicate_ids.append(record.source_listing_id)
        else:
            seen_ids.add(record.source_listing_id)

    # Check request payload hash/content duplication
    payload_to_pages: Dict[str, List[int]] = {}
    for req in trace.requests:
        payload = (req.raw_payload or "").strip()
        if payload:
            payload_to_pages.setdefault(payload, []).append(req.page)

    duplicate_pages: List[int] = []
    for _, pages in payload_to_pages.items():
        if len(pages) > 1:
            duplicate_pages.extend(pages[1:])

    # Also detect if duplicates account for all or majority of records in later pages
    has_duplicates = len(duplicate_ids) > 0 or len(duplicate_pages) > 0

    if not has_duplicates:
        return InvariantResult(
            invariant=InvariantType.PAGINATION_CONTINUITY,
            passed=True,
            expected="unique records per page",
            observed=f"{len(seen_ids)} unique records across {trace.total_requests} pages",
            evidence=["all record IDs unique across pagination"],
        )

    affected_pages = sorted(set(duplicate_pages))
    if not affected_pages and duplicate_ids:
        # If specific request pages were recorded, mark subsequent pages as affected
        affected_pages = [req.page for req in trace.requests[1:]]

    return InvariantResult(
        invariant=InvariantType.PAGINATION_CONTINUITY,
        passed=False,
        expected="unique records progressing across pages",
        observed=f"{len(duplicate_ids)} duplicated records detected on page(s) {affected_pages}",
        affected_pages=affected_pages,
        affected_record_ids=list(dict.fromkeys(duplicate_ids)),
        details={
            "duplicate_count": len(duplicate_ids),
            "unique_count": len(seen_ids),
            "affected_pages": affected_pages,
            "duplicate_pages": duplicate_pages,
        },
        evidence=[
            f"pagination repeated previous page",
            f"affected page(s): {affected_pages}",
            f"{len(duplicate_ids)} duplicate records detected",
        ],
    )
