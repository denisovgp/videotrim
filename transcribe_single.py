#!/usr/bin/env python3
"""
Скрипт для транскрипции одного аудио файла.
"""

import sys
import os
from video_to_mp3 import transcribe_audio_chunk, find_ffmpeg

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python transcribe_single.py <путь_к_mp3>")
        sys.exit(1)
    
    mp3_path = sys.argv[1]
    
    if not os.path.exists(mp3_path):
        print(f"✗ Ошибка: файл '{mp3_path}' не найден.")
        sys.exit(1)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("✗ Ошибка: переменная окружения OPENROUTER_API_KEY не установлена.")
        sys.exit(1)
    
    output_dir = os.path.dirname(mp3_path)
    
    print(f"Транскрипция файла: {mp3_path}")
    print("="*50)
    
    result = transcribe_audio_chunk(mp3_path, 0, api_key)
    
    if result:
        import json
        json_path = mp3_path.replace('.mp3', '_transcription.json')
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Транскрипция завершена!")
        print(f"JSON файл: {json_path}")
        print(f"\nТекст:")
        print(result.get('text', ''))
    else:
        print("✗ Ошибка при транскрипции")
        sys.exit(1)

