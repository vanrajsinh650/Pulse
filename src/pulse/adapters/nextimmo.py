from __future__ import annotations

import json
import re
from typing import Any

import requests

from pulse.adapters.base import BaseAdapter, SourceFetchError, SourceParseError, TransportFunc
from pulse.contracts.models import PropertyRecord, RequestTrace


class NextimmoAdapter(BaseAdapter):
    """Adapter for Nextimmo.lu real estate listings."""

    BASE_URL = "https://nextimmo.lu"
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(
        self,
        transport: TransportFunc | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        super().__init__(transport=transport)
        self.timeout_seconds = timeout_seconds

    @property
    def source_name(self) -> str:
        return "nextimmo"

    def fetch_page(self, page: int, params: dict[str, Any] | None = None) -> RequestTrace:
        url = f"{self.BASE_URL}/search/page/{page}"
        request_params = params or {}
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        if self.transport is not None:
            return self.transport(url, request_params, headers)

        try:
            response = requests.get(
                url,
                params=request_params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SourceFetchError(f"Failed to fetch {url}: {exc}") from exc

        # Sanitize sensitive headers before persisting in trace
        safe_headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in {"set-cookie", "cookie", "authorization", "cf-ray"}
        }

        return RequestTrace(
            page=page,
            url=url,
            method="GET",
            params=request_params,
            status_code=response.status_code,
            headers=safe_headers,
            response_size=len(response.content),
            raw_payload=response.text,
        )

    def extract_raw_records(self, payload: str) -> list[dict[str, Any]]:
        if not payload:
            return []

        # If payload is already a raw JSON string (e.g. from fixture or API)
        trimmed = payload.strip()
        if trimmed.startswith("{") and ("\"initialData\"" in trimmed or "\"data\"" in trimmed):
            try:
                data = json.loads(trimmed)
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                if "props" in data:
                    return data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("data", [])
            except json.JSONDecodeError:
                pass

        # Extract __NEXT_DATA__ from SSR HTML
        match = re.search(r'id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', payload, re.DOTALL)
        if not match:
            # If payload looks like valid HTML with no __NEXT_DATA__, parser returns empty list
            # Zero-yield detector will distinguish empty source from parser failure based on HTML size
            return []

        try:
            parsed = json.loads(match.group(1))
            page_props = parsed.get("props", {}).get("pageProps", {})
            initial_data = page_props.get("initialData", {})
            listings = initial_data.get("data", [])
            if not isinstance(listings, list):
                return []
            return listings
        except (json.JSONDecodeError, AttributeError) as exc:
            raise SourceParseError(f"Corrupted __NEXT_DATA__ in Nextimmo page: {exc}") from exc

    def normalize_record(self, raw: dict[str, Any]) -> PropertyRecord:
        raw_id = raw.get("id") or raw.get("_id") or raw.get("refId")
        if not raw_id:
            raise ValueError("Raw record missing identifier")

        listing_id = str(raw_id)
        slug = raw.get("slug")
        url = f"{self.BASE_URL}/listing/{slug or listing_id}"

        # Deal type
        is_sale = raw.get("hasForSale", True)
        group = str(raw.get("group", "")).lower()
        deal_type = "sale" if (is_sale or group == "sale") else "rent"

        # Price extraction
        price_obj = raw.get("price")
        price_val: float | None = None
        currency = "EUR"
        if isinstance(price_obj, dict):
            val = price_obj.get("value")
            if val is not None:
                try:
                    price_val = float(val)
                except (ValueError, TypeError):
                    price_val = None
            currency = price_obj.get("currency") or "EUR"
        elif isinstance(price_obj, (int, float)):
            price_val = float(price_obj)

        # Area extraction
        area_obj = raw.get("area")
        area_val: float | None = None
        if isinstance(area_obj, dict):
            val = area_obj.get("value")
            if val is not None:
                try:
                    area_val = float(val)
                except (ValueError, TypeError):
                    area_val = None
        elif isinstance(area_obj, (int, float)):
            area_val = float(area_obj)

        # Rooms
        rooms = raw.get("bedrooms") or raw.get("rooms")
        room_val: int | None = None
        if rooms is not None:
            try:
                room_val = int(rooms)
            except (ValueError, TypeError):
                room_val = None

        # Location
        loc_obj = raw.get("location")
        loc_str: str | None = None
        if isinstance(loc_obj, dict):
            loc_str = loc_obj.get("name")
        elif isinstance(loc_obj, str):
            loc_str = loc_obj
        elif isinstance(raw.get("city"), dict):
            loc_str = raw["city"].get("name")

        # Map property type
        type_code = raw.get("type")
        type_map = {1: "house", 2: "apartment", 3: "commercial", 4: "land", 5: "garage", 6: "office"}
        property_type: str | None = None
        if isinstance(type_code, int):
            property_type = type_map.get(type_code, str(type_code))
        elif type_code:
            property_type = str(type_code)

        return PropertyRecord(
            property_entity_id=f"nextimmo:{listing_id}",
            source=self.source_name,
            source_listing_id=listing_id,
            source_url=url,
            deal_type=deal_type,
            property_type=property_type,
            price=price_val,
            currency=currency,
            area=area_val,
            rooms=room_val,
            location=loc_str,
        )
