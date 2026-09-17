from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from pulse.contracts.models import IncidentReport, InvariantType, InvestigationResult
from pulse.diff.comparator import DiffReport


def synthesize_evidence_diagnosis(
    report: IncidentReport,
    diff: Optional[DiffReport] = None,
    code_snippet: Optional[str] = None,
) -> InvestigationResult:
    """Deterministic, evidence-grounded diagnostic synthesizer strictly adhering to verified facts."""
    if not report.failed_invariants:
        return InvestigationResult(
            failure_type="no_failure",
            summary="All invariant checks passed; integration is operating within declared bounds.",
            evidence=["0 invariant violations detected"],
            likely_cause="Healthy run trace",
            confidence=0.99,
            recommended_action="Promote run to baseline",
            suggested_regression_test="test_happy_path_extraction",
        )

    first_inv = report.failed_invariants[0]
    inv_result = next(r for r in report.results if r.invariant == first_inv)

    evidence: List[str] = list(inv_result.evidence)
    if diff:
        evidence.extend(diff.differences_summary)

    if first_inv == InvariantType.PAGINATION_CONTINUITY:
        return InvestigationResult(
            failure_type="pagination_stalled",
            summary=f"Pagination halted on page(s) {inv_result.affected_pages}. Page repeated previously observed records.",
            evidence=evidence,
            likely_cause="Pagination state or page parameter did not advance in the adapter request loop.",
            confidence=0.96,
            recommended_action="Inspect page progression and pagination state advancement in adapter.",
            suggested_regression_test="test_pagination_must_progress_with_unique_records",
        )

    if first_inv == InvariantType.LIMIT_BOUND:
        overrun = inv_result.details.get("overrun", "unknown")
        req_limit = inv_result.details.get("requested_limit", "declared limit")
        return InvestigationResult(
            failure_type="limit_overrun",
            summary=f"Requested limit of {req_limit} was exceeded by {overrun} records across {report.total_requests} requests.",
            evidence=evidence,
            likely_cause="Adapter continues to fetch subsequent pages and does not enforce requested limit bound.",
            confidence=0.98,
            recommended_action="Enforce requested limit boundary and slice accumulated records before returning.",
            suggested_regression_test="test_adapter_respects_requested_limit_bound",
        )

    if first_inv == InvariantType.ZERO_YIELD:
        return InvestigationResult(
            failure_type="silent_zero_yield",
            summary="HTTP request succeeded with substantial payload, but parser yielded 0 records.",
            evidence=evidence,
            likely_cause="Upstream HTML markup or JSON response key structure changed, causing CSS/JSON selectors to match 0 nodes.",
            confidence=0.94,
            recommended_action="Inspect upstream payload structure and update JSON key or HTML selector paths in extract_raw_records.",
            suggested_regression_test="test_parser_extracts_listings_from_updated_source_payload",
        )

    if first_inv == InvariantType.PROVENANCE:
        return InvestigationResult(
            failure_type="missing_provenance",
            summary="Extracted records are missing canonical provenance identifiers (source, listing ID, or URL).",
            evidence=evidence,
            likely_cause="Field mapping dropped raw ID or URL attributes during normalization.",
            confidence=0.92,
            recommended_action="Verify normalize_record populates source_listing_id and source_url from raw source payload.",
            suggested_regression_test="test_records_retain_complete_provenance",
        )

    if first_inv == InvariantType.REQUEST_CONSISTENCY:
        return InvestigationResult(
            failure_type="filter_divergence",
            summary="Request parameters diverged during multi-page pagination.",
            evidence=evidence,
            likely_cause="Pagination helper rebuilt request parameters without preserving original filter dictionary.",
            confidence=0.91,
            recommended_action="Ensure fetch_page merges base filter parameters into all paginated requests.",
            suggested_regression_test="test_multipage_requests_preserve_filter_parameters",
        )

    if first_inv == InvariantType.SCHEMA_INTEGRITY:
        return InvestigationResult(
            failure_type="schema_violation",
            summary="Records violated numerical or semantic canonical schema constraints.",
            evidence=evidence,
            likely_cause="Unsanitized source strings or negative values passed into canonical model.",
            confidence=0.95,
            recommended_action="Add validation and sanitization filters for numerical fields in normalize_record.",
            suggested_regression_test="test_schema_validation_rejects_malformed_fields",
        )

    return InvestigationResult(
        failure_type="unknown_incident",
        summary=inv_result.observed,
        evidence=evidence or ["insufficient_evidence"],
        likely_cause="Unclassified integration invariant failure",
        confidence=0.60,
        recommended_action="Inspect full run trace and raw response payloads",
        suggested_regression_test="test_regression_for_unclassified_incident",
    )


class AIInvestigator:
    """Evidence-based incident diagnosis investigator."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")

    def investigate(
        self,
        report: IncidentReport,
        diff: Optional[DiffReport] = None,
        code_snippet: Optional[str] = None,
    ) -> InvestigationResult:
        """Diagnose incident strictly using verified facts and evidence."""
        # AI is the assistant, deterministic verification is the authority.
        # Synthesizes evidence-grounded diagnosis directly adhering to schema.
        return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)
