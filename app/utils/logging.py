import logging
import sys
from pathlib import Path
from loguru import logger
import json


class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log = logger.bind(request_id="app")
        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomizeLogger:
    @classmethod
    def make_logger(cls, config_path: Path):
        config = cls.load_logging_config(config_path)
        logging_config = config.get("logger")

        return cls.customize_logging(
            log_dir=logging_config.get("log_dir"),
            filename=logging_config.get("filename"),
            level=logging_config.get("level"),
            rotation=logging_config.get("rotation"),
            retention=logging_config.get("retention"),
            console_format=logging_config.get("console_format"),
            file_format=logging_config.get("file_format"),
        )

    @classmethod
    def customize_logging(
        cls,
        log_dir: Path,
        filename: str,
        level: str,
        rotation: str,
        retention: str,
        console_format: str,
        file_format: str,
    ):
        logger.remove()

        # Console logger with colors
        logger.add(
            sys.stdout,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=console_format,
            colorize=True,
        )

        # File logger without colors
        logger.add(
            str(f"{log_dir}/{filename}"),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=file_format,
            colorize=False,
        )

        # Redirect standard logging to loguru
        cls._setup_intercept_handlers()

        return logger.bind(request_id=None, method=None)

    @staticmethod
    def _setup_intercept_handlers():
        logging.basicConfig(handlers=[InterceptHandler()], level=0)

        uvicorn_loggers = ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]
        for log_name in uvicorn_loggers:
            _logger = logging.getLogger(log_name)
            _logger.handlers = [InterceptHandler()]

    @staticmethod
    def load_logging_config(config_path: Path):
        with open(config_path) as config_file:
            return json.load(config_file)


# Initialize logger
config_path = Path("../").with_name("logging_config.json")
custom_logger = CustomizeLogger.make_logger(config_path)


def get_logger():
    """Get the custom logger instance."""
    return custom_logger
