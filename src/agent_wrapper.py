# src/agent_wrapper.py
import sys
from pathlib import Path

# Добавляем текущую папку в sys.path для корректных импортов
sys.path.insert(0, str(Path(__file__).parent))

import os
import time
from typing import List, Dict, Optional
from openai import OpenAI

from settings_manager import get_model_url, get_model_name, get_big_model_name

# ============================================================
# 1. ЗАГРУЗКА .env (переменные окружения)
# ============================================================
# Пытаемся загрузить через python-dotenv (если установлен)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] python-dotenv загружен")
except ImportError:
    # Если dotenv не установлен — загружаем вручную
    print("[WARN] python-dotenv не найден, загружаем .env вручную")
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value.strip()
                        print(f"   Загружено: {key}=***")

# ============================================================
# 2. ИНИЦИАЛИЗАЦИЯ LANGFUSE
# ============================================================
# Используем Langfuse класс (НЕ get_client) для ручного трейсинга
try:
    from langfuse import Langfuse
    
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if public_key and secret_key:
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        print(f"[OK] LangFuse инициализирован: {host}")
        print(f"   Public Key: {public_key[:10]}...")
    else:
        print("[WARN] LangFuse ключи не найдены. Трейсы не будут отправляться.")
        langfuse = None
        
except ImportError:
    print("[WARN] LangFuse не установлен. Установите: pip install langfuse")
    langfuse = None
except Exception as e:
    print(f"[WARN] Ошибка инициализации LangFuse: {e}")
    langfuse = None

# ============================================================
# 3. ОСНОВНАЯ ФУНКЦИЯ ВЫЗОВА МОДЕЛИ
# ============================================================
def call_model(messages: List[Dict[str, str]], model_name: str = None, metadata: Dict = None) -> str:
    """
    Вызывает модель через OpenAI-совместимый API.
    Если LangFuse доступен — создаёт трейс и span.
    """
    if model_name is None:
        model_name = get_model_name()
    url = get_model_url()
    
    # ===== ЛОГИРОВАНИЕ НАЧАЛА =====
    from datetime import datetime
    from pathlib import Path
    log_path = Path(__file__).parent.parent / "logs" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CALL_MODEL START: model={model_name}, function={metadata.get('function', 'unknown') if metadata else 'unknown'}"
    print(log_msg)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    
    # Создаём клиент OpenAI
    client = OpenAI(base_url=url, api_key="not-needed", timeout=60.0)
    
    # ---- LangFuse ручной трейсинг ----
    trace = None
    span = None
    if langfuse:
        try:
            trace = langfuse.trace(
                name="call_model",
                metadata=metadata or {},
                tags=["human_design", "agent", model_name]
            )
            span = trace.span(
                name="llm_call",
                input={"messages": messages, "model": model_name, "url": url}
            )
        except Exception as e:
            print(f"[WARN] LangFuse трейсинг ошибка: {e}")
    
    # ---- Вызов модели ----
    try:
        # Лог перед вызовом
        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CALL_MODEL: отправка запроса к {model_name}..."
        print(log_msg)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.85,
            max_tokens=600,
            timeout=60.0,
        )
        result = response.choices[0].message.content
        
        # Лог после ответа
        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CALL_MODEL DONE: получили ответ ({len(result)} символов)"
        print(log_msg)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
        
        # Закрываем span с результатом
        if span:
            span.update(output=result)
            span.end()
            langfuse.flush()
        
        return result
        
    except Exception as e:
        error_msg = f"Ошибка вызова модели: {e}"
        
        # Лог ошибки
        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CALL_MODEL ERROR: {e}"
        print(log_msg)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
        
        if span:
            span.update(output=error_msg, status="error")
            span.end()
            langfuse.flush()
        
        return error_msg

# ============================================================
# 4. ГЕНЕРАЦИЯ ОТВЕТА В ДИАЛОГЕ
# ============================================================
def generate_response(prompt: str, history: list = None, gate_line: str = None, gate_desc: str = None) -> str:
    """
    Генерирует ответ в чате. Использует системный промпт с ролью консультанта.
    """
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
    
    metadata = {
        "gate_line": gate_line or "unknown",
        "gate_desc": gate_desc or "unknown",
        "function": "generate_response"
    }
    
    return call_model(messages, metadata=metadata)

# ============================================================
# 5. ГЕНЕРАЦИЯ СОВЕТА (ЛАЙФХАК) НА ОСНОВЕ ДИАЛОГА
# ============================================================
def generate_summary(history: list, gate_line: str, gate_desc: str) -> str:
    """
    Анализирует диалог и генерирует короткий практичный совет.
    Сначала пытается использовать большую модель, при ошибке — маленькую.
    """
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
    
    # Пытаемся вызвать большую модель
    try:
        return call_model(messages, model_name=get_big_model_name(), metadata={"function": "generate_summary", "gate": gate_line})
    except Exception as e:
        # Если большая не доступна — используем маленькую
        print(f"[WARN] Ошибка большой модели: {e}. Использую маленькую.")
        return call_model(messages, metadata={"function": "generate_summary_fallback", "gate": gate_line})