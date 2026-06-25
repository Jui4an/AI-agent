# tests/test_tool_calls.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from src.tools import (
    get_numbers_from_db,
    get_descriptions_for_numbers,
    validate_numbers,
    save_advice_tool
)
from src.db_tips import get_tips

class TestToolCalls:
    
    def test_get_numbers_from_db_returns_string(self):
        """Проверяем, что get_numbers_from_db возвращает строку."""
        result = get_numbers_from_db()  # без .invoke({})
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_descriptions_for_numbers_returns_string(self):
        """Проверяем, что get_descriptions_for_numbers возвращает строку."""
        test_pairs = "12.3, 5.2, 10.6, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.1, 8.2, 9.3, 10.4"
        result = get_descriptions_for_numbers(test_pairs)  # напрямую
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_validate_numbers_valid(self):
        """Проверяем, что validate_numbers одобряет корректные числа."""
        test_pairs = "12.3, 5.2, 10.6, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.1, 8.2, 9.3, 10.4"
        result = validate_numbers(test_pairs)
        assert "корректны" in result.lower() or "успешно" in result.lower()
    
    def test_validate_numbers_invalid_count(self):
        """Проверяем, что validate_numbers ловит неправильное количество чисел."""
        test_pairs = "12.3, 5.2"  # только 2 числа
        result = validate_numbers(test_pairs)
        assert "ожидалось" in result.lower() or "13" in result
    
    def test_validate_numbers_invalid_range(self):
        """Проверяем, что validate_numbers ловит числа вне диапазона."""
        test_pairs = "99.9, 5.2, 10.6, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.1, 8.2, 9.3, 10.4"
        result = validate_numbers(test_pairs)
        assert "ошибка" in result.lower() or "должно быть" in result.lower()
    
    def test_save_advice_tool_valid(self):
        """Проверяем, что сохранение совета работает."""
        test_advice = "Это тестовый совет для проверки сохранения в БД."
        result = save_advice_tool(
            gate_line="1.1",
            advice=test_advice,
            dialog_summary="Тестовое сохранение"
        )
        assert "сохранён" in result.lower()
        assert "ID" in result
    
    def test_save_advice_tool_short_advice(self):
        """Проверяем, что слишком короткий совет не сохраняется."""
        result = save_advice_tool(
            gate_line="1.1",
            advice="Коротко.",
            dialog_summary=""
        )
        assert "ошибка" in result.lower() or "valid" in result.lower()
    
    def test_get_tips_returns_list(self):
        """Проверяем, что get_tips возвращает список."""
        tips = get_tips()
        assert isinstance(tips, list)