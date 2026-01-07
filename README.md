# VideoTrim - Конвертер видео в MP3

Простой скрипт для конвертации видео файлов в сжатые MP3 файлы.

## Требования

- Python 3.6+
- ffmpeg (должен быть установлен в системе)

### Установка ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Скачайте с [официального сайта](https://ffmpeg.org/download.html) и добавьте в PATH.

## Использование

```bash
python video_to_mp3.py <путь_к_видео> [bitrate]
```

### Примеры

```bash
# Конвертация с битрейтом по умолчанию (128k)
python video_to_mp3.py video.mp4

# Конвертация с указанным битрейтом
python video_to_mp3.py video.mp4 192k
```

## Выходные файлы

Все сконвертированные MP3 файлы сохраняются в папку `output/<timestamp>/`, где timestamp - это дата и время конвертации в формате `YYYYMMDD_HHMMSS`.

## Формат выходного файла

- Кодек: MP3 (libmp3lame)
- Битрейт: 128k (по умолчанию) или указанный
- Частота дискретизации: 44100 Hz

