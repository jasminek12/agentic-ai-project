from __future__ import annotations

import json
from pathlib import Path

from interview_helper.models import SessionSnapshot


def load_session(path: Path) -> SessionSnapshot | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionSnapshot.model_validate(data)


def save_session(path: Path, session: SessionSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
