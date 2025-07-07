from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
import os
from ..utils.logger import get_logger

# 配置日志
logger = get_logger(__name__)


class SyncThread(QThread):
    finished = pyqtSignal(bool, str)
    def run(self):
        import subprocess
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'sync', 'sync.exe'))
        try:
            subprocess.run(
                ['powershell', '-Command', f'Start-Process "{exe_path}" "-r -nobanner" -Verb runAs -WindowStyle Hidden'],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.finished.emit(True, "刷新成功！")
        except Exception as e:
            self.finished.emit(False, f"无法以管理员权限运行sync.exe：{str(e)}")

class ToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("第三方工具")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        # diskprobe按钮
        diskprobe_btn = QPushButton("磁盘扇区查看diskprobe.exe")
        diskprobe_btn.clicked.connect(self.open_diskprobe)
        layout.addWidget(diskprobe_btn)
        # DiskGenius按钮
        diskgenius_btn = QPushButton("磁盘信息查看DiskGenius")
        diskgenius_btn.clicked.connect(self.open_diskgenius)
        layout.addWidget(diskgenius_btn)
        # sync按钮
        self.sync_btn = QPushButton("刷新系统缓存sync.exe")
        self.sync_btn.clicked.connect(self.run_sync)
        layout.addWidget(self.sync_btn)
        # 新增clumsy按钮
        clumsy_btn = QPushButton("网络异常模拟clumsy")
        clumsy_btn.clicked.connect(self.open_clumsy)
        layout.addWidget(clumsy_btn)
        self.setLayout(layout)
        self.sync_thread = None

    def open_diskprobe(self):
        logger.info("打开diskprobe")
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'diskprobe', 'diskprobe.exe')
        exe_path = os.path.abspath(exe_path)
        try:
            os.startfile(exe_path)
        except Exception as e:
            QMessageBox.warning(self, "打开diskprobe", f"无法打开diskprobe：{str(e)}")

    def open_diskgenius(self):
        logger.info("打开DiskGenius")
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'DiskGenius', 'DiskGenius.exe')
        exe_path = os.path.abspath(exe_path)
        try:
            os.startfile(exe_path)
        except Exception as e:
            QMessageBox.warning(self, "打开DiskGenius", f"无法打开DiskGenius：{str(e)}")

    def open_clumsy(self):
        logger.info("打开clumsy")
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'clumsy', 'clumsy.exe')
        exe_path = os.path.abspath(exe_path)
        try:
            import subprocess
            subprocess.run(
                ['powershell', '-Command', f'Start-Process "{exe_path}" -Verb runAs'],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            QMessageBox.warning(self, "打开clumsy", f"无法以管理员权限打开clumsy：{str(e)}")

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
        self.sync_btn.setText("sync")
