from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QCheckBox
)
import os
from src.utils.logger import get_logger
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
import subprocess
import shlex
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger(__name__)

class SignatureCheckerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("程序文件签名检查")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # 扫描目录行优化，参考file_hash_calc_ui.py风格
        top_layout = QHBoxLayout()
        dir_label = QLabel("扫描目录:")
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("请选择要扫描的目录")
        self.dir_edit.setMinimumHeight(28)
        self.scan_btn = QPushButton()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "open_dirs.png")
        self.scan_btn.setIcon(QIcon(icon_path))
        self.scan_btn.setToolTip("选择目录")
        self.scan_btn.setFixedSize(28, 28)
        self.scan_btn.clicked.connect(self.choose_directory)

        self.start_btn = QPushButton()
        scan_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "scan.png")
        self.start_btn.setIcon(QIcon(scan_icon_path))
        self.start_btn.setToolTip("开始扫描")
        self.start_btn.setFixedSize(28, 28)
        self.start_btn.clicked.connect(self.on_start_scan)
        self.start_btn.setEnabled(False)

        top_layout.addWidget(dir_label)
        top_layout.addWidget(self.dir_edit, 1)
        top_layout.addWidget(self.scan_btn)
        top_layout.addWidget(self.start_btn)
        top_layout.setSpacing(8)
        top_layout.setContentsMargins(4, 8, 4, 8)
        layout.addLayout(top_layout)

        # 过滤复选框
        self.exclude_ms_checkbox = QCheckBox("排除微软文件")
        self.exclude_ms_checkbox.setChecked(False)
        self.exclude_ms_checkbox.stateChanged.connect(self.apply_filter)
        layout.addWidget(self.exclude_ms_checkbox)

        # 表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["文件名", "签名状态", "签名者姓名"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.dir_edit.textChanged.connect(self.on_dir_edit_changed)
        self.dir_edit.setText(r"C:\Program Files\Enterprise Information Management\HostAgent")
        # 存储所有结果
        self._all_rows = []

    def on_dir_edit_changed(self, text):
        self.start_btn.setEnabled(os.path.isdir(text.strip()))

    def choose_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if dir_path:
            self.dir_edit.setText(dir_path)
            self.table.setRowCount(0)

    def on_start_scan(self):
        dir_path = self.dir_edit.text().strip()
        if not dir_path or not os.path.isdir(dir_path):
            QMessageBox.warning(self, "无效目录", "请输入或选择一个有效的扫描目录！")
            return
        self.scan_and_display(dir_path)
        self.start_btn.setEnabled(False)

    def scan_and_display(self, dir_path):
        self.table.setRowCount(0)
        self._all_rows = []
        # 关闭按钮防止重复点击
        self.scan_btn.setEnabled(False)
        # 启动异步扫描线程
        self.worker = SignatureScanWorker(dir_path, self.get_signature_info)
        self.worker.result_signal.connect(self.add_signature_row)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()

    def add_signature_row(self, file_path, status, signer):
        self._all_rows.append((file_path, status, signer))
        self.apply_filter()

    def apply_filter(self):
        # 重新填充表格，按过滤条件
        self.table.setRowCount(0)
        exclude_ms = self.exclude_ms_checkbox.isChecked()
        for file_path, status, signer in self._all_rows:
            if exclude_ms and signer.strip() in ("Microsoft Corporation", "Microsoft Windows"):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(file_path))
            self.table.setItem(row, 1, QTableWidgetItem(status))
            self.table.setItem(row, 2, QTableWidgetItem(signer))
            if status == "未签名":
                for col in range(3):
                    self.table.item(row, col).setBackground(QColor(255, 220, 220))
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        width = sum([self.table.columnWidth(i) for i in range(self.table.columnCount())]) + 60
        height = min(600, self.table.verticalHeader().length() + 120)
        self.resize(width, height)

    def on_scan_finished(self):
        self.scan_btn.setEnabled(True)
        self.start_btn.setEnabled(True)

    def get_signature_info(self, file_path):
        logger = get_logger(__name__)
        try:
            ps_cmd = (
                f"$sig=Get-AuthenticodeSignature -FilePath {shlex.quote(file_path)};"
                "if ($sig.SignerCertificate -ne $null) { "
                "($sig.SignerCertificate.Subject -split ',')[0] -replace 'CN=', '' "
                "} else { '' }"
            )
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=20, encoding="gbk", errors="replace",
                creationflags=creationflags
            )
            logger.info(f"Powershell签名解析结果: {result.stdout}")
            signer = result.stdout.strip()
            status = "已签名" if signer else "未签名"
            return status, signer if signer else "-"
        except Exception as e:
            logger.error(f"Powershell签名解析异常: {e}")
            return "无法解析", "-" 

class SignatureScanWorker(QThread):
    result_signal = pyqtSignal(str, str, str)  # file_path, status, signer
    finished_signal = pyqtSignal()
    def __init__(self, dir_path, get_signature_info_func, max_workers=6):
        super().__init__()
        self.dir_path = dir_path
        self.get_signature_info_func = get_signature_info_func
        self.max_workers = max_workers
        self._is_running = True
    def run(self):
        file_list = []
        for root, _, files in os.walk(self.dir_path):
            for f in files:
                if f.lower().endswith((".exe", ".dll")):
                    file_list.append(os.path.join(root, f))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.get_signature_info_func, fp): fp for fp in file_list}
            for future in as_completed(futures):
                if not self._is_running:
                    break
                file_path = futures[future]
                try:
                    status, signer = future.result()
                except Exception:
                    status, signer = "无法解析", "-"
                self.result_signal.emit(file_path, status, signer)
        self.finished_signal.emit()
    def stop(self):
        self._is_running = False 