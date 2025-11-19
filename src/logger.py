# src/logger.py
"""
Централизованная система логирования для Video Intelligence System
Исправляет проблемы с print() и кодировкой
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "video_intelligence",
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Настройка логгера с поддержкой файлов и консоли

    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для логов (если None, только консоль)
        console_output: Выводить ли в консоль

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)

    # Избегаем дублирования handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Формат логов (без эмодзи для совместимости)
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Консольный handler с UTF-8
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        # Явная UTF-8 кодировка для Windows
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8')
            except Exception:
                pass  # Если не поддерживается, игнорируем

        logger.addHandler(console_handler)

    # Файловый handler
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Основной лог-файл
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8',  # Явная UTF-8 для файлов
            mode='a'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Отдельный файл для ошибок
        error_file = log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(
            error_file,
            encoding='utf-8',
            mode='a'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    return logger


class TaskLogger:
    """
    Логгер для отслеживания задач обработки
    Префиксы для лучшей читаемости
    """

    def __init__(self, task_id: str, logger: Optional[logging.Logger] = None):
        """
        Args:
            task_id: ID задачи
            logger: Базовый логгер (если None, создается новый)
        """
        self.task_id = task_id
        self.logger = logger or setup_logger()
        self.prefix = f"[Task {task_id}]"

    def debug(self, message: str):
        """Отладочное сообщение"""
        self.logger.debug(f"{self.prefix} {message}")

    def info(self, message: str):
        """Информационное сообщение"""
        self.logger.info(f"{self.prefix} {message}")

    def warning(self, message: str):
        """Предупреждение"""
        self.logger.warning(f"{self.prefix} {message}")

    def error(self, message: str, exc_info: bool = False):
        """Ошибка"""
        self.logger.error(f"{self.prefix} {message}", exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        """Критическая ошибка"""
        self.logger.critical(f"{self.prefix} {message}", exc_info=exc_info)

    def stage(self, stage_num: int, total: int, description: str):
        """Логирование этапа обработки"""
        self.info(f"[{stage_num}/{total}] {description}")

    def success(self, message: str):
        """Успешное выполнение"""
        self.info(f"✓ {message}")

    def failure(self, message: str):
        """Неудачное выполнение"""
        self.error(f"✗ {message}")


# Глобальный логгер по умолчанию
_default_logger = None


def get_logger(name: str = "video_intelligence") -> logging.Logger:
    """
    Получить логгер (создает если не существует)

    Args:
        name: Имя логгера

    Returns:
        Настроенный логгер
    """
    global _default_logger

    if _default_logger is None:
        # Создаем директорию для логов
        log_dir = Path("logs")
        _default_logger = setup_logger(
            name=name,
            level=logging.INFO,
            log_dir=log_dir,
            console_output=True
        )

    return _default_logger


def set_log_level(level: str):
    """
    Изменить уровень логирования

    Args:
        level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    logger = get_logger()
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    if level.upper() in level_map:
        logger.setLevel(level_map[level.upper()])
        for handler in logger.handlers:
            handler.setLevel(level_map[level.upper()])


# Вспомогательные функции для быстрого доступа
def debug(message: str):
    """Быстрое логирование DEBUG"""
    get_logger().debug(message)


def info(message: str):
    """Быстрое логирование INFO"""
    get_logger().info(message)


def warning(message: str):
    """Быстрое логирование WARNING"""
    get_logger().warning(message)


def error(message: str, exc_info: bool = False):
    """Быстрое логирование ERROR"""
    get_logger().error(message, exc_info=exc_info)


def critical(message: str, exc_info: bool = False):
    """Быстрое логирование CRITICAL"""
    get_logger().critical(message, exc_info=exc_info)


if __name__ == "__main__":
    # Тестирование логгера
    logger = get_logger()

    logger.info("Тест логирования с кириллицей")
    logger.debug("Отладочное сообщение")
    logger.warning("Предупреждение")
    logger.error("Ошибка")

    # Тест TaskLogger
    task_logger = TaskLogger("test_123")
    task_logger.stage(1, 8, "Транскрибация")
    task_logger.success("Транскрипция завершена!")
    task_logger.failure("Не удалось загрузить модель")

    print(f"\nЛоги сохранены в директории: logs/")
