from __future__ import annotations

from typing import Any, Dict, List
from pulse.contracts.models import InvariantResult, InvariantType, RunTrace


def check_request_consistency(trace: RunTrace) -> InvariantResult:
    """Verify that search filters and parameters remain consistent across all pages in a run."""
    if trace.total_requests <= 1:
        return InvariantResult(
            invariant=InvariantType.REQUEST_CONSISTENCY,
            passed=True,
            expected="consistent parameters across requests",
            observed=f"{trace.total_requests} request (single request run)",
            evidence=["no multi-request divergence possible"],
        )

    # Filter out pagination-specific params (e.g., page, offset) to compare base query filters
    def base_params(params: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in params.items() if k.lower() not in {"page", "p", "offset", "start"}}

    first_req = trace.requests[0]
    expected_filters = base_params(first_req.params)

    inconsistent_pages: List[int] = []
    discrepancies: List[str] = []

    for req in trace.requests[1:]:
        current_filters = base_params(req.params)
        if current_filters != expected_filters:
            inconsistent_pages.append(req.page)
            discrepancies.append(
                f"Page {req.page} filters {current_filters} diverged from initial filters {expected_filters}"
            )

    if not inconsistent_pages:
        return InvariantResult(
            invariant=InvariantType.REQUEST_CONSISTENCY,
            passed=True,
            expected=f"parameters consistent with initial request ({expected_filters})",
            observed=f"all {trace.total_requests} requests maintained consistent filters",
            evidence=["all requests maintained identical base filter parameters"],
        )

    return InvariantResult(
        invariant=InvariantType.REQUEST_CONSISTENCY,
        passed=False,
        expected=f"consistent filters ({expected_filters})",
        observed=f"parameter divergence detected on page(s) {inconsistent_pages}",
        affected_pages=inconsistent_pages,
        details={"discrepancies": discrepancies},
        evidence=discrepancies[:5],
    )
