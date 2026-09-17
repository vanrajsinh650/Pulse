from __future__ import annotations

from pulse.contracts.models import InvariantResult, InvariantType, RunTrace


def check_limit_bound(trace: RunTrace) -> InvariantResult:
    """Verify that collected records do not exceed the requested limit bound."""
    if trace.requested_limit is None:
        return InvariantResult(
            invariant=InvariantType.LIMIT_BOUND,
            passed=True,
            expected="no limit set",
            observed=f"{trace.total_records} records collected",
            evidence=["no limit declared"],
        )

    limit = trace.requested_limit
    collected = trace.total_records
    passed = collected <= limit

    if passed:
        return InvariantResult(
            invariant=InvariantType.LIMIT_BOUND,
            passed=True,
            expected=f"<= {limit} records",
            observed=f"{collected} records",
            evidence=[f"total_records ({collected}) <= requested_limit ({limit})"],
        )

    overrun = collected - limit
    return InvariantResult(
        invariant=InvariantType.LIMIT_BOUND,
        passed=False,
        expected=f"<= {limit} records",
        observed=f"{collected} records",
        affected_pages=[r.page for r in trace.requests],
        affected_record_ids=[r.source_listing_id for r in trace.records[limit:]],
        details={
            "requested_limit": limit,
            "collected": collected,
            "overrun": overrun,
            "requests_count": trace.total_requests,
        },
        evidence=[
            f"requested limit = {limit}",
            f"collected records = {collected}",
            f"limit exceeded by {overrun} records across {trace.total_requests} requests",
        ],
    )
