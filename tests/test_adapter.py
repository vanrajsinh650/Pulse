import json
import pytest
from pulse.adapters.base import SourceParseError
from pulse.adapters.nextimmo import NextimmoAdapter
from pulse.contracts.models import RequestTrace


SAMPLE_LISTING = {
    "id": 59335,
    "slug": "magnificent-flat-rollingergrund",
    "type": "apartment",
    "group": "sale",
    "hasForSale": True,
    "price": {"value": 485000, "currency": "EUR"},
    "area": {"value": 95.5},
    "bedrooms": 2,
    "location": {"name": "Luxembourg-Rollingergrund", "zipcode": "2440"},
}

SAMPLE_HTML = f"""
<!DOCTYPE html>
<html>
<head><title>Search</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">
{json.dumps({
    "props": {
        "pageProps": {
            "initialData": {
                "pagination": {
                    "currentPage": 1,
                    "totalPages": 5,
                    "itemsPerPage": 2
                },
                "data": [
                    SAMPLE_LISTING,
                    {
                        "id": 59336,
                        "slug": "studio-belair",
                        "type": "studio",
                        "group": "rent",
                        "hasForSale": False,
                        "price": {"value": 1400, "currency": "EUR"},
                        "area": {"value": 35.0},
                        "bedrooms": 1,
                        "location": {"name": "Luxembourg-Belair", "zipcode": "1140"},
                    }
                ]
            }
        }
    }
})}
</script>
</body>
</html>
"""


def test_nextimmo_normalization():
    adapter = NextimmoAdapter()
    record = adapter.normalize_record(SAMPLE_LISTING)

    assert record.property_entity_id == "nextimmo:59335"
    assert record.source == "nextimmo"
    assert record.source_listing_id == "59335"
    assert record.source_url == "https://nextimmo.lu/listing/magnificent-flat-rollingergrund"
    assert record.deal_type == "sale"
    assert record.property_type == "apartment"
    assert record.price == 485000.0
    assert record.currency == "EUR"
    assert record.area == 95.5
    assert record.rooms == 2
    assert record.location == "Luxembourg-Rollingergrund"


def test_nextimmo_extract_from_html():
    adapter = NextimmoAdapter()
    records = adapter.extract_raw_records(SAMPLE_HTML)
    assert len(records) == 2
    assert records[0]["id"] == 59335
    assert records[1]["id"] == 59336


def test_nextimmo_extract_from_json():
    adapter = NextimmoAdapter()
    json_payload = json.dumps({"data": [SAMPLE_LISTING]})
    records = adapter.extract_raw_records(json_payload)
    assert len(records) == 1
    assert records[0]["id"] == 59335


def test_nextimmo_corrupted_payload_raises_parse_error():
    adapter = NextimmoAdapter()
    corrupted_html = '<script id="__NEXT_DATA__">{"bad json</script>'
    with pytest.raises(SourceParseError):
        adapter.extract_raw_records(corrupted_html)


def test_nextimmo_bounded_run_pagination():
    def mock_transport(url: str, params: dict, headers: dict) -> RequestTrace:
        page = int(url.split("/")[-1])
        item = {
            "id": 1000 + page,
            "type": "apartment",
            "price": {"value": 500000},
        }
        payload = json.dumps({"data": [item]})
        return RequestTrace(
            page=page,
            url=url,
            status_code=200,
            response_size=len(payload),
            raw_payload=payload,
        )

    adapter = NextimmoAdapter(transport=mock_transport)
    trace = adapter.run(limit=2)

    assert trace.total_records == 2
    assert trace.total_requests == 2
    assert trace.records[0].source_listing_id == "1001"
    assert trace.records[1].source_listing_id == "1002"
