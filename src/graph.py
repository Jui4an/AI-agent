from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

# Импортируем сами инструменты
from tools import get_numbers_from_db, get_descriptions_for_numbers, validate_numbers

class AgentState(TypedDict):
    messages: list
    numbers_str: str
    descriptions: str
    validation_result: str
    error: str

def get_numbers_node(state: AgentState) -> AgentState:
    # Вызываем инструмент напрямую
    result = get_numbers_from_db.invoke({})
    state['messages'].append(AIMessage(content=result))
    if "Найдены числа:" in result:
        numbers_part = result.split("Найдены числа:")[1].strip()
        state['numbers_str'] = numbers_part
    else:
        state['error'] = result
        state['numbers_str'] = ""
    return state

def get_descriptions_node(state: AgentState) -> AgentState:
    if not state['numbers_str']:
        state['error'] = "Нет чисел для получения описаний."
        return state
    result = get_descriptions_for_numbers.invoke({"pairs_str": state['numbers_str']})
    state['messages'].append(AIMessage(content=result))
    state['descriptions'] = result
    return state

def validate_node(state: AgentState) -> AgentState:
    if not state['numbers_str']:
        state['error'] = "Нет чисел для валидации."
        return state
    result = validate_numbers.invoke({"pairs_str": state['numbers_str']})
    state['messages'].append(AIMessage(content=result))
    state['validation_result'] = result
    return state

def error_node(state: AgentState) -> AgentState:
    state['messages'].append(AIMessage(content=f"Ошибка: {state.get('error', 'Неизвестная ошибка')}"))
    return state

def final_node(state: AgentState) -> AgentState:
    summary = f"""Результат работы агента:

Числа: {state['numbers_str']}

Валидация: {state['validation_result']}

Описания:
{state['descriptions']}
"""
    state['messages'].append(AIMessage(content=summary))
    return state

def check_numbers_ok(state: AgentState) -> Literal["get_descriptions", "error"]:
    if state.get('error') or not state['numbers_str']:
        return "error"
    return "get_descriptions"

def check_validation_ok(state: AgentState) -> Literal["final", "error"]:
    if state.get('error'):
        return "error"
    if "корректны" in state.get('validation_result', ''):
        return "final"
    else:
        return "final"

builder = StateGraph(AgentState)

builder.add_node("get_numbers", get_numbers_node)
builder.add_node("get_descriptions", get_descriptions_node)
builder.add_node("validate", validate_node)
builder.add_node("error", error_node)
builder.add_node("final", final_node)

builder.set_entry_point("get_numbers")

builder.add_conditional_edges(
    "get_numbers",
    check_numbers_ok,
    {
        "get_descriptions": "get_descriptions",
        "error": "error"
    }
)
builder.add_edge("get_descriptions", "validate")
builder.add_conditional_edges(
    "validate",
    check_validation_ok,
    {
        "final": "final",
        "error": "error"
    }
)
builder.add_edge("final", END)
builder.add_edge("error", END)

graph = builder.compile()