# src/run_benchmark.py
import sys
import io
from pathlib import Path
import json
import site
from datetime import datetime

# Фикс кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ===== АВТОМАТИЧЕСКИ НАХОДИМ ПУТЬ К SITE-PACKAGES =====
project_root = Path(__file__).parent.parent

try:
    site_packages = site.getsitepackages()
    if site_packages:
        sys.path.insert(0, site_packages[0])
except:
    pass

venv_site = project_root / "venv" / "Lib" / "site-packages"
if venv_site.exists():
    sys.path.insert(0, str(venv_site))

venv_site_alt = project_root / "venv" / "lib" / "python3.12" / "site-packages"
if venv_site_alt.exists():
    sys.path.insert(0, str(venv_site_alt))

src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from agent_wrapper import generate_response

def safe_str(value, default=""):
    """Безопасное преобразование в строку. Если value = None → возвращает default."""
    if value is None:
        return default
    return str(value)

def safe_list(value, default=None):
    """Безопасное получение списка. Если value = None → возвращает пустой список."""
    if value is None:
        return default or []
    return value

def write_log(message: str):
    """Записывает сообщение в лог-файл."""
    log_path = Path(__file__).parent.parent / "logs" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def run_benchmark():
    write_log("ЗАПУСК BENCHMARK")
    
    benchmark_path = Path(__file__).parent.parent / "benchmark.json"
    if not benchmark_path.exists():
        print(f"[ERR] benchmark.json не найден по пути: {benchmark_path}")
        write_log("benchmark.json не найден")
        return
    
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
    
    results = []
    success_count = 0
    tests = safe_list(benchmark.get("tests"), [])
    total = len(tests)
    
    print(f"Запуск benchmark: {safe_str(benchmark.get('name'), 'unnamed')}")
    print(f"Всего тестов: {total}")
    print("=" * 60)
    write_log(f"Всего тестов: {total}")
    
    for idx, test in enumerate(tests):
        test_id = safe_str(test.get("id"), f"test_{idx+1:03d}")
        gate_line = safe_str(test.get("gate_line"), "0.0")
        test_input = safe_str(test.get("input"), "Нет вопроса")
        expected_contains = safe_list(test.get("expected_output_contains"), [])
        expected_not_contains = safe_list(test.get("expected_output_not_contains"), [])
        min_len = test.get("min_length", 20)
        if min_len is None:
            min_len = 20
        
        write_log(f"TEST {test_id} ({idx+1}/{total}): {gate_line}")
        
        print(f"\n[{idx+1}/{total}] {test_id}: {gate_line}")
        print(f"   Вопрос: {test_input[:80]}...")
        print(f"   Ожидание ответа...")
        sys.stdout.flush()
        
        try:
            response = generate_response(
                prompt=test_input,
                history=[],
                gate_line=gate_line,
                gate_desc="Тестирование"
            )
        except Exception as e:
            error_msg = f"Ошибка: {e}"
            print(f"   [ERR] {error_msg}")
            write_log(f"TEST {test_id} ERROR: {e}")
            results.append({"id": test_id, "passed": False, "error": str(e)})
            continue
        
        if response is None:
            response = "[Нет ответа]"
        
        print(f"   Ответ: {response[:120]}...")
        write_log(f"TEST {test_id} получен ответ ({len(response)} символов)")
        
        passed = True
        checks = []
        
        for expected in expected_contains:
            expected_str = safe_str(expected)
            if expected_str.lower() in response.lower():
                checks.append(f"[OK] Найдено: {expected_str}")
            else:
                checks.append(f"[FAIL] Не найдено: {expected_str}")
                passed = False
        
        for forbidden in expected_not_contains:
            forbidden_str = safe_str(forbidden)
            if forbidden_str.lower() in response.lower():
                checks.append(f"[FAIL] Найдено запрещённое: {forbidden_str}")
                passed = False
            else:
                checks.append(f"[OK] Нет запрещённого: {forbidden_str}")
        
        if len(response) >= min_len:
            checks.append(f"[OK] Длина: {len(response)} >= {min_len}")
        else:
            checks.append(f"[FAIL] Длина: {len(response)} < {min_len}")
            passed = False
        
        if passed:
            success_count += 1
            write_log(f"TEST {test_id} ПРОЙДЕН")
        else:
            write_log(f"TEST {test_id} НЕ ПРОЙДЕН")
        
        results.append({
            "id": test_id,
            "passed": passed,
            "checks": checks
        })
    
    success_rate = (success_count / total) * 100 if total > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТЫ BENCHMARK")
    print(f"   Всего тестов: {total}")
    print(f"   Успешно: {success_count}")
    print(f"   Success Rate: {success_rate:.1f}%")
    print("=" * 60)
    
    write_log(f"ИТОГ: {success_count}/{total} успешно ({success_rate:.1f}%)")
    
    results_path = Path(__file__).parent.parent / "benchmark_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "success_rate": success_rate,
            "total": total,
            "passed": success_count,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nРезультаты сохранены в {results_path}")
    write_log(f"Результаты сохранены в {results_path}")

if __name__ == "__main__":
    run_benchmark()