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
- **Commit**: `m1-contracts`
