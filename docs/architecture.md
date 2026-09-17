# Pulse - Architecture Document

## 1. Overview
Pulse is a developer incident reproduction, verification, and offline replay laboratory for web data integrations (scrapers, crawlers, and data pipelines). When upstream web sources mutate, integration code fails in subtle, insidious ways: pagination loops indefinitely, requested record limits are breached, or markup changes cause parsers to silently return 0 listings without raising HTTP errors.

Pulse reproduces these incidents deterministically offline, evaluates violations against mathematical data invariants, computes baseline-to-incident structural diffs, synthesizes evidence-grounded AI diagnoses via Google Gemini, and generates executable pytest regression tests.

---

## 2. Core Architecture Pipeline

```text
[Live Website / Source]
           │
           ▼
    [Source Adapter] (e.g. NextimmoAdapter)
           │
      ┌────┴──────────────────────────┐
      ▼                               ▼
 [Live Run]                      [incidents/ Library]
      │                          (Flight Data Recorder)
      ▼                          ├─ INC-001 (Limit Overrun)
 [Run Trace Recorder]            ├─ INC-002 (Duplicate Pagination)
 (Sanitizes Auth/Cookies/Keys)   └─ INC-003 (Silent Zero-Yield)
      │                               │
      │                               ▼
      └──────────────────────► [Offline Replay Engine]
                                      │ (Zero live HTTP calls)
                                      ▼
                        [Structural Comparator]
                        (Baseline vs. Incident Diff)
                                      │
                                      ▼
                        [Verification Engine]
                        (6 Deterministic Invariants)
                        ├─ Limit Bound
                        ├─ Pagination Continuity
                        ├─ Silent Zero-Yield
                        ├─ Record Provenance
                        ├─ Request / Filter Consistency
                        └─ Schema Integrity
                                      │
                                      ▼
                               [Incident Report]
                           (Status: PASSED / FAILED)
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          [AI Investigator]                   [Test Generator]
     (Deterministic Authority)              (Executable Pytest Files)
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
[Google Gemini Mode]   [Deterministic Fallback]
 (gemini-3.1-flash-lite) (Offline Heuristic Synthesizer)
         │                     │
         └──────────┬──────────┘
                    ▼
     [Structured InvestigationResult]
     (Pydantic-validated JSON Diagnosis)
```

---

## 3. The `incidents/` Folder: Scraper Flight Data Recorder

The `incidents/` directory acts as an offline, version-controlled repository of captured integration failures. In production scraping, reproducing bugs against live targets is problematic:
1. Target pages mutate continuously (listings expire, prices shift).
2. Live websites impose rate limits, Cloudflare challenges, or IP bans.
3. CI/CD pipelines cannot depend on external internet stability.

Each incident folder contains a self-contained test fixture package:
- `incident.json`: Metadata defining the failure class, category, and target invariant.
- `trace.json`: The unpatched, failing run trace containing recorded HTTP requests, status codes, response sizes, raw payload snapshots, and normalized records.
- `baseline_trace.json`: The verified, healthy run trace from prior to the regression.

### Built-in Incident Classes
- **INC-001 (Limit Overrun)**: Adapter requests 20 listings, but loop fails to terminate and harvests 40 records across 2 pages (`LIMIT_BOUND` violation).
- **INC-002 (Duplicate Pagination)**: Pagination cursor parameter stalls on page 2, ingesting identical listings as page 1 (`PAGINATION_CONTINUITY` violation).
- **INC-003 (Silent Zero Yield)**: Upstream HTML markup changes; HTTP returns `200 OK` with 103 KB payload, but CSS/JSON selectors match 0 items (`ZERO_YIELD` violation).

---

## 4. Key Architectural Decisions & Safeguards

### Decision 1: Deterministic Verification is the Sole Authority
The AI model **never** decides whether an extraction passed or failed. Pass/fail status is governed 100% mathematically by invariant assertions (limit boundaries, ID set intersections, payload size heuristics, and schema validation). The AI functions strictly as an explanatory assistant.

### Decision 2: Google Gemini Integration (`gemini-3.1-flash-lite`)
- **SDK**: Official Google Python SDK (`google-genai>=2.0.0`).
- **Structured Outputs**: Native Pydantic model validation (`response_schema=InvestigationResult`).
- **Token Efficiency**: Raw 100 KB+ HTML payloads are never forwarded to the LLM. Pulse builds a focused context (< 400 tokens) consisting strictly of verified invariant failure facts, sample IDs, request metadata, and structural diffs.
- **Environment Auto-Discovery**: Automatically discovers `GEMINI_API_KEY` from system environment or local `.env` files without third-party dependencies.

### Decision 3: Resilient Deterministic Fallback
If `GEMINI_API_KEY` is missing, or if Gemini encounters network timeouts, rate limits (HTTP 429), or service outages, the system automatically routes to `synthesize_evidence_diagnosis()`. The CLI marks the output source honestly (`Investigation source: deterministic fallback`) and never crashes.

### Decision 4: API & Network Safeguards
- **Timeout Protection**: `types.HttpOptions(timeout=15000)` enforces a 15-second cutoff to prevent terminal hangs.
- **Function Calling Disabled**: `types.AutomaticFunctionCallingConfig(disable=True)` disables automatic remote calls.
- **Strict Test Isolation**: `_load_env_file()` detects `PYTEST_CURRENT_TEST` and skips `.env` loading during automated testing. Unit tests run 100% offline in < 3 seconds using injectable mock clients.

### Decision 5: Credential Sanitization
Before traces are saved to disk or forwarded to Gemini:
- Cookies, authorization headers, session tokens, and API keys are redacted to `[REDACTED]`.
- Sensitive query parameters (`key`, `api_key`, `token`, `secret`) are sanitized.
