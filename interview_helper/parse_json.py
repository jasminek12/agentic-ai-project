from __future__ import annotations

import json
import re


def extract_json_object(text: str) -> dict:
    """Parse first JSON object from model output (handles extra prose)."""
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in: {text[:200]}...")
    return json.loads(text[start : end + 1])


def extract_json_array(text: str) -> list:
    """Parse first JSON array from model output (handles extra prose)."""
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON array found in: {text[:200]}...")
    return json.loads(text[start : end + 1])
