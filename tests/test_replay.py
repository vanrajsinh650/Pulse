import json

from pulse.adapters.nextimmo import NextimmoAdapter
from pulse.contracts.models import PropertyRecord, RequestTrace, RunTrace
from pulse.replay.engine import ReplayEngine
from pulse.replay.recorder import load_run_trace, save_run_trace


def test_save_and_load_trace_with_sanitization(tmp_path):
    trace_file = tmp_path / "trace.json"
    req = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        headers={"Authorization": "Bearer secret123", "User-Agent": "TestAgent"},
        params={"api_key": "private_key", "filter": "sale"},
        raw_payload=json.dumps({"data": []}),
    )
    rec = PropertyRecord(
        property_entity_id="p1",
        source="nextimmo",
        source_listing_id="1",
        source_url="https://nextimmo.lu/1",
    )
    run_trace = RunTrace(
        run_id="run-test",
        source="nextimmo",
        requested_limit=10,
        requests=[req],
        records=[rec],
    )

    saved_path = save_run_trace(run_trace, trace_file)
    assert saved_path.exists()

    loaded = load_run_trace(saved_path)
    assert loaded.run_id == "run-test"
    assert loaded.requests[0].headers["Authorization"] == "[REDACTED]"
    assert loaded.requests[0].headers["User-Agent"] == "TestAgent"
    assert loaded.requests[0].params["api_key"] == "[REDACTED]"
    assert loaded.requests[0].params["filter"] == "sale"
    assert loaded.records[0].source_listing_id == "1"


def test_replay_engine_offline_adapter(tmp_path):
    sample_item_1 = {"id": 101, "type": "apartment", "price": {"value": 300000}}
    sample_item_2 = {"id": 102, "type": "house", "price": {"value": 600000}}

    req1 = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        raw_payload=json.dumps({"data": [sample_item_1]}),
    )
    req2 = RequestTrace(
        page=2,
        url="https://nextimmo.lu/search/page/2",
        raw_payload=json.dumps({"data": [sample_item_2]}),
    )

    trace = RunTrace(
        run_id="run-original",
        source="nextimmo",
        requested_limit=2,
        requests=[req1, req2],
        records=[],
    )

    file_path = tmp_path / "trace.json"
    save_run_trace(trace, file_path)

    engine = ReplayEngine.from_file(file_path)
    replayed_trace = engine.replay_adapter(NextimmoAdapter, limit=2)

    assert replayed_trace.total_records == 2
    assert replayed_trace.records[0].source_listing_id == "101"
    assert replayed_trace.records[1].source_listing_id == "102"
    assert replayed_trace.total_requests == 2
