from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QPushButton, QHBoxLayout, QMessageBox
import winreg
import subprocess
import logging
from ..utils.logger import get_logger

logger = get_logger(__name__)

class HostAgentConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HostAgent配置")
        self.setMinimumWidth(400)
        self.init_ui()
        self.refresh_log_btn()

    def init_ui(self):
        layout = QVBoxLayout()
        # 未来可扩展多个模块，每个模块一个QGroupBox
        eim_group = QGroupBox("EIMVssProvider日志配置")
        eim_layout = QHBoxLayout()
        # 目前只有一个操作按钮
        self.log_btn = QPushButton()
        self.log_btn.clicked.connect(self.toggle_log_level)
        eim_layout.addWidget(self.log_btn)
        eim_group.setLayout(eim_layout)
        layout.addWidget(eim_group)
        
        # 预留后续模块分块
        layout.addStretch()
        self.setLayout(layout)

    def refresh_log_btn(self):
        logger.info("刷新日志按钮")
        # 检查注册表项是否存在
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\\CurrentControlSet\\Services\\EIMVssProvider', 0, winreg.KEY_READ)
            try:
                level, _ = winreg.QueryValueEx(key, 'Level')
            except FileNotFoundError:
                level = 0
            winreg.CloseKey(key)
            self.log_btn.setEnabled(True)
            if str(level) == '1':
                self.log_btn.setText('关闭日志')
            else:
                self.log_btn.setText('启用日志')
        except FileNotFoundError:
            self.log_btn.setEnabled(False)
            self.log_btn.setText('未检测到EIMVssProvider')
        logger.info("刷新日志按钮完成")

    def toggle_log_level(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\\CurrentControlSet\\Services\\EIMVssProvider', 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
            try:
                level, _ = winreg.QueryValueEx(key, 'Level')
            except FileNotFoundError:
                level = 0
            new_level = 0 if str(level) == '1' else 1
            winreg.SetValueEx(key, 'Level', 0, winreg.REG_DWORD, new_level)
            winreg.CloseKey(key)
            # 重启EIMVssProvider服务
            try:
                subprocess.run(['sc', 'stop', 'EIMVssProvider'], check=True, capture_output=True, text=True)
            except Exception as e:
                logger.warning(f"停止EIMVssProvider服务时出错：{e}")

            try:
                subprocess.run(['sc', 'start', 'EIMVssProvider'], check=True, capture_output=True, text=True)
            except Exception as e:
                QMessageBox.warning(self, "服务启动失败", f"启动EIMVssProvider服务时出错：{e}")

            self.refresh_log_btn()
        except PermissionError:
            QMessageBox.warning(self, "权限不足", "修改注册表需要管理员权限！")
        except Exception as e:
            QMessageBox.warning(self, "操作失败", f"操作注册表时出错：{e}")
