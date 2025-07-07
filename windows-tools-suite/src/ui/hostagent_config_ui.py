from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QPushButton, QHBoxLayout, QMessageBox
import winreg
import subprocess
import logging
import ctypes
from ..utils.logger import get_logger
import tempfile
import os
from PyQt5.QtCore import QThread, pyqtSignal
import time
import shutil

logger = get_logger(__name__)

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

class HostAgentConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HostAgent配置")
        self.setMinimumWidth(400)
        self.query_thread = None
        self.set_thread = None
        self.update_reset_thread = None
        self.init_ui()
        self.refresh_log_btn()
        self.refresh_sign_btn()

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
        # 签名验证分组
        sign_group = QGroupBox("驱动签名验证")
        sign_layout = QVBoxLayout()
        
        # 添加状态显示
        from PyQt5.QtWidgets import QLabel
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
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, lambda: (
            self.update_reset_btn.setText("重置更新配置"),
            self.update_reset_btn.setEnabled(True)
        ))
