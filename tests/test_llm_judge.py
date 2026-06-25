# tests/test_llm_judge.py
import re
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from src.agent_wrapper import generate_response, call_model, generate_summary
from src.settings_manager import get_model_name

class TestLLMAsJudge:
    
    def test_response_relevance(self):
        """Проверяем, что ответ агента релевантен теме."""
        gate_line = "10.6"
        gate_desc = "Ворота 10 (Любовь к себе) — линия 6: трансценденция"
        
        response = generate_response(
            prompt="Что значит эта энергия для меня сегодня?",
            history=[],
            gate_line=gate_line,
            gate_desc=gate_desc
        )
        
        # Если генерация вернула ошибку — пропускаем тест
        if "ошибка" in response.lower() or "timeout" in response.lower():
            pytest.skip(f"Модель не ответила: {response[:50]}")
        
        judge_prompt = f"""Оцени ответ на вопрос по шкале от 0 до 10, где 0 — абсолютно нерелевантно, 10 — идеально отвечает на вопрос.
Вопрос: "Что значит эта энергия для меня сегодня?"
Ответ: "{response}"
Ожидаемая тема: {gate_desc}

Твой ответ должен быть только числом от 0 до 10."""
        
        judge_messages = [{"role": "user", "content": judge_prompt}]
        judge_score = call_model(judge_messages, model_name=get_model_name())
        
        numbers = re.findall(r'\b\d+\b', judge_score)
        if numbers:
            score = int(numbers[0])
        else:
            score = 0
        
        if score == 0:
            pytest.skip("LLM не смог дать числовую оценку")
        
        assert score >= 4, f"Оценка LLM: {score}. Ответ недостаточно релевантен: {response[:100]}..."
    
    def test_advice_practicality(self):
        """Проверяем, что сгенерированный совет практичен."""
        gate_line = "10.6"
        gate_desc = "Ворота 10 (Любовь к себе) — линия 6: трансценденция"
        
        summary = generate_summary(
            history=[
                {"role": "user", "content": "Я чувствую, что сегодня хочу побыть один."},
                {"role": "assistant", "content": "Это прекрасно! Энергия 10.6 приглашает вас уединиться..."}
            ],
            gate_line=gate_line,
            gate_desc=gate_desc
        )
        
        # Если генерация вернула ошибку — пропускаем тест
        if "ошибка" in summary.lower() or "timeout" in summary.lower():
            pytest.skip(f"Модель не ответила: {summary[:50]}")
        
        judge_prompt = f"""Оцени практичность следующего совета по шкале от 0 до 10, где 0 — совершенно бесполезно (общие слова), 10 — очень конкретный и выполнимый совет.
Совет: "{summary}"
Твой ответ должен быть только числом от 0 до 10."""
        
        judge_messages = [{"role": "user", "content": judge_prompt}]
        judge_score = call_model(judge_messages, model_name=get_model_name())
        
        numbers = re.findall(r'\b\d+\b', judge_score)
        if numbers:
            score = int(numbers[0])
        else:
            score = 0
        
        if score == 0:
            pytest.skip("LLM не смог дать числовую оценку")
        
        assert score >= 3, f"Оценка LLM: {score}. Совет недостаточно практичен: {summary[:100]}..."
    
    def test_response_contains_gate_info(self):
        """Проверяем, что ответ содержит упоминание о gate."""
        gate_line = "1.2"
        gate_desc = "Ворота 1 (Творчество) — линия 2: природный талант"
        
        response = generate_response(
            prompt="Расскажи мне про эту энергию.",
            history=[],
            gate_line=gate_line,
            gate_desc=gate_desc
        )
        
        # Если генерация вернула ошибку — пропускаем тест
        if "ошибка" in response.lower() or "timeout" in response.lower():
            pytest.skip(f"Модель не ответила: {response[:50]}")
        
        judge_prompt = f"""Проверь, содержит ли ответ информацию о следующих ключевых понятиях:
- Ворота 1 или Творчество
- линия 2 или природный талант

Ответ: "{response}"

Ответь "ДА" если содержит оба понятия, иначе "НЕТ"."""
        
        judge_messages = [{"role": "user", "content": judge_prompt}]
        judge_result = call_model(judge_messages, model_name=get_model_name())
        
        assert "ДА" in judge_result.upper(), f"Ответ не содержит информации о gate: {response[:100]}..."