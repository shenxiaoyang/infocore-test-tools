import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QFrame, QMessageBox, QHBoxLayout, QSizePolicy, QGridLayout, QDialog, QVBoxLayout as QVBoxLayout2, QHBoxLayout as QHBoxLayout2)
from PyQt5.QtCore import Qt, QTimer
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

class AutoExecDialog(QDialog):
    """自动执行倒计时对话框"""
    def __init__(self, parent=None, modules=None):
        super().__init__(parent)
        self.modules = modules or []
        self.setWindowTitle("自动执行模块")
        self.setFixedSize(400, 200)
        self.setModal(True)
        self.countdown = 10
        self.init_ui()
        self.start_countdown()
        
    def init_ui(self):
        layout = QVBoxLayout2()
        
        # 显示要执行的模块
        modules_text = "\n".join([f"• {module}" for module in self.modules])
        label = QLabel(f"即将自动执行以下模块：\n{modules_text}\n\n{self.countdown}秒后开始执行...")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # 按钮布局
        btn_layout = QHBoxLayout2()
        ok_btn = QPushButton("立即执行")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
    def start_countdown(self):
        """开始倒计时"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        
    def update_countdown(self):
        """更新倒计时"""
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
            self.accept()
        else:
            # 更新标签文本
            label = self.findChild(QLabel)
            if label:
                modules_text = "\n".join([f"• {module}" for module in self.modules])
                label.setText(f"即将自动执行以下模块：\n{modules_text}\n\n{self.countdown}秒后开始执行...")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 记录软件启动文件路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            self.startup_file_path = sys.executable
        else:
            # 如果是Python脚本
            self.startup_file_path = os.path.abspath(sys.argv[0])
        
        # 解析出版号 Windows工具集-v1.1.18-x64.exe
        file_name = os.path.basename(self.startup_file_path)
        logger.info(f"file_name: {file_name}")
        
        # 提取版本号，格式如：Windows工具集-v1.1.18-x64.exe
        try:
            if '-v' in file_name:
                version_part = file_name.split('-v')[1]
                if '-' in version_part:
                    self.version = version_part.split('-')[0]  # 1.1.18
                else:
                    self.version = version_part.split('.exe')[0]  # 如果没有架构标识
            else:
                self.version = "unknown"
        except Exception as e:
            logger.error(f"解析版本号失败: {str(e)}")
            self.version = "unknown"
            
        logger.info(f"当前版本: {self.version}")
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), 'src', 'resources', 'icons', 'app.ico')
        self.setWindowIcon(QIcon(icon_path))
        # 添加窗口实例属性
        self.md5_calculator_window = None
        self.file_compare_window = None
        self.file_generator_window = None
        self.file_verify_window = None
        self.logger = get_logger(__name__)
        
        self.setWindowTitle(f"Windows工具集-v{self.version}")
        self.setMinimumSize(400, 400)
        self.setAcceptDrops(True)
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

        # 第二行：MD5计算器
        md5calc_btn = QPushButton("MD5计算器")
        md5calc_btn.setMinimumHeight(30)
        md5calc_btn.setStyleSheet(self.btn_style)
        md5calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        md5calc_btn.clicked.connect(self.open_md5_calc_dialog)
        md5calc_btn.enterEvent = lambda e: self.update_subtitle("文件MD5/SHA哈希计算与校验")
        md5calc_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(md5calc_btn, 1, 0, 1, 2)

        # 第三行：文件对比
        compare_btn = QPushButton("文件对比")
        compare_btn.setMinimumHeight(30)
        compare_btn.setStyleSheet(self.btn_style)
        compare_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        compare_btn.clicked.connect(self.open_file_compare)
        compare_btn.enterEvent = lambda e: self.update_subtitle("文件对比工具用于对比两个文件的内容差异")
        compare_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(compare_btn, 2, 0, 1, 2)

        # 第四行
        generator_btn = QPushButton("本地文件产生器")
        generator_btn.setMinimumHeight(30)
        generator_btn.setStyleSheet(self.btn_style)
        generator_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        generator_btn.clicked.connect(self.open_file_generator)
        generator_btn.enterEvent = lambda e: self.update_subtitle("本地文件产生器用于生成指定大小和数量的测试文件")
        generator_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(generator_btn, 3, 0)

        verify_btn = QPushButton("文件校验")
        verify_btn.setMinimumHeight(30)
        verify_btn.setStyleSheet(self.btn_style)
        verify_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        verify_btn.clicked.connect(self.open_file_verify)
        verify_btn.enterEvent = lambda e: self.update_subtitle("文件校验工具用于验证本地文件产生器产生的文件的完整性")
        verify_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(verify_btn, 3, 1)

        # HostAgent配置按钮
        hostagent_btn = QPushButton("HostAgent配置")
        hostagent_btn.setMinimumHeight(30)
        hostagent_btn.setStyleSheet(self.btn_style)
        hostagent_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hostagent_btn.clicked.connect(self.open_hostagent_config)
        hostagent_btn.enterEvent = lambda e: self.update_subtitle("HostAgent相关模块配置和操作")
        hostagent_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(hostagent_btn, 4, 0, 1, 2)

        # 第六行：第三方工具按钮
        thirdparty_btn = QPushButton("第三方工具")
        thirdparty_btn.setMinimumHeight(30)
        thirdparty_btn.setStyleSheet(self.btn_style)
        thirdparty_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        thirdparty_btn.clicked.connect(self.open_tools_dialog)
        thirdparty_btn.enterEvent = lambda e: self.update_subtitle("打开第三方磁盘工具")
        thirdparty_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(thirdparty_btn, 5, 0, 1, 2)

        # 第七行：Windows系统配置按钮
        system_config_btn = QPushButton("Windows系统配置")
        system_config_btn.setMinimumHeight(30)
        system_config_btn.setStyleSheet(self.btn_style)
        system_config_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        system_config_btn.clicked.connect(self.open_system_config)
        system_config_btn.enterEvent = lambda e: self.update_subtitle("Windows系统配置和优化工具")
        system_config_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(system_config_btn, 6, 0, 1, 2)

        # 新增：工具集配置按钮
        software_config_btn = QPushButton("工具集配置")
        software_config_btn.setMinimumHeight(30)
        software_config_btn.setStyleSheet(self.btn_style)
        software_config_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        software_config_btn.clicked.connect(self.open_software_config)
        software_config_btn.enterEvent = lambda e: self.update_subtitle("工具集相关配置和自启设置")
        software_config_btn.leaveEvent = lambda e: self.update_subtitle("便捷实用的Windows工具箱")
        tools_grid.addWidget(software_config_btn, 7, 0, 1, 2)

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
        footer = QLabel("© 2025 InfoCore 测试部")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #7f8fa6;
            font-size: 12px;
            margin-top: 10px;
        """)
        layout.addWidget(footer)
        
        # 减小底部弹性空间
        layout.addStretch(0)
        
        # 检查自动执行配置
        self.check_auto_exec_config()
    
    def check_auto_exec_config(self):
        """检查自动执行配置"""
        program_data = os.environ.get('ProgramData', r'C:\ProgramData')
        config_dir = os.path.join(program_data, "InfoCoreTestTools")
        config_file = os.path.join(config_dir, "auto_exec_config.yaml")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        # 检查是否仅在本地应急时执行
                        emergency_only = config.get('emergency_only', False)
                        if emergency_only:
                            # 检查客户端保护状态
                            try:
                                key = winreg.OpenKey(
                                    winreg.HKEY_LOCAL_MACHINE,
                                    r"SYSTEM\\CurrentControlSet\\Services\\OsnCliService\\Parameters"
                                )
                                protected, _ = winreg.QueryValueEx(key, "Protected")
                                winreg.CloseKey(key)
                                
                                # 如果Protected值为true（已保护），则不执行自动模块
                                if str(protected).lower() == "true":
                                    logger.info("客户端已保护，跳过自动执行模块")
                                    return
                                logger.info("客户端未保护，继续执行自动模块")
                            except FileNotFoundError:
                                # 如果注册表键值不存在，判断为未保护状态
                                logger.info("注册表键值不存在，判断为未保护状态，继续执行自动模块")
                            except Exception as e:
                                logger.error(f"检查客户端保护状态失败: {str(e)}")
                                # 如果检查失败，默认不执行
                                return
                        
                        modules_to_exec = []
                        
                        # 检查快速计算系统盘
                        if config.get('auto_system_disk', False):
                            modules_to_exec.append("快速计算系统盘")
                        
                        # 检查本地文件产生器
                        if config.get('auto_filegen', False):
                            filegen_config = os.path.join(config_dir, "filegen_config.yaml")
                            if os.path.exists(filegen_config):
                                modules_to_exec.append("本地文件产生器")
                        
                        # 检查文件校验
                        if config.get('auto_fileverify', False):
                            fileverify_config = os.path.join(config_dir, "fileverify_config.yaml")
                            if os.path.exists(fileverify_config):
                                modules_to_exec.append("文件校验")
                        
                        if modules_to_exec:
                            # 显示倒计时对话框
                            dialog = AutoExecDialog(self, modules_to_exec)
                            if dialog.exec_() == QDialog.Accepted:
                                self.execute_auto_modules(modules_to_exec)
                                
            except Exception as e:
                logger.error(f"读取自动执行配置失败: {str(e)}")

    def execute_auto_modules(self, modules):
        """执行自动模块"""
        for module in modules:
            if module == "快速计算系统盘":
                self.open_system_disk_calculator()
            elif module == "本地文件产生器":
                self.open_file_generator()
                # 延迟0.5秒后自动开始文件产生
                if self.file_generator_window:
                    threading.Timer(0.5, self.file_generator_window.start_generation).start()
            elif module == "文件校验":
                self.open_file_verify()
                # 延迟0.5秒后自动开始文件校验
                if self.file_verify_window:
                    threading.Timer(0.5, self.file_verify_window.start_verify).start()

    def open_md5_calculator(self):
        """打开MD5计算器窗口（单例模式）"""
        logger.info("打开MD5计算器")
        if self.md5_calculator_window is None or not self.md5_calculator_window.isVisible():
            self.md5_calculator_window = MD5CalculatorUI()
            self.md5_calculator_window.show()
        else:
            self.md5_calculator_window.activateWindow()
            self.md5_calculator_window.raise_()
        
    def open_system_disk_calculator(self):
        """打开系统盘MD5计算器窗口（单例模式）"""
        logger.info("打开系统盘MD5计算器")
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
        logger.info("打开文件对比")
        if self.file_compare_window is None or not self.file_compare_window.isVisible():
            self.file_compare_window = FileCompareUI()
            self.file_compare_window.show()
        else:
            self.file_compare_window.activateWindow()
            self.file_compare_window.raise_()

    def open_file_generator(self):
        """打开本地文件产生器窗口（单例模式）"""
        logger.info("打开本地文件产生器")
        if self.file_generator_window is None or not self.file_generator_window.isVisible():
            self.file_generator_window = FileGeneratorUI()
            self.file_generator_window.show()
        else:
            self.file_generator_window.activateWindow()
            self.file_generator_window.raise_()

    def open_file_verify(self):
        """打开文件校验窗口（单例模式）"""
        logger.info("打开文件校验")
        if self.file_verify_window is None or not self.file_verify_window.isVisible():
            self.file_verify_window = FileVerifyUI()
            self.file_verify_window.show()
        else:
            self.file_verify_window.activateWindow()
            self.file_verify_window.raise_()

    def open_tools_dialog(self):
        logger.info("打开第三方工具")
        from src.ui.tools_ui import ToolsDialog
        dialog = ToolsDialog(self)
        dialog.exec_()

    def open_hostagent_config(self):
        logger.info("打开HostAgent配置")
        from src.ui.hostagent_config_ui import HostAgentConfigDialog
        dialog = HostAgentConfigDialog(self)
        dialog.exec_()

    def open_md5_calc_dialog(self):
        logger.info("打开MD5计算器")
        from src.ui.file_hash_calc_ui import FileHashCalcDialog
        dialog = FileHashCalcDialog(self)
        dialog.exec_()

    def open_system_config(self):
        """打开Windows系统配置"""
        logger.info("打开Windows系统配置")
        from src.ui.windows_config_ui import WindowsConfigDialog
        dialog = WindowsConfigDialog(self)
        dialog.exec_()

    def open_software_config(self):
        from src.ui.software_config_ui import SoftwareConfigDialog
        dialog = SoftwareConfigDialog(self)
        dialog.exec_()

    def update_subtitle(self, text):
        """更新副标题文本"""
        self.subtitle.setText(text)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logger.info("以手动方式运行")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 