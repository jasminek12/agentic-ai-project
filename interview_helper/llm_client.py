from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs: dict = {"api_key": api_key or "ollama"}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def chat_completion(
    *,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.4,
    max_retries: int = 2,
) -> str:
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            choice: Any = resp.choices[0].message
            content = getattr(choice, "content", None)
            if not content or not str(content).strip():
                raise RuntimeError("Empty model response")
            return str(content).strip()
        except Exception as e:
            last_err = e
            if attempt >= max_retries:
                break
            time.sleep(0.35 * (2**attempt))
    raise RuntimeError(f"Model call failed after retries (model={model}).") from last_err


def model_for(kind: str) -> str:
    env_key = "INTERVIEW_MODEL" if kind == "interview" else "EVALUATOR_MODEL"
    return os.getenv(env_key) or os.getenv("INTERVIEW_MODEL") or "gpt-4o-mini"
