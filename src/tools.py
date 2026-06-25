# src/tools.py (без LangChain)
from datetime import datetime
from typing import List, Tuple
from .db_tips import save_tip
from .models import Tip
from .database import get_today_numbers, parse_number_pair
from .rag import get_description_for_number

# Простая обёртка для имитации интерфейса LangChain
class ToolWrapper:
    """Обёртка для совместимости с кодом, который ожидает .invoke()"""
    def __init__(self, func):
        self.func = func
    
    def invoke(self, input_data: dict):
        """Вызывает функцию с аргументами из словаря."""
        return self.func(**input_data)

def get_numbers_from_db() -> str:
    """
    Получает 13 пар чисел из локальной базы (CSV) за текущий день.
    """
    try:
        pairs = get_today_numbers()
        pairs_str = ', '.join(f"{a}.{b}" for a, b in pairs)
        return f"Найдены числа: {pairs_str}"
    except Exception as e:
        return f"Ошибка получения чисел: {e}"

def get_descriptions_for_numbers(pairs_str: str) -> str:
    """
    Принимает строку с парами вида "12.3, 5.2, ..." и возвращает описания для каждой пары.
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

def validate_numbers(pairs_str: str) -> str:
    """
    Проверяет, что все пары корректны (1-64 и 1-12) и их ровно 13.
    """
    try:
        parts = [p.strip() for p in pairs_str.replace(',', ' ').split() if p.strip()]
        if len(parts) != 13:
            return f"Ошибка: ожидалось 13 чисел, получено {len(parts)}"
        for p in parts:
            a, b = parse_number_pair(p)
        return "Все 13 чисел корректны (1-64 и 1-12)."
    except Exception as e:
        return f"Ошибка валидации: {e}"

def save_advice_tool(gate_line: str, advice: str, dialog_summary: str = "") -> str:
    """
    Сохраняет совет в базу данных.
    """
    try:
        tip = Tip(
            gate_line=gate_line,
            advice=advice,
            dialog_summary=dialog_summary,
            date=datetime.now().strftime("%Y-%m-%d")
        )
        tip_id = save_tip(tip.gate_line, tip.advice, tip.dialog_summary, tip.date)
        return f"Совет сохранён с ID {tip_id}"
    except Exception as e:
        return f"Ошибка сохранения совета: {e}"

# Создаём обёртки для совместимости с тестами (которые используют .invoke())
get_numbers_from_db_tool = ToolWrapper(get_numbers_from_db)
get_descriptions_for_numbers_tool = ToolWrapper(get_descriptions_for_numbers)
validate_numbers_tool = ToolWrapper(validate_numbers)
save_advice_tool_tool = ToolWrapper(save_advice_tool)