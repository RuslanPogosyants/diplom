#!/usr/bin/env python3
"""
Веб-интерфейс для Video Intelligence System
Система интеллектуального анализа образовательных видео
"""
from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Optional
import os
import subprocess
import threading
import time
import sys
import logging

# Импорт централизованной системы логирования
from src.logger import setup_application_logging, get_logger, ProcessLogger

# Настройка логирования приложения
setup_application_logging(log_dir="logs", debug=False)
logger = get_logger("web_server")

app = Flask(__name__)
app.config['ARTIFACTS_DIR'] = Path('artifacts')
app.config['UPLOAD_FOLDER'] = Path('artifacts')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['JSON_AS_ASCII'] = False

# Отключаем стандартное логирование Flask для /api/process/status
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Thread-safe словарь для отслеживания активных процессов обработки
processing_tasks = {}
processing_tasks_lock = threading.Lock()


def get_all_sessions() -> List[Dict]:
    """Получить список всех обработанных видео"""
    artifacts_dir = app.config['ARTIFACTS_DIR']

    if not artifacts_dir.exists():
        return []

    sessions = []

    for session_dir in sorted(artifacts_dir.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue

        # Пропускаем служебные директории
        if session_dir.name in ['checkpoints', 'latest']:
            continue

        checkpoint_path = session_dir / 'checkpoint.json'

        if checkpoint_path.exists():
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)

            # Определяем статус обработки
            stage = checkpoint.get('stage', 'unknown')

            # Загружаем базовую информацию
            info = {
                'id': session_dir.name,
                'path': str(session_dir),
                'stage': stage,
                'timestamp': checkpoint.get('timestamp', 0),
                'video_source': checkpoint.get('video_source', 'N/A'),
                'files': checkpoint.get('files', {})
            }

            # Добавляем статистику если есть финальная суммаризация
            final_summary_path = session_dir / 'final_summary.json'
            if final_summary_path.exists():
                with open(final_summary_path, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    info['statistics'] = summary.get('statistics', {})

            sessions.append(info)

    return sessions


def load_session_data(session_id: str) -> Optional[Dict]:
    """Загрузить все данные сессии"""
    session_dir = app.config['ARTIFACTS_DIR'] / session_id

    if not session_dir.exists():
        return None

    data = {
        'id': session_id,
        'path': str(session_dir)
    }

    # Checkpoint
    checkpoint_path = session_dir / 'checkpoint.json'
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data['checkpoint'] = json.load(f)

    # Транскрипция
    transcript_path = session_dir / 'transcript_raw.json'
    if transcript_path.exists():
        with open(transcript_path, 'r', encoding='utf-8') as f:
            data['transcript'] = json.load(f)

    # Сегменты
    segments_path = session_dir / 'segments_semantic.json'
    if segments_path.exists():
        with open(segments_path, 'r', encoding='utf-8') as f:
            data['segments'] = json.load(f)

    # Суммаризация
    summaries_path = session_dir / 'summaries_per_segment.json'
    if summaries_path.exists():
        with open(summaries_path, 'r', encoding='utf-8') as f:
            data['summaries'] = json.load(f)

    # Финальная суммаризация
    final_summary_path = session_dir / 'final_summary.json'
    if final_summary_path.exists():
        with open(final_summary_path, 'r', encoding='utf-8') as f:
            data['final_summary'] = json.load(f)

    # Термины
    terms_path = session_dir / 'terms_and_entities.json'
    if terms_path.exists():
        with open(terms_path, 'r', encoding='utf-8') as f:
            data['terms'] = json.load(f)

    # Вопросы
    questions_path = session_dir / 'questions.json'
    if questions_path.exists():
        with open(questions_path, 'r', encoding='utf-8') as f:
            data['questions'] = json.load(f)

    # Статьи
    articles_path = session_dir / 'related_articles.json'
    if articles_path.exists():
        with open(articles_path, 'r', encoding='utf-8') as f:
            data['articles'] = json.load(f)

    return data


@app.template_filter('format_time')
def format_time(seconds):
    """Форматирование времени"""
    if not seconds:
        return "N/A"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


@app.template_filter('format_datetime')
def format_datetime(timestamp):
    """Форматирование даты и времени"""
    if not timestamp:
        return "N/A"

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%d.%m.%Y %H:%M")


@app.route('/')
def index():
    """Главная страница со списком обработанных видео"""
    sessions = get_all_sessions()
    return render_template('index.html', sessions=sessions)


@app.route('/session/<session_id>')
def session_view(session_id):
    """Детальный просмотр результатов обработки"""
    data = load_session_data(session_id)

    if not data:
        return "Session not found", 404

    return render_template('session.html', data=data)


@app.route('/api/sessions')
def api_sessions():
    """API: список сессий"""
    sessions = get_all_sessions()
    return jsonify(sessions)


@app.route('/api/session/<session_id>')
def api_session(session_id):
    """API: данные конкретной сессии"""
    data = load_session_data(session_id)

    if not data:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(data)


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Отдача статических файлов"""
    return send_from_directory('static', filename)


def get_available_audio_files() -> List[Dict]:
    """Получить список доступных аудио файлов"""
    artifacts_dir = app.config['ARTIFACTS_DIR']

    if not artifacts_dir.exists():
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        return []

    audio_files = []

    # Ищем wav, mp3, mp4 файлы
    for ext in ['*.wav', '*.mp3', '*.mp4', '*.m4a']:
        for file_path in artifacts_dir.rglob(ext):
            # Пропускаем файлы внутри обработанных папок
            if 'video_' in str(file_path.parent):
                continue

            stat = file_path.stat()
            audio_files.append({
                'name': file_path.name,
                'path': str(file_path.relative_to(artifacts_dir)),
                'full_path': str(file_path),
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': stat.st_mtime,
                'ext': file_path.suffix
            })

    # Сортируем по дате изменения (новые первые)
    audio_files.sort(key=lambda x: x['modified'], reverse=True)

    return audio_files


@app.route('/process')
def process_page():
    """Страница обработки новых файлов"""
    audio_files = get_available_audio_files()
    return render_template('process.html', audio_files=audio_files)


@app.route('/api/audio-files')
def api_audio_files():
    """API: список доступных аудио файлов"""
    files = get_available_audio_files()
    return jsonify(files)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка нового файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Проверяем расширение
    allowed_extensions = {'.wav', '.mp3', '.mp4', '.m4a', '.avi', '.mkv'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'}), 400

    # Сохраняем файл
    filename = file.filename
    file_path = app.config['UPLOAD_FOLDER'] / filename

    # Если файл уже существует, добавляем timestamp
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_without_ext = file_path.stem
        filename = f"{name_without_ext}_{timestamp}{file_ext}"
        file_path = app.config['UPLOAD_FOLDER'] / filename

    file.save(str(file_path))

    return jsonify({
        'success': True,
        'filename': filename,
        'path': str(file_path)
    })


def run_processing(file_path: str, task_id: str, options: Dict):
    """
    Запуск обработки в отдельном потоке с качественным логированием

    Args:
        file_path: Путь к файлу для обработки
        task_id: Уникальный идентификатор задачи
        options: Параметры обработки
    """
    # Инициализация логгера для этой задачи
    proc_logger = ProcessLogger(task_id, log_dir="logs")

    try:
        proc_logger.info("INIT", f"Начало обработки файла: {file_path}")
        proc_logger.info("INIT", f"Параметры: {options}")

        with processing_tasks_lock:
            processing_tasks[task_id]['status'] = 'running'
            processing_tasks[task_id]['stage'] = 'Подготовка...'
            processing_tasks[task_id]['progress'] = 5

        # Формируем команду
        cmd = [
            sys.executable, '-m', 'src.cli', 'process-all',
            file_path,
            '--language', options.get('language', 'ru'),
            '--model', options.get('model', 'base'),
            '--device', options.get('device', 'auto'),
        ]

        # Добавляем флаги для LLM/KeyBERT/Answers
        if options.get('use_llm'):
            cmd.append('--use-llm')
            proc_logger.info("CONFIG", "LLM (GigaChat) включен")

        if options.get('use_keybert'):
            cmd.append('--use-keybert')
            proc_logger.info("CONFIG", "KeyBERT включен")

        if options.get('with_answers'):
            cmd.append('--with-answers')
            proc_logger.info("CONFIG", "Генерация ответов включена")

        if options.get('skip_questions'):
            cmd.append('--skip-questions')
            proc_logger.info("CONFIG", "Генерация вопросов пропущена")

        if options.get('skip_articles'):
            cmd.append('--skip-articles')
            proc_logger.info("CONFIG", "Поиск статей пропущен")

        with processing_tasks_lock:
            processing_tasks[task_id]['stage'] = 'Запуск обработки...'
            processing_tasks[task_id]['progress'] = 10

        proc_logger.info("EXEC", f"Запуск команды: {' '.join(cmd)}")

        # Запускаем процесс с таймаутом и правильной кодировкой
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',  # Заменяем нераспознанные символы вместо ошибки
            bufsize=1,
            universal_newlines=True
        )

        with processing_tasks_lock:
            processing_tasks[task_id]['process'] = process

        output_lines = []
        error_lines = []

        proc_logger.info("PROC", f"Процесс запущен (PID: {process.pid})")

        # Читаем stdout и обновляем прогресс
        if process.stdout:
            for line in process.stdout:
                line_stripped = line.strip()

                if line_stripped:
                    output_lines.append(line_stripped)

                    # Определяем этап и обновляем прогресс
                    stage_info = None
                    progress = None

                    if '[1/8]' in line or 'Транскрибация' in line or 'Transcription' in line:
                        stage_info = 'Транскрибация аудио...'
                        progress = 20
                    elif '[2/8]' in line or 'Сегментация' in line or 'Segmentation' in line:
                        stage_info = 'Семантическая сегментация...'
                        progress = 35
                    elif '[3/8]' in line or 'Суммаризация' in line or 'Summarizing' in line:
                        stage_info = 'Суммаризация сегментов...'
                        progress = 50
                    elif '[4/8]' in line or 'Мета-анализ' in line or 'Meta-analysis' in line:
                        stage_info = 'Мета-анализ контента...'
                        progress = 65
                    elif '[5/8]' in line or 'Извлечение терминов' in line or 'Term extraction' in line:
                        stage_info = 'Извлечение ключевых терминов...'
                        progress = 75
                    elif '[6/8]' in line or 'Генерация вопросов' in line or 'Generating questions' in line:
                        stage_info = 'Генерация вопросов...'
                        progress = 85
                    elif '[7/8]' in line or 'Поиск статей' in line or 'Searching articles' in line:
                        stage_info = 'Поиск релевантных статей...'
                        progress = 90
                    elif '[8/8]' in line or 'Экспорт' in line or 'Export' in line:
                        stage_info = 'Экспорт отчёта...'
                        progress = 95
                    elif 'ЗАВЕРШЁН' in line or 'SUCCESS' in line or 'Complete!' in line:
                        stage_info = 'Завершено!'
                        progress = 100

                    # Обновляем статус с thread-safe доступом
                    if stage_info:
                        with processing_tasks_lock:
                            processing_tasks[task_id]['stage'] = stage_info
                            processing_tasks[task_id]['progress'] = progress
                        proc_logger.info("STAGE", f"{stage_info} ({progress}%)")

                    # Логируем ошибки
                    if 'ERROR' in line or 'Error' in line or 'Ошибка' in line:
                        error_lines.append(line_stripped)
                        proc_logger.error("OUTPUT", line_stripped)

        # Ждём завершения и читаем stderr
        proc_logger.info("PROC", "Процесс завершил работу, ожидание кода возврата...")

        try:
            return_code = process.wait(timeout=3600)  # Таймаут 1 час
        except subprocess.TimeoutExpired:
            proc_logger.error("PROC", "Превышен таймаут выполнения (1 час)")
            process.kill()
            raise TimeoutError("Процесс превысил максимальное время выполнения")

        stderr_output = ""
        if process.stderr:
            try:
                stderr_output = process.stderr.read()
                if stderr_output:
                    proc_logger.warning("STDERR", stderr_output)
            except Exception as e:
                proc_logger.error("STDERR", f"Не удалось прочитать stderr: {e}")

        proc_logger.info("PROC", f"Код возврата: {return_code}")

        # Обновляем финальный статус
        with processing_tasks_lock:
            if return_code == 0:
                # Пытаемся определить session_id из вывода
                session_id = None
                for line in output_lines:
                    if 'Все результаты сохранены в:' in line or 'artifacts/' in line:
                        # Ищем путь вида artifacts/video_TIMESTAMP (например video_20231122_153045)
                        import re
                        match = re.search(r'artifacts[/\\](video_[\d_]+)', line)
                        if match:
                            session_id = match.group(1)
                            break

                processing_tasks[task_id]['status'] = 'completed'
                processing_tasks[task_id]['stage'] = 'Обработка завершена успешно!'
                processing_tasks[task_id]['progress'] = 100
                processing_tasks[task_id]['output'] = '\n'.join(output_lines)
                processing_tasks[task_id]['session_id'] = session_id  # Сохраняем session_id
                proc_logger.info("SUCCESS", f"Обработка успешно завершена. Session ID: {session_id}")
            else:
                error_msg = f"Процесс завершился с кодом {return_code}\n\n"
                if stderr_output:
                    error_msg += f"STDERR:\n{stderr_output}\n\n"
                if error_lines:
                    error_msg += f"Ошибки из лога:\n" + "\n".join(error_lines[-10:])

                processing_tasks[task_id]['status'] = 'error'
                processing_tasks[task_id]['stage'] = 'Ошибка обработки'
                processing_tasks[task_id]['error'] = error_msg
                processing_tasks[task_id]['output'] = '\n'.join(output_lines)
                proc_logger.error("FAILED", f"Процесс завершился с ошибкой: {error_msg}")

    except TimeoutError as e:
        with processing_tasks_lock:
            processing_tasks[task_id]['status'] = 'error'
            processing_tasks[task_id]['stage'] = 'Превышен таймаут'
            processing_tasks[task_id]['error'] = str(e)
        proc_logger.error("TIMEOUT", str(e), exc_info=True)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()

        with processing_tasks_lock:
            processing_tasks[task_id]['status'] = 'error'
            processing_tasks[task_id]['stage'] = 'Критическая ошибка'
            processing_tasks[task_id]['error'] = f"Исключение: {str(e)}\n\nТрассировка:\n{error_trace}"

        proc_logger.error("EXCEPTION", f"Критическая ошибка: {str(e)}", exc_info=True)

@app.route('/api/process/start', methods=['POST'])
def start_processing():
    """
    Запуск обработки файла с валидацией и логированием

    Returns:
        JSON с task_id или ошибкой
    """
    data = request.get_json()

    if not data or 'file_path' not in data:
        logger.warning("Попытка запуска обработки без указания пути к файлу")
        return jsonify({'error': 'Путь к файлу не указан'}), 400

    file_path = data['file_path']

    # Валидация пути (предотвращение path traversal)
    try:
        file_path_obj = Path(file_path).resolve()
        artifacts_dir = app.config['ARTIFACTS_DIR'].resolve()

        # Проверяем, что файл находится в разрешенной директории
        if not str(file_path_obj).startswith(str(artifacts_dir)):
            logger.error(f"Попытка доступа к файлу вне artifacts: {file_path}")
            return jsonify({'error': 'Недопустимый путь к файлу'}), 403

    except Exception as e:
        logger.error(f"Ошибка валидации пути: {e}")
        return jsonify({'error': 'Некорректный путь к файлу'}), 400

    # Проверяем существование файла
    if not file_path_obj.exists():
        logger.warning(f"Файл не найден: {file_path}")
        return jsonify({'error': 'Файл не найден'}), 404

    # Проверяем тип файла
    allowed_extensions = {'.wav', '.mp3', '.mp4', '.m4a', '.avi', '.mkv'}
    if file_path_obj.suffix.lower() not in allowed_extensions:
        logger.warning(f"Недопустимое расширение файла: {file_path_obj.suffix}")
        return jsonify({'error': 'Недопустимый тип файла'}), 400

    # Создаём уникальный ID задачи
    task_id = f"task_{int(time.time() * 1000)}"

    # Опции обработки
    options = {
        'language': data.get('language', 'ru'),
        'model': data.get('model', 'base'),
        'device': data.get('device', 'auto'),
        'skip_questions': data.get('skip_questions', False),
        'skip_articles': data.get('skip_articles', False),
        'use_llm': data.get('use_llm', True),
        'use_keybert': data.get('use_keybert', True),
        'with_answers': data.get('with_answers', True),
    }

    # Инициализируем задачу с thread-safe доступом
    with processing_tasks_lock:
        processing_tasks[task_id] = {
            'status': 'pending',
            'stage': 'Инициализация...',
            'progress': 0,
            'file_path': str(file_path_obj),
            'started_at': time.time(),
            'options': options
        }

    logger.info(f"Создана задача {task_id} для файла: {file_path_obj.name}")
    logger.info(f"Параметры: язык={options['language']}, модель={options['model']}, устройство={options['device']}")

    # Запускаем в отдельном потоке
    thread = threading.Thread(
        target=run_processing,
        args=(str(file_path_obj), task_id, options),
        name=f"ProcessingThread-{task_id}"
    )
    thread.daemon = False  # Изменено на False для корректного завершения
    thread.start()

    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': 'Обработка запущена'
    })


@app.route('/api/process/status/<task_id>')
def processing_status(task_id):
    """
    Получить статус обработки (без логирования для избежания спама)

    Args:
        task_id: ID задачи

    Returns:
        JSON с информацией о статусе
    """
    with processing_tasks_lock:
        if task_id not in processing_tasks:
            return jsonify({'error': 'Задача не найдена'}), 404

        task = processing_tasks[task_id].copy()  # Копируем для thread-safety

    return jsonify({
        'task_id': task_id,
        'status': task['status'],
        'stage': task['stage'],
        'progress': task['progress'],
        'started_at': task['started_at'],
        'elapsed': time.time() - task['started_at'],
        'error': task.get('error'),
        'output': task.get('output'),
        'session_id': task.get('session_id')  # Добавляем session_id
    })


@app.route('/api/process/cancel/<task_id>', methods=['POST'])
def cancel_processing(task_id):
    """
    Отменить обработку задачи

    Args:
        task_id: ID задачи

    Returns:
        JSON с результатом отмены
    """
    with processing_tasks_lock:
        if task_id not in processing_tasks:
            return jsonify({'error': 'Задача не найдена'}), 404

        task = processing_tasks[task_id]

        if 'process' in task:
            try:
                task['process'].terminate()
                task['status'] = 'cancelled'
                task['stage'] = 'Отменено пользователем'
                logger.info(f"Задача {task_id} отменена пользователем")
            except Exception as e:
                logger.error(f"Ошибка при отмене задачи {task_id}: {e}")
                return jsonify({'error': 'Не удалось отменить задачу'}), 500

    return jsonify({'success': True, 'message': 'Задача отменена'})


if __name__ == '__main__':
    import platform

    print("\n" + "=" * 70)
    print("  СИСТЕМА ИНТЕЛЛЕКТУАЛЬНОГО АНАЛИЗА ВИДЕО")
    print("  Video Intelligence System - Web Interface")
    print("=" * 70)
    print(f"  • Директория артефактов: {app.config['ARTIFACTS_DIR']}")
    print(f"  • Максимальный размер файла: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)} МБ")
    print(f"  • Директория логов: logs/")
    print(f"  • Платформа: {platform.system()} {platform.release()}")
    print("=" * 70)
    print("  Сервер запускается на http://localhost:5000")
    print("  Для остановки используйте Ctrl+C")
    print("=" * 70 + "\n")

    logger.info("Запуск веб-сервера Video Intelligence System")
    logger.info(f"Artifacts directory: {app.config['ARTIFACTS_DIR']}")
    logger.info("Сервер готов к приёму запросов")

    try:
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки сервера")
        print("\n\nСервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка сервера: {e}", exc_info=True)
        raise