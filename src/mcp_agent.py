# src/mcp_agent.py
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from agent_wrapper import call_model
from settings_manager import get_model_name, get_big_model_name

MODEL_NAME = get_model_name()
BIG_MODEL_NAME = get_big_model_name()
from db_tips import get_tips, save_tip
from rag import get_description_for_number

app = FastAPI(title="MCP Agent for Advice Evaluation")

class AdviceRequest(BaseModel):
    gate_line: str
    advice: str
    dialog_summary: Optional[str] = ""
    history: Optional[List[dict]] = []

class AdviceResponse(BaseModel):
    should_save: bool
    enriched_advice: str
    reason: str
    score: int

def check_uniqueness(gate_line: str, advice: str) -> bool:
    """Проверяет, есть ли похожий совет для этого gate за последние 7 дней."""
    tips = get_tips(gate_line=gate_line)
    if not tips:
        return True
    # Простая проверка: если хотя бы 50% слов совпадают с каким-либо советом, считаем неуникальным
    words = set(advice.lower().split())
    for t in tips:
        if t.get('date') and datetime.strptime(t['date'], "%Y-%m-%d") >= datetime.now() - timedelta(days=7):
            t_words = set(t['advice'].lower().split())
            if len(words & t_words) / max(len(words), 1) > 0.5:
                return False
    return True

def evaluate_with_llm(gate_line: str, advice: str) -> tuple[int, str]:
    """Использует LLM для оценки практичности и конкретности совета."""
    prompt = f"""Оцените следующий совет для транзитной энергии {gate_line} по шкале от 0 до 100, где 0 — совершенно бесполезно, 100 — очень практично и конкретно.
Совет: "{advice}"
Ответ должен быть в формате: <оценка>|<краткое обоснование> (например: 85|Совет конкретный и выполнимый)"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = call_model(messages, BIG_MODEL_NAME)  # пробуем большую
    except:
        response = call_model(messages, MODEL_NAME)      # fallback
    # Парсим ответ
    if '|' in response:
        score_str, reason = response.split('|', 1)
        try:
            score = int(score_str.strip())
        except:
            score = 50
    else:
        score = 50
        reason = "Не удалось распарсить оценку"
    return min(max(score, 0), 100), reason.strip()

def enrich_with_llm(gate_line: str, advice: str) -> str:
    """Генерирует 1-2 конкретных бытовых действия для совета."""
    prompt = f"""Дополните следующий совет для транзитной энергии {gate_line} одной-двумя конкретными практическими рекомендациями (бытовыми действиями), которые помогут человеку прожить эту энергию сегодня. Не меняйте сам совет, просто добавьте в конце предложения, начинающиеся с "Что сделать сегодня:".
Исходный совет: "{advice}"
Ответ должен быть в виде: "{advice} Что сделать сегодня: действие1, действие2."
"""
    messages = [{"role": "user", "content": prompt}]
    try:
        enriched = call_model(messages, BIG_MODEL_NAME)
    except:
        enriched = call_model(messages, MODEL_NAME)
    return enriched

@app.post("/evaluate", response_model=AdviceResponse)
async def evaluate_advice(req: AdviceRequest):
    # 1. Проверка уникальности
    is_unique = check_uniqueness(req.gate_line, req.advice)
    if not is_unique:
        return AdviceResponse(
            should_save=False,
            enriched_advice=req.advice,
            reason="Похожий совет уже существует за последнюю неделю.",
            score=0
        )
    
    # 2. Оценка LLM
    score, reason = evaluate_with_llm(req.gate_line, req.advice)
    
    # 3. Решение о сохранении (порог > 60)
    should_save = score >= 60
    
    # 4. Если сохраняем, обогащаем совет
    enriched = req.advice
    if should_save:
        enriched = enrich_with_llm(req.gate_line, req.advice)
        # Сохраняем в БД (можно делать здесь или вернуть для сохранения в основном приложении)
        # Мы вернём обогащённый совет, а сохранение сделаем в основном приложении.
    
    return AdviceResponse(
        should_save=should_save,
        enriched_advice=enriched,
        reason=reason,
        score=score
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)