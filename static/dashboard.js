// static/dashboard.js

async function runTests() {
    const btn = document.getElementById('test-btn');
    const resultDiv = document.getElementById('test-result');
    
    btn.disabled = true;
    btn.textContent = '⏳ Запуск...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<pre>⏳ Выполняется...</pre>';
    
    try {
        const resp = await fetch('/api/run_tests', { method: 'POST' });
        const data = await resp.json();
        
        if (data.output) {
            // Экранируем HTML-символы для безопасного отображения
            const escaped = data.output
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            resultDiv.innerHTML = `<pre>${escaped}</pre>`;
        } else if (data.error) {
            resultDiv.innerHTML = `<pre style="color: #f44336;">❌ ${data.error}</pre>`;
        } else {
            resultDiv.innerHTML = '<pre>⚠️ Нет данных</pre>';
        }
    } catch (e) {
        resultDiv.innerHTML = `<pre style="color: #f44336;">❌ Ошибка: ${e.message}</pre>`;
    }
    
    btn.disabled = false;
    btn.textContent = '▶ Запустить тесты';
}

async function runBenchmark() {
    const btn = document.getElementById('bench-btn');
    const resultDiv = document.getElementById('bench-result');
    
    btn.disabled = true;
    btn.textContent = '⏳ Запуск...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<pre>⏳ Выполняется...</pre>';
    
    try {
        const resp = await fetch('/api/run_benchmark', { method: 'POST' });
        const data = await resp.json();
        
        if (data.output) {
            const escaped = data.output
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            resultDiv.innerHTML = `<pre>${escaped}</pre>`;
        } else if (data.error) {
            resultDiv.innerHTML = `<pre style="color: #f44336;">❌ ${data.error}</pre>`;
        } else {
            resultDiv.innerHTML = '<pre>⚠️ Нет данных</pre>';
        }
    } catch (e) {
        resultDiv.innerHTML = `<pre style="color: #f44336;">❌ Ошибка: ${e.message}</pre>`;
    }
    
    btn.disabled = false;
    btn.textContent = '▶ Запустить Benchmark';
}

async function loadModelLogs() {
    const container = document.getElementById('log-container');
    try {
        const resp = await fetch('/api/logs?log_type=model');
        const data = await resp.json();
        if (data.logs && data.logs.length > 0) {
            container.innerHTML = data.logs.map(log => 
                `<div class="log-entry"><span class="timestamp">${log.timestamp}</span> ${log.message}</div>`
            ).join('');
        } else {
            container.innerHTML = '<div class="log-entry">📭 Логов модели пока нет</div>';
        }
    } catch (e) {
        container.innerHTML = `<div class="log-entry" style="color: #f44336;">❌ Ошибка: ${e.message}</div>`;
    }
}

async function loadLogs() {
    const container = document.getElementById('log-container');
    
    try {
        const resp = await fetch('/api/logs');
        const data = await resp.json();
        
        if (data.error) {
            container.innerHTML = `<div class="log-entry" style="color: #f44336;">❌ ${data.error}</div>`;
            return;
        }
        
        if (!data.logs || data.logs.length === 0) {
            container.innerHTML = '<div class="log-entry">📭 Логов пока нет</div>';
            return;
        }
        
        container.innerHTML = data.logs.map(log => {
            const timestamp = log.timestamp || '';
            const message = log.message || '';
            return `<div class="log-entry"><span class="timestamp">${timestamp}</span> ${message}</div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div class="log-entry" style="color: #f44336;">❌ Ошибка загрузки логов: ${e.message}</div>`;
    }
}

// Автоматическая загрузка логов при открытии
document.addEventListener('DOMContentLoaded', function() {
    loadLogs();
    // Обновление логов каждые 5 секунд
    setInterval(loadLogs, 5000);
});