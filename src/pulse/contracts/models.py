from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class InvariantType(str, Enum):
    LIMIT_BOUND = "LIMIT_BOUND"
    PAGINATION_CONTINUITY = "PAGINATION_CONTINUITY"
    ZERO_YIELD = "ZERO_YIELD"
    PROVENANCE = "PROVENANCE"
    REQUEST_CONSISTENCY = "REQUEST_CONSISTENCY"
    SCHEMA_INTEGRITY = "SCHEMA_INTEGRITY"


class PropertyRecord(BaseModel):
    """Canonical model for extracted property records."""

    property_entity_id: str = Field(description="Unique entity identifier within Pulse")
    source: str = Field(description="Source identifier, e.g. nextimmo")
    source_listing_id: str = Field(description="Raw source listing ID")
    source_url: str = Field(description="Direct URL to listing on source")
    deal_type: str = Field(default="sale", description="sale, rent, etc.")
    property_type: Optional[str] = Field(default=None, description="apartment, house, etc.")
    price: Optional[float] = Field(default=None, description="Listing price")
    currency: str = Field(default="EUR", description="Price currency")
    area: Optional[float] = Field(default=None, description="Living area in sq meters")
    rooms: Optional[int] = Field(default=None, description="Number of rooms or bedrooms")
    location: Optional[str] = Field(default=None, description="Location description or municipality")
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("source_listing_id", "property_type", mode="before")
    @classmethod
    def stringify_fields(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip()


class RequestTrace(BaseModel):
    """Trace of a single HTTP request during extraction."""

    page: int
    url: str
    method: str = "GET"
    params: Dict[str, Any] = Field(default_factory=dict)
    status_code: int = 200
    headers: Dict[str, str] = Field(default_factory=dict)
    response_size: int = 0
    raw_payload: Optional[str] = None


class RunTrace(BaseModel):
    """Complete trace of an adapter extraction run."""

    run_id: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requested_limit: Optional[int] = None
    requests: List[RequestTrace] = Field(default_factory=list)
    records: List[PropertyRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def total_requests(self) -> int:
        return len(self.requests)

    @property
    def unique_record_ids(self) -> List[str]:
        return list(dict.fromkeys(r.source_listing_id for r in self.records))


class InvariantResult(BaseModel):
    """Result of a single deterministic invariant check."""

    invariant: InvariantType
    passed: bool
    expected: str
    observed: str
    affected_pages: List[int] = Field(default_factory=list)
    affected_record_ids: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)


class IncidentReport(BaseModel):
    """Complete diagnostic report for a run."""

    incident_id: str
    source: str
    status: str  # "PASSED" or "FAILED"
    results: List[InvariantResult] = Field(default_factory=list)
    summary: str
    recommended_next_step: str
    total_records: int = 0
    total_requests: int = 0
    failed_invariants: List[InvariantType] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    """Structured AI diagnostic investigation."""

    failure_type: str
    summary: str
    evidence: List[str] = Field(default_factory=list)
    likely_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    suggested_regression_test: str
