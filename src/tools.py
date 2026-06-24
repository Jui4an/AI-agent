from typing import List, Tuple
from datetime import datetime
from langchain.tools import tool
from pydantic import BaseModel, Field, ValidationError

from .db_tips import save_tip
from .models import Tip

from database import get_today_numbers, parse_number_pair
from rag import get_description_for_number

class NumberPair(BaseModel):
    first: int = Field(..., ge=1, le=64, description="Первое число (1-64)")
    second: int = Field(..., ge=1, le=6, description="Второе число (1-6)")

@tool
def get_numbers_from_db() -> str:
    """
    Получает 13 пар чисел из локальной базы (CSV) за текущий день.
    Возвращает строку с перечислением пар, например: "12.3, 5.2, ..."
    """
    try:
        pairs = get_today_numbers()
        pairs_str = ', '.join(f"{a}.{b}" for a, b in pairs)
        return f"Найдены числа: {pairs_str}"
    except Exception as e:
        return f"Ошибка получения чисел: {e}"

@tool
def get_descriptions_for_numbers(pairs_str: str) -> str:
    """
    Принимает строку с парами вида "12.3, 5.2, ..." и возвращает описания для каждой пары.
    Если описание отсутствует, используется случайное (с пометкой).
    """
    try:
        parts = [p.strip() for p in pairs_str.replace(',', ' ').split() if p.strip()]
        if len(parts) != 13:
            return f"Ожидалось 13 чисел, получено {len(parts)}"
        pairs = [parse_number_pair(p) for p in parts]
    except Exception as e:
        return f"Ошибка разбора чисел: {e}"
    
    result_lines = []
    for idx, (a, b) in enumerate(pairs, 1):
        desc, fallback = get_description_for_number(a, b)
        fallback_note = " (использовано случайное описание, так как точное не найдено)" if fallback else ""
        result_lines.append(f"{idx}. {a}.{b}: {desc}{fallback_note}")
    return "\n".join(result_lines)

@tool
def validate_numbers(pairs_str: str) -> str:
    """
    Проверяет, что все пары корректны (1-64 и 1-6) и их ровно 13.
    Возвращает сообщение об успехе или ошибке.
    """
    try:
        parts = [p.strip() for p in pairs_str.replace(',', ' ').split() if p.strip()]
        if len(parts) != 13:
            return f"Ошибка: ожидалось 13 чисел, получено {len(parts)}"
        for p in parts:
            a, b = parse_number_pair(p)
        return "Все 13 чисел корректны (1-64 и 1-6)."
    except Exception as e:
        return f"Ошибка валидации: {e}"

if __name__ == "__main__":
    print(get_numbers_from_db.invoke({}))
    print(get_descriptions_for_numbers.invoke({"pairs_str": "12.3, 5.2, 10.6, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.1, 8.2, 9.3, 10.4"}))

@tool
def save_advice_tool(gate_line: str, advice: str, dialog_summary: str = "") -> str:
    """
    Сохраняет совет в базу данных.
    gate_line: строка вида "X.Y"
    advice: текст совета (3-5 предложений)
    dialog_summary: краткое содержание диалога (опционально)
    """
    try:
        # Валидация через Pydantic
        tip = Tip(gate_line=gate_line, advice=advice, dialog_summary=dialog_summary, date=datetime.now().strftime("%Y-%m-%d"))
        tip_id = save_tip(tip.gate_line, tip.advice, tip.dialog_summary, tip.date)
        return f"Совет сохранён с ID {tip_id}"
    except Exception as e:
        return f"Ошибка сохранения совета: {e}"