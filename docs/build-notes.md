# Pulse - Build Notes

This log documents key milestones, architectural decisions, test verification, and commit references.

---

## Milestone 0: Initialization & Source Reconnaissance
- **Task**: Initialize project repository, virtual environment, and perform source reconnaissance on candidate `nextimmo.lu`.
- **What changed**:
  - Initialized git repository with `main` branch tracking `origin`.
  - Configured `pyproject.toml` with `pulse` package and dev dependencies.
  - Verified live source accessibility for `nextimmo.lu/search/page/1`. Identified Next.js SSR payload containing `initialData` with structured pagination and listing records.
  - Initialized `docs/architecture.md` and `docs/build-notes.md`.
- **Why**: Solid foundations with verified live source contract ensure real data can be extracted and reproduced offline.
- **How it was tested**: Automated python requests probe confirmed 200 OK and valid JSON data extraction from `__NEXT_DATA__`.
- **Commit**: `4a8f936`

---

## Milestone 1: Canonical Contracts
- **Task**: Define typed Pydantic models in `pulse.contracts.models`.
- **What changed**:
  - Implemented `PropertyRecord`, `RequestTrace`, `RunTrace`, `InvariantResult`, `IncidentReport`, and `InvestigationResult`.
  - Coerced raw source listing IDs to strings, added validation boundaries.
  - Added unit test suite `tests/test_contracts.py`.
- **Why**: Clean canonical representations decouple source-specific adapter logic from verification, replay, and incident diagnosis engines.
- **How it was tested**: `pytest tests/test_contracts.py` passed with 100% success.
- **Commit**: `b60bd4f`

---

## Milestone 2: Source Adapter Implementation
- **Task**: Implement real public source adapter for Nextimmo.lu.
- **What changed**:
  - Created `pulse.adapters.base.BaseAdapter` with pluggable transport injection, bounded pagination, and clear error hierarchy (`SourceFetchError`, `SourceParseError`).
  - Created `pulse.adapters.nextimmo.NextimmoAdapter` with SSR `__NEXT_DATA__` extraction, semantic property type mapping, price/area parsing, and header sanitization.
  - Added string coercion for `property_type` in `PropertyRecord`.
  - Added unit test suite `tests/test_adapter.py`.
- **Why**: Proves real source extraction capabilities on public Luxembourg property data without scraping bypasses.
- **How it was tested**: Unit tests in `tests/test_adapter.py` and live network probe extracting 5 real listings verified against `https://nextimmo.lu`.
- **Commit**: `206301a`

---

## Milestone 3: Run Recording & Deterministic Offline Replay
- **Task**: Implement run trace serialization with credential redaction and offline replay transport.
- **What changed**:
  - Implemented `pulse.replay.recorder.save_run_trace` and `load_run_trace` with automatic sanitization of authorization headers, tokens, and sensitive query parameters.
  - Implemented `pulse.replay.engine.ReplayEngine` providing an offline transport matching adapter requests to recorded traces without network access.
  - Added test suite in `tests/test_replay.py`.
- **Why**: Ensures incidents can be deterministically reproduced offline without network flakiness, credential leaks, or external rate limiting.
- **How it was tested**: `pytest tests/test_replay.py` passed, verifying offline replay of multi-page adapter execution and secret sanitization.
- **Commit**: `6bdf4c2`

---

## Milestone 4: Deterministic Verification Engine
- **Task**: Implement deterministic invariant checks and reporting engine.
- **What changed**:
  - Created `pulse.verification.checks`:
    - `limit_bound.py`: Verifies collected count does not overrun requested limit.
    - `pagination_continuity.py`: Detects repeated pages and pagination stalls.
    - `zero_yield.py`: Distinguishes legitimate empty source from silent parser failure on substantial payload.
    - `provenance.py`: Guarantees source name, ID, valid URL, and timestamp.
    - `request_consistency.py`: Detects filter/parameter divergence across pages.
    - `schema_integrity.py`: Validates numerical constraints and schema conformity.
  - Implemented `VerificationEngine` coordinating checks and emitting structured `IncidentReport` with actionable next steps.
  - Added unit test suite `tests/test_verification.py`.
- **Why**: Ground truth must be 100% deterministic and mathematical rather than probabilistic or dependent on an LLM.
- **How it was tested**: `pytest tests/test_verification.py` passed with 8 comprehensive scenarios covering passes, failures, and edge cases.
- **Commit**: `m4-verification`
