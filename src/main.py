# src/main.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from graph import graph, AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Импортируем настройки
from settings_manager import get_model_url, get_model_name, get_big_model_name

def call_model(base_url: str, model_name: str, prompt: str) -> str:
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
        return f"Ошибка вызова модели: {e}"

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
        # 1. Первая модель (маленькая) – генерирует черновик
        prompt_first = f"""На основе следующих описаний для 13 чисел, дайте краткий сводный ответ.
Числа и их описания:
{final_state['descriptions']}

Сформулируйте итоговый вывод."""
        print("\n=== Вызов первой модели ===")
        first_answer = call_model(get_model_url(), get_model_name(), prompt_first)
        print("Ответ первой модели:\n", first_answer)
        
        # 2. Вторая модель (большая) – обсуждает ответ
        prompt_second = f"""Вы — критик. Оцените следующий ответ...
        # ... остальной код без изменений
        """
        print("\n=== Вызов второй модели для обсуждения ===")
        second_answer = call_model(get_model_url(), get_big_model_name(), prompt_second)
        print("Ответ второй модели:\n", second_answer)
    else:
        print("\n=== Ошибка: нет описаний ===")

if __name__ == "__main__":
    run_agent()