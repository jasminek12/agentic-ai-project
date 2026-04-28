import json
import re
from typing import Any, Dict, List

from app.config import STORAGE_DIR


DEFAULT_MEMORY: Dict[str, Any] = {
    "mode": "",
    "job_description": "",
    "resume": "",
    "panel_mode": False,
    "pressure_round": False,
    "company_context": "",
    "role_context": "",
    "interview_date": "",
    "panel_personas": [],
    "panel_turn_index": 0,
    "weak_topic_memory": [],
    "target_question_count": 6,
    "answered_count": 0,
    "pending_next_step": {},
    "interview_complete": False,
    "final_evaluation": "",
    "debrief_actions": [],
    "next_round_target": "",
    "curriculum_plan": [],
    "completed_at": "",
    "system_metrics": {
        "latency_ms_avg": 0.0,
        "consistency_score": 0.0,
        "drift_score": 0.0,
    },
    "resume_job_match": {
        "skill_overlap_pct": 0.0,
        "keyword_match_score": 0.0,
        "experience_alignment_score": 0.0,
        "ats_style_score": 0.0,
    },
    "history": [],
}


def _memory_file_path(session_id: str):
    safe_session_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return STORAGE_DIR / f"memory_{safe_session_id}.json"


def memory_exists(session_id: str) -> bool:
    memory_file = _memory_file_path(session_id)
    return memory_file.exists()


def delete_memory(session_id: str) -> bool:
    memory_file = _memory_file_path(session_id)
    if not memory_file.exists():
        return False
    memory_file.unlink()
    return True


def list_memory_sessions() -> List[Dict[str, Any]]:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    sessions: List[Dict[str, Any]] = []
    for memory_file in STORAGE_DIR.glob("memory_*.json"):
        session_id = memory_file.stem.replace("memory_", "", 1)
        try:
            stat = memory_file.stat()
            sessions.append(
                {
                    "session_id": session_id,
                    "updated_at": stat.st_mtime,
                }
            )
        except OSError:
            continue
    sessions.sort(key=lambda item: float(item.get("updated_at", 0)), reverse=True)
    return sessions


def load_memory(session_id: str) -> Dict[str, Any]:
    print(f"[DEBUG] Loading interview memory for session_id={session_id}")
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        memory_file = _memory_file_path(session_id)
        if not memory_file.exists():
            save_memory(session_id, DEFAULT_MEMORY)
            return dict(DEFAULT_MEMORY)

        with memory_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                print("[DEBUG] Memory file is not a dict. Resetting.")
                reset_memory(session_id)
                return dict(DEFAULT_MEMORY)
            return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[DEBUG] Failed to load memory: {exc}. Resetting memory file.")
        reset_memory(session_id)
        return dict(DEFAULT_MEMORY)


def save_memory(session_id: str, memory: Dict[str, Any]) -> None:
    print(f"[DEBUG] Saving interview memory for session_id={session_id}")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    memory_file = _memory_file_path(session_id)
    with memory_file.open("w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2, ensure_ascii=False)


def reset_memory(session_id: str) -> Dict[str, Any]:
    print(f"[DEBUG] Resetting interview memory for session_id={session_id}")
    save_memory(session_id, dict(DEFAULT_MEMORY))
    return dict(DEFAULT_MEMORY)
