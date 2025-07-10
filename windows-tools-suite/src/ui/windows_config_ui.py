from PyQt5.QtWidgets import ( QDialog, QVBoxLayout, QGroupBox, QPushButton, 
                             QHBoxLayout, QMessageBox, QLabel, QLineEdit, QDialog)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import winreg
import ctypes
from ..utils.logger import get_logger
import tempfile
import os
import sys
import time
import shutil

logger = get_logger(__name__)


# 新增：系统缓存刷新线程
class SyncThread(QThread):
    finished = pyqtSignal(bool, str)
    def run(self):
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'sync', 'sync.exe'))
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f'/c "{exe_path}" -r -nobanner', None, 0
            )
            if ret > 32:
                self.finished.emit(True, "刷新成功！")
            else:
                self.finished.emit(False, f"无法以管理员权限运行sync.exe，返回码：{ret}")
        except Exception as e:
            self.finished.emit(False, f"无法以管理员权限运行sync.exe：{str(e)}")

class BcdEditQueryThread(QThread):
    result = pyqtSignal(bool, bool, str)  # testsigning_on, nointegrity_on, error_msg
    
    def run(self):
        try:
            # 使用临时文件获取bcdedit输出
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 使用管理员权限执行bcdedit并输出到临时文件
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f"/c bcdedit > {tmp_path}", None, 0
            )
            if ret <= 32:
                self.result.emit(False, False, f"ShellExecuteW failed with return code {ret}")
                return
            
            # 等待命令执行完成
            time.sleep(1.5)
            
            # 读取临时文件内容
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                output = f.read()
            os.unlink(tmp_path)  # 删除临时文件
            
            testsigning_on = False
            nointegrity_on = False
            for line in output.splitlines():
                if 'testsigning' in line:
                    if 'Yes' in line or '开启' in line:
                        testsigning_on = True
                if 'nointegritychecks' in line:
                    if 'Yes' in line or '开启' in line:
                        nointegrity_on = True
            
            self.result.emit(testsigning_on, nointegrity_on, "")
        except Exception as e:
            self.result.emit(False, False, str(e))

class BcdEditSetThread(QThread):
    finished = pyqtSignal(bool, str)  # success, error_msg
    
    def __init__(self, testsigning_value, nointegrity_value):
        super().__init__()
        self.testsigning_value = testsigning_value
        self.nointegrity_value = nointegrity_value
    
    def run(self):
        try:
            ret1 = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f"/c bcdedit /set testsigning {self.testsigning_value}", None, 1
            )
            if ret1 <= 32:
                self.finished.emit(False, f"testsigning {self.testsigning_value} failed with return code {ret1}")
                return
            
            ret2 = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f"/c bcdedit /set nointegritychecks {self.nointegrity_value}", None, 1
            )
            if ret2 <= 32:
                self.finished.emit(False, f"nointegritychecks {self.nointegrity_value} failed with return code {ret2}")
                return
            
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class WindowsUpdateResetThread(QThread):
    progress = pyqtSignal(str)  # 当前步骤描述
    finished = pyqtSignal(bool, str)  # success, error_msg
    
    def run(self):
        try:
            # 步骤1：停止Windows更新服务
            self.progress.emit("正在停止Windows更新服务...")
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", "/c net stop wuauserv", None, 0
            )
            if ret <= 32:
                self.finished.emit(False, f"停止Windows更新服务失败，返回码: {ret}")
                return
            time.sleep(1)
            
            # 步骤2：禁用Windows更新服务
            self.progress.emit("正在禁用Windows更新服务...")
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", "/c sc config wuauserv start=disabled", None, 0
            )
            if ret <= 32:
                self.finished.emit(False, f"禁用Windows更新服务失败，返回码: {ret}")
                return
            time.sleep(1)
            
            # 步骤3：删除相关目录
            self.progress.emit("正在删除相关目录...")
            download_path = r"C:\Windows\SoftwareDistribution\Download"
            datastore_path = r"C:\Windows\SoftwareDistribution\DataStore"
            
            try:
                if os.path.exists(download_path):
                    shutil.rmtree(download_path, ignore_errors=True)
                if os.path.exists(datastore_path):
                    shutil.rmtree(datastore_path, ignore_errors=True)
            except Exception as e:
                self.finished.emit(False, f"删除目录失败: {str(e)}")
                return
            time.sleep(1)
            
            # 步骤4：设置Windows更新服务为自动
            self.progress.emit("正在设置Windows更新服务为自动...")
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", "/c sc config wuauserv start=auto", None, 0
            )
            if ret <= 32:
                self.finished.emit(False, f"设置Windows更新服务为自动失败，返回码: {ret}")
                return
            time.sleep(1)
            
            # 步骤5：启动Windows更新服务
            self.progress.emit("正在启动Windows更新服务...")
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", "/c net start wuauserv", None, 0
            )
            if ret <= 32:
                self.finished.emit(False, f"启动Windows更新服务失败，返回码: {ret}")
                return
            time.sleep(1)
            
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class WindowsConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Windows系统配置")
        self.setMinimumWidth(450)
        self.setMinimumHeight(450)
        self.query_thread = None
        self.set_thread = None
        self.update_reset_thread = None
        self.init_ui()
        self.refresh_sign_btn()
        self.check_auto_login_status()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 签名验证分组
        sign_group = QGroupBox("驱动签名验证")
        sign_layout = QVBoxLayout()
        
        # 添加状态显示
        self.driver_verify_label = QLabel("驱动验证: 未知")
        self.testsigning_label = QLabel("testsigning: 未知")
        self.nointegrity_label = QLabel("nointegritychecks: 未知")
        sign_layout.addWidget(self.driver_verify_label)
        sign_layout.addWidget(self.testsigning_label)
        sign_layout.addWidget(self.nointegrity_label)
        
        # 操作按钮
        self.sign_btn = QPushButton()
        self.sign_btn.clicked.connect(self.toggle_sign_check)
        sign_layout.addWidget(self.sign_btn)
        sign_group.setLayout(sign_layout)
        layout.addWidget(sign_group)
        
        # Windows更新重置分组
        update_group = QGroupBox("Windows更新重置")
        update_layout = QVBoxLayout()
        self.update_reset_btn = QPushButton("重置更新配置")
        self.update_reset_btn.clicked.connect(self.reset_windows_update)
        update_layout.addWidget(self.update_reset_btn)
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # 新增：系统缓存管理分组
        cache_group = QGroupBox("系统缓存管理")
        cache_layout = QVBoxLayout()
        self.sync_btn = QPushButton("刷新系统缓存")
        self.sync_btn.clicked.connect(self.run_sync)
        cache_layout.addWidget(self.sync_btn)
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        # Windows系统自动登录分组
        auto_login_group = QGroupBox("Windows系统自动登录")
        auto_login_layout = QVBoxLayout()
        self.auto_login_btn = QPushButton()
        self.auto_login_btn.clicked.connect(self.set_auto_login)
        auto_login_layout.addWidget(self.auto_login_btn)
        auto_login_group.setLayout(auto_login_layout)
        layout.addWidget(auto_login_group)
        
        # 预留后续模块分块
        layout.addStretch()
        self.setLayout(layout)

    def refresh_sign_btn(self):
        logger.info("刷新签名验证按钮")
        self.sign_btn.setEnabled(False)
        self.sign_btn.setText('正在查询状态...')
        
        self.query_thread = BcdEditQueryThread()
        self.query_thread.result.connect(self.on_query_result)
        self.query_thread.start()

    def on_query_result(self, testsigning_on, nointegrity_on, error_msg):
        if error_msg:
            logger.error(f"查询bcdedit状态失败: {error_msg}")
            self.sign_btn.setText(f'查询失败')
            self.sign_btn.setEnabled(True)
            # 更新状态显示
            self.driver_verify_label.setText("驱动验证: 查询失败")
            self.testsigning_label.setText("testsigning: 查询失败")
            self.nointegrity_label.setText("nointegritychecks: 查询失败")
        else:
            # 更新状态显示
            testsigning_status = "Yes" if testsigning_on else "No"
            nointegrity_status = "Yes" if nointegrity_on else "No"
            self.testsigning_label.setText(f"testsigning: {testsigning_status}")
            self.nointegrity_label.setText(f"nointegritychecks: {nointegrity_status}")
            
            if testsigning_on and nointegrity_on:
                self.sign_btn.setText('打开驱动验证')
                self.driver_verify_label.setText("驱动验证: 已关闭")
            else:
                self.sign_btn.setText('关闭驱动验证')
                self.driver_verify_label.setText("驱动验证: 已打开")
            self.sign_btn.setEnabled(True)
        logger.info("刷新签名验证按钮完成")

    def toggle_sign_check(self):
        logger.info("切换签名验证")
        current_text = self.sign_btn.text()
        
        if current_text == '打开驱动验证':
            logger.info("打开驱动验证")
            self.sign_btn.setEnabled(False)
            self.sign_btn.setText('正在打开验证...')
            self.set_thread = BcdEditSetThread("off", "off")
            self.set_thread.finished.connect(lambda success, msg: self.on_set_result(success, msg, "已打开驱动签名验证（testsigning/off, nointegritychecks/off）\n重启后生效", "打开驱动验证成功"))
            self.set_thread.start()
        elif current_text == '关闭驱动验证':
            logger.info("关闭驱动验证")
            self.sign_btn.setEnabled(False)
            self.sign_btn.setText('正在关闭验证...')
            self.set_thread = BcdEditSetThread("on", "on")
            self.set_thread.finished.connect(lambda success, msg: self.on_set_result(success, msg, "已关闭驱动签名验证（testsigning/on, nointegritychecks/on）\n重启后生效", "关闭驱动验证成功"))
            self.set_thread.start()
        else:
            QMessageBox.warning(self, "操作失败", f"未知的按钮状态：{current_text}")

    def on_set_result(self, success, error_msg, success_msg, log_msg):
        if success:
            QMessageBox.information(self, "操作成功", success_msg)
            logger.info(log_msg)
            self.refresh_sign_btn()
        else:
            logger.error(f"切换签名验证失败: {error_msg}")
            QMessageBox.warning(self, "操作失败", f"切换签名验证时出错：{error_msg}")
            self.sign_btn.setEnabled(True)
            # 恢复原来的按钮文本
            self.refresh_sign_btn()

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def reset_windows_update(self):
        # 添加二级确认对话框
        reply = QMessageBox.question(
            self, 
            "确认重置Windows更新", 
            "此操作将执行以下步骤：\n\n"
            "1. 停止Windows更新服务\n"
            "2. 禁用Windows更新服务\n"
            "3. 删除更新缓存目录\n"
            "4. 重新启用Windows更新服务\n"
            "5. 启动Windows更新服务\n\n"
            "此操作需要管理员权限，确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # 默认选择"否"
        )
        
        if reply != QMessageBox.Yes:
            logger.info("用户取消了Windows更新重置操作")
            return
            
        logger.info("开始重置Windows更新配置")
        self.update_reset_btn.setEnabled(False)
        self.update_reset_btn.setText("准备重置...")
        
        self.update_reset_thread = WindowsUpdateResetThread()
        self.update_reset_thread.progress.connect(self.on_update_progress)
        self.update_reset_thread.finished.connect(self.on_update_finished)
        self.update_reset_thread.start()

    def on_update_progress(self, step_text):
        self.update_reset_btn.setText(step_text)
        logger.info(step_text)

    def on_update_finished(self, success, error_msg):
        if success:
            self.update_reset_btn.setText("重置完成")
            QMessageBox.information(self, "操作成功", "Windows更新配置已重置完成！\n\n已执行以下操作：\n1. 停止Windows更新服务\n2. 禁用Windows更新服务\n3. 删除相关目录\n4. 设置服务为自动启动\n5. 启动Windows更新服务")
            logger.info("Windows更新重置成功")
        else:
            self.update_reset_btn.setText("重置失败")
            QMessageBox.warning(self, "操作失败", f"Windows更新重置失败：{error_msg}")
            logger.error(f"Windows更新重置失败: {error_msg}")
        
        # 3秒后恢复按钮
        QTimer.singleShot(3000, lambda: (
            self.update_reset_btn.setText("重置更新配置"),
            self.update_reset_btn.setEnabled(True)
        ))

    def check_auto_login_status(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon"
            )
            value, _ = winreg.QueryValueEx(key, "AutoAdminLogon")
            winreg.CloseKey(key)
            if value == '1':
                self.auto_login_btn.setText("取消自动登录")
                try:
                    self.auto_login_btn.clicked.disconnect()
                except Exception:
                    pass
                self.auto_login_btn.clicked.connect(self.unset_auto_login)
                return
        except Exception:
            pass
        self.auto_login_btn.setText("系统自动登录")
        try:
            self.auto_login_btn.clicked.disconnect()
        except Exception:
            pass
        self.auto_login_btn.clicked.connect(self.set_auto_login)

    def set_auto_login(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("系统自动登录配置")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("请输入要自动登录的用户名和密码："))
        user_edit = QLineEdit()
        user_edit.setPlaceholderText("用户名")
        pwd_edit = QLineEdit()
        pwd_edit.setPlaceholderText("密码")
        pwd_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(user_edit)
        layout.addWidget(pwd_edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            username = user_edit.text().strip()
            password = pwd_edit.text().strip()
            if not username or not password:
                QMessageBox.warning(self, "警告", "用户名和密码不能为空！")
                return
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, '1')
                winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, username)
                winreg.SetValueEx(key, "DefaultPassword", 0, winreg.REG_SZ, password)
                winreg.CloseKey(key)
                QMessageBox.information(self, "设置成功", "系统自动登录已配置！")
            except Exception as e:
                QMessageBox.critical(self, "设置失败", f"自动登录配置失败：{str(e)}\n请尝试以管理员身份运行程序。")
        self.check_auto_login_status()

    def unset_auto_login(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "AutoAdminLogon")
            winreg.DeleteValue(key, "DefaultUserName")
            winreg.DeleteValue(key, "DefaultPassword")
            winreg.CloseKey(key)
            QMessageBox.information(self, "取消成功", "已取消系统自动登录。")
        except FileNotFoundError:
            QMessageBox.information(self, "无需操作", "未设置系统自动登录。")
        except Exception as e:
            QMessageBox.critical(self, "取消失败", f"取消自动登录失败：{str(e)}\n请尝试以管理员身份运行程序。")
        self.check_auto_login_status()

    def run_sync(self):
        logger.info("运行sync")
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("正在刷新...")
        self.sync_thread = SyncThread()
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.start()

    def on_sync_finished(self, success, msg):
        if success:
            QMessageBox.information(self, "Sync", msg)
        else:
            QMessageBox.warning(self, "运行sync", msg)
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("刷新系统缓存")
