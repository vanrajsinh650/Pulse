from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union
from pulse.contracts.models import RunTrace


SENSITIVE_HEADERS = {"cookie", "set-cookie", "authorization", "x-api-key", "token"}
SENSITIVE_PARAMS = {"key", "api_key", "token", "auth", "secret"}


def sanitize_dict(d: Dict[str, Any], sensitive_keys: set[str]) -> Dict[str, Any]:
    sanitized = {}
    for k, v in d.items():
        if k.lower() in sensitive_keys:
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized


def save_run_trace(trace: RunTrace, target_path: Union[str, Path]) -> Path:
    """Save a RunTrace to disk with security sanitization."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = trace.model_dump(mode="json")

    # Sanitize requests
    if "requests" in data:
        for req in data["requests"]:
            if "headers" in req and isinstance(req["headers"], dict):
                req["headers"] = sanitize_dict(req["headers"], SENSITIVE_HEADERS)
            if "params" in req and isinstance(req["params"], dict):
                req["params"] = sanitize_dict(req["params"], SENSITIVE_PARAMS)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return path


def load_run_trace(source_path: Union[str, Path]) -> RunTrace:
    """Load and validate a RunTrace from disk."""
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Run trace file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return RunTrace.model_validate(data)
