import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from graph import graph, AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

LM_STUDIO_URL = "http://localhost:1234/v1"   # замените на IP и порт другого компьютера
USE_MOCK = True   # пока нет соединения, используем заглушку

def get_llm_response(prompt: str) -> str:
    if USE_MOCK:
        return f"Это заглушка. Ваш запрос: {prompt[:100]}..."
    else:
        try:
            llm = ChatOpenAI(
                base_url=LM_STUDIO_URL,
                api_key="not-needed",
                model="qwen-3.5",
                temperature=0.7,
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            return f"Ошибка подключения к LM Studio: {e}"

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
    
    print("\n=== Лог работы ===")
    for msg in final_state['messages']:
        print(msg.content)
    
    if final_state.get('descriptions') and not final_state.get('error'):
        prompt = f"""На основе следующих описаний для 13 чисел, дайте краткий сводный ответ.
Числа и их описания:
{final_state['descriptions']}

Сформулируйте итоговый вывод."""
        llm_answer = get_llm_response(prompt)
        print("\n=== Ответ модели ===")
        print(llm_answer)
    else:
        print("\n=== Ошибка: нет описаний ===")

if __name__ == "__main__":
    run_agent()