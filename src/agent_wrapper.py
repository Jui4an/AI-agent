# src/agent_wrapper.py
from openai import OpenAI
from typing import List, Dict, Optional

# ===== НАСТРОЙКИ МОДЕЛИ =====
MODEL_URL = "http://10.164.224.226:1234/v1"
MODEL_NAME = "qwen/qwen3-vl-8b"  # маленькая модель

def call_model(messages: List[Dict[str, str]]) -> str:
    """Вызов модели через OpenAI-совместимый API."""
    client = OpenAI(base_url=MODEL_URL, api_key="not-needed", timeout=30.0)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.85,      # немного креативности
            max_tokens=600,
            timeout=30.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка вызова модели: {e}"

def generate_response(prompt: str, history: list = None, gate_line: str = None, gate_desc: str = None) -> str:
    """
    Генерирует ответ от модели с учётом контекста gate.
    """
    if history is None:
        history = []
    
    # Системный промпт – задаёт роль модели
    system_prompt = f"""Ты — мудрый, чуткий и вдохновляющий консультант по Дизайну Человека (Human Design). 
Твоя задача — помогать людям осознавать и проживать транзитные энергии, которые влияют на них сегодня.

Текущая энергия: {gate_line} — {gate_desc}.

Ты ведёшь глубокий, доверительный диалог. Ты не даёшь готовых ответов, а задаёшь вопросы, раскрываешь суть энергии через метафоры и примеры из жизни. Ты говоришь просто, но с душой, как старший друг.

Правила:
- Отвечай на русском языке, красиво и вдохновляюще.
- Спрашивай, как человек чувствует эту энергию в своей жизни.
- Если человек делится опытом — подтверждай его чувства и углубляй понимание.
- Не навязывай, а предлагай взглянуть по-новому.
- Если человек спрашивает о чём-то, что не связано с энергией — мягко возвращай к теме, но не жёстко.

Твои ответы — это приглашение к исследованию себя."""
    
    # Формируем сообщения
    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": prompt}
    ]
    
    return call_model(messages)