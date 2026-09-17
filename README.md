# Pulse

**Pulse** is a developer tool and verification lab for reproducing, investigating, and testing web-data integration failures.

## Why does it exist?
Web data integrations inevitably break when upstream sources change: pagination loops infinitely, limits are overrun, or schema/parser mutations silently drop yield to zero. Pulse provides a deterministic developer workflow to record run traces, replay incidents offline, identify failed invariants with mathematical certainty, generate regression tests, and leverage an AI investigator to diagnose root causes without giving LLMs control over verification truth.

## Architecture
```
source → adapter → run trace → incident engine → report → AI investigator → regression test
```
* **Adapter**: Fetches and normalizes source data with explicit request bounds and pagination.
* **Run Trace**: Captures sanitized request parameters, raw responses, and extracted records.
* **Offline Replay**: Reproduces incidents faithfully without live network access.
* **Verification Engine**: Deterministic invariant checks (Limit Bounds, Pagination Continuity, Silent Zero-Yield, Schema Integrity, Provenance).
* **AI Investigator**: Structured, evidence-backed diagnostic assistant operating strictly on verified evidence.
* **Regression Test Generator**: Auto-generates executable pytest test cases from incidents.

## Quick Start
```bash
# Install dependencies
pip install -e ".[dev]"

# Run integration against live source
pulse run nextimmo --limit 20

# Replay an incident offline
pulse replay incidents/INC-001

# Run structured diagnosis
pulse investigate INC-001

# Generate an executable regression test
pulse generate-test INC-001
```

## Running Tests
```bash
pytest
```
