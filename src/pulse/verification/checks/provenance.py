from __future__ import annotations

from typing import List
from pulse.contracts.models import InvariantResult, InvariantType, RunTrace


def check_provenance(trace: RunTrace) -> InvariantResult:
    """Verify that all extracted records preserve required provenance attributes."""
    if not trace.records:
        return InvariantResult(
            invariant=InvariantType.PROVENANCE,
            passed=True,
            expected="provenance on extracted records",
            observed="0 records extracted",
            evidence=["no records to verify provenance on"],
        )

    missing_provenance_ids: List[str] = []
    reasons: List[str] = []

    for rec in trace.records:
        rec_id = rec.source_listing_id
        if not rec.source or not rec.source.strip():
            missing_provenance_ids.append(rec_id or "UNKNOWN")
            reasons.append(f"Record {rec_id} missing source name")
        elif not rec_id or not rec_id.strip():
            missing_provenance_ids.append("UNKNOWN")
            reasons.append("Record missing source_listing_id")
        elif not rec.source_url or not (rec.source_url.startswith("http://") or rec.source_url.startswith("https://")):
            missing_provenance_ids.append(rec_id)
            reasons.append(f"Record {rec_id} missing valid source_url ({rec.source_url})")
        elif rec.observed_at is None:
            missing_provenance_ids.append(rec_id)
            reasons.append(f"Record {rec_id} missing observed_at timestamp")

    if not missing_provenance_ids:
        return InvariantResult(
            invariant=InvariantType.PROVENANCE,
            passed=True,
            expected="valid source, ID, URL, and observed_at for all records",
            observed=f"all {len(trace.records)} records retain complete provenance",
            evidence=["provenance verified for 100% of extracted records"],
        )

    return InvariantResult(
        invariant=InvariantType.PROVENANCE,
        passed=False,
        expected="complete provenance (source, source_id, source_url, observed_at)",
        observed=f"{len(missing_provenance_ids)} records have missing or malformed provenance",
        affected_record_ids=missing_provenance_ids,
        details={"reasons": reasons[:10]},
        evidence=reasons[:5],
    )
