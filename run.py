# run.py
import subprocess
import threading
import time
import os
import sys

def run_fastapi():
    """Запускает основной FastAPI-сервер на порту 8001"""
    os.system("uvicorn src.app:app --host 0.0.0.0 --port 8001")

def run_mcp():
    """Запускает MCP-агент на порту 8002"""
    time.sleep(2)  # Даём FastAPI немного времени стартовать
    os.system("python src/mcp_agent.py")

if __name__ == "__main__":
    print("=" * 50)
    print(" Запуск Magnolia Agent")
    print("=" * 50)
    print("   FastAPI: http://localhost:8001")
    print("   MCP:     http://localhost:8002")
    print("=" * 50)
    print("Нажми Ctrl+C для остановки")
    print("=" * 50)
    
    # Запускаем в отдельных потоках
    thread1 = threading.Thread(target=run_fastapi, daemon=True)
    thread2 = threading.Thread(target=run_mcp, daemon=True)
    
    thread1.start()
    thread2.start()
    
    # Держим главный поток живым
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Остановка...")
        sys.exit(0)