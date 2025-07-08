from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFileDialog, QLineEdit, QRadioButton, 
                           QButtonGroup, QComboBox, QMessageBox, QFrame, QGroupBox, QStyle, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import hashlib
import random
import time
import shutil
from ..utils.logger import get_logger
import re
from src.core.file_generator import FileGenerator
from src.utils.common import format_size
import yaml

# 配置日志
logger = get_logger(__name__)

class FileGeneratorWorker(QThread):
    """文件生成工作线程，调用核心逻辑类FileGenerator"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal()     # 完成信号
    stopped = pyqtSignal()      # 停止信号
    progress_value = pyqtSignal(int)  # 进度值信号
    
    def __init__(self, target_dir, file_size_min, file_size_max, 
                 size_unit, is_loop, max_files, interval):
        super().__init__()
        self.target_dir = target_dir
        self.file_size_min = file_size_min
        self.file_size_max = file_size_max
        self.size_unit = size_unit
        self.is_loop = is_loop
        self.max_files = max_files
        self.interval = interval
        self.is_running = True
        self.is_paused = False
        self.was_stopped = False
        self.total_size = 0
        self.round_number = 1
        self._pause_cond = None
        # 停止时的最后状态
        self.stopped_files_dir = None
        self.stopped_files_created = 0
        self.stopped_total_size = 0
        # 生成随机目录名
        random_suffix = ''.join(random.choices('0123456789ABCDEF', k=8))
        self.files_dir = os.path.join(self.target_dir, f'files_{random_suffix}')
        # 设置分块大小为10MB
        self.chunk_size = 10 * 1024 * 1024
        logger.info(f"工作线程初始化完成，参数：目录={self.files_dir}, 大小范围={file_size_min}-{file_size_max}{size_unit}, 循环={is_loop}, 文件数={max_files}, 间隔={interval}")
        
    def run(self):
        generator = FileGenerator(
            self.target_dir,
            self.file_size_min,
            self.file_size_max,
            self.size_unit,
            self.max_files,
            self.is_loop,
            self.interval
        )
        generator.generate_files(
            progress_callback=self._progress_callback,
            finished_callback=self._finished_callback,
            stop_flag=self._stop_flag,
            pause_flag=self._pause_flag,
            stopped_callback=self._stopped_callback
        )

    def _stop_flag(self):
        return not self.is_running

    def _pause_flag(self):
        return self.is_paused

    def _progress_callback(self, stage, files_dir, files_created, max_files, total_size, round_number):
        round_info = f"第{round_number}轮："
        if stage == 'start':
            msg = f"{round_info}开始{'新一轮' if self.is_loop else ''}文件生成\n文件生成目录：{files_dir}"
        elif stage == 'progress':
            percent = int((files_created / max_files) * 100) if max_files else 0
            self.progress_value.emit(percent)
            msg = (f"{round_info}文件生成目录：{files_dir}\n"
                   f"当前{'循环模式，' if self.is_loop else ''}已生成 {files_created} 个文件，共需要 {max_files} 个\n"
                   f"已生成文件总大小：{format_size(total_size)}\n")
        elif stage == 'finished':
            msg = (f"{round_info}{'本轮' if self.is_loop else ''}文件生成完成\n"
                   f"文件生成目录：{files_dir}\n"
                   f"共生成了 {files_created} 个文件\n"
                   f"文件总大小：{format_size(total_size)}")
        elif stage == 'loop_wait':
            msg = f"{round_info}等待3秒后开始下一轮文件生成..."
        else:
            msg = ""
        self.progress.emit(msg)

    def _finished_callback(self, files_dir, files_created, total_size):
        self.progress.emit(f"文件生成完成，目录：{files_dir}，共{files_created}个文件，总大小{total_size}字节")
        self.finished.emit()

    def _stopped_callback(self, files_dir, files_created, max_files, total_size, round_number):
        self.stopped_files_dir = files_dir
        self.stopped_files_created = files_created
        self.stopped_total_size = total_size
        self.stopped_max_files = max_files
        self.stopped_round_number = round_number
        self.stopped.emit()

    def stop(self):
        """停止生成"""
        self.is_running = False
        self.was_stopped = True
        
    def pause(self):
        """暂停生成"""
        self.is_paused = True
        
    def resume(self):
        """恢复生成"""
        self.is_paused = False

class FileGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.current_progress = 0  # 添加当前进度记录
        logger.info("初始化文件生成器UI")
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('本地文件产生器')
        self.setMinimumWidth(600)
        self.setMinimumHeight(660)  # 增加最小高度
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
            QComboBox {
                border: 1px solid #cccccc;  
                border-radius: 4px;
            }

            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QRadioButton {
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
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
        
        # 文件大小设置组
        size_group = QGroupBox("文件大小设置")
        size_layout = QHBoxLayout()
        size_layout.setSpacing(5)
        
        self.size_min = QLineEdit("1")
        self.size_min.setFixedWidth(60)
        
        self.size_unit = QComboBox()
        self.size_unit.addItems(['KB', 'MB', 'GB'])
        self.size_unit.setFixedWidth(85)
        self.size_unit.setFixedHeight(30)
        
        size_layout.addWidget(QLabel("大小范围:"))
        size_layout.addWidget(self.size_min)
        size_layout.addWidget(self.size_unit)
        size_layout.addWidget(QLabel("-"))
        
        self.size_max = QLineEdit("10")
        self.size_max.setFixedWidth(60)
        self.size_unit2 = QComboBox()
        self.size_unit2.addItems(['KB', 'MB', 'GB'])
        self.size_unit2.setFixedWidth(85)
        self.size_unit2.setFixedHeight(30)
        self.size_unit2.setStyleSheet(self.size_unit.styleSheet())
        self.size_unit2.view().setStyleSheet(self.size_unit.view().styleSheet())
        
        size_layout.addWidget(self.size_max)
        size_layout.addWidget(self.size_unit2)
        size_layout.addStretch()
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 产生模式设置组
        mode_group = QGroupBox("产生模式")
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(5)
        
        self.single_mode = QRadioButton("单次")
        self.loop_mode = QRadioButton("循环")
        self.single_mode.setChecked(True)
        
        mode_layout.addWidget(self.single_mode)
        mode_layout.addWidget(self.loop_mode)
        mode_layout.addStretch()
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 文件数量设置组
        limit_group = QGroupBox("文件数量设置")
        limit_layout = QHBoxLayout()
        limit_layout.setSpacing(5)
        
        self.limit_edit = QLineEdit("1000")
        self.limit_edit.setFixedWidth(80)
        
        limit_layout.addWidget(QLabel("文件数量上限:"))
        limit_layout.addWidget(self.limit_edit)
        limit_layout.addWidget(QLabel("个"))
        limit_layout.addStretch()
        
        limit_group.setLayout(limit_layout)
        layout.addWidget(limit_group)
        
        # 时间间隔设置组
        interval_group = QGroupBox("时间间隔设置")
        interval_layout = QHBoxLayout()
        interval_layout.setSpacing(5)
        
        self.interval_edit = QLineEdit("0.01")
        self.interval_edit.setFixedWidth(80)
        
        interval_layout.addWidget(QLabel("产生间隔:"))
        interval_layout.addWidget(self.interval_edit)
        interval_layout.addWidget(QLabel("秒"))
        interval_layout.addStretch()
        
        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)
        
        # 操作按钮组
        btn_group = QGroupBox("操作")
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # 定义按钮样式
        self.btn_style = {
            'blue': """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """,
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
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setFixedWidth(80)
        self.save_config_btn.setStyleSheet(self.btn_style['blue'])
        self.save_config_btn.clicked.connect(self.save_config)
        

        
        self.start_btn.clicked.connect(self.start_generation)
        self.pause_btn.clicked.connect(self.pause_generation)
        self.stop_btn.clicked.connect(self.stop_generation)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.save_config_btn)
        btn_layout.addStretch()
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # 状态显示组
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
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
        self.status_label.setWordWrap(True)  # 允许文本换行
        self.status_label.setMinimumHeight(60)  # 设置最小高度
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
            error_msg = "请选择目标目录"
            logger.warning(error_msg)
            self.update_error_status(error_msg)
            return False
            
        try:
            min_size = float(self.size_min.text())
            max_size = float(self.size_max.text())
            if min_size <= 0 or max_size <= 0 or min_size > max_size:
                raise ValueError
        except ValueError:
            error_msg = "请输入有效的文件大小范围"
            logger.warning(error_msg)
            self.update_error_status(error_msg)
            return False
            
        try:
            max_files = int(self.limit_edit.text())
            if max_files <= 0:
                raise ValueError
        except ValueError:
            error_msg = "请输入有效的文件数量上限"
            logger.warning(error_msg)
            self.update_error_status(error_msg)
            return False
            
        try:
            interval = float(self.interval_edit.text())
            if interval < 0:
                raise ValueError
        except ValueError:
            error_msg = "请输入有效的时间间隔"
            logger.warning(error_msg)
            self.update_error_status(error_msg)
            return False
            
        return True

    def update_error_status(self, message):
        """更新错误状态"""
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                min-height: 40px;
                color: #f44336;
                background-color: #ffebee;
                border: 1px solid #ffcdd2;
                border-radius: 4px;
                qproperty-wordWrap: true;
            }
        """)
        self.status_label.setText(message)
        self.status_label.adjustSize()

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

    def start_generation(self):
        logger.info("点击了开始生成按钮")
        
        if not self.validate_inputs():
            return
            
        if self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                # 从暂停状态恢复
                logger.info("从暂停状态恢复")
                self.worker.resume()
                self.set_running_state()
                # 移除状态中的暂停标记
                current_status = self.status_label.text()
                self.status_label.setText(current_status.replace("[已暂停]", ""))
            return
            
        try:
            # 创建并启动工作线程
            logger.info("创建工作线程")
            self.worker = FileGeneratorWorker(
                target_dir=self.dir_edit.text(),
                file_size_min=float(self.size_min.text()),
                file_size_max=float(self.size_max.text()),
                size_unit=self.size_unit.currentText(),
                is_loop=self.loop_mode.isChecked(),
                max_files=int(self.limit_edit.text()),
                interval=float(self.interval_edit.text())
            )
            
            # 连接信号
            logger.info("连接信号")
            self.worker.progress.connect(self.update_progress)
            self.worker.progress_value.connect(self.update_progress_bar)
            self.worker.finished.connect(self.generation_finished)
            self.worker.stopped.connect(self.generation_stopped)  # 添加停止信号连接
            
            # 更新状态
            status_msg = "正在准备生成文件..."
            logger.info(status_msg)
            self.status_label.setText(status_msg)
            self.progress_bar.setValue(0)
            self.current_progress = 0  # 重置当前进度
            
            # 启动线程
            logger.info("启动工作线程")
            self.worker.start()
            
            # 更新按钮状态
            logger.info("更新UI状态")
            self.set_running_state()
            
            # 禁用输入控件
            self.disable_inputs(True)
            
        except Exception as e:
            error_msg = f"启动生成过程时出错: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def pause_generation(self):
        logger.info("点击了暂停/继续按钮")
        if self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                logger.info("继续生成")
                self.worker.resume()
                self.set_running_state()
            else:
                logger.info("暂停生成")
                self.worker.pause()
                self.set_paused_state()
                # 在状态标签的当前文本后添加暂停状态
                current_status = self.status_label.text()
                self.status_label.setText(current_status + "[已暂停]")

    def stop_generation(self):
        logger.info("点击了停止按钮")
        if self.worker and self.worker.isRunning():
            logger.info("停止生成")
            self.worker.stop()
            self.set_initial_state()
            # 保持当前进度值，添加停止状态提示
            current_progress = self.progress_bar.value()
            self.status_label.setText(f"已停止生成 - 进度 {current_progress}%")
            self.disable_inputs(False)

    def update_progress(self, message):
        logger.debug(f"进度更新: {message}")
        self.setWindowTitle('本地文件产生器')
        # 按钮状态控制
        if "等待3秒后开始下一轮" in message or ("开始" in message and "文件生成目录" in message):
            self.set_running_state()
        # 根据消息类型设置不同的样式
        if "错误" in message or "已存在" in message:
            self.update_error_status(message)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    min-height: 40px;
                    qproperty-wordWrap: true;
                }
            """)
            self.status_label.setText(message)
            self.status_label.adjustSize()
        
    def update_progress_bar(self, value):
        """更新进度条"""
        self.current_progress = value  # 记录当前进度
        self.progress_bar.setValue(value)
        
    def generation_stopped(self):
        """生成停止的处理"""
        logger.info("生成已停止")
        self.set_initial_state()
        self.disable_inputs(False)
        self.setWindowTitle('本地文件产生器')
        self.progress_bar.setValue(self.current_progress)
        # 获取最后状态
        files_dir = getattr(self.worker, 'stopped_files_dir', None)
        files_created = getattr(self.worker, 'stopped_files_created', 0)
        total_size = getattr(self.worker, 'stopped_total_size', 0)
        round_number = getattr(self.worker, 'stopped_round_number', 1)
        # 显示详细停止信息
        if files_dir:
            msg = (f"第{round_number}轮：文件生成已停止\n"
                   f"文件生成目录：{files_dir}\n"
                   f"共生成了 {files_created} 个文件\n"
                   f"文件总大小：{format_size(total_size)}（已停止）")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    min-height: 40px;
                    color: #FF5722;
                    background-color: #FBE9E7;
                    border: 1px solid #FFCCBC;
                    border-radius: 4px;
                    qproperty-wordWrap: true;
                }
            """)
            self.status_label.setText(msg)
        else:
            # 兜底：原有逻辑
            current_status = self.status_label.text()
            self.status_label.setText(current_status + "[已停止]")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    min-height: 40px;
                    color: #FF5722;
                    background-color: #FBE9E7;
                    border: 1px solid #FFCCBC;
                    border-radius: 4px;
                    qproperty-wordWrap: true;
                }
            """)

    def generation_finished(self):
        """生成完成的处理"""
        self.set_initial_state()
        self.disable_inputs(False)
        self.setWindowTitle('本地文件产生器')
        self.progress_bar.setValue(100)
        
        # 如果状态中没有显示目录信息（比如出错的情况），就不改变状态文本
        current_status = self.status_label.text()
        if not ("已存在" in current_status or "错误" in current_status):
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    min-height: 40px;
                    color: #4CAF50;
                    background-color: #E8F5E9;
                    border: 1px solid #C8E6C9;
                    border-radius: 4px;
                    qproperty-wordWrap: true;
                }
            """)

    def disable_inputs(self, disabled):
        """禁用/启用输入控件"""
        self.dir_edit.setEnabled(not disabled)
        self.size_min.setEnabled(not disabled)
        self.size_max.setEnabled(not disabled)
        self.size_unit.setEnabled(not disabled)
        self.size_unit2.setEnabled(not disabled)
        self.single_mode.setEnabled(not disabled)
        self.loop_mode.setEnabled(not disabled)
        self.limit_edit.setEnabled(not disabled)
        self.interval_edit.setEnabled(not disabled)

    def save_config(self):
        if not self.dir_edit.text():
            QMessageBox.warning(self, "警告", "请先选择目标目录后再保存配置！")
            return
        # 转换为字节并保存原始单位
        config = {
            'target_dir': self.dir_edit.text(),
            'file_size_min': self.size_min.text(),
            'file_size_max': self.size_max.text(),
            'file_size_min_unit': self.size_unit.currentText(),
            'file_size_max_unit': self.size_unit2.currentText(),
            'mode': '循环' if self.loop_mode.isChecked() else '单次',
            'max_files': self.limit_edit.text(),
            'interval': self.interval_edit.text(),
        }
        exe_dir = os.path.dirname(sys.argv[0])
        file_path = os.path.join(exe_dir, "filegen_config.yaml")
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, allow_unicode=True)
        QMessageBox.information(self, "保存成功", f"配置已保存到: {file_path}")

