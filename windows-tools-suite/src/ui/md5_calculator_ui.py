import os
import sys
import time
import threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QProgressBar, QTextEdit,
                            QFileDialog, QComboBox, QSpinBox, QCheckBox,
                            QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from ..core.md5_calculator import MD5Calculator
from ..utils.logger import Logger

class ProgressSignal(QObject):
    """进度信号类"""
    progress = pyqtSignal(int, int, str)

class MD5CalculatorUI(QWidget):
    """MD5计算器UI类"""
    def __init__(self):
        super().__init__()
        self.logger = Logger("MD5CalculatorUI")
        self.md5_calculator = MD5Calculator()
        self.progress_signal = ProgressSignal()
        self.progress_signal.progress.connect(self.update_progress)
        self.md5_calculator.set_progress_callback(self.progress_callback)
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 目录选择
        dir_layout = QHBoxLayout()
        dir_label = QLabel('目录:')
        self.dir_edit = QLineEdit()
        self.dir_edit.setText(self.md5_calculator.default_directory)
        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
        # 文件扩展名
        ext_layout = QHBoxLayout()
        ext_label = QLabel('文件扩展名:')
        self.ext_edit = QLineEdit()
        self.ext_edit.setText('.exe, .dll, .sys')
        ext_layout.addWidget(ext_label)
        ext_layout.addWidget(self.ext_edit)
        layout.addLayout(ext_layout)
        
        # 排除关键字
        exclude_layout = QHBoxLayout()
        exclude_label = QLabel('排除关键字:')
        self.exclude_edit = QLineEdit()
        exclude_layout.addWidget(exclude_label)
        exclude_layout.addWidget(self.exclude_edit)
        layout.addLayout(exclude_layout)
        
        # 时间选择
        time_layout = QHBoxLayout()
        
        # 时间类型选择
        time_type_label = QLabel('时间类型:')
        self.time_type_combo = QComboBox()
        self.time_type_combo.addItems(['修改时间', '创建时间', '访问时间'])
        time_layout.addWidget(time_type_label)
        time_layout.addWidget(self.time_type_combo)
        
        # 排除时间
        exclude_time_label = QLabel('排除时间(小时):')
        self.exclude_time_spin = QSpinBox()
        self.exclude_time_spin.setRange(0, 999999)
        self.exclude_time_spin.setValue(4)
        time_layout.addWidget(exclude_time_label)
        time_layout.addWidget(self.exclude_time_spin)
        
        layout.addLayout(time_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 状态显示
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton('开始')
        self.start_btn.clicked.connect(self.start_calculation)
        self.stop_btn = QPushButton('停止')
        self.stop_btn.clicked.connect(self.stop_calculation)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setWindowTitle('MD5计算器')
        self.resize(600, 400)
        
        # 添加工作线程属性
        self.worker_thread = None
        self.is_running = False
    
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
        self.status_text.append(message)
        # 滚动到底部
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def start_calculation(self):
        """开始计算"""
        try:
            # 获取目录
            directory = self.dir_edit.text().strip()
            if not directory:
                QMessageBox.warning(self, '警告', '请选择目录')
                return
            if not os.path.exists(directory):
                QMessageBox.warning(self, '警告', '目录不存在')
                return
            
            # 获取文件扩展名
            extensions = [ext.strip() for ext in self.ext_edit.text().split(',')]
            if not extensions:
                QMessageBox.warning(self, '警告', '请输入文件扩展名')
                return
            
            # 获取排除关键字
            exclude_keywords = [kw.strip() for kw in self.exclude_edit.text().split(',') if kw.strip()]
            
            # 获取时间类型
            time_type_map = {
                '修改时间': 'modified',
                '创建时间': 'created',
                '访问时间': 'accessed'
            }
            time_type = time_type_map[self.time_type_combo.currentText()]
            
            # 获取排除时间
            exclude_hours = self.exclude_time_spin.value()
            
            # 更新UI状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.is_running = True
            
            # 清空状态显示
            self.status_text.clear()
            
            # 创建并启动工作线程
            self.worker_thread = threading.Thread(
                target=self.calculation_worker,
                args=(directory, extensions, exclude_hours, exclude_keywords, time_type)
            )
            self.worker_thread.start()
            
        except Exception as e:
            self.logger.error(f"启动计算失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'启动计算失败: {str(e)}')
            self.reset_ui()
    
    def calculation_worker(self, directory, extensions, exclude_hours, exclude_keywords, time_type):
        """计算工作线程"""
        try:
            # 执行扫描
            output_file = self.md5_calculator.scan_directory(
                directory, extensions, exclude_hours, exclude_keywords, time_type
            )
            
            # 在主线程中显示完成消息
            if output_file:
                self.progress_signal.progress.emit(
                    100, 100,
                    f"计算完成！结果已保存到: {output_file}"
                )
            
        except Exception as e:
            self.logger.error(f"计算过程出错: {str(e)}")
            self.progress_signal.progress.emit(0, 0, f"错误: {str(e)}")
        finally:
            self.is_running = False
            # 重置UI状态
            self.progress_signal.progress.emit(-1, -1, "")  # 特殊信号用于重置UI
    
    def stop_calculation(self):
        """停止计算"""
        self.is_running = False
        self.status_text.append("正在停止...")
        self.stop_btn.setEnabled(False)
    
    def reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.is_running:
            reply = QMessageBox.question(
                self, '确认',
                '计算正在进行中，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.is_running = False
                if self.worker_thread and self.worker_thread.is_alive():
                    self.worker_thread.join(2)  # 等待最多2秒
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()