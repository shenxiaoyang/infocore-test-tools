from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QPushButton, QHBoxLayout, QMessageBox
import winreg
import subprocess
import logging
import ctypes

logger = logging.getLogger(__name__)

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
        eim_group = QGroupBox("EIMVssProvider")
        eim_layout = QHBoxLayout()
        # 目前只有一个操作按钮
        self.log_btn = QPushButton()
        self.log_btn.clicked.connect(self.toggle_log_level)
        eim_layout.addWidget(self.log_btn)
        eim_group.setLayout(eim_layout)
        layout.addWidget(eim_group)
        # 签名验证分组
        sign_group = QGroupBox("驱动签名验证")
        sign_layout = QHBoxLayout()
        self.disable_sign_btn = QPushButton("关闭验证")
        self.enable_sign_btn = QPushButton("打开验证")
        self.disable_sign_btn.clicked.connect(self.disable_sign_check)
        self.enable_sign_btn.clicked.connect(self.enable_sign_check)
        self.query_sign_btn = QPushButton("查询状态")
        self.query_sign_btn.clicked.connect(self.query_sign_status)
        sign_layout.addWidget(self.disable_sign_btn)
        sign_layout.addWidget(self.enable_sign_btn)
        sign_layout.addWidget(self.query_sign_btn)
        sign_group.setLayout(sign_layout)
        layout.addWidget(sign_group)
        # 预留后续模块分块
        layout.addStretch()
        self.setLayout(layout)

    def refresh_log_btn(self):
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

    def disable_sign_check(self):
        if not self.is_admin():
            QMessageBox.warning(self, "权限不足", "请以管理员身份运行本程序，否则无法正确查询/修改签名状态。")
            return
        try:
            subprocess.run(['bcdedit', '/set', 'testsigning', 'on'], check=True, capture_output=True, text=True)
            subprocess.run(['bcdedit', '/set', 'nointegritychecks', 'on'], check=True, capture_output=True, text=True)
            QMessageBox.information(self, "操作成功", "已关闭签名验证（testsigning/on, nointegritychecks/on）\n重启后生效")
        except Exception as e:
            QMessageBox.warning(self, "操作失败", f"关闭签名验证时出错：{e}")

    def enable_sign_check(self):
        if not self.is_admin():
            QMessageBox.warning(self, "权限不足", "请以管理员身份运行本程序，否则无法正确查询/修改签名状态。")
            return
        try:
            subprocess.run(['bcdedit', '/set', 'testsigning', 'off'], check=True, capture_output=True, text=True)
            subprocess.run(['bcdedit', '/set', 'nointegritychecks', 'off'], check=True, capture_output=True, text=True)
            QMessageBox.information(self, "操作成功", "已打开签名验证（testsigning/off, nointegritychecks/off）\n重启后生效")
        except Exception as e:
            QMessageBox.warning(self, "操作失败", f"打开签名验证时出错：{e}")

    def query_sign_status(self):
        if not self.is_admin():
            QMessageBox.warning(self, "权限不足", "请以管理员身份运行本程序，否则无法正确查询/修改签名状态。")
            return
        try:
            result = subprocess.run(['bcdedit'], capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            QMessageBox.information(self, "bcdedit状态", output if output else "无输出")
        except Exception as e:
            QMessageBox.warning(self, "查询失败", f"执行bcdedit时出错：{e}")

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
