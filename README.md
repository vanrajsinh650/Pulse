# Pulse

> **A developer tool to reproduce, debug, and test broken web-data integrations faster.**

When upstream websites change, scrapers and data adapters break in frustrating ways: pagination loops infinitely, limits get ignored, or markup changes cause parsers to return 0 listings without throwing an error.

**Pulse** gives engineers an offline verification lab to:
1. **Replay** integration failures offline without touching live websites.
2. **Detect** exactly what failed using deterministic invariant checks (not probabilistic guessing).
3. **Investigate** the root cause with an evidence-grounded AI assistant.
4. **Generate** executable regression tests that fail now and pass once you fix the adapter.

---

## The Core Workflow

```text
source changes / adapter breaks
            ↓
    reproduce offline          →  pulse replay incidents/INC-001
            ↓
  deterministic check fails     →  FAILED: Limit bound exceeded (40 > 20)
            ↓
    diagnose root cause        →  pulse investigate INC-001
            ↓
  generate regression test     →  pulse generate-test INC-001
            ↓
     engineer fixes it
            ↓
       verify test             →  pytest (PASSES)
```

---

## Architecture

```text
[Live Website] ──► [Adapter] ──► [Run Trace] ──► [Offline Replay Engine]
                                                        │
                                                        ▼
                                           [Deterministic Checks]
                                           ├─ Limit Bounds
                                           ├─ Duplicate Pagination
                                           ├─ Silent Zero-Yield
                                           ├─ Record Provenance
                                           ├─ Filter Consistency
                                           └─ Schema Integrity
                                                        │
                                            ┌───────────┴───────────┐
                                            ▼                       ▼
                                    [AI Investigator]       [Test Generator]
                                  (Structured Diagnosis)   (pytest test files)
```

> **Key Rule**: Deterministic checks are the authority. AI is only an assistant that explains verified evidence—it never decides whether data is correct.

---

## Quick Start (Under 60 Seconds)

### 1. Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install pulse in development mode
pip install -e ".[dev]"
```

### 2. Extract Real Data from Nextimmo.lu
Run the live adapter on Luxembourg's public real estate portal:
```bash
pulse run nextimmo --limit 3
```
Output:
```text
Running source adapter: nextimmo (limit=3)
                      Extracted Records (3 items in 1.45s)
┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID    ┃ Type      ┃       Price ┃ Location            ┃ URL                  ┃
┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 59335 │ apartment │ 485,000 EUR │ Luxembourg-Rolling… │ https://nextimmo.lu… │
│ 58569 │ apartment │ 485,000 EUR │ Diekirch            │ https://nextimmo.lu… │
│ 58333 │ house     │ 499,000 EUR │ Esch-sur-Alzette    │ https://nextimmo.lu… │
└───────┴───────────┴─────────────┴─────────────────────┴──────────────────────┘
```

---

## Everyday Commands

### 1. Replay an Incident Offline
Reproduce a bug instantly from recorded fixtures (no live requests, no flaky network):

```bash
pulse replay incidents/INC-001
```

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

---

### 2. Investigate the Bug with AI
Get a structured JSON explanation backed strictly by verified trace evidence:

```bash
pulse investigate INC-001
```

```json
{
  "failure_type": "limit_overrun",
  "summary": "Requested limit of 20 was exceeded by 20 records across 2 requests.",
  "evidence": [
    "requested limit = 20",
    "collected records = 40",
    "limit exceeded by 20 records across 2 requests"
  ],
  "likely_cause": "Adapter continues to fetch subsequent pages and does not enforce requested limit bound.",
  "confidence": 0.98,
  "recommended_action": "Enforce requested limit boundary and slice accumulated records before returning.",
  "suggested_regression_test": "test_adapter_respects_requested_limit_bound"
}
```

---

### 3. Generate a Regression Test
Automatically generate an executable pytest test file for the incident:

```bash
pulse generate-test INC-001
```

```text
Generated regression test: tests/regression/test_inc_001_regression.py
Run test: pytest tests/regression/test_inc_001_regression.py
```

The generated test proves two things:
1. `test_inc_001_fails_before_repair` confirms the bug fails verification.
2. `test_inc_001_passes_after_repair` verifies that applying the fix makes the suite pass.

---

### 4. Compare Baseline vs Broken Run (Structural Diff)
See what changed between a good run and a broken run:

```bash
pulse diff incidents/INC-001/baseline_trace.json incidents/INC-001/trace.json
```

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

---

### 5. Run Performance Benchmark
Measure actual execution times across all three built-in incident classes:

```bash
pulse benchmark
```

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

## The 3 Controlled Incident Scenarios

| Incident | Failure Class | Problem | What Pulse Catches |
| :--- | :--- | :--- | :--- |
| **INC-001** | **Limit Overrun** | User requested 20 items, adapter kept paginating and collected 40. | `LIMIT_BOUND` invariant violation. Pinpoints overrun count. |
| **INC-002** | **Duplicate Pagination** | Page 2 repeated the exact IDs from Page 1 (stalled cursor). | `PAGINATION_CONTINUITY` invariant violation. Pinpoints stalled page and duplicate IDs. |
| **INC-003** | **Silent Zero Yield** | HTTP 200 succeeded, but markup shifted so the parser yielded 0 items. | `ZERO_YIELD` invariant violation. Distinguishes parser bug from legitimate empty search. |

---

## Real Data vs Controlled Failures

To keep engineering standards transparent:

* **Real**: Source data, HTML structure, field mapping (listing IDs, EUR prices, sqm areas, rooms, location strings), and URLs are taken directly from the public Luxembourg portal `nextimmo.lu`.
* **Controlled**: The 3 failure cases are synthetic mutations based on publicly documented integration failure classes (e.g. pagination loops, limit overruns, and selector drift).
* **Sanitized**: All recorded headers redact cookies, authorization headers, and API keys automatically.

---

## Testing & Code Quality

Run tests:
```bash
pytest
```
*41 passed in ~2s*

Run lint & type checks:
```bash
ruff check src/ tests/
mypy src/
```
*Zero lint errors, zero type errors.*

---

## Limitations

1. **One Source Adapter**: Pulse implements `NextimmoAdapter` for `nextimmo.lu` to demonstrate depth rather than shallow breadth across 50 sites.
2. **Client-Side Only**: Pulse validates the adapter's client requests and normalized output. It does not monitor third-party backend databases.
3. **No Scraping Bypasses**: Pulse uses public web requests. It does not contain CAPTCHA solvers, proxy rotators, or auth bypasses.

---

## Independent Prototype Note

This project is an **independent developer tool** inspired by publicly documented web-data engineering workflows and incident patterns. It is not affiliated with CleanedWeb and does not use any private systems or APIs.
