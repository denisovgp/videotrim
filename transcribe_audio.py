#!/usr/bin/env python3
"""
Утилита для транскрипции отдельного аудио файла.
Использование: python transcribe_audio.py <путь_к_mp3>
"""

import sys
import os
import json
from video_to_mp3 import transcribe_audio_chunk

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    """Основная функция."""
    if len(sys.argv) < 2:
        print("Использование: python transcribe_audio.py <путь_к_mp3>")
        sys.exit(1)
    
    mp3_path = sys.argv[1]
    
    if not os.path.exists(mp3_path):
        print(f"✗ Ошибка: файл '{mp3_path}' не найден.")
        sys.exit(1)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("✗ Ошибка: переменная окружения OPENROUTER_API_KEY не установлена.")
        print("Установите API ключ в файле .env или через переменную окружения.")
        sys.exit(1)
    
    print(f"Транскрипция файла: {mp3_path}")
    print("=" * 50)
    
    result = transcribe_audio_chunk(mp3_path, chunk_offset=0, api_key=api_key)
    
    if not result:
        print("✗ Ошибка при транскрипции")
        sys.exit(1)
    
    # Сохраняем результат в JSON
    json_path = mp3_path.replace('.mp3', '_transcription.json')
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Транскрипция завершена!")
    print(f"JSON файл: {json_path}")
    
    # Выводим статистику
    if 'words' in result:
        print(f"Количество слов: {len(result['words'])}")
    if 'text' in result:
        text_length = len(result['text'])
        print(f"Длина текста: {text_length} символов")


if __name__ == '__main__':
    main()

