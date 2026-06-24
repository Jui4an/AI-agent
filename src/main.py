import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from graph import graph, AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# ===== НАСТРОЙКИ ДВУХ МОДЕЛЕЙ ЧЕРЕЗ LM STUDIO =====
# Первая модель (маленькая) – запущена локально на этом же компьютере
FIRST_MODEL_URL = "http://10.164.224.226:1234/v1"        # если на этом же ПК
FIRST_MODEL_NAME = "qwen/qwen3-vl-8b"          # точное имя в LM Studio

# Вторая модель (большая) – на ноутбуке с 16 ГБ
SECOND_MODEL_URL = "http://10.164.224.226:1234/v1"   # замените на реальный IP
SECOND_MODEL_NAME = "eva-qwen2.5-14b-v0.2"           # или другая модель

def call_model(base_url: str, model_name: str, prompt: str) -> str:
    """Универсальная функция для вызова любой модели через LM Studio API."""
    try:
        llm = ChatOpenAI(
            base_url=base_url,
            api_key="not-needed",
            model=model_name,
            temperature=0.7,
            max_tokens=500,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Ошибка вызова модели ({base_url}): {e}"

def run_agent():
    initial_state = AgentState(
        messages=[],
        numbers_str="",
        descriptions="",
        validation_result="",
        error=""
    )
    
    print("Запуск агента...")
    final_state = graph.invoke(initial_state)
    
    print("\n=== Лог работы агента ===")
    for msg in final_state['messages']:
        print(msg.content)
    
    if final_state.get('descriptions') and not final_state.get('error'):
        # 1. Первая модель (маленькая) генерирует ответ
        prompt_first = f"""На основе следующих описаний для 13 чисел, дайте краткий сводный ответ.
Числа и их описания:
{final_state['descriptions']}

Сформулируйте итоговый вывод."""
        print("\n=== Вызов первой модели (локально, Qwen 0.5B) ===")
        first_answer = call_model(FIRST_MODEL_URL, FIRST_MODEL_NAME, prompt_first)
        print("Ответ первой модели:\n", first_answer)
        
        # 2. Вторая модель (на ноутбуке) обсуждает ответ первой
        prompt_second = f"""Вы — критик. Оцените следующий ответ, сгенерированный другой моделью на основе описаний чисел.
Опишите, что в ответе хорошо, что можно улучшить, и предложите свой улучшенный вариант ответа.

Исходные описания чисел:
{final_state['descriptions']}

Ответ первой модели:
{first_answer}

Ваша задача: дать конструктивную критику и предложить улучшенную версию."""
        print("\n=== Вызов второй модели (на ноутбуке) для обсуждения ===")
        second_answer = call_model(SECOND_MODEL_URL, SECOND_MODEL_NAME, prompt_second)
        print("Ответ второй модели (критика и улучшение):\n", second_answer)
    else:
        print("\n=== Ошибка: нет описаний ===")

if __name__ == "__main__":
    run_agent()