"""Tolerant JSON extraction from LLM responses."""

from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_object(raw: str) -> dict | None:
    """Best-effort extraction of a single JSON object from an LLM response.

    Tries, in order: the whole string, the contents of a markdown code fence,
    and the substring from the first "{" to the last "}". Returns None when no
    attempt yields a JSON object (arrays and scalars also return None).
    """
    candidates = [raw]

    fence = _FENCE_RE.search(raw)
    if fence:
        candidates.append(fence.group(1))

    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
