# src/agent_wrapper.py
from openai import OpenAI
from typing import List, Dict, Optional

# ===== НАСТРОЙКИ МОДЕЛЕЙ =====
MODEL_URL = "http://10.164.224.226:1234/v1"          # или localhost
MODEL_NAME = "qwen/qwen3-vl-8b"                      # основная модель
BIG_MODEL_NAME = "eva-qwen2.5-14b-v0.2"  # большая (если доступна)

def call_model(messages: List[Dict[str, str]], model_name: str = None) -> str:
    """
    Вызов модели с возможностью указать имя модели.
    Если model_name не указан, используется MODEL_NAME.
    """
    if model_name is None:
        model_name = MODEL_NAME
    client = OpenAI(base_url=MODEL_URL, api_key="not-needed", timeout=30.0)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.85,
            max_tokens=600,
            timeout=30.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        # Если большая модель недоступна, пробуем маленькую (если вызывали большую)
        if model_name == BIG_MODEL_NAME and BIG_MODEL_NAME != MODEL_NAME:
            print(f"Ошибка вызова большой модели ({model_name}): {e}. Пробую маленькую...")
            try:
                return call_model(messages, MODEL_NAME)
            except Exception as e2:
                return f"Ошибка вызова обеих моделей: {e2}"
        return f"Ошибка вызова модели ({model_name}): {e}"

def generate_response(prompt: str, history: list = None, gate_line: str = None, gate_desc: str = None) -> str:
    """Генерация ответа в диалоге (основная модель)."""
    if history is None:
        history = []
    
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
    
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": prompt}]
    return call_model(messages, MODEL_NAME)

def generate_summary(history: list, gate_line: str, gate_desc: str) -> str:
    """Генерирует лайфхак-совет. Сначала пытается использовать большую модель, при ошибке – маленькую."""
    dialog_text = ""
    for msg in history:
        role = "Консультант" if msg["role"] == "assistant" else "Пользователь"
        dialog_text += f"{role}: {msg['content']}\n"
    
    prompt = f"""На основе следующего диалога о транзитной энергии {gate_line} ({gate_desc}), сформулируй один короткий, практичный и вдохновляющий лайфхак-совет, который поможет человеку прожить эту энергию сегодня. Совет должен быть конкретным, выполнимым и отражать суть диалога. Ответ должен быть в виде одного предложения или короткого абзаца (не более 30 слов).

Диалог:
{dialog_text}

Твой лайфхак-совет:"""
    
    messages = [
        {"role": "system", "content": "Ты — мудрый наставник, который умеет выделять главное из диалога и давать практичные советы."},
        {"role": "user", "content": prompt}
    ]
    
    # Если большая модель отличается от основной, пробуем вызвать её
    if BIG_MODEL_NAME != MODEL_NAME:
        try:
            return call_model(messages, BIG_MODEL_NAME)
        except Exception as e:
            print(f"Ошибка при вызове большой модели: {e}. Использую маленькую.")
            # fallback на маленькую модель
            return call_model(messages, MODEL_NAME)
    else:
        # Если большая не задана отдельно, используем основную
        return call_model(messages, MODEL_NAME)