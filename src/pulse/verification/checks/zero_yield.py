from __future__ import annotations

import json

from pulse.contracts.models import InvariantResult, InvariantType, RunTrace


def check_zero_yield(trace: RunTrace) -> InvariantResult:
    """Verify that extraction yield reflects legitimate source state rather than silent parser failure."""
    if trace.total_records > 0:
        return InvariantResult(
            invariant=InvariantType.ZERO_YIELD,
            passed=True,
            expected="> 0 records for non-empty search",
            observed=f"{trace.total_records} records extracted",
            evidence=[f"{trace.total_records} records successfully extracted"],
        )

    # If 0 records were extracted, examine the request payloads to determine if it was legitimate or silent failure
    if not trace.requests:
        return InvariantResult(
            invariant=InvariantType.ZERO_YIELD,
            passed=False,
            expected="requests made and records extracted",
            observed="0 requests executed",
            evidence=["no requests in trace"],
        )

    for req in trace.requests:
        payload = req.raw_payload or ""
        # Check if source explicitly reports 0 items
        is_legitimate_empty = False
        if '"totalItems": 0' in payload or '"total": 0' in payload or '"found": 0' in payload:
            is_legitimate_empty = True
        elif payload.strip().startswith("{"):
            try:
                data = json.loads(payload)
                if isinstance(data, dict) and (data.get("total") == 0 or data.get("totalItems") == 0 or data.get("data") == []):
                    is_legitimate_empty = True
            except json.JSONDecodeError:
                pass

        if is_legitimate_empty:
            return InvariantResult(
                invariant=InvariantType.ZERO_YIELD,
                passed=True,
                expected="0 records for legitimately empty search",
                observed="0 records extracted (confirmed legitimate empty upstream)",
                evidence=["source payload explicitly confirmed zero available listings"],
            )

        # If payload is substantial (e.g. > 300 bytes or has HTML/JSON structure) but parser extracted 0
        if len(payload) > 300 or "listing" in payload.lower() or "price" in payload.lower() or "property" in payload.lower():
            return InvariantResult(
                invariant=InvariantType.ZERO_YIELD,
                passed=False,
                expected="records extracted from substantial response",
                observed=f"0 records extracted from HTTP 200 payload ({len(payload)} bytes)",
                affected_pages=[req.page],
                details={
                    "status_code": req.status_code,
                    "payload_length": len(payload),
                    "page": req.page,
                },
                evidence=[
                    f"HTTP {req.status_code} received with {len(payload)} bytes payload",
                    "payload contains search content but parser extracted 0 records",
                    "unexpected zero yield: parser failed to match modified source structure",
                ],
            )

    return InvariantResult(
        invariant=InvariantType.ZERO_YIELD,
        passed=True,
        expected=">= 0 records",
        observed="0 records extracted from empty response",
        evidence=["response was empty or not substantial"],
    )
