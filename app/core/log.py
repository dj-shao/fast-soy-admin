import logging
import sys
from types import FrameType
from typing import cast

from loguru import logger

from app.core.config import APP_SETTINGS
from app.core.ctx import CTX_X_REQUEST_ID


def x_request_id_filter(record) -> bool:
    record["x_request_id"] = CTX_X_REQUEST_ID.get()
    return True


class Logger:
    """输出日志到文件和控制台"""

    LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} - {process.name} | {thread.name} | <red> {x_request_id} </red> | {module}.{function}:{line} - {level} -{message}"

    def __init__(self):
        self.logger = logger
        self.logger.remove()

        for sub in ("info", "error", "uncaught"):
            (APP_SETTINGS.LOGS_ROOT / sub).mkdir(parents=True, exist_ok=True)

        self.logger.add(sys.stdout)

        # 普通日志（DEBUG/INFO/WARNING/SUCCESS）→ logs/info/，定期删除
        self.logger.add(
            APP_SETTINGS.LOGS_ROOT / "info" / "info_{time:YYYY_MM_DD}.log",
            format=self.LOG_FORMAT,
            encoding="utf-8",
            level="DEBUG",
            filter=lambda record: x_request_id_filter(record) and record["level"].no < 40,
            retention=APP_SETTINGS.LOG_INFO_RETENTION,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            rotation="00:00",
        )

        # 严重错误日志（ERROR/CRITICAL）→ logs/error/，永不删除
        self.logger.add(
            APP_SETTINGS.LOGS_ROOT / "error" / "error_{time:YYYY_MM_DD}.log",
            format=self.LOG_FORMAT,
            encoding="utf-8",
            level="ERROR",
            filter=x_request_id_filter,
            retention=None,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            rotation="00:00",
        )

    @staticmethod
    def init_config():
        LOGGER_NAMES = ("uvicorn.asgi", "uvicorn.access", "uvicorn")

        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in LOGGER_NAMES:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]


    def get_logger(self):
        return self.logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


Loggers = Logger()
Loggers.init_config()
log = Loggers.get_logger()
