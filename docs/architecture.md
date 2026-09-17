# Pulse - Architecture Document

## 1. Overview
Pulse is a developer-side incident reproduction and verification laboratory for web-data integration pipelines. When an upstream web source changes, adapters break subtly: pagination loops, limits overrun, or markup shifts cause zero listings to be extracted without raising network errors. Pulse reproduces these incidents deterministically offline, identifies the violated invariants with zero hallucinations, generates executable regression tests, and provides an evidence-based AI diagnosis.

## 2. Core Architecture Pipeline
```
[Real Source / Network]
          │
          ▼
   [Source Adapter] (NextimmoAdapter)
          │
     ┌────┴──────────────────────────┐
     ▼                               ▼
[Live Run]                     [Saved Traces]
     │                               │
     ▼                               ▼
[Run Trace Recorder] <────── [Offline Replay Engine]
     │
     ▼
[Structural Diff Engine] (Baseline vs Current)
     │
     ▼
[Deterministic Verification Engine]
  ├─ Limit Bound Invariant
  ├─ Pagination Continuity Invariant
  ├─ Silent Zero-Yield Invariant
  ├─ Provenance Invariant
  ├─ Request/Filter Consistency Invariant
  └─ Schema Integrity Invariant
     │
     ▼
[Incident Report] (Status: FAILED/PASSED, Invariant, Evidence)
     │
     ├──────────────────────────────┐
     ▼                              ▼
[AI Investigator]         [Regression Test Generator]
(Structured JSON Diagnosis)   (Executable pytest file)
```

## 3. Key Design Decisions

### Decision 1: Deterministic Verification is the Ground Truth
AI is never used to determine whether an invariant passed or failed. Correctness is governed entirely by mathematical and deterministic checks (limit counting, exact ID overlap set comparisons, schema validation, and non-empty response parsing).

### Decision 2: Zero Leakage of Secrets
Recorded run traces sanitize headers (Authorization, Cookie, Session tokens) and URL query parameters before writing fixtures to disk or feeding context to LLMs.

### Decision 3: Offline Replay First
Incidents must be reproducible offline with zero network flakiness. The replay engine acts as a transport layer that serves recorded fixtures to the adapter identically to live HTTP calls.

### Decision 4: AI as Diagnostic Assistant, Not Validator
The AI Investigator receives verified failure categories, invariant metadata, diff statistics, sanitized request parameters, and parser code. It returns structured JSON adhering to a strict Pydantic contract. If evidence is insufficient, it reports `insufficient_evidence`.
