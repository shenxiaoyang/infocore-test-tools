import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QFrame, QMessageBox, QHBoxLayout, QSizePolicy, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from src.ui.md5_calculator_ui import MD5CalculatorUI
from src.ui.file_compare_ui import FileCompareUI
from src.ui.file_generator_ui import FileGeneratorUI
from src.ui.file_verify_ui import FileVerifyUI
import yaml
import threading
import winreg
from src.utils.logger import get_logger

logger = get_logger(__name__)

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
        self.logger = get_logger(__name__)
        
        self.setWindowTitle("Windows工具集")
        self.setMinimumSize(400, 400)
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
        layout.setContentsMargins(16, 16, 16, 16)
        central_widget.setLayout(layout)
        
        # 添加标题
        title_container = QFrame()
        title_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 5px;
            }
        """)
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 修改subtitle为类属性，以便在其他方法中访问
        self.subtitle = QLabel("便捷实用的Windows工具箱")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("""
            font-size: 13px;
            color: #7f8fa6;
            margin-top: 2px;
        """)

        title_layout.addWidget(self.subtitle)
        title_container.setLayout(title_layout)
        title_container.setFixedHeight(84)
        layout.addWidget(title_container)
        
        # 工具卡片容器
        tools_container = QFrame()
        tools_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        tools_grid = QGridLayout()
        tools_grid.setContentsMargins(8, 8, 8, 8)
        tools_grid.setSpacing(8)

        # Apple风格按钮样式
        self.btn_style = """
            QPushButton {
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', 'Helvetica', 'PingFang SC', 'Hiragino Sans GB', 'sans-serif';
                background-color: #f0f0f0;
                color: #222;
                border-radius: 6px;
                font-size: 14px;
                padding-left: 12px;
                min-height: 30px;
                border: 1px solid #e0e0e0;
            }
            QPushButton:hover {
                background-color: #e5e5ea;
            }
            QPushButton:pressed {
                background-color: #cccccc;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #bfbfbf;
            }
        """
        self.btn_style_blue = """
            QPushButton {
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', 'Helvetica', 'PingFang SC', 'Hiragino Sans GB', 'sans-serif';
                background-color: #007AFF;
                color: #fff;
                border-radius: 6px;
                font-size: 14px;
                padding-left: 12px;
                min-height: 30px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0051a8;
            }
            QPushButton:pressed {
                background-color: #003e7e;
            }
            QPushButton:disabled {
                background-color: #b0cfff;
                color: #f5f5f5;
            }
        """

        # 第一行
        md5_btn = QPushButton("MD5一致性计算器")
        md5_btn.setMinimumHeight(30)
        md5_btn.setStyleSheet(self.btn_style)
        md5_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        md5_btn.enterEvent = lambda e: self.update_subtitle("MD5一致性计算器用于计算选定目录的MD5值")
        md5_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        md5_btn.clicked.connect(self.open_md5_calculator)
        tools_grid.addWidget(md5_btn, 0, 0)

        system_disk_btn = QPushButton("快速计算系统盘")
        system_disk_btn.setMinimumHeight(30)
        system_disk_btn.setStyleSheet(self.btn_style_blue)
        system_disk_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        system_disk_btn.enterEvent = lambda e: self.update_subtitle("快速计算系统盘Windows目录下dll、sys、exe文件的MD5值")
        system_disk_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        system_disk_btn.clicked.connect(self.open_system_disk_calculator)
        tools_grid.addWidget(system_disk_btn, 0, 1)

        # 第二行
        compare_btn = QPushButton("文件对比")
        compare_btn.setMinimumHeight(30)
        compare_btn.setStyleSheet(self.btn_style)
        compare_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        compare_btn.clicked.connect(self.open_file_compare)
        compare_btn.enterEvent = lambda e: self.update_subtitle("文件对比工具用于对比两个文件的内容差异")
        compare_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(compare_btn, 1, 0, 1, 2)

        # 第三行
        generator_btn = QPushButton("本地文件产生器")
        generator_btn.setMinimumHeight(30)
        generator_btn.setStyleSheet(self.btn_style)
        generator_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        generator_btn.clicked.connect(self.open_file_generator)
        generator_btn.enterEvent = lambda e: self.update_subtitle("本地文件产生器用于生成指定大小和数量的测试文件")
        generator_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(generator_btn, 2, 0)

        verify_btn = QPushButton("文件校验")
        verify_btn.setMinimumHeight(30)
        verify_btn.setStyleSheet(self.btn_style)
        verify_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        verify_btn.clicked.connect(self.open_file_verify)
        verify_btn.enterEvent = lambda e: self.update_subtitle("文件校验工具用于验证本地文件产生器产生的文件的完整性")
        verify_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(verify_btn, 2, 1)

        # 第四行
        sector_btn = QPushButton("扇区查看工具diskprobe.exe")
        sector_btn.setMinimumHeight(30)
        sector_btn.setStyleSheet(self.btn_style)
        sector_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sector_btn.clicked.connect(self.show_sector_message)
        sector_btn.enterEvent = lambda e: self.update_subtitle("扇区查看工具用于查看磁盘扇区内容")
        sector_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(sector_btn, 3, 0, 1, 2)

        # 第五行
        hostagent_btn = QPushButton("HostAgent配置")
        hostagent_btn.setMinimumHeight(30)
        hostagent_btn.setStyleSheet(self.btn_style)
        hostagent_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hostagent_btn.clicked.connect(self.open_hostagent_config)
        hostagent_btn.enterEvent = lambda e: self.update_subtitle("HostAgent相关模块配置和操作")
        hostagent_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(hostagent_btn, 4, 0, 1, 2)

        # 用QWidget包裹GridLayout，便于加到主layout
        tools_widget = QWidget()
        tools_widget.setLayout(tools_grid)
        tools_widget.setStyleSheet("background: transparent;")
        tools_container_layout = QVBoxLayout()
        tools_container_layout.setContentsMargins(0, 0, 0, 0)
        tools_container_layout.addWidget(tools_widget)
        tools_container.setLayout(tools_container_layout)
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
            # 如果是autorun, 需要检查客户端是否已保护，未保护的情况系下直接返回不自动执行文件产生器
            if is_autorun():
                # 检查Protected值
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\\CurrentControlSet\\Services\\OsnCliService\\Parameters"
                    )
                    protected, _ = winreg.QueryValueEx(key, "Protected")
                    winreg.CloseKey(key)
                    if str(protected).lower() == "false":
                        self.logger.info("Protected值为false，不执行文件产生器")
                        return
                    self.logger.info("Protected值为true，继续执行")
                except Exception:
                    self.logger.error("Protected值不存在，继续执行")
                    pass  # 没有该项默认继续
            # 继续原有逻辑
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

    def show_sector_message(self):
        # 打开扇区查看工具 diskprobe.exe
        exe_path = os.path.join(os.path.dirname(__file__), 'src', 'resources', 'diskprobe', 'diskprobe.exe')
        try:
            os.startfile(exe_path)
        except Exception as e:
            QMessageBox.warning(self, "扇区查看", f"无法打开扇区查看工具：{str(e)}")

    def open_hostagent_config(self):
        from src.ui.hostagent_config_ui import HostAgentConfigDialog
        dialog = HostAgentConfigDialog(self)
        dialog.exec_()

    def update_subtitle(self, text):
        """更新副标题文本"""
        self.subtitle.setText(text)

def is_autorun():
    return "autorun" in sys.argv

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if is_autorun():
        logger.info("以自启动方式运行（带autorun参数）")
        # 可在此处添加自动恢复、自动弹窗等逻辑
    else:
        logger.info("以手动方式运行")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 