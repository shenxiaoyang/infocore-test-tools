from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QCheckBox, QTextEdit, QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QWidget
from PyQt5.QtGui import QIcon
import hashlib
import os
import pathlib
import time
from src.utils.logger import get_logger
from PyQt5.QtCore import QThread, pyqtSignal

logger = get_logger(__name__)

class HashCalcWorker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(dict, str)
    error = pyqtSignal(str)
    def __init__(self, file_path, algos):
        super().__init__()
        self.file_path = file_path
        self.algos = algos
        self._is_running = True
    def run(self):
        try:
            file_size = os.path.getsize(self.file_path)
            hashes = {}
            hash_objs = {}
            if 'md5' in self.algos: hash_objs['md5'] = hashlib.md5()
            if 'sha1' in self.algos: hash_objs['sha1'] = hashlib.sha1()
            if 'sha256' in self.algos: hash_objs['sha256'] = hashlib.sha256()
            if 'sha512' in self.algos: hash_objs['sha512'] = hashlib.sha512()
            read_size = 0
            with open(self.file_path, 'rb') as f:
                while self._is_running:
                    chunk = f.read(1024*1024)
                    if not chunk:
                        break
                    for h in hash_objs.values():
                        h.update(chunk)
                    read_size += len(chunk)
                    percent = int(read_size * 100 / file_size) if file_size else 100
                    self.progress.emit(percent)
            for k, h in hash_objs.items():
                hashes[k] = h.hexdigest()
            self.result.emit(hashes, self.file_path)
        except Exception as e:
            self.error.emit(str(e))
    def stop(self):
        self._is_running = False

class FileHashCalcDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件MD5/SHA哈希计算与校验")
        self.setMinimumWidth(580)
        self.setAcceptDrops(True)  # 允许拖拽
        layout = QVBoxLayout()
        self.worker = None
        # 路径选择
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("您可以拖拽文件到此处")
        path_layout.addWidget(QLabel("文件路径:"))
        path_layout.addWidget(self.path_edit)
        browse_btn = QPushButton()
        browse_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons', 'open_dirs.png')))
        browse_btn.setFixedSize(28, 28)
        browse_btn.clicked.connect(self.select_file)
        path_layout.addWidget(browse_btn)
        
        # 历史记录按钮
        history_btn = QPushButton()
        history_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons', 'history.png')))
        history_btn.setFixedSize(28, 28)
        history_btn.setToolTip("历史记录")
        history_btn.clicked.connect(self.show_history)
        path_layout.addWidget(history_btn)
        layout.addLayout(path_layout)
        # 文件信息（每项一行，风格与哈希一致）
        self.size_edit = QLineEdit()
        self.size_edit.setReadOnly(True)
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("文件大小:"))
        size_layout.addWidget(self.size_edit)
        layout.addLayout(size_layout)
        self.ctime_edit = QLineEdit()
        self.ctime_edit.setReadOnly(True)
        ctime_layout = QHBoxLayout()
        ctime_layout.addWidget(QLabel("创建时间:"))
        ctime_layout.addWidget(self.ctime_edit)
        layout.addLayout(ctime_layout)
        self.mtime_edit = QLineEdit()
        self.mtime_edit.setReadOnly(True)
        mtime_layout = QHBoxLayout()
        mtime_layout.addWidget(QLabel("修改时间:"))
        mtime_layout.addWidget(self.mtime_edit)
        layout.addLayout(mtime_layout)
        self.atime_edit = QLineEdit()
        self.atime_edit.setReadOnly(True)
        atime_layout = QHBoxLayout()
        atime_layout.addWidget(QLabel("访问时间:"))
        atime_layout.addWidget(self.atime_edit)
        layout.addLayout(atime_layout)
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        # MD5
        self.md5_cb = QCheckBox("MD5")
        self.md5_cb.setChecked(True)
        self.md5_edit = QLineEdit()
        self.md5_edit.setReadOnly(True)
        md5_layout = QHBoxLayout()
        md5_layout.addWidget(self.md5_cb)
        md5_layout.addWidget(self.md5_edit)
        layout.addLayout(md5_layout)
        # SHA1
        self.sha1_cb = QCheckBox("SHA1")
        self.sha1_cb.setChecked(True)
        self.sha1_edit = QLineEdit()
        self.sha1_edit.setReadOnly(True)
        sha1_layout = QHBoxLayout()
        sha1_layout.addWidget(self.sha1_cb)
        sha1_layout.addWidget(self.sha1_edit)
        layout.addLayout(sha1_layout)
        # SHA256
        self.sha256_cb = QCheckBox("SHA256")
        self.sha256_cb.setChecked(True)
        self.sha256_edit = QLineEdit()
        self.sha256_edit.setReadOnly(True)
        sha256_layout = QHBoxLayout()
        sha256_layout.addWidget(self.sha256_cb)
        sha256_layout.addWidget(self.sha256_edit)
        layout.addLayout(sha256_layout)
        # SHA512
        self.sha512_cb = QCheckBox("SHA512")
        self.sha512_cb.setChecked(True)
        self.sha512_edit = QLineEdit()
        self.sha512_edit.setReadOnly(True)
        sha512_layout = QHBoxLayout()
        sha512_layout.addWidget(self.sha512_cb)
        sha512_layout.addWidget(self.sha512_edit)
        layout.addLayout(sha512_layout)
        # 粘贴比对
        self.compare_edit = QLineEdit()
        self.compare_edit.setPlaceholderText("请在此处粘贴要对比的哈希值:")
        self.compare_edit.textChanged.connect(self.compare_hash)
        layout.addWidget(self.compare_edit)
        self.setLayout(layout)

    def show_file_info(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            self.size_edit.clear()
            self.ctime_edit.clear()
            self.mtime_edit.clear()
            self.atime_edit.clear()
            return
        stat = os.stat(file_path)
        size = stat.st_size
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_ctime))
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        atime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_atime))
        size_str = self.human_readable_size(size)
        self.size_edit.setText(f"{size_str} ({size} 字节)")
        self.ctime_edit.setText(ctime)
        self.mtime_edit.setText(mtime)
        self.atime_edit.setText(atime)

    def human_readable_size(self, size):
        for unit in ['B','KB','MB','GB','TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "所有文件 (*)")
        if file_path:
            self.path_edit.setText(file_path)
            self.show_file_info(file_path)
            self.calc_hash_async()

    def calc_hash_async(self):
        file_path = self.path_edit.text().strip()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "错误", "请选择一个有效的文件！")
            self.size_edit.clear()
            self.ctime_edit.clear()
            self.mtime_edit.clear()
            self.atime_edit.clear()
            return
        self.show_file_info(file_path)
        algos = []
        if self.md5_cb.isChecked(): algos.append('md5')
        if self.sha1_cb.isChecked(): algos.append('sha1')
        if self.sha256_cb.isChecked(): algos.append('sha256')
        if self.sha512_cb.isChecked(): algos.append('sha512')
        if not algos:
            QMessageBox.warning(self, "错误", "请至少选择一个哈希算法！")
            return
        self.set_ui_busy(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.worker = HashCalcWorker(file_path, algos)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.result.connect(self.on_hash_result)
        self.worker.error.connect(self.on_hash_error)
        self.worker.start()

    def set_ui_busy(self, busy):
        # 禁用/恢复相关控件
        self.path_edit.setDisabled(busy)
        self.md5_cb.setDisabled(busy)
        self.sha1_cb.setDisabled(busy)
        self.sha256_cb.setDisabled(busy)
        self.sha512_cb.setDisabled(busy)

    def on_hash_result(self, hashes, file_path):
        self.md5_edit.setText(hashes.get('md5', ''))
        self.sha1_edit.setText(hashes.get('sha1', ''))
        self.sha256_edit.setText(hashes.get('sha256', ''))
        self.sha512_edit.setText(hashes.get('sha512', ''))
        self.progress_bar.setVisible(False)
        self.set_ui_busy(False)
        self.compare_hash()
        # 写入历史记录
        try:
            program_data = os.environ.get('ProgramData', r'C:\ProgramData')
            history_dir = os.path.join(program_data, 'InfoCoreTestTools')
            history_file = os.path.join(history_dir, 'hash_history.txt')
            pathlib.Path(history_dir).mkdir(parents=True, exist_ok=True)
            file_path = self.path_edit.text()
            size = self.size_edit.text()
            md5 = self.md5_edit.text()
            record = f"{file_path}\t{size}\t{md5}"
            records = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    records = [line.strip() for line in f if line.strip()]
            records.append(record)
            records = records[-10:]
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(records) + '\n')
        except Exception as e:
            logger.warning(f'写入历史记录失败: {e}')

    def on_hash_error(self, msg):
        QMessageBox.warning(self, "计算失败", f"哈希计算失败：{msg}")
        self.progress_bar.setVisible(False)
        self.set_ui_busy(False)

    def compare_hash(self):
        cmp = self.compare_edit.text().strip().lower()
        for edit in [self.md5_edit, self.sha1_edit, self.sha256_edit, self.sha512_edit]:
            val = edit.text().strip().lower()
            if cmp and val and cmp == val:
                edit.setStyleSheet("background: #c8f7c5;")  # 绿色
            else:
                edit.setStyleSheet("")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.isfile(file_path):
                self.path_edit.setText(file_path)
                self.show_file_info(file_path)
                self.calc_hash_async()

    def show_history(self):
        dlg = HistoryDialog(self)
        dlg.exec_()

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("哈希历史记录")
        self.max_width = 1000
        self.min_col_width = 200
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件", "文件大小", "MD5"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        layout.addWidget(self.table)
        # 无历史记录图片和文字
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout()
        empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_label_img = QLabel()
        pixmap = QPixmap(os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons', 'no_history.png'))
        pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.empty_label_img.setPixmap(pixmap)
        self.empty_label_img.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_label_img)
        self.empty_label_text = QLabel("无历史记录")
        self.empty_label_text.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_label_text)
        self.empty_widget.setLayout(empty_layout)
        layout.addWidget(self.empty_widget)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        clear_btn = QPushButton("清除历史记录")
        clear_btn.setFixedWidth(140)
        clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(clear_btn)
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_history()

    def load_history(self):
        program_data = os.environ.get('ProgramData', r'C:\ProgramData')
        history_file = os.path.join(program_data, 'InfoCoreTestTools', 'hash_history.txt')
        self.table.setRowCount(0)
        has_data = False
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                for row_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    fields = line.split('\t')
                    self.table.insertRow(row_idx)
                    for col, val in enumerate(fields):
                        self.table.setItem(row_idx, col, QTableWidgetItem(val))
                    has_data = True
        # 控件显示切换
        self.table.setVisible(has_data)
        self.empty_widget.setVisible(not has_data)
        # 设置列宽和窗口宽度
        if has_data:
            self.table.resizeColumnsToContents()
            total_width = sum([self.table.columnWidth(i) for i in range(self.table.columnCount())])
            total_width = min(total_width + 60, self.max_width)
            self.resize(total_width, 400)
        else:
            for i in range(self.table.columnCount()):
                self.table.setColumnWidth(i, self.min_col_width)
            self.resize(self.min_col_width * self.table.columnCount() + 60, 400)

    def clear_history(self):
        program_data = os.environ.get('ProgramData', r'C:\ProgramData')
        history_file = os.path.join(program_data, 'InfoCoreTestTools', 'hash_history.txt')
        try:
            if os.path.exists(history_file):
                os.remove(history_file)
            self.table.setRowCount(0)
            self.table.setVisible(False)
            self.empty_widget.setVisible(True)
            for i in range(self.table.columnCount()):
                self.table.setColumnWidth(i, self.min_col_width)
            self.resize(self.min_col_width * self.table.columnCount() + 60, 400)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清除历史记录失败: {e}")
