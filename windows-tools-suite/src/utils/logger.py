import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self, name="MD5Calculator"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 使用exe所在目录作为基准目录
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        
        # 创建logs目录
        logs_dir = os.path.join(base_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # 创建output目录
        output_dir = os.path.join(base_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 设置日志文件名（使用当前日期）
        log_file = os.path.join(logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        
        # 创建文件处理器，使用 RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,          # 保留5个备份
            encoding='utf-8',
            delay=True              # 延迟创建文件，直到第一次写入
        )
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(message) 