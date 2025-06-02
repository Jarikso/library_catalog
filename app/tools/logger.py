# logging_config.py
import logging
import logging.handlers
from pathlib import Path

# Настройки логгера
LOG_FILE = "app.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Создаем директорию для логов, если ее нет
Path("logs").mkdir(exist_ok=True)

def setup_logger(name: str) -> logging.Logger:
    """
    Настраивает и возвращает логгер с заданным именем.

    Args:
        name (str): Имя логгера (обычно __name__)

    Returns:
        logging.Logger: Сконфигурированный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Форматирование
    formatter = logging.Formatter(LOG_FORMAT)

    # Обработчик для записи в файл (ротация по 5 МБ)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f"logs/{LOG_FILE}",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger