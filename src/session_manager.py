# Простой менеджер сессий в памяти (для демонстрации)
from typing import Dict, List
import uuid

sessions: Dict[str, Dict] = {}

def create_session(gate_line: str) -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "gate_line": gate_line,
        "history": []  # список сообщений [{"role": "user/assistant", "content": "..."}]
    }
    return session_id

def get_session(session_id: str) -> Dict | None:
    return sessions.get(session_id)

def update_session(session_id: str, data: Dict):
    if session_id in sessions:
        sessions[session_id].update(data)

def add_message(session_id: str, role: str, content: str):
    if session_id in sessions:
        sessions[session_id]["history"].append({"role": role, "content": content})