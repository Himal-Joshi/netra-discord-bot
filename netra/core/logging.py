import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import colorlog

def setup_logging(level: str = "INFO"):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Base formatter
    standard_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Colored formatter for console
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter)

    # File Handlers
    def create_file_handler(name: str, level: int):
        handler = RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=5*1024*1024, # 5MB
            backupCount=5,
            encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(standard_format))
        handler.setLevel(level)
        return handler

    # Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(create_file_handler("bot", logging.INFO))
    root_logger.addHandler(create_file_handler("errors", logging.ERROR))

    # Module specific loggers
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger
