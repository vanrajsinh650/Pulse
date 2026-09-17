# Pulse

**Pulse** is a developer tool and verification laboratory that helps software engineers reproduce, investigate, and test web-data integration failures faster.

When upstream websites mutate—pagination parameters stall, limits overrun, or markup shifts cause parsers to silently drop yield—engineers spend hours manually reconstructing state, querying live sites, and guessing root causes. Pulse provides a deterministic developer workflow to capture sanitized run traces, replay incidents completely offline, verify invariants with mathematical certainty, generate executable regression tests, and provide evidence-grounded root-cause diagnosis.

Pulse is designed around a core engineering principle: **deterministic verification is the authority, while AI is the assistant**. Correctness is never delegated to an LLM; rather, mathematical invariant checks detect the failure, and the AI investigator synthesizes structured, evidence-backed explanations from verified run facts.

---

## Why Does It Exist?

Public evidence from web-data engineering teams demonstrates recurring classes of upstream failures:
* **Limit overruns**: Adapters fail to stop when reaching requested boundaries, making unnecessary requests.
* **Pagination stalls & loops**: Adapters keep querying the same page or fail to advance cursors, ingesting duplicated records.
* **Silent zero-yield parser failures**: Upstream HTTP requests return 200 OK with substantial payloads, but modified DOM or JSON keys cause parsers to silently return zero records.
* **Request filter divergence**: Multi-page crawlers drop query parameters or filters between requests.
* **Provenance loss**: Extracted records lose origin URLs, source IDs, or observation timestamps during normalization.

Pulse solves this by turning integration failures into reproducible, version-controlled incident packages that can be diagnosed in milliseconds.

---

## Architecture

```text
                    REAL SOURCE (Nextimmo.lu)
                                │
                                ▼
                         SOURCE ADAPTER
                                │
                                ▼
                            RUN TRACE
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
            BASELINE TRACE               INCIDENT TRACE
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                         STRUCTURAL DIFF
                                │
                                ▼
                  DETERMINISTIC VERIFIER
          ┌─────────────┬───────┴───────┬─────────────┐
          ▼             ▼               ▼             ▼
     LIMIT BOUND   PAGINATION      ZERO YIELD    PROVENANCE
      INVARIANT    CONTINUITY       DETECTOR     INTEGRITY
          │             │               │             │
          └─────────────┴───────┬───────┴─────────────┘
                                ▼
                         INCIDENT REPORT
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
          AI INVESTIGATOR            REGRESSION TEST GENERATOR
     (Evidence-Backed Diagnosis)      (Executable pytest files)
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                           REPAIR FIX
                                │
                                ▼
                         VERIFY (pytest)
```

---

## Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/vanrajsinh650/Pulse.git
cd Pulse

# Set up virtual environment and install in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Run a Live Source Integration
Run the adapter against the real public Luxembourg property source (`nextimmo.lu`):
```bash
pulse run nextimmo --limit 5
```
Output:
```text
Running source adapter: nextimmo (limit=5)
                      Extracted Records (5 items in 1.45s)
┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID    ┃ Type      ┃       Price ┃ Location            ┃ URL                  ┃
┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 59335 │ apartment │ 485,000 EUR │ Luxembourg-Rolling… │ https://nextimmo.lu… │
│ 58569 │ apartment │ 485,000 EUR │ Diekirch            │ https://nextimmo.lu… │
│ 58333 │ house     │ 499,000 EUR │ Esch-sur-Alzette    │ https://nextimmo.lu… │
│ 57905 │ house     │ 382,200 EUR │ Luxembourg-Neudorf  │ https://nextimmo.lu… │
│ 57467 │ apartment │ 750,000 EUR │ Clemency            │ https://nextimmo.lu… │
└───────┴───────────┴─────────────┴─────────────────────┴──────────────────────┘
```

### 3. Replay a Recorded Incident Offline
Replay an incident fixture without making any live HTTP calls:
```bash
pulse replay incidents/INC-001
```
Output:
```text
Incident: INC-001

Status: FAILED

Detected:
  requested limit exceeded

Affected:
  page 1, page 2

Records:
  40 received

Evidence:
  requested limit = 20
  collected records = 40
  limit exceeded by 20 records across 2 requests

Suggested next step:
  inspect loop termination bounds and slicing when record count reaches requested limit
```

Or replay a pagination stall incident:
```bash
pulse replay incidents/INC-002
```
Output:
```text
Incident: INC-002

Status: FAILED

Detected:
  pagination repeated previous page

Affected:
  page 2

Records:
  40 received
  20 duplicated
  20 new

Evidence:
  pagination repeated previous page
  affected page(s): [2]
  20 duplicate records detected

Suggested next step:
  inspect pagination state advancement and next_page offset handling
```

### 4. Investigate an Incident with AI Diagnosis
Generate an evidence-grounded, structured diagnostic:
```bash
pulse investigate INC-001
```
Output:
```json
{
  "failure_type": "limit_overrun",
  "summary": "Requested limit of 20 was exceeded by 20 records across 2 requests.",
  "evidence": [
    "requested limit = 20",
    "collected records = 40",
    "limit exceeded by 20 records across 2 requests",
    "Request count changed: 1 (baseline) vs 2 (incident)",
    "Record yield changed: 20 (baseline) vs 40 (incident) ",
    "Incident violated invariant(s): LIMIT_BOUND"
  ],
  "likely_cause": "Adapter continues to fetch subsequent pages and does not enforce requested limit bound.",
  "confidence": 0.98,
  "recommended_action": "Enforce requested limit boundary and slice accumulated records before returning.",
  "suggested_regression_test": "test_adapter_respects_requested_limit_bound"
}
```

### 5. Generate Executable Regression Tests
```bash
pulse generate-test INC-001
```
Output:
```text
Generated regression test: tests/regression/test_inc_001_regression.py
Run test: pytest tests/regression/test_inc_001_regression.py
```

### 6. Compare Baseline and Incident Traces
```bash
pulse diff incidents/INC-001/baseline_trace.json incidents/INC-001/trace.json
```
Output:
```text
        Structural Diff: Baseline vs Incident
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ Metric              ┃ Baseline ┃ Incident ┃ Delta ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ Total Requests      │        1 │        2 │     1 │
│ Total Records       │       20 │       40 │   +20 │
│ Unique Records      │       20 │       40 │   +20 │
│ Verification Status │   PASSED │   FAILED │   N/A │
└─────────────────────┴──────────┴──────────┴───────┘
```

### 7. Run Performance Benchmark
```bash
pulse benchmark
```
Output:
```text
                      Pulse Incident Lab Benchmark Results
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Incident ┃ Failure Class        ┃ Replay Time ┃ Verification Time ┃ Diagnosis Time    ┃ Network Avoided ┃ Precision          ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ INC-001  │ Limit Overrun        │     1.92 ms │           0.40 ms │           0.02 ms │      2 requests │ 100% deterministic │
│ INC-002  │ Duplicate Pagination │     1.83 ms │           0.28 ms │           0.02 ms │      2 requests │ 100% deterministic │
│ INC-003  │ Silent Zero Yield    │     0.64 ms │           0.28 ms │           0.02 ms │       1 request │ 100% deterministic │
└──────────┴──────────────────────┴─────────────┴───────────────────┴───────────────────┴─────────────────┴────────────────────┘

Summary: All 3 incident classes diagnosed offline in < 10 ms with 0 live HTTP requests made.
```

---

## Running the Test Suite

Run unit, integration, and regression tests:
```bash
pytest
```
Run type-checking and linting:
```bash
ruff check src/ tests/
mypy src/
```

---

## What Is Real vs Controlled

To maintain absolute engineering integrity, the distinction between real observations and controlled mutations is explicit:

| Component | Source / Methodology |
| :--- | :--- |
| **Source Data** | Real listings fetched directly from the public Luxembourg portal `nextimmo.lu` via SSR `__NEXT_DATA__`. |
| **Field Mapping** | Real listing IDs, URLs, EUR prices, living areas, room counts, and municipalities. |
| **Sanitization** | Real headers sanitized of session cookies, CF ray tokens, and auth headers. |
| **INC-001 (Limit Overrun)** | Controlled scenario: Real page 1 and page 2 fixtures combined without slicing to simulate boundary bypass. |
| **INC-002 (Duplicate Pagination)** | Controlled scenario: Real page 1 repeated across page 2 requests to simulate cursor stall. |
| **INC-003 (Silent Zero Yield)** | Controlled scenario: Real listing data nested in an altered DOM container to simulate selector drift. |
| **AI Investigation** | Strict schema-enforced Pydantic output operating entirely on verified trace evidence. |

---

## Limitations

* **Single Source Adapter**: The prototype implements `NextimmoAdapter` for `nextimmo.lu`. It does not attempt to cover dozens of portals.
* **Client-Side Verification**: Pulse verifies client-side requests, extracted records, and parameter consistency. It does not monitor upstream database states or backend server health.
* **No Bot Bypass**: Pulse uses standard public HTTP requests and respects technical boundaries. It does not contain CAPTCHA bypasses, proxy rotations, or credential scrapers.

---

## Relation to CleanedWeb

This project is an **independent engineering prototype** built by studying public technical descriptions of integration workflows, junior web-data engineering job specifications, and published incident patterns.

It does **not** claim to be an internal CleanedWeb system, does not use private CleanedWeb code or APIs, and does not assert that CleanedWeb lacks these verification capabilities internally. It is a focused demonstration of developer-side incident reproduction and verification engineering.
