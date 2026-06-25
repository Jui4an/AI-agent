# tests/test_asserts.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from src.database import parse_number_pair, get_today_numbers
from src.rag import get_description_for_number
from src.models import Tip

class TestAsserts:
    
    def test_parse_number_pair_valid(self):
        """Проверяем, что парсинг корректных чисел работает."""
        result = parse_number_pair("12.3")
        assert result == (12, 3)
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)
    
    def test_parse_number_pair_invalid_format(self):
        """Проверяем, что неверный формат вызывает ошибку."""
        with pytest.raises(ValueError, match="Неверный формат"):
            parse_number_pair("12-3")
    
    def test_parse_number_pair_out_of_range(self):
        """Проверяем, что числа вне диапазона вызывают ошибку."""
        with pytest.raises(ValueError, match="Первое число должно быть от 1 до 64"):
            parse_number_pair("0.3")
        
        with pytest.raises(ValueError, match="Второе число должно быть от 1 до 6"):
            parse_number_pair("12.15")
    
    def test_rag_key_exists(self):
        """Проверяем, что для существующего ключа возвращается описание."""
        desc, fallback = get_description_for_number(1, 2)
        assert desc is not None
        assert len(desc) > 0
        assert fallback is False
    
    def test_rag_key_missing_uses_fallback(self):
        """Проверяем, что для отсутствующего ключа возвращается fallback."""
        desc, fallback = get_description_for_number(99, 99)
        assert desc is not None
        assert len(desc) > 0
        assert fallback is True
    
    def test_tip_model_validation_valid(self):
        """Проверяем, что валидный совет проходит валидацию Pydantic."""
        tip = Tip(
            gate_line="10.6",
            advice="Это валидный совет длиной более десяти символов.",
            dialog_summary="Краткое содержание",
            date="2026-06-24"
        )
        assert tip.gate_line == "10.6"
        assert len(tip.advice) >= 10
    
    def test_tip_model_validation_invalid_gate(self):
        """Проверяем, что невалидный gate_line вызывает ошибку."""
        with pytest.raises(Exception):
            Tip(
                gate_line="100.6",
                advice="Это валидный совет длиной более десяти символов.",
                date="2026-06-24"
            )
    
    def test_tip_model_validation_short_advice(self):
        """Проверяем, что слишком короткий совет вызывает ошибку."""
        with pytest.raises(Exception):
            Tip(
                gate_line="10.6",
                advice="Коротко.",
                date="2026-06-24"
            )