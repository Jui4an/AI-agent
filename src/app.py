import os
import httpx
import subprocess
import asyncio
import uuid

from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pydantic import ValidationError

from .post_generator import generate_post_content
from .db_posts import init_db, get_post, save_post
from .session_manager import create_session, get_session, add_message, sessions
from .rag import get_description_for_number
from .models import ChatRequest, Tip
from .settings_manager import load_settings, save_settings, get_model_url, get_model_name, get_big_model_name
from .db_tips import get_tips, save_tip
from .agent_wrapper import generate_response, generate_summary
from .dashboard import dashboard_app

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dashboard", dashboard_app)

init_db()

def write_log(message: str):
    """Записывает сообщение в лог-файл."""
    log_path = Path(__file__).parent.parent / "logs" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")  # Также выводим в консоль

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
    post_content = get_post(today)
    if post_content is None:
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
            <p>
                <a href="/dashboard" style="color: #6c8cff; text-decoration: none; margin-right: 15px;">📊 Dashboard</a>
                <a href="/settings" style="color: #6c8cff; text-decoration: none;">⚙️ Настройки</a>
            </p>
        </header>
        <main>
            {post_content}
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# ============ API для проверки моделей ============
@app.get("/api/check_models")
async def check_models():
    """Проверяет доступность LM Studio/Ollama и возвращает список моделей."""
    settings = load_settings()
    url = settings.get("model_url", "").rstrip('/')
    if not url:
        return JSONResponse({"error": "URL модели не задан"}, status_code=400)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/models")
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("id", str(m)) for m in data.get("data", [])]
            return JSONResponse({
                "success": True,
                "url": url,
                "models": models,
                "count": len(models)
            })
    except httpx.ConnectError:
        return JSONResponse({"error": "Не удалось подключиться к серверу"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": f"Ошибка: {str(e)}"}, status_code=500)

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
                <p style="margin: 10px 0;">
                    <a href="/">← На главную</a>
                    <span style="margin: 0 10px; color: #ccc;">|</span>
                    <a href="/dashboard" style="color: #6c8cff; text-decoration: none;">📊 Dashboard</a>
                </p>
            </div>
            <div class="chat-messages" id="messages">
                {messages_html}
            </div>
            <div class="chat-input">
                <textarea id="user-input" placeholder="Напишите свой ответ..."></textarea>
                <button onclick="sendMessage()">Отправить</button>
            </div>
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

# ============ API для получения советов ============
@app.get("/api/tips")
async def get_all_tips(gate: str = None, date: str = None):
    """Возвращает все сохранённые советы, можно фильтровать по gate или date."""
    tips = get_tips(gate_line=gate, date=date)
    return JSONResponse(tips)

# ============ Страница настроек ============
@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    settings = load_settings()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Настройки моделей</title>
        <style>
            body {{ font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; }}
            label {{ display: block; margin: 15px 0 5px; font-weight: bold; }}
            input {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }}
            button {{ margin-top: 10px; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .btn-save {{ background: #6c8cff; color: white; }}
            .btn-check {{ background: #4CAF50; color: white; }}
            .nav {{ margin-bottom: 20px; }}
            #models-list {{ margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px; display: none; }}
            #models-list ul {{ margin: 5px 0; padding-left: 20px; }}
            #models-list code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="nav"><a href="/">← На главную</a></div>
        <h1>⚙️ Настройки моделей</h1>
        <form id="settings-form">
            <label>URL модели (LM Studio/Ollama):</label>
            <input type="text" id="model_url" value="{settings.get('model_url', '')}" placeholder="http://localhost:1234/v1">
            
            <label>Название маленькой модели:</label>
            <input type="text" id="model_name" value="{settings.get('model_name', '')}" placeholder="qwen/qwen3-vl-8b">
            
            <label>Название большой модели:</label>
            <input type="text" id="big_model_name" value="{settings.get('big_model_name', '')}" placeholder="qwen3.6-35b...">
            
            <div style="display: flex; gap: 10px; margin-top: 15px;">
                <button type="submit" class="btn-save">💾 Сохранить</button>
                <button type="button" class="btn-check" onclick="checkModels()">🔍 Проверить модели</button>
            </div>
        </form>
        <div id="models-list"></div>
        <div id="message" style="margin-top:15px; color:green;"></div>

        <script>
            async function checkModels() {{
                const container = document.getElementById('models-list');
                container.style.display = 'block';
                container.innerHTML = '⏳ Проверка подключения...';
                
                try {{
                    const resp = await fetch('/api/check_models');
                    const data = await resp.json();
                    if (data.error) {{
                        container.innerHTML = `<span style="color:red;">❌ ${{data.error}}</span>`;
                    }} else if (data.models && data.models.length > 0) {{
                        let html = `<strong>✅ Найдено ${{data.count}} моделей:</strong><ul>`;
                        data.models.forEach(m => {{
                            html += `<li><code>${{m}}</code></li>`;
                        }});
                        html += '</ul>';
                        html += `<p style="font-size:12px; color:#666; margin-top:5px;">URL: ${{data.url}}</p>`;
                        container.innerHTML = html;
                    }} else {{
                        container.innerHTML = '⚠️ Модели не найдены';
                    }}
                }} catch (e) {{
                    container.innerHTML = `<span style="color:red;">❌ Ошибка: ${{e.message}}</span>`;
                }}
            }}

            document.getElementById('settings-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const data = {{
                    model_url: document.getElementById('model_url').value,
                    model_name: document.getElementById('model_name').value,
                    big_model_name: document.getElementById('big_model_name').value
                }};
                const resp = await fetch('/api/settings', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                const result = await resp.json();
                document.getElementById('message').textContent = result.message || 'Сохранено!';
                setTimeout(() => document.getElementById('message').textContent = '', 3000);
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/api/settings")
async def save_settings_api(request: Request):
    data = await request.json()
    save_settings(data)
    return JSONResponse({"message": "Настройки сохранены"})

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
    
    prompt = user_message
    response_text = generate_response(
        prompt=prompt,
        history=history,
        gate_line=gate_line,
        gate_desc=desc
    )
    
    add_message(session_id, "assistant", response_text)
    return JSONResponse({"response": response_text})

# ============ Эндпоинт: завершение чата и сохранение совета ============
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
        
        try:
            summary = generate_summary(history, gate_line, desc)
        except Exception as e:
            return JSONResponse({"error": f"Ошибка генерации совета: {str(e)}"}, status_code=500)
        
        try:
            mcp_result = await call_mcp_agent(gate_line, summary, "", history)
        except Exception as e:
            mcp_result = {
                "should_save": True,
                "enriched_advice": summary,
                "reason": "MCP-агент недоступен, совет сохранён по умолчанию.",
                "score": 70
            }
        
        if mcp_result["should_save"]:
            final_advice = mcp_result["enriched_advice"]
            try:
                tip = Tip(
                    gate_line=gate_line,
                    advice=final_advice,
                    dialog_summary="",
                    date=datetime.now().strftime("%Y-%m-%d")
                )
                tip_id = save_tip(tip.gate_line, tip.advice, tip.dialog_summary, tip.date)
                save_result = f"Совет сохранён с ID {tip_id} (оценка: {mcp_result['score']})"
            except ValidationError as e:
                save_result = f"Ошибка валидации: {e}"
                final_advice = summary
            except Exception as e:
                save_result = f"Ошибка сохранения: {e}"
                final_advice = summary
        else:
            final_advice = summary
            save_result = f"Совет не сохранён: {mcp_result['reason']}"
        
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

# ============ API для запуска тестов ============
@app.post("/api/run_tests")
async def run_tests():
    write_log("Запуск тестов (pytest)...")
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        # Защита от None
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        write_log(f"Тесты завершены (код: {result.returncode})")
        return JSONResponse({"output": output})
    except Exception as e:
        write_log(f"Ошибка тестов: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============ API для запуска Benchmark ============
@app.post("/api/run_benchmark")
async def run_benchmark():
    write_log("Запуск Benchmark...")
    try:
        result = subprocess.run(
            ["python", "src/run_benchmark.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        # Защита от None
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        write_log(f"Benchmark завершён (код: {result.returncode})")
        return JSONResponse({"output": output})
    except Exception as e:
        write_log(f"Ошибка Benchmark: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============ API для просмотра логов ============
@app.get("/api/logs")
async def get_logs(log_type: str = "app"):
    """Возвращает последние 50 строк логов. log_type: 'app' или 'model'."""
    if log_type == "model":
        log_file = "model.log"
    else:
        log_file = "app.log"
    
    log_path = Path(__file__).parent.parent / "logs" / log_file
    if not log_path.exists():
        return JSONResponse({"logs": []})
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        last_lines = lines[-50:] if len(lines) > 50 else lines
        logs = [{"timestamp": "", "message": line.strip()} for line in last_lines]
        return JSONResponse({"logs": logs})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)