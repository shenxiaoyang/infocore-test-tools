from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QFileDialog, QMessageBox,
                             QProgressBar, QGroupBox, QMenu, QFrame, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from ..core.md5_calculator import MD5Calculator
from ..utils.logger import Logger
import os
import traceback  # 添加 traceback 模块

class MD5CalculatorWorker(QThread):
    """后台工作线程，用于执行MD5计算"""
    progress = pyqtSignal(str)
    progress_count = pyqtSignal(int, int, str)  # 当前处理数, 总数, 状态信息
    finished = pyqtSignal()  # 移除 dict 参数
    error = pyqtSignal(str)
    
    def __init__(self, calculator, directories, extensions, exclude_hours=24, exclude_keywords=[], time_type='modified'):
        super().__init__()
        self.calculator = calculator  # 使用传入的calculator实例
        self.directories = directories
        self.extensions = extensions
        self.exclude_hours = exclude_hours
        self.exclude_keywords = exclude_keywords
        self.time_type = time_type
        self.logger = Logger("MD5CalculatorWorker")
        # 设置进度回调
        self.calculator.set_progress_callback(self.update_progress)
        self.is_running = True
    
    def update_progress(self, current, total, message):
        """更新进度信息"""
        if self.is_running:  # 只在运行状态下发送进度信号
            self.progress_count.emit(current, total, message)
    
    def run(self):
        try:
            # 遍历所有目录
            for directory in self.directories:
                if not self.is_running:
                    self.logger.info("计算被用户终止")
                    break
                    
                self.logger.info(f"开始处理目录: {directory}")
                self.progress.emit(f"正在处理目录: {directory}")
                
                # scan_directory 方法会自动保存结果并返回输出文件路径
                output_file = self.calculator.scan_directory(
                    directory, 
                    self.extensions, 
                    self.exclude_hours, 
                    self.exclude_keywords,
                    self.time_type
                )
            
            if self.is_running:  # 只在运行状态下发送完成信号
                self.logger.info("所有目录处理完成")
                self.finished.emit()  # 不再传递结果字典
                
        except Exception as e:
            error_msg = f"处理过程中出现错误: {str(e)}\n调用栈信息:\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            self.error.emit(str(e))
    
    def terminate(self):
        """停止处理"""
        self.is_running = False
        self.logger.info("正在终止计算线程...")
        super().terminate()

class MD5CalculatorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.calculator = MD5Calculator()
        self.logger = Logger("MD5CalculatorUI")
        self.default_exclude_keywords = [
            "balloon.sys", "blnsvr.exe", "netkvm.sys", "vioser.sys", 
            "viostor.sys", "E1G6032E.sys", "Wdfcoinstaller01005.dll",
            "Wdfcoinstaller01007.dll", "Wdfcoinstaller01009.dll",
            "WdfCoInstaller01011.dll", r"Windows\assembly",
        ]
        self.worker = None  # 添加worker属性
        self.setMinimumWidth(800)  # 设置最小宽度
        self.setMinimumHeight(600)  # 设置最小高度
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        
        # 目录选择区域
        dir_group = QGroupBox("目录列表")
        dir_group.setStyleSheet("""
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
        """)
        dir_layout = QVBoxLayout()
        dir_layout.setSpacing(5)
        
        # 添加目录按钮
        self.add_btn = QPushButton("添加目录")
        self.add_btn.setFixedWidth(80)
        self.add_btn.setStyleSheet("""
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
        """)
        self.add_btn.clicked.connect(self.add_directory)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addStretch()
        dir_layout.addLayout(btn_layout)
        
        # 目录列表
        self.dir_list = QListWidget()
        self.dir_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
            }
        """)
        self.dir_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_list.customContextMenuRequested.connect(self.show_context_menu)
        self.dir_list.addItem(self.calculator.default_directory)
        dir_layout.addWidget(self.dir_list)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 设置区域
        settings_group = QGroupBox("设置")
        settings_group.setStyleSheet("""
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
        """)
        settings_layout = QVBoxLayout()  # 改为垂直布局
        
        # 文件扩展名设置（单独一行）
        ext_layout = QHBoxLayout()
        ext_label = QLabel("文件扩展名:")
        ext_label.setFixedWidth(80)
        self.ext_input = QLineEdit()
        self.ext_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        self.ext_input.setText(",".join(self.calculator.default_extensions))
        ext_layout.addWidget(ext_label)
        ext_layout.addWidget(self.ext_input)
        settings_layout.addLayout(ext_layout)
        
        # 时间排除设置（单独一行）
        time_layout = QHBoxLayout()
        time_label = QLabel("时间排除:")
        time_label.setFixedWidth(80)
        self.time_input = QLineEdit()
        self.time_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        self.time_input.setFixedWidth(50)
        self.time_input.setText("4")
        
        # 添加时间类型选择
        self.time_type_combo = QComboBox()
        self.time_type_combo.addItems(["修改时间", "创建时间", "访问时间"])
        self.time_type_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_input)
        time_layout.addWidget(QLabel("小时内的"))
        time_layout.addWidget(self.time_type_combo)
        time_layout.addStretch()
        settings_layout.addLayout(time_layout)
        
        # 添加关键字排除设置（单独一行）
        exclude_layout = QHBoxLayout()
        exclude_label = QLabel("排除关键字:")
        exclude_label.setFixedWidth(80)
        self.exclude_input = QLineEdit()
        self.exclude_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-height: 25px;
            }
        """)
        self.exclude_input.setText(",".join(self.default_exclude_keywords))
        exclude_layout.addWidget(exclude_label)
        exclude_layout.addWidget(self.exclude_input)
        settings_layout.addLayout(exclude_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 操作按钮区域
        btn_group = QGroupBox("操作")
        btn_group.setStyleSheet("""
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
        """)
        btn_layout = QHBoxLayout()
        
        # 开始计算按钮
        self.calc_btn = QPushButton("开始计算")
        self.calc_btn.setFixedWidth(80)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.calc_btn.clicked.connect(self.start_calculation)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_calculation)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.calc_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # 状态区域
        status_group = QGroupBox("状态")
        status_group.setStyleSheet("""
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
        """)
        status_layout = QVBoxLayout()
        
        # 状态标签
        self.status_label = QLabel()
        self.status_label.setStyleSheet("padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        # 进度标签
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("padding: 5px;")
        status_layout.addWidget(self.progress_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 设置窗口属性
        self.setWindowTitle("MD5一致性计算器")
        self.setMinimumWidth(700)
        self.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei, Arial;
                font-size: 9pt;
            }
        """)
        
        self.logger.info("MD5计算器UI初始化完成")
    
    def add_directory(self):
        """添加目录到列表"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录")
        if dir_path:
            self.dir_list.addItem(dir_path)
            self.logger.info(f"添加目录到列表: {dir_path}")
    
    def start_calculation(self):
        self.calculator.reset()
        # 获取所有目录
        directories = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
        if not directories:
            QMessageBox.warning(self, "警告", "请至少添加一个目录")
            return
        
        # 获取文件扩展名
        extensions = [ext.strip() for ext in self.ext_input.text().split(",")]
        if not extensions:
            QMessageBox.warning(self, "警告", "请输入至少一个文件扩展名")
            return
        
        # 获取时间排除设置
        try:
            exclude_hours = float(self.time_input.text())
        except ValueError:
            QMessageBox.warning(self, "警告", "时间排除必须是数字")
            return
            
        # 获取时间类型
        time_type_map = {
            "修改时间": "modified",
            "创建时间": "created",
            "访问时间": "accessed"
        }
        time_type = time_type_map[self.time_type_combo.currentText()]
        
        # 获取排除关键字
        exclude_keywords = [k.strip() for k in self.exclude_input.text().split(",") if k.strip()]
        
        # 创建工作线程
        self.worker = MD5CalculatorWorker(self.calculator, directories, extensions, exclude_hours, exclude_keywords, time_type)
        self.worker.progress.connect(self.update_status)
        self.worker.progress_count.connect(self.update_progress)
        self.worker.finished.connect(self.calculation_finished)  # 不再传递参数
        self.worker.error.connect(self.calculation_error)
        
        # 禁用相关按钮
        self.calc_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("开始计算...")
        self.progress_label.setText("")
        self.worker.start()
    
    def stop_calculation(self):
        """停止计算"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.calc_btn.setEnabled(True)
            self.add_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("计算已停止")
    
    def update_status(self, message):
        self.status_label.setText(message)
        self.logger.info(message)
    
    def update_progress(self, current, total, message):
        """更新进度显示"""
        # 更新进度标签
        self.progress_label.setText(message)
        
        # 更新状态标签
        current_dir = self.worker.calculator.current_directory if hasattr(self.worker, 'calculator') else ""
        if current_dir:
            self.status_label.setText(f"正在处理目录: {current_dir}")
    
    def calculation_finished(self):
        try:
            # 获取最后一次保存的文件路径
            filename = self.calculator.output_file
            if not filename:
                # 如果没有输出文件，可能是因为计算被终止
                self.status_label.setText("计算已完成")
                self.logger.info("计算完成，但没有生成输出文件（可能是因为计算被终止或没有找到符合条件的文件）")
                return
                
            self.status_label.setText(f"计算完成！结果已保存到 {filename}")
            self.logger.info(f"计算完成，结果保存到: {filename}")
            QMessageBox.information(self, "完成", 
                                  f"MD5计算已完成！\n结果已保存到 {filename}")
        except Exception as e:
            error_msg = f"计算完成处理时出错: {str(e)}\n调用栈信息:\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            self.calculation_error(str(e))
        finally:
            self.calc_btn.setEnabled(True)
            self.add_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def calculation_error(self, error_message):
        error_msg = f"错误: {error_message}\n调用栈信息:\n{traceback.format_exc()}"
        self.status_label.setText(f"错误: {error_message}")
        self.logger.error(error_msg)
        QMessageBox.critical(self, "错误", f"计算过程中出现错误：\n{error_message}")
        self.calc_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self.remove_selected_directory)
        
        # 获取点击位置的项目
        item = self.dir_list.itemAt(position)
        if item is None:
            delete_action.setEnabled(False)
        
        menu.exec_(self.dir_list.mapToGlobal(position))
    
    def remove_selected_directory(self):
        """删除选中的目录"""
        selected_items = self.dir_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.dir_list.takeItem(self.dir_list.row(item))

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()  # 等待线程完全终止
            self.logger.info("计算线程已终止")
        event.accept() 