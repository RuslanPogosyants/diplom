"""
Централизованная система логирования для Video Intelligence System
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """
    Цветное форматирование для консоли
    """

    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s [%(levelname)s] %(name)s: %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s [%(levelname)s] %(name)s: %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s [%(levelname)s] %(name)s: %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s [%(levelname)s] %(name)s: %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s [%(levelname)s] %(name)s: %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str = None,
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Настройка логгера с поддержкой файлов и консоли

    Args:
        name: Имя логгера
        level: Уровень логирования
        log_file: Путь к файлу логов (опционально)
        console: Выводить ли в консоль
        max_bytes: Максимальный размер файла лога
        backup_count: Количество бэкапов

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Удаляем существующие handlers чтобы избежать дубликатов
    logger.handlers.clear()

    # Консольный handler с цветным форматированием
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    # Файловый handler с ротацией
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # Формат для файла (без цветов)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Предотвращаем распространение логов в root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер по имени (используется в модулях)

    Args:
        name: Имя логгера (обычно __name__)

    Returns:
        Логгер
    """
    return logging.getLogger(name)


# Настройка логгеров для разных компонентов
def setup_application_logging(log_dir: str = "logs", debug: bool = False):
    """
    Настройка логирования для всего приложения

    Args:
        log_dir: Директория для логов
        debug: Включить ли DEBUG уровень
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    level = logging.DEBUG if debug else logging.INFO

    # Главный логгер приложения
    setup_logger(
        "video_intelligence",
        level=level,
        log_file=str(log_path / "app.log"),
        console=True
    )

    # Логгер для веб-сервера
    setup_logger(
        "web_server",
        level=level,
        log_file=str(log_path / "web_server.log"),
        console=True
    )

    # Логгер для обработки (процессинга)
    setup_logger(
        "processing",
        level=level,
        log_file=str(log_path / "processing.log"),
        console=True
    )

    # Логгер для моделей AI
    setup_logger(
        "ai_models",
        level=level,
        log_file=str(log_path / "ai_models.log"),
        console=False  # Не выводим в консоль, только в файл
    )

    # Отключаем излишнее логирование сторонних библиотек
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)

    # Настраиваем Flask logger
    logging.getLogger("flask.app").setLevel(logging.WARNING)


class ProcessLogger:
    """
    Специальный логгер для отслеживания процесса обработки
    """

    def __init__(self, task_id: str, log_dir: str = "logs"):
        self.task_id = task_id
        self.logger = setup_logger(
            f"task_{task_id}",
            level=logging.INFO,
            log_file=f"{log_dir}/task_{task_id}.log",
            console=True
        )
        self.start_time = datetime.now()

    def info(self, stage: str, message: str, **kwargs):
        """Логирование информации о процессе"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"[{stage}] [{elapsed:.1f}s] {message}", extra=kwargs)

    def error(self, stage: str, message: str, exc_info=None, **kwargs):
        """Логирование ошибки"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.error(f"[{stage}] [{elapsed:.1f}s] {message}", exc_info=exc_info, extra=kwargs)

    def warning(self, stage: str, message: str, **kwargs):
        """Логирование предупреждения"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.warning(f"[{stage}] [{elapsed:.1f}s] {message}", extra=kwargs)

    def debug(self, stage: str, message: str, **kwargs):
        """Отладочное логирование"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.debug(f"[{stage}] [{elapsed:.1f}s] {message}", extra=kwargs)
