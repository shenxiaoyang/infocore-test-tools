from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFileDialog, QLineEdit, QFrame, QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import hashlib
import logging
from datetime import datetime
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileVerifyWorker(QThread):
    """文件校验工作线程"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal()     # 完成信号
    progress_value = pyqtSignal(int)  # 进度值信号
    stats_update = pyqtSignal(int, int, int)  # 统计信息信号：总数、成功数、失败数
    
    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = target_dir
        self.reset()
        
    def reset(self):
        """重置所有状态"""
        self.is_running = True
        self.is_paused = False
        self.total_files = 0
        self.checked_files = 0
        self.success_files = 0
        self.error_files = []
        
    def calculate_md5(self, file_path):
        """计算文件的MD5值"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def run(self):
        logger.info(f"开始校验目录: {self.target_dir}")
        
        try:
            # 统计.md5file文件总数
            for root, _, files in os.walk(self.target_dir):
                for file in files:
                    if file.endswith('.md5file'):
                        self.total_files += 1
            
            if self.total_files == 0:
                self.progress.emit("所选目录中无可校验的.md5file文件")
                return
                
            self.progress.emit(f"找到 {self.total_files} 个.md5file文件，开始校验...")
            
            # 创建output目录（在exe所在目录下）
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(output_dir, f'verify_result_{timestamp}.txt')
            
            # 遍历目录进行校验
            for root, _, files in os.walk(self.target_dir):
                for file in files:
                    if not self.is_running:
                        break
                        
                    if self.is_paused:
                        while self.is_paused and self.is_running:
                            self.msleep(100)
                            
                    if file.endswith('.md5file'):
                        file_path = os.path.join(root, file)
                        # 兼容 编号.md5.md5file、md5.编号.md5file 和 md5.md5file
                        parts = file.split('.')
                        if len(parts) == 3 and parts[2] == 'md5file':
                            # 形如 编号.md5.md5file 或 md5.编号.md5file
                            if parts[0].isdigit():
                                expected_md5 = parts[1]
                            else:
                                expected_md5 = parts[0]
                        else:
                            expected_md5 = file[:-8]  # 兼容老格式
                        actual_md5 = self.calculate_md5(file_path)
                        
                        self.checked_files += 1
                        progress = int((self.checked_files / self.total_files) * 100)
                        self.progress_value.emit(progress)
                        
                        if expected_md5 != actual_md5:
                            error_info = f"文件: {file_path} 实际MD5: {actual_md5}\n"
                            self.error_files.append(error_info)
                            self.progress.emit(f"发现不一致文件: {file_path}")
                        else:
                            self.success_files += 1
                            
                        # 发送统计信息更新
                        self.stats_update.emit(self.total_files, self.success_files, len(self.error_files))
            
            # 写入结果
            if self.error_files:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"校验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"目标目录: {self.target_dir}\n")
                    f.write(f"共检查 {self.checked_files} 个文件，发现 {len(self.error_files)} 个不一致文件\n\n")
                    f.write("不一致文件列表:\n")
                    f.writelines(self.error_files)
                    
                self.progress.emit(f"校验完成，发现 {len(self.error_files)} 个不一致文件，结果已保存到: {output_file}")
            else:
                self.progress.emit(f"校验完成，所有文件MD5值一致")
                
        except Exception as e:
            self.progress.emit(f"校验过程出错: {str(e)}")
        finally:
            self.finished.emit()
            
    def stop(self):
        """停止校验"""
        self.is_running = False
        
    def pause(self):
        """暂停校验"""
        self.is_paused = True
        
    def resume(self):
        """恢复校验"""
        self.is_paused = False

class FileVerifyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        logger.info("初始化文件校验器UI")
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('文件校验器')
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei, Arial;
                font-size: 9pt;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        
        # 目标目录选择组
        dir_group = QGroupBox("目标目录")
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(5)
        
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        dir_btn = QPushButton("选择目录")
        dir_btn.setFixedWidth(80)
        dir_btn.clicked.connect(self.select_directory)
        
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(dir_btn)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 操作按钮组
        btn_group = QGroupBox("操作")
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # 定义按钮样式
        self.btn_style = {
            'green': """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """,
            'yellow': """
                QPushButton {
                    background-color: #FFC107;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #FFA000;
                }
                QPushButton:pressed {
                    background-color: #FF8F00;
                }
            """,
            'red': """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:pressed {
                    background-color: #d32f2f;
                }
            """,
            'gray': """
                QPushButton {
                    background-color: #9E9E9E;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:disabled {
                    background-color: #CCCCCC;
                }
            """
        }
        
        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedWidth(80)
        self.start_btn.setStyleSheet(self.btn_style['green'])
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setFixedWidth(80)
        self.pause_btn.setStyleSheet(self.btn_style['gray'])
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setStyleSheet(self.btn_style['gray'])
        self.stop_btn.setEnabled(False)
        
        self.start_btn.clicked.connect(self.start_verify)
        self.pause_btn.clicked.connect(self.pause_verify)
        self.stop_btn.clicked.connect(self.stop_verify)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # 状态显示组
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
        # 添加统计信息显示
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # 总数显示
        self.total_label = QLabel("总数: 0")
        self.total_label.setStyleSheet("""
            QLabel {
                color: #2f3640;
                font-weight: bold;
            }
        """)
        
        # 成功数显示
        self.success_label = QLabel("成功: 0")
        self.success_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
            }
        """)
        
        # 失败数显示
        self.failed_label = QLabel("失败: 0")
        self.failed_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-weight: bold;
            }
        """)
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.success_label)
        stats_layout.addWidget(self.failed_label)
        stats_layout.addStretch()
        
        stats_frame.setLayout(stats_layout)
        status_layout.addWidget(stats_frame)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                min-height: 40px;
                qproperty-wordWrap: true;
            }
        """)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(60)
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
    def select_directory(self):
        """选择目标目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if dir_path:
            self.dir_edit.setText(dir_path)
            
    def validate_inputs(self):
        """验证输入"""
        if not self.dir_edit.text():
            self.status_label.setText("请选择目标目录")
            return False
        return True
        
    def set_running_state(self):
        """设置运行状态的按钮样式"""
        self.start_btn.setStyleSheet(self.btn_style['gray'])
        self.start_btn.setEnabled(False)
        self.start_btn.setText("开始")
        self.pause_btn.setStyleSheet(self.btn_style['yellow'])
        self.pause_btn.setEnabled(True)
        self.stop_btn.setStyleSheet(self.btn_style['red'])
        self.stop_btn.setEnabled(True)

    def set_paused_state(self):
        """设置暂停状态的按钮样式"""
        self.start_btn.setStyleSheet(self.btn_style['green'])
        self.start_btn.setEnabled(True)
        self.start_btn.setText("继续")
        self.pause_btn.setStyleSheet(self.btn_style['gray'])
        self.pause_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self.btn_style['red'])
        self.stop_btn.setEnabled(True)

    def set_initial_state(self):
        """设置初始状态的按钮样式"""
        self.start_btn.setStyleSheet(self.btn_style['green'])
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始")
        self.pause_btn.setStyleSheet(self.btn_style['gray'])
        self.pause_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self.btn_style['gray'])
        self.stop_btn.setEnabled(False)

    def start_verify(self):
        """开始校验"""
        if not self.validate_inputs():
            return
            
        if self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                self.worker.resume()
                self.set_running_state()
                # 移除状态中的暂停标记
                current_status = self.status_label.text()
                self.status_label.setText(current_status.replace("\n[已暂停]", ""))
            return
            
        try:
            # 重置所有显示状态
            self.progress_bar.setValue(0)
            self.total_label.setText("总数: 0")
            self.success_label.setText("成功: 0")
            self.failed_label.setText("失败: 0")
            self.status_label.setText("正在准备校验...")
            
            self.worker = FileVerifyWorker(self.dir_edit.text())
            self.worker.progress.connect(self.update_progress)
            self.worker.progress_value.connect(self.update_progress_bar)
            self.worker.finished.connect(self.verify_finished)
            self.worker.stats_update.connect(self.update_stats)
            
            self.set_running_state()
            self.dir_edit.setEnabled(False)
            
            self.worker.start()
            
        except Exception as e:
            self.status_label.setText(f"启动校验过程时出错: {str(e)}")
            
    def pause_verify(self):
        """暂停校验"""
        if self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                self.worker.resume()
                self.set_running_state()
                # 移除状态中的暂停标记
                current_status = self.status_label.text()
                self.status_label.setText(current_status.replace("\n[已暂停]", ""))
            else:
                self.worker.pause()
                self.set_paused_state()
                # 在状态标签的当前文本后添加暂停状态
                current_status = self.status_label.text()
                self.status_label.setText(current_status + "\n[已暂停]")
                
    def stop_verify(self):
        """停止校验"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.set_initial_state()
            self.dir_edit.setEnabled(True)
            self.status_label.setText("已停止校验")
            
    def update_progress(self, message):
        """更新进度信息"""
        self.status_label.setText(message)
        
    def update_progress_bar(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def update_stats(self, total, success, failed):
        """更新统计信息"""
        self.total_label.setText(f"总数: {total}")
        self.success_label.setText(f"成功: {success}")
        self.failed_label.setText(f"失败: {failed}")
        
    def verify_finished(self):
        """校验完成的处理"""
        self.set_initial_state()
        self.dir_edit.setEnabled(True) 