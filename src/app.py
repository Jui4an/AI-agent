import os
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import uuid

from .post_generator import generate_post_content
from .db_posts import init_db, get_post, save_post
from .session_manager import create_session, get_session, add_message, sessions
from .rag import get_description_for_number
from .models import ChatRequest

# ===== НОВЫЕ ИМПОРТЫ ДЛЯ СОВЕТОВ =====
from .models import Tip
from .db_tips import get_tips, save_tip
from pydantic import ValidationError

# ===== ИМПОРТ ОБЁРТКИ ДЛЯ МОДЕЛЕЙ =====
from .agent_wrapper import generate_response, generate_summary

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

async def call_mcp_agent(gate_line: str, advice: str, dialog_summary: str, history: list) -> dict:
    """
    Отправляет сгенерированный совет в MCP-агент для оценки и обогащения.
    Возвращает словарь с полями:
        - should_save (bool)
        - enriched_advice (str)
        - reason (str)
        - score (int)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "http://localhost:8002/evaluate",
                json={
                    "gate_line": gate_line,
                    "advice": advice,
                    "dialog_summary": dialog_summary,
                    "history": history
                }
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            # Если MCP-агент не запущен, возвращаем "сохранять всегда" (fallback)
            return {
                "should_save": True,
                "enriched_advice": advice,
                "reason": "MCP-агент недоступен, совет сохранён по умолчанию.",
                "score": 70
            }
        except Exception as e:
            # Любая другая ошибка – тоже fallback
            return {
                "should_save": True,
                "enriched_advice": advice,
                "reason": f"Ошибка вызова MCP: {e}, совет сохранён по умолчанию.",
                "score": 50
            }

# ============ Главная страница ============
@app.get("/", response_class=HTMLResponse)
async def index():
    today = datetime.now().strftime("%Y-%m-%d")
    post_content = generate_post_content(today) 
    save_post(today, post_content)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Human Design – Транзиты</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <header>
            <h1>Как вы проживаете вот эти энергии?</h1>
            <p class="subtitle">Транзиты на {today}</p>
        </header>
        <main>
            {post_content}
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# ============ Страница чата ============
@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, gate: str):
    try:
        gate_num, line_num = map(int, gate.split('.'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный формат gate")
    
    desc, _ = get_description_for_number(gate_num, line_num)
    if not desc:
        raise HTTPException(status_code=404, detail="Описание не найдено")
    
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = create_session(gate)
        add_message(session_id, "assistant", f"Как вы проживаете энергию {gate}? Расскажите.")
    
    history = sessions[session_id]["history"]
    
    messages_html = ""
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        messages_html += f'<div class="message {role}"><strong>{role}:</strong> {content}</div>\n'
    
    # ===== ДОБАВЛЯЕМ КНОПКУ И БЛОК ДЛЯ СОВЕТА =====
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Диалог о {gate}</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h2>Тема: {gate}</h2>
                <p class="essence">{desc}</p>
                <a href="/">← На главную</a>
            </div>
            <div class="chat-messages" id="messages">
                {messages_html}
            </div>
            <div class="chat-input">
                <textarea id="user-input" placeholder="Напишите свой ответ..."></textarea>
                <button onclick="sendMessage()">Отправить</button>
            </div>
            <!-- НОВЫЙ БЛОК: завершение диалога -->
            <div class="finish-section" style="margin-top: 30px; text-align: center;">
                <button id="finish-btn" onclick="finishChat()" style="
                    background: linear-gradient(135deg, #6c8cff, #4a6cf7);
                    color: white;
                    border: none;
                    padding: 16px 40px;
                    border-radius: 50px;
                    font-size: 1.3rem;
                    font-weight: bold;
                    cursor: pointer;
                    box-shadow: 0 6px 20px rgba(108, 140, 255, 0.4);
                    transition: all 0.3s ease;
                    letter-spacing: 0.5px;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    💡 Получить совет
                </button>
                <div id="summary-block" style="display:none; margin-top: 25px; padding: 20px; background: #f0f4ff; border-radius: 16px; border-left: 6px solid #6c8cff; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <h3 style="margin:0 0 10px 0; color: #2c3e50;">✨ Ваш лайфхак-совет на сегодня:</h3>
                    <p id="summary-text" style="font-size: 1.15rem; line-height: 1.6; color: #1a2a3a;"></p>
                </div>
            </div>
        </div>
        <script>
            const sessionId = "{session_id}";
            const messagesContainer = document.getElementById('messages');
            const userInput = document.getElementById('user-input');

            async function sendMessage() {{
                const text = userInput.value.trim();
                if (!text) return;
                const userDiv = document.createElement('div');
                userDiv.className = 'message user';
                userDiv.innerHTML = `<strong>Вы:</strong> ${{text}}`;
                messagesContainer.appendChild(userDiv);
                userInput.value = '';
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ session_id: sessionId, message: text }})
                }});
                const data = await response.json();
                if (data.response) {{
                    const botDiv = document.createElement('div');
                    botDiv.className = 'message assistant';
                    botDiv.innerHTML = `<strong>Агент:</strong> ${{data.response}}`;
                    messagesContainer.appendChild(botDiv);
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }}
            }}

            userInput.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter' && !e.shiftKey) {{
                    e.preventDefault();
                    sendMessage();
                }}
            }});

            // ===== НОВАЯ ФУНКЦИЯ ДЛЯ ЗАВЕРШЕНИЯ ДИАЛОГА =====
            async function finishChat() {{
                const btn = document.getElementById('finish-btn');
                btn.disabled = true;
                btn.innerText = 'Генерация совета...';
                
                try {{
                    const response = await fetch('/api/finish_chat', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ session_id: sessionId }})
                    }});
                    const data = await response.json();
                    if (data.summary) {{
                        document.getElementById('summary-text').innerText = data.summary;
                        document.getElementById('summary-block').style.display = 'block';
                        btn.innerText = '✅ Совет получен';
                    }} else {{
                        alert('Ошибка: ' + (data.error || 'неизвестная ошибка'));
                        btn.disabled = false;
                        btn.innerText = 'Завершить диалог и получить совет';
                    }}
                }} catch (e) {{
                    alert('Ошибка сети: ' + e.message);
                    btn.disabled = false;
                    btn.innerText = 'Завершить диалог и получить совет';
                }}
            }}

            window.onload = function() {{
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/tips")
async def get_all_tips(gate: str = None, date: str = None):
    """Возвращает все сохранённые советы, можно фильтровать по gate или date."""
    tips = get_tips(gate_line=gate, date=date)
    return JSONResponse(tips)

# ============ API для отправки сообщений ============
@app.post("/api/chat")
async def chat_api(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    user_message = data.get("message")
    if not session_id or not user_message:
        return JSONResponse({"error": "Не хватает данных"}, status_code=400)
    
    session = get_session(session_id)
    if not session:
        return JSONResponse({"error": "Сессия не найдена"}, status_code=404)
    
    gate_line = session.get("gate_line")
    try:
        a, b = map(int, gate_line.split('.'))
        desc, _ = get_description_for_number(a, b)
    except:
        desc = "неизвестная энергия"
    
    add_message(session_id, "user", user_message)
    history = session["history"]
    
    # Используем агента для генерации ответа
    prompt = user_message
    response_text = generate_response(
        prompt=prompt,
        history=history,
        gate_line=gate_line,
        gate_desc=desc
    )
    
    add_message(session_id, "assistant", response_text)
    return JSONResponse({"response": response_text})

# ============ НОВЫЙ ЭНДПОИНТ: завершение чата и сохранение совета ============
@app.post("/api/finish_chat")
async def finish_chat(request: Request):
    try:
        data = await request.json()
        session_id = data.get("session_id")
        if not session_id:
            return JSONResponse({"error": "Не указан session_id"}, status_code=400)
        
        session = get_session(session_id)
        if not session:
            return JSONResponse({"error": "Сессия не найдена"}, status_code=404)
        
        gate_line = session.get("gate_line")
        try:
            a, b = map(int, gate_line.split('.'))
            desc, _ = get_description_for_number(a, b)
        except:
            desc = "неизвестная энергия"
        
        history = session.get("history", [])
        if len(history) < 2:
            return JSONResponse({"error": "Диалог слишком короткий для совета"}, status_code=400)
        
        # Генерация совета
        try:
            summary = generate_summary(history, gate_line, desc)
        except Exception as e:
            return JSONResponse({"error": f"Ошибка генерации совета: {str(e)}"}, status_code=500)
        
        # Вызов MCP-агента (с fallback)
        try:
            mcp_result = await call_mcp_agent(gate_line, summary, "", history)
        except Exception as e:
            # Если MCP не работает, сохраняем как есть
            mcp_result = {
                "should_save": True,
                "enriched_advice": summary,
                "reason": "MCP-агент недоступен, совет сохранён по умолчанию.",
                "score": 70
            }
        
        # Обработка результата MCP
        if mcp_result["should_save"]:
            final_advice = mcp_result["enriched_advice"]
            # Валидация и сохранение через Pydantic
            try:
                tip = Tip(
                    gate_line=gate_line,
                    advice=final_advice,
                    dialog_summary="",   # можно добавить краткое содержание диалога
                    date=datetime.now().strftime("%Y-%m-%d")
                )
                tip_id = save_tip(tip.gate_line, tip.advice, tip.dialog_summary, tip.date)
                save_result = f"Совет сохранён с ID {tip_id} (оценка: {mcp_result['score']})"
            except ValidationError as e:
                save_result = f"Ошибка валидации: {e}"
                final_advice = summary  # на случай ошибки показываем исходный совет
            except Exception as e:
                save_result = f"Ошибка сохранения: {e}"
                final_advice = summary
        else:
            final_advice = summary
            save_result = f"Совет не сохранён: {mcp_result['reason']}"
        
        # Сохраняем в сессии
        session["summary"] = final_advice
        session["save_result"] = save_result
        
        return JSONResponse({"summary": final_advice, "save_result": save_result})
    
    except Exception as e:
        return JSONResponse({"error": f"Внутренняя ошибка: {str(e)}"}, status_code=500)

# ============ Админский эндпоинт для перегенерации поста ============
@app.post("/api/regenerate_post")
async def regenerate_post():
    today = datetime.now().strftime("%Y-%m-%d")
    content = generate_post_content(today)
    save_post(today, content)
    return JSONResponse({"status": "ok", "date": today})