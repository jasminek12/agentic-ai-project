import json
import os
from typing import Any, Dict

import requests

from app.config import GROQ_BASE_URL, GROQ_MODEL


def call_llm(prompt: str) -> str:
    """Call Groq Chat Completions API and return text content only."""
    print("[DEBUG] call_llm invoked")
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise assistant. Follow JSON formatting exactly when requested."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }

    try:
        response = requests.post(GROQ_BASE_URL, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 401:
            print(f"[DEBUG] RAW RESPONSE: {response.text}")
            raise ValueError("Invalid GROQ API key.")
        response.raise_for_status()
        body = response.json()
        print("[DEBUG] LLM response received successfully")
        return body["choices"][0]["message"]["content"].strip()
    except ValueError:
        raise
    except requests.RequestException as exc:
        print(f"[DEBUG] Network/API error from Groq: {exc}")
        raise RuntimeError("Failed to connect to LLM provider.") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[DEBUG] Unexpected LLM response format: {exc}")
        raise RuntimeError("Received malformed response from LLM provider.") from exc