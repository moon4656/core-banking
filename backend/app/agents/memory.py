import json

import redis as redis_lib

from app.core.config import settings

MAX_TURNS = 5
SESSION_TTL = 3600


def _get_client() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def load_history(session_id: str | None) -> list[dict]:
    if not session_id:
        return []
    try:
        client = _get_client()
        data = client.get(f"session:{session_id}:history")
        return json.loads(data) if data else []
    except Exception:
        return []


def save_turn(session_id: str | None, user_msg: str, assistant_msg: str) -> dict:
    if not session_id:
        return {"saved": False, "reason": "missing_session_id", "stored_turns": 0, "preview": []}

    try:
        history = load_history(session_id)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})

        if len(history) > MAX_TURNS * 2:
            history = history[-(MAX_TURNS * 2):]

        client = _get_client()
        client.setex(
            f"session:{session_id}:history",
            SESSION_TTL,
            json.dumps(history, ensure_ascii=False),
        )
        return {
            "saved": True,
            "stored_turns": len(history) // 2,
            "preview": history[-2:],
        }
    except Exception:
        return {"saved": False, "reason": "redis_error", "stored_turns": 0, "preview": []}
