import os
import time
import glob
import logging.config
from logging.handlers import BaseRotatingHandler


from core.config import settings

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 1. 自定义日志切割处理器
class DateSizeRotatingFileHandler(BaseRotatingHandler):
    """
    自定义日志切割器：
    - 触发条件：按文件大小 (maxBytes)
    - 命名规则：app.2026-04-03.1.log (标准日期 + 序号)
    - 清理规则：保留最新的 backupCount 个文件
    """

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        super().__init__(filename, mode, encoding, delay)

    def shouldRollover(self, record):
        if self.stream is None:
            self.stream = self._open()
        if self.maxBytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg.encode(self.encoding or 'utf-8')) >= self.maxBytes:
                return 1
        return 0

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        # 使用标准日期格式 YYYY-MM-DD
        current_date = time.strftime("%Y-%m-%d")
        dir_name, base_name = os.path.split(self.baseFilename)
        name, ext = os.path.splitext(base_name)

        # 组装新文件名，例如 logs/app.2026-04-03.1.log
        index = 1
        while True:
            backup_name = os.path.join(dir_name, f"{name}.{current_date}.{index}{ext}")
            if not os.path.exists(backup_name):
                break
            index += 1

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, backup_name)

        # 精确匹配 YYYY-MM-DD 格式的历史文件
        if self.backupCount > 0:
            # 匹配类似 app.2026-04-03.1.log 的文件
            pattern = os.path.join(dir_name, f"{name}.????-??-??.*{ext}")
            files = glob.glob(pattern)

            files.sort(key=os.path.getmtime)

            while len(files) > self.backupCount:
                file_to_delete = files.pop(0)
                try:
                    os.remove(file_to_delete)
                except OSError:
                    pass

        if not self.delay:
            self.stream = self._open()


# 2. 注册日志字典配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)-8s | PID:%(process)d | %(name)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "uvicorn_access": {
            "()": "uvicorn.logging.AccessFormatter",
            "format": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file_app": {
            "level": "INFO",
            "class": "core.config.log_config.DateSizeRotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "app.log"),
            "maxBytes": 1024 * 1024 * 50,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf8",
        },
        "file_error": {
            "level": "ERROR",
            "class": "core.config.log_config.DateSizeRotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "error.log"),
            "maxBytes": 1024 * 1024 * 50,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf8",
        },
    },
    "loggers": {
        "core": {"handlers": ["console", "file_app", "file_error"], "level": "DEBUG", "propagate": False},
        "api": {"handlers": ["console", "file_app", "file_error"], "level": "DEBUG", "propagate": False},
        "services": {"handlers": ["console", "file_app", "file_error"], "level": "DEBUG", "propagate": False},
        "uvicorn.error": {"handlers": ["console", "file_error"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False, "formatter": "uvicorn_access"},
        "sqlalchemy.engine": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.info("⚙️  系统日志模块初始化成功完毕")
