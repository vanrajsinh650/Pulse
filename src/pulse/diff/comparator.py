from __future__ import annotations

from typing import Any, Dict, List, Set
from pydantic import BaseModel, Field
from pulse.contracts.models import RunTrace
from pulse.verification.engine import VerificationEngine


class DiffReport(BaseModel):
    baseline_run_id: str
    incident_run_id: str
    pages_baseline: int
    pages_incident: int
    records_baseline: int
    records_incident: int
    records_delta: int
    unique_ids_baseline: int
    unique_ids_incident: int
    added_ids_count: int
    removed_ids_count: int
    duplicate_ids_in_incident: List[str] = Field(default_factory=list)
    baseline_status: str
    incident_status: str
    failed_invariants_baseline: List[str] = Field(default_factory=list)
    failed_invariants_incident: List[str] = Field(default_factory=list)
    differences_summary: List[str] = Field(default_factory=list)


class StructuralComparator:
    """Compares baseline and incident run traces to produce evidence-backed structural diffs."""

    def __init__(self) -> None:
        self.verifier = VerificationEngine()

    def compare(self, baseline: RunTrace, incident: RunTrace) -> DiffReport:
        b_ids: List[str] = [r.source_listing_id for r in baseline.records]
        i_ids: List[str] = [r.source_listing_id for r in incident.records]

        b_id_set: Set[str] = set(b_ids)
        i_id_set: Set[str] = set(i_ids)

        # Detect duplicates within incident
        seen: Set[str] = set()
        dupes: List[str] = []
        for r_id in i_ids:
            if r_id in seen:
                dupes.append(r_id)
            else:
                seen.add(r_id)

        added = i_id_set - b_id_set
        removed = b_id_set - i_id_set

        b_report = self.verifier.verify(baseline)
        i_report = self.verifier.verify(incident)

        summaries: List[str] = []
        if baseline.total_requests != incident.total_requests:
            summaries.append(
                f"Request count changed: {baseline.total_requests} (baseline) vs {incident.total_requests} (incident)"
            )
        if baseline.total_records != incident.total_records:
            summaries.append(
                f"Record yield changed: {baseline.total_records} (baseline) vs {incident.total_records} (incident) [delta: {incident.total_records - baseline.total_records}]"
            )
        if dupes:
            summaries.append(f"{len(dupes)} duplicated record IDs detected in incident execution")
        if i_report.failed_invariants:
            failed_str = ", ".join(inv.value for inv in i_report.failed_invariants)
            summaries.append(f"Incident violated invariant(s): {failed_str}")

        return DiffReport(
            baseline_run_id=baseline.run_id,
            incident_run_id=incident.run_id,
            pages_baseline=baseline.total_requests,
            pages_incident=incident.total_requests,
            records_baseline=baseline.total_records,
            records_incident=incident.total_records,
            records_delta=incident.total_records - baseline.total_records,
            unique_ids_baseline=len(b_id_set),
            unique_ids_incident=len(i_id_set),
            added_ids_count=len(added),
            removed_ids_count=len(removed),
            duplicate_ids_in_incident=list(dict.fromkeys(dupes)),
            baseline_status=b_report.status,
            incident_status=i_report.status,
            failed_invariants_baseline=[i.value for i in b_report.failed_invariants],
            failed_invariants_incident=[i.value for i in i_report.failed_invariants],
            differences_summary=summaries,
        )
