import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

DATA_DIR = Path(__file__).parent.parent / "data"
NUMBERS_CSV = DATA_DIR / "numbers.csv"

def parse_number_pair(pair_str: str) -> Tuple[int, int]:
    """Преобразует '12.3' в (12, 3)."""
    parts = pair_str.strip().split('.')
    if len(parts) != 2:
        raise ValueError(f"Неверный формат: '{pair_str}', ожидается 'x.y'")
    first = int(parts[0])
    second = int(parts[1])
    if not (1 <= first <= 64):
        raise ValueError(f"Первое число должно быть от 1 до 64, получено {first}")
    if not (1 <= second <= 6):
        raise ValueError(f"Второе число должно быть от 1 до 6, получено {second}")
    return (first, second)

def get_today_numbers(date_str: Optional[str] = None) -> List[Tuple[int, int]]:
    """
    Читает CSV с нестандартными заголовками:
    - строка 0: общий заголовок (пропускаем)
    - строка 1: названия столбцов (пропускаем)
    - далее: дата в первом столбце, 13 чисел в столбцах 1..13.
    Возвращает список из 13 кортежей (a, b) для указанной даты.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Проверяем существование файла
    if not NUMBERS_CSV.exists():
        raise FileNotFoundError(f"Файл {NUMBERS_CSV} не найден")
    
    with open(NUMBERS_CSV, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Пропускаем первую строку (общий заголовок)
        next(reader, None)
        # Пропускаем вторую строку (названия столбцов)
        next(reader, None)
        
        # Теперь читаем строки с данными
        for row in reader:
            if not row:
                continue  # пустая строка
            # Первый столбец – дата (может содержать пробелы)
            row_date = row[0].strip().strip('"')
            if row_date == date_str:
                # Берём столбцы с 1 по 13 (индексы 1..13 включительно)
                # Всего должно быть 14 столбцов (дата + 13 чисел)
                if len(row) < 14:
                    raise ValueError(f"Недостаточно столбцов: ожидается 14, получено {len(row)}")
                numbers_str = row[1:14]  # список из 13 строк
                # Проверяем, что все не пустые
                if any(not s.strip() for s in numbers_str):
                    raise ValueError("Обнаружены пустые значения в числовых столбцах")
                result = [parse_number_pair(p) for p in numbers_str]
                return result
        # Если дата не найдена
        raise ValueError(f"Дата {date_str} не найдена в CSV")

if __name__ == "__main__":
    try:
        nums = get_today_numbers()
        print(f"Числа за сегодня: {nums}")
    except Exception as e:
        print(f"Ошибка: {e}")