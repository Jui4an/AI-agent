import os
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

from .agent_wrapper import generate_response  

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

# ============ Главная страница (без шаблона) ============
@app.get("/", response_class=HTMLResponse)
async def index():
    today = datetime.now().strftime("%Y-%m-%d")
    post_content = get_post(today)
    if post_content is None:
        # Генерируем пост через агента
        prompt = f"Создайте пост для блога о транзитах Human Design на сегодня, {today}. Опишите основные энергии и дайте советы."
        post_content = generate_response(prompt)
        save_post(today, post_content)
    
    # Обёртка с подключением CSS
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

# ============ Страница чата (генерируем HTML вручную) ============
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
    
    # Формируем HTML для сообщений
    messages_html = ""
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        messages_html += f'<div class="message {role}"><strong>{role}:</strong> {content}</div>\n'
    
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

            window.onload = function() {{
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

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
    
    # Формируем промпт (без gate_line и desc – они уже в системном промпте)
    prompt = user_message  # просто сообщение пользователя
    
    # Вызываем модель с передачей gate_line и gate_desc
    response_text = generate_response(
        prompt=prompt,
        history=history,
        gate_line=gate_line,
        gate_desc=desc
    )
    
    add_message(session_id, "assistant", response_text)
    return JSONResponse({"response": response_text})

# ============ Админский эндпоинт для перегенерации поста ============
@app.post("/api/regenerate_post")
async def regenerate_post():
    today = datetime.now().strftime("%Y-%m-%d")
    content = generate_post_content(today)
    save_post(today, content)
    return JSONResponse({"status": "ok", "date": today})