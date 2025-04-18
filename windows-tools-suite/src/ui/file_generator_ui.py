import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QProgressBar, QTextEdit,
                            QFileDialog, QSpinBox, QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject
from ..core.file_generator import FileGenerator
from ..utils.logger import Logger

class ProgressSignal(QObject):
    """进度信号类"""
    progress = pyqtSignal(int, int, str)

class FileGeneratorUI(QWidget):
    """文件生成器UI类"""
    
    def __init__(self):
        """初始化UI"""
        super().__init__()
        self.logger = Logger("FileGeneratorUI")
        self.file_generator = FileGenerator()
        self.progress_signal = ProgressSignal()
        self.progress_signal.progress.connect(self.update_progress)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 目录选择
        dir_layout = QHBoxLayout()
        dir_label = QLabel('目录:')
        self.dir_edit = QLineEdit()
        self.dir_edit.setText(os.path.join(os.path.expanduser('~'), 'Desktop', 'generated_files'))
        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
        # 文件大小设置
        size_layout = QHBoxLayout()
        size_label = QLabel('文件大小 (字节):')
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 1000000000)  # 1B to 1GB
        self.size_spin.setValue(1024)  # 默认1KB
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)
        
        # 文件数量设置
        count_layout = QHBoxLayout()
        count_label = QLabel('文件数量:')
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10000)
        self.count_spin.setValue(10)
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_spin)
        layout.addLayout(count_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 状态显示
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton('开始生成')
        self.start_btn.clicked.connect(self.start_generation)
        self.stop_btn = QPushButton('停止生成')
        self.stop_btn.clicked.connect(self.stop_generation)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setWindowTitle('文件生成器')
        self.resize(500, 400)
    
    def browse_directory(self):
        """浏览目录"""
        directory = QFileDialog.getExistingDirectory(self, '选择目录')
        if directory:
            self.dir_edit.setText(directory)
    
    def progress_callback(self, current, total, message):
        """进度回调函数"""
        self.progress_signal.progress.emit(current, total, message)
    
    def update_progress(self, current, total, message):
        """更新进度信息"""
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        else:
            self.progress_bar.setValue(0)
            
        if message:
            self.status_text.append(message)
            # 滚动到底部
            self.status_text.verticalScrollBar().setValue(
                self.status_text.verticalScrollBar().maximum()
            )
        
        # 如果生成完成或停止，重置UI状态
        if current == total or current == 0:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def start_generation(self):
        """开始生成文件"""
        try:
            # 获取参数
            directory = self.dir_edit.text().strip()
            if not directory:
                QMessageBox.warning(self, '警告', '请选择目录')
                return
                
            file_size = self.size_spin.value()
            file_count = self.count_spin.value()
            
            # 更新UI状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_text.clear()
            self.progress_bar.setValue(0)
            
            # 开始生成
            self.file_generator.start_generation(
                directory,
                file_size,
                file_count,
                self.progress_callback
            )
            
        except Exception as e:
            self.logger.error(f"启动生成失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'启动生成失败: {str(e)}')
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def stop_generation(self):
        """停止生成文件"""
        try:
            self.stop_btn.setEnabled(False)
            self.status_text.append("正在停止...")
            self.file_generator.stop_generation()
            
        except Exception as e:
            self.logger.error(f"停止生成失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'停止生成失败: {str(e)}')
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        try:
            self.file_generator.stop_generation()
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭窗口时出错: {str(e)}")
            event.accept()