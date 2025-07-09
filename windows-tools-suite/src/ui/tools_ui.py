from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QMessageBox, QGroupBox, QHBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal
import os
import ctypes
from ..utils.logger import get_logger

# 配置日志
logger = get_logger(__name__)


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

class ToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("第三方工具")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        # diskprobe分组
        diskprobe_group = QGroupBox("磁盘扇区查看")
        diskprobe_layout = QHBoxLayout()
        diskprobe_btn = QPushButton("打开diskprobe")
        diskprobe_btn.clicked.connect(self.open_diskprobe)
        diskprobe_layout.addWidget(diskprobe_btn)
        diskprobe_group.setLayout(diskprobe_layout)
        layout.addWidget(diskprobe_group)

        # DiskGenius分组
        diskgenius_group = QGroupBox("磁盘信息查看")
        diskgenius_layout = QHBoxLayout()
        diskgenius_btn = QPushButton("打开DiskGenius")
        diskgenius_btn.clicked.connect(self.open_diskgenius)
        diskgenius_layout.addWidget(diskgenius_btn)
        diskgenius_group.setLayout(diskgenius_layout)
        layout.addWidget(diskgenius_group)

        # clumsy分组
        clumsy_group = QGroupBox("网络异常模拟")
        clumsy_layout = QHBoxLayout()
        clumsy_btn = QPushButton("打开clumsy")
        clumsy_btn.clicked.connect(self.open_clumsy)
        clumsy_layout.addWidget(clumsy_btn)
        clumsy_group.setLayout(clumsy_layout)
        layout.addWidget(clumsy_group)

        # 新增：进程查看器分组
        procmon_group = QGroupBox("进程查看器")
        procmon_layout = QHBoxLayout()
        procmon_btn = QPushButton("打开Procmon")
        procmon_btn.clicked.connect(self.open_procmon)
        procmon_layout.addWidget(procmon_btn)
        procmon_group.setLayout(procmon_layout)
        layout.addWidget(procmon_group)

        # 新增：内存检测实用工具分组
        vmmap_group = QGroupBox("内存检测实用工具")
        vmmap_layout = QHBoxLayout()
        vmmap_btn = QPushButton("打开VMMap")
        vmmap_btn.clicked.connect(self.open_vmmap)
        vmmap_layout.addWidget(vmmap_btn)
        vmmap_group.setLayout(vmmap_layout)
        layout.addWidget(vmmap_group)

        self.setLayout(layout)

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
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f'/c start "" "{exe_path}"', None, 1
            )
            if ret <= 32:
                QMessageBox.warning(self, "打开clumsy", f"无法以管理员权限打开clumsy，返回码：{ret}")
        except Exception as e:
            QMessageBox.warning(self, "打开clumsy", f"无法以管理员权限打开clumsy：{str(e)}")

    def open_procmon(self):
        logger.info("打开Procmon")
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'processmonitor', 'Procmon.exe')
        exe_path = os.path.abspath(exe_path)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f'/c start "" "{exe_path}"', None, 1
            )
            if ret <= 32:
                QMessageBox.warning(self, "打开Procmon", f"无法以管理员权限打开Procmon，返回码：{ret}")
        except Exception as e:
            QMessageBox.warning(self, "打开Procmon", f"无法以管理员权限打开Procmon：{str(e)}")

    def open_vmmap(self):
        logger.info("打开VMMap")
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'vmmap', 'vmmap.exe')
        exe_path = os.path.abspath(exe_path)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "cmd.exe", f'/c start "" "{exe_path}"', None, 1
            )
            if ret <= 32:
                QMessageBox.warning(self, "打开VmMap", f"无法以管理员权限打开VmMap，返回码：{ret}")
        except Exception as e:
            QMessageBox.warning(self, "打开VmMap", f"无法以管理员权限打开VmMap：{str(e)}")
