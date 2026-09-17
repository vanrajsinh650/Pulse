from __future__ import annotations

from typing import List, Optional
from pulse.contracts.models import IncidentReport, InvariantResult, InvariantType, RunTrace
from pulse.verification.checks.limit_bound import check_limit_bound
from pulse.verification.checks.pagination_continuity import check_pagination_continuity
from pulse.verification.checks.provenance import check_provenance
from pulse.verification.checks.request_consistency import check_request_consistency
from pulse.verification.checks.schema_integrity import check_schema_integrity
from pulse.verification.checks.zero_yield import check_zero_yield


class VerificationEngine:
    """Coordinates deterministic invariant evaluation over extraction run traces."""

    def __init__(self) -> None:
        self.checks = [
            check_limit_bound,
            check_pagination_continuity,
            check_zero_yield,
            check_provenance,
            check_request_consistency,
            check_schema_integrity,
        ]

    def verify(self, trace: RunTrace, incident_id: Optional[str] = None) -> IncidentReport:
        results: List[InvariantResult] = []
        failed_invariants: List[InvariantType] = []

        for check_fn in self.checks:
            result = check_fn(trace)
            results.append(result)
            if not result.passed:
                failed_invariants.append(result.invariant)

        status = "FAILED" if failed_invariants else "PASSED"
        inc_id = incident_id or f"INC-{trace.run_id}"

        # Generate actionable summary and recommended next step
        if not failed_invariants:
            summary = f"All {len(self.checks)} invariants passed successfully across {trace.total_records} records."
            recommended_next_step = "run is healthy; integration ready for promotion"
        else:
            first_fail = next(r for r in results if not r.passed)
            summary = f"Invariant {first_fail.invariant.value} violated: {first_fail.observed}"

            if first_fail.invariant == InvariantType.PAGINATION_CONTINUITY:
                recommended_next_step = "inspect pagination state advancement and next_page offset handling"
            elif first_fail.invariant == InvariantType.LIMIT_BOUND:
                recommended_next_step = "inspect loop termination bounds and slicing when record count reaches requested limit"
            elif first_fail.invariant == InvariantType.ZERO_YIELD:
                recommended_next_step = "inspect HTML/JSON parser selectors; upstream markup structure changed"
            elif first_fail.invariant == InvariantType.PROVENANCE:
                recommended_next_step = "inspect record normalization mappings for source_listing_id or source_url"
            elif first_fail.invariant == InvariantType.REQUEST_CONSISTENCY:
                recommended_next_step = "verify query parameter propagation in multi-page request builder"
            elif first_fail.invariant == InvariantType.SCHEMA_INTEGRITY:
                recommended_next_step = "inspect field coercion and type validation on parsed numerical fields"
            else:
                recommended_next_step = "inspect adapter logs and request payloads"

        return IncidentReport(
            incident_id=inc_id,
            source=trace.source,
            status=status,
            results=results,
            summary=summary,
            recommended_next_step=recommended_next_step,
            total_records=trace.total_records,
            total_requests=trace.total_requests,
            failed_invariants=failed_invariants,
        )
