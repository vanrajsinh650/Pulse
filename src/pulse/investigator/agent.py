from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types

from pulse.contracts.models import IncidentReport, InvariantType, InvestigationResult, RunTrace
from pulse.diff.comparator import DiffReport

INVESTIGATOR_SYSTEM_INSTRUCTION = (
    "You are an integration debugging assistant.\n"
    "You are given verified facts from a deterministic verification system.\n"
    "Your job is to explain the likely cause of the failure.\n\n"
    "Rules:\n"
    "- Use only supplied evidence.\n"
    "- Never invent source behavior.\n"
    "- Never invent code behavior.\n"
    "- Never claim the incident is healthy.\n"
    "- Never override deterministic verification.\n"
    "- Distinguish evidence from inference.\n"
    "- If evidence is insufficient, set failure_type to 'insufficient_evidence' and explain why.\n"
    "- Suggest the smallest reasonable next debugging step.\n"
    "- Suggest a regression test that protects the observed failure.\n"
    "- Do not use dramatic or marketing language.\n"
    "- The output should sound like a practical engineer's debugging note."
)


def synthesize_evidence_diagnosis(
    report: IncidentReport,
    diff: DiffReport | None = None,
    code_snippet: str | None = None,
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
            source="deterministic fallback",
        )

    first_inv = report.failed_invariants[0]
    inv_result = next(r for r in report.results if r.invariant == first_inv)

    evidence: list[str] = list(inv_result.evidence)
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
            source="deterministic fallback",
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
            source="deterministic fallback",
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
            source="deterministic fallback",
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
            source="deterministic fallback",
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
            source="deterministic fallback",
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
            source="deterministic fallback",
        )

    return InvestigationResult(
        failure_type="unknown_incident",
        summary=inv_result.observed,
        evidence=evidence or ["insufficient_evidence"],
        likely_cause="Unclassified integration invariant failure",
        confidence=0.60,
        recommended_action="Inspect full run trace and raw response payloads",
        suggested_regression_test="test_regression_for_unclassified_incident",
        source="deterministic fallback",
    )


def build_investigation_prompt(
    report: IncidentReport,
    diff: DiffReport | None = None,
    code_snippet: str | None = None,
    trace: RunTrace | None = None,
) -> str:
    """Build a sanitized, evidence-grounded prompt without leaking credentials or raw payloads."""
    prompt_parts = [
        f"Incident ID: {report.incident_id}",
        f"Source Adapter: {report.source}",
        f"Status: {report.status}",
        f"Total Requests: {report.total_requests}",
        f"Total Records Extracted: {report.total_records}",
    ]
    failed_names = [inv.value for inv in report.failed_invariants]
    prompt_parts.append(f"Failed Invariants: {', '.join(failed_names)}")

    for res in report.results:
        if not res.passed:
            prompt_parts.append(f"\n--- Invariant Violation: {res.invariant.value} ---")
            prompt_parts.append(f"Expected: {res.expected}")
            prompt_parts.append(f"Observed: {res.observed}")
            if res.affected_pages:
                prompt_parts.append(f"Affected Pages: {res.affected_pages}")
            if res.affected_record_ids:
                prompt_parts.append(f"Affected Record IDs (sample): {res.affected_record_ids[:10]}")
            if res.details:
                prompt_parts.append(f"Details: {res.details}")
            if res.evidence:
                prompt_parts.append("Evidence:")
                for ev in res.evidence:
                    prompt_parts.append(f"  - {ev}")

    if diff:
        prompt_parts.append("\n--- Structural Diff (Baseline vs Incident) ---")
        prompt_parts.append(f"Requests: {diff.pages_baseline} (baseline) vs {diff.pages_incident} (incident)")
        prompt_parts.append(
            f"Records: {diff.records_baseline} (baseline) vs {diff.records_incident} (incident) [delta: {diff.records_delta:+d}]"
        )
        prompt_parts.append(f"Unique Records: {diff.unique_ids_baseline} (baseline) vs {diff.unique_ids_incident} (incident)")
        if diff.differences_summary:
            prompt_parts.append("Differences Summary:")
            for d in diff.differences_summary:
                prompt_parts.append(f"  - {d}")

    if trace and trace.requests:
        prompt_parts.append("\n--- Sanitized Request Summary ---")
        for req in trace.requests:
            prompt_parts.append(
                f"Page {req.page}: {req.method} {req.url} -> Status {req.status_code}, Response Size: {req.response_size} bytes"
            )

    if code_snippet:
        prompt_parts.append(f"\n--- Relevant Parser/Adapter Code Snippet ---\n{code_snippet}")

    return "\n".join(prompt_parts)


class AIInvestigator:
    """Evidence-based incident diagnosis investigator using Gemini with deterministic fallback."""

    DEFAULT_MODEL = "gemini-3.1-flash-lite"

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self._client = client
        if self._client is None and self.api_key:
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=15000),
            )

    def investigate(
        self,
        report: IncidentReport,
        diff: DiffReport | None = None,
        code_snippet: str | None = None,
        trace: RunTrace | None = None,
    ) -> InvestigationResult:
        """Diagnose incident strictly using verified facts and evidence.

        Deterministic verification is the sole authority for pass/fail.
        If healthy or no Gemini client is available, falls back to deterministic synthesis.
        """
        # 1. Authority: AI never decides pass/fail or diagnoses healthy runs as broken
        if not report.failed_invariants:
            return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)

        # 2. Check client availability
        if self._client is None:
            return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)

        # 3. Build focused, sanitized context
        user_prompt = build_investigation_prompt(report, diff=diff, code_snippet=code_snippet, trace=trace)

        # 4. Request structured diagnosis from Gemini
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InvestigationResult,
                system_instruction=INVESTIGATOR_SYSTEM_INSTRUCTION,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )

            if hasattr(self._client, "models"):
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=config,
                )
            elif callable(self._client):
                response = self._client(
                    model=self.model,
                    contents=user_prompt,
                    config=config,
                )
            else:
                return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)

            parsed: InvestigationResult | None = None
            if hasattr(response, "parsed") and isinstance(response.parsed, InvestigationResult):
                parsed = response.parsed
            elif hasattr(response, "text") and response.text:
                parsed = InvestigationResult.model_validate_json(response.text)

            if parsed is not None:
                # Clamp confidence within schema bounds
                parsed.confidence = max(0.0, min(1.0, float(parsed.confidence)))
                parsed.source = "Gemini 3.1 Flash-Lite"

                # Ensure verified evidence from failed invariants is preserved
                base_evidence: list[str] = []
                for r in report.results:
                    if not r.passed:
                        base_evidence.extend(r.evidence)
                for ev in base_evidence:
                    if ev not in parsed.evidence:
                        parsed.evidence.insert(0, ev)

                return parsed

            return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)
        except Exception:  # noqa: BLE001
            # Fallback on any API, network, rate-limit, or parsing error
            return synthesize_evidence_diagnosis(report, diff=diff, code_snippet=code_snippet)
