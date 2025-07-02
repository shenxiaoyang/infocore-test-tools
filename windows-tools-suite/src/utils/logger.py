import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

def get_logger(name="infocore"):
    """
    获取一个全局唯一的logger，防止重复添加handler。
    :param name: logger名称，建议用模块名或功能名
    :return: logger对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 只在没有handler时添加，防止重复
    if not logger.handlers:
        # 日志目录
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log")

        # 文件handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.INFO)

        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# 兼容旧用法
class Logger:
    def __init__(self, name="infocore"):
        self._logger = get_logger(name)
    def info(self, msg): self._logger.info(msg)
    def error(self, msg): self._logger.error(msg)
    def warning(self, msg): self._logger.warning(msg)
    def debug(self, msg): self._logger.debug(msg) 