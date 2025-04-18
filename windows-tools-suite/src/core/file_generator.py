import os
import random
import string
import threading
from ..utils.logger import Logger

class FileGeneratorWorker:
    """文件生成器工作类"""
    
    def __init__(self, files_dir, file_size, file_count):
        """
        初始化文件生成器工作类
        
        Args:
            files_dir: 文件生成目录
            file_size: 文件大小（字节）
            file_count: 文件数量
        """
        self.files_dir = files_dir
        self.file_size = file_size
        self.file_count = file_count
        self.logger = Logger("FileGeneratorWorker")
        self.is_running = False
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def update_progress(self, current, total, message):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def generate_random_content(self, size):
        """生成随机内容"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(size)).encode()
    
    def run(self):
        """运行生成器"""
        try:
            self.is_running = True
            
            # 创建目录
            if not os.path.exists(self.files_dir):
                os.makedirs(self.files_dir)
            
            # 生成文件
            for i in range(self.file_count):
                if not self.is_running:
                    break
                
                # 生成文件内容
                content = self.generate_random_content(self.file_size)
                
                # 计算文件名（使用内容的部分作为文件名）
                filename = f"{i + 1}.md5file"
                file_path = os.path.join(self.files_dir, filename)
                
                # 写入文件
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # 更新进度
                self.update_progress(
                    i + 1,
                    self.file_count,
                    f"已生成文件: {file_path}"
                )
            
            if self.is_running:
                self.update_progress(
                    self.file_count,
                    self.file_count,
                    "文件生成完成！"
                )
            else:
                self.update_progress(
                    0, 0,
                    "文件生成已停止。"
                )
                
        except Exception as e:
            self.logger.error(f"生成文件时出错: {str(e)}")
            self.update_progress(0, 0, f"错误: {str(e)}")
        finally:
            self.is_running = False

class FileGenerator:
    """文件生成器类"""
    
    def __init__(self):
        """初始化文件生成器"""
        self.logger = Logger("FileGenerator")
        self.worker = None
        self.worker_thread = None
    
    def start_generation(self, files_dir, file_size, file_count, progress_callback=None):
        """
        开始生成文件
        
        Args:
            files_dir: 文件生成目录
            file_size: 文件大小（字节）
            file_count: 文件数量
            progress_callback: 进度回调函数
        """
        try:
            # 创建工作对象
            self.worker = FileGeneratorWorker(files_dir, file_size, file_count)
            if progress_callback:
                self.worker.set_progress_callback(progress_callback)
            
            # 创建并启动工作线程
            self.worker_thread = threading.Thread(target=self.worker.run)
            self.worker_thread.start()
            
        except Exception as e:
            self.logger.error(f"启动文件生成失败: {str(e)}")
            raise
    
    def stop_generation(self):
        """停止生成文件"""
        if self.worker:
            self.worker.is_running = False
            
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join()