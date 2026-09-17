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
- **Commit**: `05bc6b4`

---

## Milestone 5: Controlled Incidents & Structural Diff
- **Task**: Create reproducible controlled incident packages and structural diff comparator.
- **What changed**:
  - Built real-data controlled incidents:
    - `incidents/INC-001`: Limit overrun (requested 20, collected 40, failed `LIMIT_BOUND`).
    - `incidents/INC-002`: Duplicate pagination (page 2 repeats page 1 IDs, failed `PAGINATION_CONTINUITY`).
    - `incidents/INC-003`: Silent zero yield (HTTP 200 with substantial mutated markup, failed `ZERO_YIELD`).
  - Implemented `pulse.diff.comparator.StructuralComparator` producing comprehensive baseline vs incident delta metrics.
  - Added test suite `tests/test_incidents.py`.
- **Why**: Enables instant offline replay of realistic failure classes based on publicly observed integration incidents.
- **How it was tested**: `pytest tests/test_incidents.py` verified all three incident classes and diff metric generation.
- **Commit**: `c89a4ff`

---

## Milestone 6: AI Investigator & Regression Test Generator
- **Task**: Implement evidence-backed AI diagnostic assistant and executable test generator.
- **What changed**:
  - Implemented `pulse.investigator.agent.AIInvestigator` providing structured JSON root cause diagnosis strictly grounded on verified facts.
  - Implemented `pulse.generator.test_generator.generate_regression_test` writing executable pytest test files that fail before repair and pass after repair.
  - Pre-generated executable regression tests for `INC-001`, `INC-002`, and `INC-003` in `tests/regression/`.
  - Added test suites `tests/test_investigator.py` and `tests/test_generator.py`.
- **Why**: Completes the incident reproduction loop: broken fixture -> incident detected -> AI diagnosis -> regression test generated -> test passes after repair.
- **How it was tested**: `pytest` passed 33 tests across all modules.
- **Commit**: `ee35417`

---

## Milestone 7: CLI, Benchmark & End-to-End Test Suite
- **Task**: Implement unified developer CLI with rich output and end-to-end integration test suite.
- **What changed**:
  - Implemented `pulse.cli`:
    - `pulse run`: Live extraction with Rich formatting and trace persistence.
    - `pulse replay`: Deterministic offline replay with human-friendly failure reports.
    - `pulse investigate`: Evidence-backed JSON diagnostics panel.
    - `pulse generate-test`: Auto-generation of executable regression tests.
    - `pulse diff`: Tabular baseline vs incident structural comparison.
    - `pulse benchmark`: Precise performance timings across all 3 incident classes.
  - Added CLI test suite `tests/test_cli.py` and full loop verification in `tests/test_end_to_end.py`.
  - Enforced strict linting (`ruff`) and type safety (`mypy`).
- **Why**: Delivers a finished, demonstrable developer workflow tool directly runnable via command line.
- **How it was tested**: `pytest` passed all 41 unit and integration tests; `mypy` reported 0 type errors; `ruff` reported 0 lint errors.
- **Commit**: `m7-cli-benchmark`

---

## Milestone 8: Real Google Gemini Integration & Resilient Fallback
- **Task**: Connect real `gemini-3.1-flash-lite` via official `google-genai` SDK with deterministic verification authority and fallback.
- **What changed**:
  - Added `google-genai>=2.0.0` as single AI dependency in `pyproject.toml`.
  - Implemented `AIInvestigator` calling `client.models.generate_content` with Pydantic structured output (`response_schema=InvestigationResult`).
  - Added credential-free prompt builder forwarding only verified invariant evidence, request metadata, and diff metrics (< 400 tokens).
  - Added 15-second network timeout guard (`types.HttpOptions(timeout=15000)`) and disabled automatic function calling.
  - Added auto-discovery of `GEMINI_API_KEY` from `.env` or environment with strict `PYTEST_CURRENT_TEST` isolation.
  - Preserved deterministic `synthesize_evidence_diagnosis` as robust fallback for missing keys, rate limits (HTTP 429), or network dropouts.
  - Added comprehensive test suite in `tests/test_investigator.py` with injectable mock client (testing valid AI output, invalid JSON fallback, API errors, `insufficient_evidence`, confidence bounds, and evidence preservation).
  - Updated CLI output to clearly report `Investigation source: Gemini 3.1 Flash-Lite` or `Investigation source: deterministic fallback`.
- **Why**: Replaced static placeholder with real LLM reasoning while guaranteeing zero network calls in tests and zero CLI crashes when offline.
- **How it was tested**: `pytest` passed all 47 tests in ~2.8s offline; live Gemini diagnosis confirmed against `INC-001`.
- **Commits**: `8791ab5`, `57e8915`
