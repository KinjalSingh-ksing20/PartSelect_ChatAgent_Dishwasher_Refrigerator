from typing import Dict, Any
import time

SESSION_TTL = 1800  # 30 minutes

_sessions: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    session = _sessions.get(session_id)
    if not session:
        session = {
            "created_at": time.time(),
            "model_number": None,
            "appliance": None,
            "last_intent": None,
            "issue": None,
        }
        _sessions[session_id] = session
    return session


def update_session(session_id: str, updates: Dict[str, Any]):
    session = get_session(session_id)
    session.update(updates)
    _sessions[session_id] = session

