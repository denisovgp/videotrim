#!/usr/bin/env python3
"""
Веб-интерфейс для конвертации видео в MP3 с транскрипцией.
Запуск: python3 video_to_mp3_web.py
Откройте браузер: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import sys
import threading
from pathlib import Path
from werkzeug.utils import secure_filename

# Импортируем функции из основного модуля
try:
    from video_to_mp3 import (
        find_ffmpeg,
        convert_video_to_mp3,
        transcribe_audio_with_timestamps
    )
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    sys.exit(1)

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB максимум
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>VideoTrim - Конвертер видео в MP3</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        input[type="file"] {
            width: 100%;
            padding: 10px;
            border: 2px dashed #ddd;
            border-radius: 8px;
            background: #f9f9f9;
            cursor: pointer;
        }
        select, .checkbox-group {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            border: none;
            padding: 0;
        }
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .progress {
            margin-top: 20px;
            display: none;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
        }
        .log {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            display: none;
            margin-top: 10px;
        }
        .status {
            margin-top: 15px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .download-links {
            margin-top: 20px;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 8px;
            display: none;
        }
        .download-link {
            display: block;
            margin: 10px 0;
            padding: 12px;
            background: white;
            border: 2px solid #667eea;
            border-radius: 8px;
            text-decoration: none;
            color: #667eea;
            font-weight: 600;
            transition: all 0.2s;
        }
        .download-link:hover {
            background: #667eea;
            color: white;
        }
        .download-link::before {
            content: "⬇️ ";
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 VideoTrim</h1>
        <p class="subtitle">Конвертация видео в MP3 с автоматической транскрипцией</p>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="videoFile">Выберите видео файл:</label>
                <input type="file" id="videoFile" name="video" accept="video/*" required>
            </div>
            
            <div class="form-group">
                <label for="bitrate">Битрейт MP3:</label>
                <select id="bitrate" name="bitrate">
                    <option value="64k">64k</option>
                    <option value="96k">96k</option>
                    <option value="128k" selected>128k</option>
                    <option value="192k">192k</option>
                    <option value="256k">256k</option>
                    <option value="320k">320k</option>
                </select>
            </div>
            
            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="transcribe" name="transcribe" checked>
                    <label for="transcribe" style="margin: 0;">Выполнить транскрипцию через OpenRouter API</label>
                </div>
            </div>
            
            <button type="submit" id="submitBtn">Начать обработку</button>
        </form>
        
        <div class="progress" id="progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="log" id="log"></div>
        </div>
        
        <div class="status" id="status"></div>
        
        <div class="download-links" id="downloadLinks">
            <h3 style="margin-bottom: 15px; color: #333;">Скачать результаты:</h3>
            <a href="#" id="mp3Link" class="download-link" target="_blank">MP3 файл</a>
            <a href="#" id="jsonLink" class="download-link" target="_blank">JSON с транскрипцией</a>
        </div>
    </div>
    
    <script>
        // VideoTrim JavaScript
        (function() {
            'use strict';
            
            // Ждем загрузки DOM
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', init);
            } else {
                init();
            }
            
            function init() {
        const form = document.getElementById('uploadForm');
        const progress = document.getElementById('progress');
        const progressFill = document.getElementById('progressFill');
        const log = document.getElementById('log');
        const status = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');
        
        if (!form) {
            console.error('Form element not found');
            return;
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const videoFile = document.getElementById('videoFile').files[0];
            if (!videoFile) {
                alert('Пожалуйста, выберите видео файл');
                return;
            }
            
            // Проверка размера файла (500MB максимум)
            const maxSize = 500 * 1024 * 1024; // 500MB
            if (videoFile.size > maxSize) {
                const sizeMB = (videoFile.size / 1024 / 1024).toFixed(1);
                alert('Файл слишком большой (' + sizeMB + 'MB). Максимальный размер: 500MB');
                return;
            }
            
            console.log('Начало обработки файла:', videoFile.name);
            
            const formData = new FormData(form);
            submitBtn.disabled = true;
            progress.style.display = 'block';
            log.style.display = 'block';
            status.style.display = 'none';
            document.getElementById('downloadLinks').style.display = 'none';
            document.getElementById('jsonLink').style.display = 'none';
            log.textContent = 'Начало обработки...\\n';
            progressFill.style.width = '10%';
            progressFill.textContent = '10%';
            
            try {
                console.log('Отправка запроса на сервер...');
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                console.log('Ответ получен, статус:', response.status);
                
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                function processLine(line) {
                    if (!line.trim()) return;
                    
                    // Обработка прогресса
                    if (line.startsWith('PROGRESS:')) {
                        const progressValue = line.replace('PROGRESS:', '').trim();
                        progressFill.style.width = progressValue + '%';
                        progressFill.textContent = progressValue + '%';
                    } else {
                        // Добавляем в лог все остальные строки
                        log.textContent += line + '\\n';
                        log.scrollTop = log.scrollHeight;
                    }
                    
                    if (line.includes('✓ Обработка завершена успешно!')) {
                        progressFill.style.width = '100%';
                        progressFill.textContent = '100%';
                        status.className = 'status success';
                        status.textContent = 'Обработка завершена успешно!';
                        status.style.display = 'block';
                    } else if (line.includes('⚠ Обработка завершена с предупреждениями')) {
                        progressFill.style.width = '100%';
                        progressFill.textContent = '100%';
                        status.className = 'status error';
                        status.textContent = 'Обработка завершена с предупреждениями. Проверьте логи.';
                        status.style.display = 'block';
                    } else if (line.startsWith('OUTPUT_DIR:')) {
                        document.getElementById('downloadLinks').style.display = 'block';
                    } else if (line.startsWith('MP3_FILE:')) {
                        const mp3Path = line.replace('MP3_FILE:', '').trim();
                        document.getElementById('mp3Link').href = '/download?file=' + encodeURIComponent(mp3Path);
                    } else if (line.startsWith('JSON_FILE:')) {
                        const jsonPath = line.replace('JSON_FILE:', '').trim();
                        document.getElementById('jsonLink').href = '/download?file=' + encodeURIComponent(jsonPath);
                        document.getElementById('jsonLink').style.display = 'block';
                    } else if (line.startsWith('✗') || (line.includes('✗') && line.includes('Ошибка'))) {
                        status.className = 'status error';
                        status.textContent = line.replace('✗', '').trim();
                        status.style.display = 'block';
                        // При ошибке останавливаем прогресс
                        if (line.includes('Ошибка') && !line.includes('транскрипция не удалась')) {
                            progressFill.style.width = '0%';
                            progressFill.textContent = 'Ошибка';
                        }
                    }
                }
                
                let buffer = '';
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        // Обрабатываем оставшийся буфер
                        if (buffer) {
                            const lines = buffer.split('\\n');
                            for (const line of lines) {
                                processLine(line);
                            }
                        }
                        break;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || ''; // Сохраняем неполную строку
                    
                    for (const line of lines) {
                        processLine(line);
                    }
                }
            } catch (error) {
                console.error('Ошибка:', error);
                status.className = 'status error';
                status.textContent = 'Ошибка: ' + error.message;
                status.style.display = 'block';
                progressFill.style.width = '0%';
                progressFill.textContent = '0%';
            } finally {
                submitBtn.disabled = false;
            }
        });
            } // End of init function
        })(); // End of IIFE
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Главная страница."""
    response = app.response_class(
        render_template_string(HTML_TEMPLATE),
        mimetype='text/html; charset=utf-8'
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response


@app.route('/process', methods=['POST'])
def process_video():
    """Обрабатывает видео файл."""
    # Сохраняем данные из request ДО создания генератора
    # Проверка файла
    if 'video' not in request.files:
        return app.response_class(
            "✗ Ошибка: файл не загружен\n",
            mimetype='text/plain'
        )
    
    file = request.files['video']
    if file.filename == '':
        return app.response_class(
            "✗ Ошибка: файл не выбран\n",
            mimetype='text/plain'
        )
    
    # Сохраняем файл
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Настройки из формы
    bitrate = request.form.get('bitrate', '128k')
    transcribe = request.form.get('transcribe') == 'on'
    
    def generate():
        try:
            yield f"✓ Файл загружен: {filename}\n"
            
            # Проверка ffmpeg
            ffmpeg_path = find_ffmpeg()
            if not ffmpeg_path:
                yield "✗ Ошибка: ffmpeg не найден в системе\n"
                return
            
            yield f"✓ ffmpeg найден\n"
            
            # Создаем выходную директорию
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(app.config['OUTPUT_FOLDER'], timestamp)
            os.makedirs(output_dir, exist_ok=True)
            
            yield "=" * 50 + "\n"
            yield "Начало обработки\n"
            yield "=" * 50 + "\n"
            
            # Конвертация в MP3
            yield "\nКонвертация видео в MP3...\n"
            yield "PROGRESS:30\n"
            mp3_path = None
            try:
                # Перехватываем SystemExit, который может быть вызван sys.exit()
                try:
                    mp3_path = convert_video_to_mp3(filepath, output_dir, bitrate, ffmpeg_path)
                except SystemExit:
                    # sys.exit() выбрасывает SystemExit, перехватываем его
                    yield "✗ Ошибка при конвертации: процесс завершился с ошибкой\n"
                    return
                
                if not mp3_path or not os.path.exists(mp3_path):
                    yield "✗ Ошибка: не удалось создать MP3 файл\n"
                    return
                mp3_filename = os.path.basename(mp3_path)
                yield f"✓ MP3 файл создан: {mp3_filename}\n"
                yield "PROGRESS:50\n"
            except Exception as convert_error:
                yield f"✗ Ошибка при конвертации: {str(convert_error)}\n"
                return
            
            json_path = None
            success = True
            # Транскрипция
            if transcribe:
                yield "\n" + "=" * 50 + "\n"
                yield "Начало транскрипции...\n"
                yield "PROGRESS:60\n"
                try:
                    json_path = transcribe_audio_with_timestamps(
                        mp3_path, output_dir, ffmpeg_path=ffmpeg_path
                    )
                    if json_path:
                        json_filename = os.path.basename(json_path)
                        yield f"✓ Транскрипция завершена: {json_filename}\n"
                        yield "PROGRESS:90\n"
                    else:
                        yield "✗ Ошибка: транскрипция не удалась. Проверьте API ключ и логи.\n"
                        yield "PROGRESS:90\n"
                        success = False
                except Exception as transcribe_error:
                    yield f"✗ Ошибка при транскрипции: {str(transcribe_error)}\n"
                    yield "PROGRESS:90\n"
                    success = False
            
            # Выводим финальное сообщение только если все прошло успешно
            if success:
                yield "\n" + "=" * 50 + "\n"
                yield "✓ Обработка завершена успешно!\n"
                yield f"OUTPUT_DIR:{output_dir}\n"
                yield f"MP3_FILE:{mp3_path}\n"
                if json_path:
                    yield f"JSON_FILE:{json_path}\n"
                yield "PROGRESS:100\n"
                yield "=" * 50 + "\n"
            else:
                yield "\n" + "=" * 50 + "\n"
                yield "⚠ Обработка завершена с предупреждениями\n"
                yield f"OUTPUT_DIR:{output_dir}\n"
                yield f"MP3_FILE:{mp3_path}\n"
                yield "PROGRESS:100\n"
                yield "=" * 50 + "\n"
            
        except Exception as e:
            yield f"✗ Ошибка: {str(e)}\n"
    
    return app.response_class(generate(), mimetype='text/plain')


@app.route('/download')
def download_file():
    """Скачивание файла."""
    file_path = request.args.get('file')
    if not file_path:
        return "Ошибка: файл не указан", 400
    
    # Проверка безопасности - защита от path traversal
    # Убираем любые попытки выйти за пределы разрешенных директорий
    file_path = os.path.normpath(file_path)
    
    # Проверка существования файла
    if not os.path.exists(file_path):
        return "Файл не найден", 404
    
    # Проверяем, что файл находится в разрешенной директории
    abs_path = os.path.abspath(file_path)
    output_abs = os.path.abspath(app.config['OUTPUT_FOLDER'])
    upload_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
    
    # Проверяем, что путь действительно находится внутри разрешенных директорий
    # Используем os.path.commonpath для более надежной проверки
    try:
        if not (os.path.commonpath([abs_path, output_abs]) == output_abs or 
                os.path.commonpath([abs_path, upload_abs]) == upload_abs):
            return "Доступ запрещен", 403
    except ValueError:
        # Если пути на разных дисках (Windows), commonpath вызовет ValueError
        # В этом случае проверяем через startswith
        if not (abs_path.startswith(output_abs) or abs_path.startswith(upload_abs)):
            return "Доступ запрещен", 403
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )


if __name__ == '__main__':
    import socket
    
    # Пытаемся найти свободный порт
    def find_free_port(start_port=5000, max_port=5010):
        for port in range(start_port, max_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        return None
    
    port = find_free_port()
    if not port:
        print("✗ Ошибка: не удалось найти свободный порт")
        sys.exit(1)
    
    print("=" * 50)
    print("VideoTrim Web Interface")
    print("=" * 50)
    print(f"\nОткройте в браузере: http://localhost:{port}")
    print("Для остановки нажмите Ctrl+C\n")
    try:
        app.run(host='127.0.0.1', port=port, debug=True, use_reloader=False)
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        sys.exit(1)

