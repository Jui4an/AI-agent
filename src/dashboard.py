# src/dashboard.py
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

from .settings_manager import get_model_url, get_model_name, get_big_model_name

dashboard_app = FastAPI(prefix="/dashboard", tags=["dashboard"])

@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI Agent Dashboard</title>
        <link rel="stylesheet" href="/static/style.css">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <div class="header">
            <h1>🧠 AI Agent Dashboard</h1>
            <span class="status-badge">🟢 Online</span>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="label">Маленькая модель</div>
                <div class="value">{get_model_name()}</div>
            </div>
            <div class="stat-item">
                <div class="label">Большая модель</div>
                <div class="value">{get_big_model_name()}</div>
            </div>
            <div class="stat-item">
                <div class="label">URL</div>
                <div class="value" style="font-size:14px;">{get_model_url()}</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>💬 Агент</h3>
                <p>Выберите транзит на главной странице и начните диалог</p>
                <a href="/" class="btn btn-primary">На главную</a>
            </div>

            <div class="card">
                <h3>🧪 Тесты</h3>
                <p>Запустить тесты (pytest) и посмотреть результаты</p>
                <button onclick="runTests()" class="btn btn-success" id="test-btn">▶ Запустить тесты</button>
                <div id="test-result" class="result-box" style="display:none;"></div>
            </div>

            <div class="card">
                <h3>📊 Benchmark</h3>
                <p>Оценить качество ответов агента на тестовых запросах</p>
                <button onclick="runBenchmark()" class="btn btn-warning" id="bench-btn">▶ Запустить Benchmark</button>
                <div id="bench-result" class="result-box" style="display:none;"></div>
            </div>

            <div class="card">
                <h3>📋 Логи</h3>
                <p>Просмотр логов работы агента в реальном времени</p>
                <button onclick="loadLogs()" class="btn btn-primary">Обновить логи</button>
                <div class="log-container" id="log-container">Загрузка...</div>
            </div>

            <div class="card">
                <h3>🔍 Observability</h3>
                <p>Трейсы и метрики в LangFuse</p>
                <a href="https://cloud.langfuse.com" target="_blank" class="btn btn-primary">Открыть LangFuse</a>
            </div>

            <div class="card">
                <h3>⚙️ Настройки</h3>
                <p>Управление моделями и конфигурацией</p>
                <a href="/settings" class="btn btn-primary">Настройки</a>
            </div>
        </div>

        <script src="/static/dashboard.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)