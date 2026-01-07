#!/usr/bin/env python3
"""
Скрипт для конвертации видео файла в сжатый MP3 файл.
Использование: python video_to_mp3.py <путь_к_видео>
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


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


def main():
    """Основная функция."""
    if len(sys.argv) < 2:
        print("Использование: python video_to_mp3.py <путь_к_видео> [bitrate]")
        print("Пример: python video_to_mp3.py video.mp4 192k")
        sys.exit(1)
    
    video_path = sys.argv[1]
    bitrate = sys.argv[2] if len(sys.argv) > 2 else '128k'
    
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
    convert_video_to_mp3(video_path, output_dir, bitrate, ffmpeg_path)


if __name__ == '__main__':
    main()

