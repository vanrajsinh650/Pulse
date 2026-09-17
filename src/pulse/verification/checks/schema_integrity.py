from __future__ import annotations

from pulse.contracts.models import InvariantResult, InvariantType, PropertyRecord, RunTrace


def check_schema_integrity(trace: RunTrace) -> InvariantResult:
    """Verify that all records conform to canonical schema types and validation rules."""
    if not trace.records:
        return InvariantResult(
            invariant=InvariantType.SCHEMA_INTEGRITY,
            passed=True,
            expected="valid records",
            observed="0 records extracted",
            evidence=["no records to validate"],
        )

    invalid_record_ids: list[str] = []
    errors: list[str] = []

    for rec in trace.records:
        try:
            # Revalidate model schema
            PropertyRecord.model_validate(rec)

            # Business constraints
            if rec.price is not None and rec.price < 0:
                invalid_record_ids.append(rec.source_listing_id)
                errors.append(f"Record {rec.source_listing_id} negative price ({rec.price})")
            if rec.area is not None and rec.area < 0:
                invalid_record_ids.append(rec.source_listing_id)
                errors.append(f"Record {rec.source_listing_id} negative area ({rec.area})")
            if rec.rooms is not None and rec.rooms < 0:
                invalid_record_ids.append(rec.source_listing_id)
                errors.append(f"Record {rec.source_listing_id} negative rooms ({rec.rooms})")
        except (ValueError, TypeError) as exc:
            invalid_record_ids.append(rec.source_listing_id)
            errors.append(f"Record {rec.source_listing_id} schema violation: {exc}")

    if not invalid_record_ids:
        return InvariantResult(
            invariant=InvariantType.SCHEMA_INTEGRITY,
            passed=True,
            expected="all records satisfy canonical schema and positive numerical constraints",
            observed=f"all {len(trace.records)} records validated successfully",
            evidence=["100% schema validation pass rate"],
        )

    return InvariantResult(
        invariant=InvariantType.SCHEMA_INTEGRITY,
        passed=False,
        expected="canonical schema compliance",
        observed=f"{len(invalid_record_ids)} records failed schema validation",
        affected_record_ids=list(dict.fromkeys(invalid_record_ids)),
        details={"errors": errors},
        evidence=errors[:5],
    )
