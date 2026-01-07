#!/usr/bin/env python3
"""
Скрипт для конвертации видео файла в сжатый MP3 файл и транскрипции через OpenRouter API.
Использование: python video_to_mp3.py <путь_к_видео> [bitrate] [--no-transcribe]
"""

import os
import sys
import subprocess
import json
import base64
import requests
import re
from datetime import datetime
from pathlib import Path

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv не установлен, используем только переменные окружения


def find_ffmpeg():
    """Находит путь к ffmpeg в системе."""
    # Стандартные пути для macOS с Homebrew
    possible_paths = [
        'ffmpeg',  # В PATH
        '/opt/homebrew/bin/ffmpeg',  # Homebrew на Apple Silicon
        '/usr/local/bin/ffmpeg',  # Homebrew на Intel Mac
        '/usr/bin/ffmpeg',  # Системный путь
    ]
    
    for path in possible_paths:
        try:
            subprocess.run([path, '-version'], 
                          capture_output=True, 
                          check=True)
            return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    return None


def check_ffmpeg():
    """Проверяет наличие ffmpeg в системе."""
    return find_ffmpeg() is not None


def convert_video_to_mp3(video_path, output_dir, bitrate='128k', ffmpeg_path='ffmpeg'):
    """
    Конвертирует видео файл в MP3.
    
    Args:
        video_path: Путь к входному видео файлу
        output_dir: Директория для сохранения результата
        bitrate: Битрейт для MP3 (по умолчанию 128k)
        ffmpeg_path: Путь к исполняемому файлу ffmpeg
    
    Returns:
        Путь к созданному MP3 файлу
    """
    # Создаем директорию если её нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Генерируем имя выходного файла
    video_name = Path(video_path).stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"{video_name}_{timestamp}.mp3")
    
    # Команда ffmpeg для конвертации
    cmd = [
        ffmpeg_path,
        '-i', video_path,           # Входной файл
        '-vn',                      # Отключить видео
        '-acodec', 'libmp3lame',    # Кодек MP3
        '-ab', bitrate,             # Битрейт
        '-ar', '44100',             # Частота дискретизации
        '-y',                       # Перезаписать если файл существует
        output_file
    ]
    
    print(f"Конвертация {video_path} в MP3...")
    print(f"Выходной файл: {output_file}")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Конвертация завершена успешно!")
        print(f"Файл сохранен: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"✗ Ошибка при конвертации: {e.stderr.decode()}")
        sys.exit(1)


def get_audio_duration(mp3_path, ffmpeg_path='ffmpeg'):
    """
    Получает длительность аудио файла в секундах.
    
    Args:
        mp3_path: Путь к MP3 файлу
        ffmpeg_path: Путь к ffmpeg
    
    Returns:
        Длительность в секундах (float) или None при ошибке
    """
    try:
        cmd = [
            ffmpeg_path,
            '-i', mp3_path,
            '-f', 'null',
            '-'
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Ищем длительность в stderr (ffmpeg выводит информацию в stderr)
        output = result.stderr
        for line in output.split('\n'):
            if 'Duration:' in line:
                time_str = line.split('Duration:')[1].split(',')[0].strip()
                parts = time_str.split(':')
                if len(parts) == 3:
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    return total_seconds
        return None
    except Exception as e:
        print(f"⚠ Предупреждение: не удалось определить длительность: {e}")
        return None


def split_audio_into_chunks(mp3_path, output_dir, chunk_duration=300, ffmpeg_path='ffmpeg'):
    """
    Разбивает аудио файл на части заданной длительности.
    
    Args:
        mp3_path: Путь к исходному MP3 файлу
        output_dir: Директория для сохранения частей
        chunk_duration: Длительность каждой части в секундах (по умолчанию 300 = 5 минут)
        ffmpeg_path: Путь к ffmpeg
    
    Returns:
        Список путей к созданным частям
    """
    base_name = Path(mp3_path).stem
    chunks_dir = os.path.join(output_dir, 'chunks')
    os.makedirs(chunks_dir, exist_ok=True)
    
    chunks = []
    start_time = 0
    chunk_index = 0
    
    print(f"Разбиение аудио на части по {chunk_duration} секунд...")
    
    while True:
        chunk_path = os.path.join(chunks_dir, f"{base_name}_chunk_{chunk_index:03d}.mp3")
        
        cmd = [
            ffmpeg_path,
            '-i', mp3_path,
            '-ss', str(start_time),
            '-t', str(chunk_duration),
            '-acodec', 'copy',
            '-y',
            chunk_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            # Проверяем, что файл создан и не пустой
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
                chunks.append(chunk_path)
                print(f"  Создана часть {chunk_index + 1}: {chunk_path}")
                chunk_index += 1
                start_time += chunk_duration
            else:
                # Достигли конца файла
                break
        except subprocess.CalledProcessError:
            # Достигли конца файла или ошибка
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
            break
    
    print(f"✓ Создано {len(chunks)} частей")
    return chunks


def generate_word_timestamps(text, duration, chunk_offset=0):
    """
    Генерирует приблизительные таймстемпы для слов на основе текста и длительности.
    
    Args:
        text: Текст транскрипции
        duration: Длительность аудио в секундах
        chunk_offset: Смещение времени в секундах
    
    Returns:
        Список словарей с таймстемпами для каждого слова
    """
    import re
    
    # Разбиваем текст на слова (убираем знаки препинания)
    words = re.findall(r'\b\w+\b', text.lower())
    
    if not words or duration <= 0:
        return []
    
    # Вычисляем среднюю длительность на слово
    time_per_word = duration / len(words)
    
    words_with_timestamps = []
    current_time = 0
    
    for word in words:
        # Приблизительная длительность слова (чем длиннее слово, тем больше времени)
        word_duration = max(0.2, min(0.8, len(word) * 0.1))
        
        words_with_timestamps.append({
            "word": word,
            "start": round(current_time + chunk_offset, 2),
            "end": round(current_time + word_duration + chunk_offset, 2)
        })
        
        current_time += time_per_word
    
    return words_with_timestamps


def transcribe_audio_chunk(chunk_path, chunk_offset, api_key, model='mistralai/voxtral-small-24b-2507'):
    """
    Транскрибирует одну часть аудио через OpenRouter API.
    
    Args:
        chunk_path: Путь к части аудио
        chunk_offset: Смещение времени в секундах (для корректных таймстемпов)
        api_key: API ключ OpenRouter
        model: Модель для транскрипции
    
    Returns:
        Словарь с транскрипцией или None при ошибке
    """
    # Проверяем размер файла (примерно 10MB лимит для безопасности)
    file_size = os.path.getsize(chunk_path)
    if file_size > 10 * 1024 * 1024:  # 10MB
        print(f"⚠ Предупреждение: часть слишком большая ({file_size / 1024 / 1024:.1f}MB), пропускаем")
        return None
    
    # Кодируем аудио файл в base64
    try:
        with open(chunk_path, 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
    except Exception as e:
        print(f"✗ Ошибка при чтении части: {e}")
        return None
    
    # Подготавливаем запрос к OpenRouter API
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/denisovgp/videotrim",
        "X-Title": "VideoTrim Transcription"
    }
    
    # Запрос транскрипции с таймстемпами
    prompt = """Транскрибируй этот аудио файл с точными таймстемпами для КАЖДОГО слова. 

КРИТИЧЕСКИ ВАЖНО: Верни результат ТОЛЬКО в формате JSON без каких-либо дополнительных комментариев, объяснений или текста до или после JSON.

Требуемая структура JSON:
{
  "text": "полный текст транскрипции",
  "words": [
    {
      "word": "первое",
      "start": 0.0,
      "end": 0.3
    },
    {
      "word": "слово",
      "start": 0.3,
      "end": 0.6
    }
  ]
}

ПРАВИЛА:
- "text" - полный текст транскрипции без таймстемпов
- "words" - массив объектов, ОДИН объект для КАЖДОГО слова
- "word" - само слово (без знаков препинания, если возможно)
- "start" - время начала слова в секундах (число с плавающей точкой)
- "end" - время конца слова в секундах (число с плавающей точкой)
- Время отсчитывается от начала этого аудио фрагмента
- Каждое слово ДОЛЖНО иметь таймстемпы
- Верни ТОЛЬКО валидный JSON, ничего больше"""
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": "mp3"
                        }
                    }
                ]
            }
        ],
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        
        # Извлекаем транскрипцию из ответа
        if 'choices' in result and len(result['choices']) > 0:
            transcription_text = result['choices'][0]['message']['content']
            
            # Пытаемся распарсить JSON из ответа
            try:
                # Удаляем markdown код блоки если есть
                if '```json' in transcription_text:
                    transcription_text = transcription_text.split('```json')[1].split('```')[0].strip()
                elif '```' in transcription_text:
                    transcription_text = transcription_text.split('```')[1].split('```')[0].strip()
                
                # Пытаемся исправить обрезанный JSON
                # Если JSON обрывается, пытаемся найти последний валидный объект
                if transcription_text.count('{') > transcription_text.count('}'):
                    # JSON не закрыт, пытаемся закрыть его
                    if '"words"' in transcription_text and transcription_text.rfind(']') == -1:
                        # Если массив words не закрыт
                        last_bracket = transcription_text.rfind('[')
                        if last_bracket != -1:
                            transcription_text = transcription_text[:last_bracket] + ']'
                    # Закрываем объект
                    transcription_text = transcription_text.rstrip().rstrip(',') + '\n}'
                
                transcription_data = json.loads(transcription_text)
                
                # Проверяем наличие таймстемпов
                if 'words' not in transcription_data or not transcription_data['words']:
                    print("⚠ Предупреждение: модель не вернула таймстемпы для слов")
                    print("Генерирую приблизительные таймстемпы на основе текста...")
                    
                    # Получаем длительность аудио файла
                    ffmpeg_path = find_ffmpeg()
                    duration = get_audio_duration(chunk_path, ffmpeg_path) if ffmpeg_path else None
                    
                    if duration and 'text' in transcription_data:
                        # Генерируем приблизительные таймстемпы
                        transcription_data['words'] = generate_word_timestamps(
                            transcription_data['text'], 
                            duration, 
                            chunk_offset
                        )
                        print(f"✓ Сгенерировано {len(transcription_data['words'])} приблизительных таймстемпов")
                    else:
                        # Если не удалось получить длительность, создаем пустой массив
                        if 'text' not in transcription_data:
                            transcription_data['text'] = transcription_text
                        if 'words' not in transcription_data:
                            transcription_data['words'] = []
                else:
                    # Корректируем таймстемпы с учетом смещения
                    for word in transcription_data['words']:
                        if 'start' in word:
                            word['start'] += chunk_offset
                        if 'end' in word:
                            word['end'] += chunk_offset
                    print(f"✓ Получено {len(transcription_data['words'])} слов с таймстемпами")
                
                return transcription_data
            except json.JSONDecodeError as e:
                print(f"⚠ Ошибка парсинга JSON: {e}")
                print("Пытаюсь извлечь текст и сгенерировать таймстемпы...")
                
                # Пытаемся извлечь текст из ответа
                text = None
                
                # Ищем текст в JSON-подобной структуре
                text_match = re.search(r'"text"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', transcription_text, re.DOTALL)
                if text_match:
                    text = text_match.group(1)
                    # Убираем экранированные символы
                    text = text.replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                else:
                    # Если не нашли, берем весь текст после "text":
                    if '"text"' in transcription_text:
                        parts = transcription_text.split('"text"', 1)
                        if len(parts) > 1:
                            # Пытаемся извлечь текст между кавычками
                            remaining = parts[1].strip()
                            if remaining.startswith(':'):
                                remaining = remaining[1:].strip()
                                if remaining.startswith('"'):
                                    # Извлекаем текст до закрывающей кавычки
                                    end_quote = remaining.find('"', 1)
                                    if end_quote != -1:
                                        text = remaining[1:end_quote]
                
                # Если не удалось извлечь, используем весь ответ как текст
                if not text:
                    # Убираем управляющие символы и пробуем использовать как текст
                    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', transcription_text)
                    # Убираем JSON-структуру если есть
                    text = re.sub(r'^\s*\{\s*"text"\s*:\s*"', '', text)
                    text = re.sub(r'"\s*\}\s*$', '', text)
                    text = text.strip().strip('"')
                
                if text:
                    # Получаем длительность аудио и генерируем таймстемпы
                    ffmpeg_path = find_ffmpeg()
                    duration = get_audio_duration(chunk_path, ffmpeg_path) if ffmpeg_path else None
                    
                    words = []
                    if duration:
                        words = generate_word_timestamps(text, duration, chunk_offset)
                        print(f"✓ Сгенерировано {len(words)} приблизительных таймстемпов")
                    
                    return {
                        "text": text,
                        "words": words
                    }
                else:
                    # Если ничего не получилось, возвращаем исходный текст
                    return {
                        "text": transcription_text,
                        "words": []
                    }
        else:
            print(f"✗ Ошибка: неожиданный формат ответа от API")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Ошибка при запросе к API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                if 'error' in error_detail:
                    error_msg = error_detail['error'].get('message', str(error_detail))
                    print(f"Детали ошибки: {error_msg}")
            except:
                pass
        return None
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return None


def transcribe_audio_with_timestamps(mp3_path, output_dir, model='mistralai/voxtral-small-24b-2507', ffmpeg_path='ffmpeg', chunk_duration=300):
    """
    Транскрибирует аудио файл через OpenRouter API с таймстемпами.
    Автоматически разбивает большие файлы на части.
    
    Args:
        mp3_path: Путь к MP3 файлу
        output_dir: Директория для сохранения результата
        model: Модель для транскрипции
        ffmpeg_path: Путь к ffmpeg
        chunk_duration: Длительность части в секундах (по умолчанию 300 = 5 минут)
    
    Returns:
        Путь к созданному JSON файлу с транскрипцией
    """
    # Проверка наличия API ключа
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("✗ Ошибка: переменная окружения OPENROUTER_API_KEY не установлена.")
        print("Установите API ключ:")
        print("  export OPENROUTER_API_KEY='your-api-key'")
        print("Или создайте файл .env с OPENROUTER_API_KEY=your-api-key")
        return None
    
    print(f"Транскрипция аудио через OpenRouter API (модель: {model})...")
    
    # Проверяем размер файла
    file_size = os.path.getsize(mp3_path)
    file_size_mb = file_size / 1024 / 1024
    
    print(f"Размер файла: {file_size_mb:.1f}MB")
    
    # Если файл больше 5MB, разбиваем на части
    if file_size > 5 * 1024 * 1024:  # 5MB
        print(f"Файл слишком большой, разбиваем на части...")
        chunks = split_audio_into_chunks(mp3_path, output_dir, chunk_duration, ffmpeg_path)
        
        if not chunks:
            print("✗ Ошибка: не удалось создать части аудио")
            return None
        
        # Транскрибируем каждую часть
        all_words = []
        full_text_parts = []
        
        for i, chunk_path in enumerate(chunks):
            chunk_offset = i * chunk_duration
            print(f"\nТранскрипция части {i + 1}/{len(chunks)} (смещение: {chunk_offset:.1f}с)...")
            
            chunk_transcription = transcribe_audio_chunk(chunk_path, chunk_offset, api_key, model)
            
            if chunk_transcription:
                if 'words' in chunk_transcription:
                    all_words.extend(chunk_transcription['words'])
                if 'text' in chunk_transcription:
                    full_text_parts.append(chunk_transcription['text'])
                print(f"✓ Часть {i + 1} транскрибирована")
            else:
                print(f"⚠ Часть {i + 1} не удалось транскрибировать")
        
        # Объединяем результаты
        transcription_data = {
            "text": " ".join(full_text_parts),
            "words": all_words
        }
    else:
        # Файл небольшой, транскрибируем целиком
        print("Транскрипция файла целиком...")
        transcription_data = transcribe_audio_chunk(mp3_path, 0, api_key, model)
        
        if not transcription_data:
            return None
    
    # Сохраняем результат в JSON файл
    json_filename = os.path.basename(mp3_path).replace('.mp3', '_transcription.json')
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcription_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Транскрипция завершена успешно!")
    print(f"Файл сохранен: {json_path}")
    
    # Выводим статистику
    if 'words' in transcription_data:
        print(f"Количество слов: {len(transcription_data['words'])}")
    if 'text' in transcription_data:
        text_length = len(transcription_data['text'])
        print(f"Длина текста: {text_length} символов")
    
    return json_path


def main():
    """Основная функция."""
    if len(sys.argv) < 2:
        print("Использование: python video_to_mp3.py <путь_к_видео> [bitrate] [--no-transcribe]")
        print("Пример: python video_to_mp3.py video.mp4 192k")
        print("Пример без транскрипции: python video_to_mp3.py video.mp4 192k --no-transcribe")
        sys.exit(1)
    
    video_path = sys.argv[1]
    bitrate = '128k'
    skip_transcribe = False
    
    # Парсим аргументы
    for arg in sys.argv[2:]:
        if arg == '--no-transcribe':
            skip_transcribe = True
        elif not arg.startswith('--'):
            bitrate = arg
    
    # Поиск ffmpeg
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("✗ Ошибка: ffmpeg не найден в системе.")
        print("Установите ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    # Проверка существования видео файла
    if not os.path.exists(video_path):
        print(f"✗ Ошибка: файл '{video_path}' не найден.")
        sys.exit(1)
    
    # Создаем путь для выходной директории с timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join('output', timestamp)
    
    # Конвертируем видео в MP3
    mp3_path = convert_video_to_mp3(video_path, output_dir, bitrate, ffmpeg_path)
    
    # Транскрибируем аудио если не пропущено
    if not skip_transcribe:
        print("\n" + "="*50)
        transcribe_audio_with_timestamps(mp3_path, output_dir, ffmpeg_path=ffmpeg_path)
    else:
        print("\n⚠ Транскрипция пропущена (использован флаг --no-transcribe)")


if __name__ == '__main__':
    main()

