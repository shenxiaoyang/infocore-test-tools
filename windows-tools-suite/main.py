import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QFrame, QMessageBox, QHBoxLayout, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from src.ui.md5_calculator_ui import MD5CalculatorUI
from src.ui.file_compare_ui import FileCompareUI
from src.ui.file_generator_ui import FileGeneratorUI
from src.ui.file_verify_ui import FileVerifyUI
import yaml
import threading

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), 'src', 'resources', 'icons', 'app.ico')
        self.setWindowIcon(QIcon(icon_path))
        # 添加窗口实例属性
        self.md5_calculator_window = None
        self.file_compare_window = None
        self.file_generator_window = None
        self.file_verify_window = None
        
        self.setWindowTitle("Windows工具集")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QWidget {
                font-family: Microsoft YaHei, Arial;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #2f3640;
            }
            QPushButton:hover {
                background-color: #f1f2f6;
                border-color: #7f8fa6;
            }
            QPushButton:pressed {
                background-color: #dcdde1;
            }
            QPushButton:disabled {
                background-color: #f1f2f6;
                color: #a5a5a5;
                border-color: #dcdde1;
            }
        """)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建垂直布局
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 20, 40, 20)  # 减小上下边距
        central_widget.setLayout(layout)
        
        # 添加标题
        title_container = QFrame()
        title_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 10px;
            }
        """)
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 修改subtitle为类属性，以便在其他方法中访问
        self.subtitle = QLabel("便捷实用的Windows工具箱")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("""
            font-size: 16px;
            color: #7f8fa6;
            margin-top: 5px;
        """)

        title_layout.addWidget(self.subtitle)
        title_container.setLayout(title_layout)
        layout.addWidget(title_container)
        
        # 工具卡片容器
        tools_container = QFrame()
        tools_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 25px;
            }
        """)
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(10)  # 增加工具之间的间距
        tools_container.setLayout(tools_layout)
        
        # 创建MD5计算器及其快速功能按钮的水平布局
        md5_container = QFrame()
        md5_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        md5_layout = QHBoxLayout()
        md5_layout.setSpacing(10)
        md5_layout.setContentsMargins(0, 0, 0, 0)
        md5_container.setLayout(md5_layout)
        
        # 添加MD5计算器按钮
        md5_btn = QPushButton("MD5一致性计算器")
        md5_btn.setMinimumHeight(56)  # 只设置高度
        md5_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 宽度自适应
        md5_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #f5f6fa;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        # 添加鼠标悬停事件
        md5_btn.enterEvent = lambda e: self.update_subtitle("MD5一致性计算器用于计算选定目录的MD5值")
        md5_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        md5_btn.clicked.connect(self.open_md5_calculator)
        md5_layout.addWidget(md5_btn, stretch=7)
        
        # 添加快速计算系统盘按钮
        system_disk_btn = QPushButton("快速计算系统盘")
        system_disk_btn.setMinimumHeight(56)
        system_disk_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        system_disk_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        # 添加鼠标悬停事件
        system_disk_btn.enterEvent = lambda e: self.update_subtitle("快速计算系统盘Windows目录下dll、sys、exe文件的MD5值")
        system_disk_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        system_disk_btn.clicked.connect(self.open_system_disk_calculator)
        md5_layout.addWidget(system_disk_btn, stretch=3)
        
        # 将MD5容器添加到工具布局
        tools_layout.addWidget(md5_container)
        
        # 添加文件对比功能容器
        compare_container = QFrame()
        compare_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                padding: 0px;
            }
        """)
        compare_layout = QVBoxLayout()
        compare_layout.setContentsMargins(20, 0, 20, 20)
        compare_container.setLayout(compare_layout)
        
        # 添加文件对比按钮
        compare_btn = QPushButton("文件对比")
        compare_btn.setMinimumHeight(56)
        compare_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        compare_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #f5f6fa;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        compare_btn.clicked.connect(self.open_file_compare)
        # 添加鼠标悬停事件
        compare_btn.enterEvent = lambda e: self.update_subtitle("文件对比工具用于对比两个文件的内容差异")
        compare_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        compare_layout.addWidget(compare_btn)
        
        # 添加文件产生器容器
        generator_container = QFrame()
        generator_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                padding: 0px;
            }
        """)
        generator_layout = QHBoxLayout()  # 改为水平布局
        generator_layout.setContentsMargins(20, 0, 20, 20)
        generator_layout.setSpacing(10)  # 添加按钮间距
        generator_container.setLayout(generator_layout)
        
        # 添加文件产生器按钮
        generator_btn = QPushButton("本地文件产生器")
        generator_btn.setMinimumHeight(56)
        generator_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        generator_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #f5f6fa;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        generator_btn.clicked.connect(self.open_file_generator)
        # 添加鼠标悬停事件
        generator_btn.enterEvent = lambda e: self.update_subtitle("本地文件产生器用于生成指定大小和数量的测试文件")
        generator_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        generator_layout.addWidget(generator_btn, stretch=7)  # 设置较大的拉伸比例

        # 添加文件校验按钮
        verify_btn = QPushButton("文件校验")
        verify_btn.setMinimumHeight(56)
        verify_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        verify_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #f5f6fa;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        verify_btn.clicked.connect(self.show_verify_message)
        # 添加鼠标悬停事件
        verify_btn.enterEvent = lambda e: self.update_subtitle("文件校验工具用于验证本地文件产生器产生的文件的完整性")
        verify_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        generator_layout.addWidget(verify_btn, stretch=3)  # 设置较小的拉伸比例
        
        # 新增：扇区查看按钮行
        sector_container = QFrame()
        sector_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                padding: 0px;
            }
        """)
        sector_layout = QHBoxLayout()
        sector_layout.setContentsMargins(20, 0, 20, 20)
        sector_container.setLayout(sector_layout)
        
        sector_btn = QPushButton("扇区查看工具diskprobe.exe")
        sector_btn.setMinimumHeight(56)
        sector_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sector_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
                background-color: #f5f6fa;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        sector_btn.clicked.connect(self.show_sector_message)
        # 鼠标悬停事件
        sector_btn.enterEvent = lambda e: self.update_subtitle("扇区查看工具用于查看磁盘扇区内容")
        sector_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        sector_layout.addWidget(sector_btn)
        tools_layout.addWidget(compare_container)
        tools_layout.addWidget(generator_container)
        # 将扇区查看按钮放到最后
        tools_layout.addWidget(sector_container)
        
        layout.addWidget(tools_container)
        
        # 添加底部信息
        footer = QLabel("© 2024 Windows工具集")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #7f8fa6;
            font-size: 12px;
            margin-top: 10px;
        """)
        layout.addWidget(footer)
        
        # 减小底部弹性空间
        layout.addStretch(0)
        
        self._check_and_auto_run_filegen()
    
    def _check_and_auto_run_filegen(self):
        exe_dir = os.path.dirname(sys.argv[0])
        config_path = os.path.join(exe_dir, "filegen_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self._show_filegen_auto_dialog(config)

    def _show_filegen_auto_dialog(self, config):
        from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        from PyQt5.QtCore import QTimer
        dialog = QDialog(self)
        dialog.setWindowTitle("自动恢复文件产生器")
        layout = QVBoxLayout()
        label = QLabel("检测到上次保存的文件产生器配置，是否自动恢复并开始执行？\n5秒后将自动开始。\n\n配置文件路径: filegen_config.yaml")
        layout.addWidget(label)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        timer = QTimer(dialog)
        timer.setInterval(1000)
        self._countdown = 5
        def update_label():
            self._countdown -= 1
            label.setText(f"检测到上次保存的文件产生器配置，是否自动恢复并开始执行？\n{self._countdown}秒后将自动开始。\n\n配置文件路径: filegen_config.yaml")
            if self._countdown <= 0:
                timer.stop()
                dialog.accept()
        timer.timeout.connect(update_label)
        timer.start()
        ok_btn.clicked.connect(lambda: (timer.stop(), dialog.accept()))
        cancel_btn.clicked.connect(lambda: (timer.stop(), dialog.reject()))
        if dialog.exec_() == QDialog.Accepted:
            self._auto_open_filegen_with_config(config)

    def _auto_open_filegen_with_config(self, config):
        # 打开文件产生器窗口并自动填充参数并开始
        if self.file_generator_window is None or not self.file_generator_window.isVisible():
            self.file_generator_window = FileGeneratorUI()
        ui = self.file_generator_window
        # 设置参数
        ui.dir_edit.setText(config.get('target_dir', ''))
        ui.size_min.setText(str(config.get('file_size_min', '')))
        ui.size_max.setText(str(config.get('file_size_max', '')))
        ui.size_unit.setCurrentText(config.get('file_size_min_unit', 'KB'))
        ui.size_unit2.setCurrentText(config.get('file_size_max_unit', 'KB'))
        mode = config.get('mode', '单次')
        if mode == '循环':
            ui.loop_mode.setChecked(True)
        else:
            ui.single_mode.setChecked(True)
        ui.limit_edit.setText(str(config.get('max_files', '')))
        ui.interval_edit.setText(str(config.get('interval', '')))
        # 强制置顶再恢复
        ui.show()
        # 自动开始
        threading.Timer(0.5, ui.start_generation).start()

    def open_md5_calculator(self):
        """打开MD5计算器窗口（单例模式）"""
        if self.md5_calculator_window is None or not self.md5_calculator_window.isVisible():
            self.md5_calculator_window = MD5CalculatorUI()
            self.md5_calculator_window.show()
        else:
            self.md5_calculator_window.activateWindow()
            self.md5_calculator_window.raise_()
        
    def open_system_disk_calculator(self):
        """打开系统盘MD5计算器窗口（单例模式）"""
        if self.md5_calculator_window is None or not self.md5_calculator_window.isVisible():
            self.md5_calculator_window = MD5CalculatorUI()
            # 设置系统相关的文件扩展名
            self.md5_calculator_window.ext_input.setText(".exe,.dll,.sys")
            # 清空目录列表
            self.md5_calculator_window.dir_list.clear()
            # 添加Windows目录
            windows_dir = os.environ.get('SystemRoot', 'C:\\Windows')
            self.md5_calculator_window.dir_list.addItem(windows_dir)
            # 显示窗口
            self.md5_calculator_window.show()
            # 自动开始计算
            self.md5_calculator_window.start_calculation()
        else:
            self.md5_calculator_window.activateWindow()
            self.md5_calculator_window.raise_()

    def open_file_compare(self):
        """打开文件对比窗口（单例模式）"""
        if self.file_compare_window is None or not self.file_compare_window.isVisible():
            self.file_compare_window = FileCompareUI()
            self.file_compare_window.show()
        else:
            self.file_compare_window.activateWindow()
            self.file_compare_window.raise_()

    def open_file_generator(self):
        """打开本地文件产生器窗口（单例模式）"""
        if self.file_generator_window is None or not self.file_generator_window.isVisible():
            self.file_generator_window = FileGeneratorUI()
            self.file_generator_window.show()
        else:
            self.file_generator_window.activateWindow()
            self.file_generator_window.raise_()

    def open_file_verify(self):
        """打开文件校验窗口（单例模式）"""
        if self.file_verify_window is None or not self.file_verify_window.isVisible():
            self.file_verify_window = FileVerifyUI()
            self.file_verify_window.show()
        else:
            self.file_verify_window.activateWindow()
            self.file_verify_window.raise_()

    def show_verify_message(self):
        """显示文件校验功能开发中的提示"""
        self.open_file_verify()

    def show_sector_message(self):
        # 打开扇区查看工具 diskprobe.exe
        exe_path = os.path.join(os.path.dirname(__file__), 'src', 'resources', 'diskprobe', 'diskprobe.exe')
        try:
            os.startfile(exe_path)
        except Exception as e:
            QMessageBox.warning(self, "扇区查看", f"无法打开扇区查看工具：{str(e)}")

    def update_subtitle(self, text):
        """更新副标题文本"""
        self.subtitle.setText(text)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 