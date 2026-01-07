#!/usr/bin/env python3
"""
Графический интерфейс для конвертации видео в MP3 с транскрипцией.
"""

import os
import sys

# Исправление проблемы с версией macOS для tkinter
if sys.platform == 'darwin':
    # Обход проблемы с версией macOS
    os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path

# Импортируем функции из основного модуля
try:
    from video_to_mp3 import (
        find_ffmpeg,
        convert_video_to_mp3,
        transcribe_audio_with_timestamps
    )
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что файл video_to_mp3.py находится в той же директории")
    sys.exit(1)

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class VideoTrimGUI:
    """Графический интерфейс для VideoTrim."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("VideoTrim - Конвертер видео в MP3 с транскрипцией")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        self.video_path = None
        self.output_path = None
        self.is_processing = False
        
        self._create_widgets()
        self._check_dependencies()
    
    def _create_widgets(self):
        """Создает элементы интерфейса."""
        # Заголовок
        title_label = tk.Label(
            self.root,
            text="VideoTrim",
            font=("Arial", 18, "bold"),
            pady=10
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            self.root,
            text="Конвертация видео в MP3 с автоматической транскрипцией",
            font=("Arial", 10),
            fg="gray"
        )
        subtitle_label.pack()
        
        # Разделитель
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=20, pady=10)
        
        # Выбор видео файла
        file_frame = ttk.LabelFrame(self.root, text="Выбор видео файла", padding=10)
        file_frame.pack(fill='x', padx=20, pady=10)
        
        self.file_label = tk.Label(
            file_frame,
            text="Файл не выбран",
            font=("Arial", 9),
            fg="gray",
            anchor='w'
        )
        self.file_label.pack(fill='x', pady=(0, 5))
        
        select_btn = ttk.Button(
            file_frame,
            text="Выбрать видео файл",
            command=self._select_video_file
        )
        select_btn.pack()
        
        # Настройки
        settings_frame = ttk.LabelFrame(self.root, text="Настройки", padding=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        # Битрейт
        bitrate_frame = ttk.Frame(settings_frame)
        bitrate_frame.pack(fill='x', pady=5)
        
        tk.Label(bitrate_frame, text="Битрейт MP3:").pack(side='left', padx=(0, 10))
        self.bitrate_var = tk.StringVar(value="128k")
        bitrate_combo = ttk.Combobox(
            bitrate_frame,
            textvariable=self.bitrate_var,
            values=["64k", "96k", "128k", "192k", "256k", "320k"],
            state="readonly",
            width=10
        )
        bitrate_combo.pack(side='left')
        
        # Транскрипция
        transcribe_frame = ttk.Frame(settings_frame)
        transcribe_frame.pack(fill='x', pady=5)
        
        self.transcribe_var = tk.BooleanVar(value=True)
        transcribe_check = ttk.Checkbutton(
            transcribe_frame,
            text="Выполнить транскрипцию через OpenRouter API",
            variable=self.transcribe_var
        )
        transcribe_check.pack(side='left')
        
        # Кнопка запуска
        self.process_btn = ttk.Button(
            self.root,
            text="Начать обработку",
            command=self._start_processing,
            state='disabled'
        )
        self.process_btn.pack(pady=20)
        
        # Прогресс
        progress_frame = ttk.LabelFrame(self.root, text="Прогресс", padding=10)
        progress_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.progress_var = tk.StringVar(value="Готов к работе")
        self.progress_label = tk.Label(
            progress_frame,
            textvariable=self.progress_var,
            font=("Arial", 9),
            anchor='w'
        )
        self.progress_label.pack(fill='x', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate'
        )
        self.progress_bar.pack(fill='x', pady=5)
        
        # Лог
        log_frame = ttk.LabelFrame(self.root, text="Лог выполнения", padding=5)
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            font=("Courier", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill='both', expand=True)
    
    def _check_dependencies(self):
        """Проверяет наличие необходимых зависимостей."""
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self._log("⚠ Предупреждение: ffmpeg не найден в системе")
            self._log("Установите ffmpeg для работы программы")
        else:
            self._log(f"✓ ffmpeg найден: {ffmpeg_path}")
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            self._log("⚠ Предупреждение: OPENROUTER_API_KEY не установлен")
            self._log("Транскрипция будет недоступна")
        else:
            self._log("✓ API ключ OpenRouter найден")
    
    def _select_video_file(self):
        """Открывает диалог выбора видео файла."""
        file_path = filedialog.askopenfilename(
            title="Выберите видео файл",
            filetypes=[
                ("Видео файлы", "*.mp4 *.avi *.mov *.mkv *.webm *.flv"),
                ("Все файлы", "*.*")
            ]
        )
        
        if file_path:
            self.video_path = file_path
            file_name = Path(file_path).name
            self.file_label.config(text=f"Выбран: {file_name}", fg="black")
            self.process_btn.config(state='normal')
            self._log(f"Выбран файл: {file_name}")
    
    def _log(self, message):
        """Добавляет сообщение в лог."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _start_processing(self):
        """Запускает обработку в отдельном потоке."""
        if not self.video_path or self.is_processing:
            return
        
        if not os.path.exists(self.video_path):
            messagebox.showerror("Ошибка", "Выбранный файл не существует")
            return
        
        # Проверка ffmpeg
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            messagebox.showerror(
                "Ошибка",
                "ffmpeg не найден в системе.\nУстановите ffmpeg для работы программы."
            )
            return
        
        # Проверка API ключа для транскрипции
        if self.transcribe_var.get():
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                result = messagebox.askyesno(
                    "Предупреждение",
                    "API ключ OpenRouter не установлен.\n"
                    "Продолжить без транскрипции?"
                )
                if not result:
                    return
                self.transcribe_var.set(False)
        
        # Блокируем интерфейс
        self.is_processing = True
        self.process_btn.config(state='disabled')
        self.progress_bar.start()
        self.progress_var.set("Обработка...")
        self.log_text.delete(1.0, tk.END)
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._process_video, daemon=True)
        thread.start()
    
    def _process_video(self):
        """Обрабатывает видео файл."""
        try:
            from datetime import datetime
            
            # Создаем выходную директорию
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join('output', timestamp)
            os.makedirs(output_dir, exist_ok=True)
            
            self._log("=" * 50)
            self._log("Начало обработки")
            self._log("=" * 50)
            
            # Конвертация в MP3
            self._log(f"\nКонвертация видео в MP3...")
            self.progress_var.set("Конвертация видео в MP3...")
            
            ffmpeg_path = find_ffmpeg()
            bitrate = self.bitrate_var.get()
            
            mp3_path = convert_video_to_mp3(
                self.video_path,
                output_dir,
                bitrate,
                ffmpeg_path
            )
            
            self._log(f"✓ MP3 файл создан: {mp3_path}")
            
            # Транскрипция
            if self.transcribe_var.get():
                self._log("\n" + "=" * 50)
                self._log("Начало транскрипции...")
                self.progress_var.set("Транскрипция аудио...")
                
                json_path = transcribe_audio_with_timestamps(
                    mp3_path,
                    output_dir,
                    ffmpeg_path=ffmpeg_path
                )
                
                if json_path:
                    self._log(f"✓ Транскрипция завершена: {json_path}")
                else:
                    self._log("⚠ Транскрипция не выполнена")
            
            # Завершение
            self._log("\n" + "=" * 50)
            self._log("✓ Обработка завершена успешно!")
            self._log(f"Результаты сохранены в: {output_dir}")
            self._log("=" * 50)
            
            self.progress_var.set("Готово!")
            
            messagebox.showinfo(
                "Успех",
                f"Обработка завершена успешно!\n\n"
                f"Результаты сохранены в:\n{output_dir}"
            )
            
        except Exception as e:
            error_msg = f"Ошибка при обработке: {str(e)}"
            self._log(f"\n✗ {error_msg}")
            self.progress_var.set("Ошибка!")
            messagebox.showerror("Ошибка", error_msg)
        
        finally:
            # Разблокируем интерфейс
            self.is_processing = False
            self.progress_bar.stop()
            self.process_btn.config(state='normal')
            if not self.is_processing:
                self.progress_var.set("Готов к работе")


def main():
    """Запускает графический интерфейс."""
    try:
        root = tk.Tk()
        app = VideoTrimGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Ошибка при запуске GUI: {e}")
        print("\nПопробуйте использовать командную строку:")
        print("  python3 video_to_mp3.py <путь_к_видео>")
        sys.exit(1)


if __name__ == '__main__':
    main()

