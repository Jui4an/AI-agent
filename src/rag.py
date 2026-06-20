import json
import random
from pathlib import Path
from typing import Tuple, Dict, Optional

DATA_DIR = Path(__file__).parent.parent / "data"
RAG_JSON = DATA_DIR / "rag.json"

_descriptions: Optional[Dict[str, str]] = None
_all_descriptions_list: Optional[list] = None

def load_rag_data() -> Dict[str, str]:
    """Загружает rag.json и возвращает словарь { 'a.b': 'описание' }."""
    global _descriptions, _all_descriptions_list
    if _descriptions is not None:
        return _descriptions
    try:
        with open(RAG_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("rag.json должен содержать словарь")
        _descriptions = data
        _all_descriptions_list = list(data.values())
        return _descriptions
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл {RAG_JSON} не найден")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ошибка парсинга rag.json: {e}")

def get_description_for_number(a: int, b: int) -> Tuple[str, bool]:
    """
    Возвращает (описание, is_fallback).
    Если описание для "a.b" найдено – is_fallback=False.
    Если нет – берётся случайное описание из всего словаря, is_fallback=True.
    """
    data = load_rag_data()
    key = f"{a}.{b}"
    if key in data:
        return data[key], False
    else:
        if not _all_descriptions_list:
            raise RuntimeError("Нет ни одного описания в rag.json")
        fallback_desc = random.choice(_all_descriptions_list)
        return fallback_desc, True

def get_all_descriptions() -> list:
    """Возвращает список всех описаний (для возможного использования)."""
    load_rag_data()
    return _all_descriptions_list

if __name__ == "__main__":
    try:
        desc, fallback = get_description_for_number(12, 3)
        print(f"Описание для 12.3: {desc}, fallback={fallback}")
        desc2, fallback2 = get_description_for_number(99, 9)
        print(f"Описание для 99.9: {desc2}, fallback={fallback2}")
    except Exception as e:
        print(f"Ошибка: {e}")