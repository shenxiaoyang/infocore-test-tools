from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFileDialog, QPlainTextEdit, QSplitter, QGroupBox, QFrame,
                           QProgressDialog, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
from ..utils.logger import Logger
from PyQt5.QtWidgets import QApplication
from difflib import SequenceMatcher
import os

class CompareWorker(QThread):
    """后台工作线程，用于执行文件对比"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, left_file, right_file):
        super().__init__()
        self.left_file = left_file
        self.right_file = right_file
        self.logger = Logger("CompareWorker")
    
    def run(self):
        try:
            self.logger.info(f"开始对比文件: {self.left_file} 和 {self.right_file}")
            self.progress.emit("正在读取文件...")
            
            # 读取文件内容
            with open(self.left_file, 'r', encoding='utf-8') as f:
                left_lines = [line.rstrip('\n') for line in f.readlines()]
            self.logger.info(f"已读取左侧文件，共 {len(left_lines)} 行")
            
            with open(self.right_file, 'r', encoding='utf-8') as f:
                right_lines = [line.rstrip('\n') for line in f.readlines()]
            self.logger.info(f"已读取右侧文件，共 {len(right_lines)} 行")
            
            self.progress.emit("正在对比差异...")
            
            # 使用序列匹配器找出相似行
            matcher = SequenceMatcher(None, left_lines, right_lines)
            
            # 准备结果数据
            aligned_left_lines = []   # 左侧显示的行
            aligned_right_lines = []  # 右侧显示的行
            left_diff_types = {}      # 左侧差异类型 {行号: 类型}
            right_diff_types = {}     # 右侧差异类型 {行号: 类型}
            
            left_index = 0
            right_index = 0
            
            # 处理每个匹配块
            for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
                self.progress.emit(f"正在处理差异块: {tag}")
                
                if tag == 'equal':
                    # 完全相同的部分
                    for i in range(alo, ahi):
                        aligned_left_lines.append(left_lines[i])
                        aligned_right_lines.append(right_lines[blo + (i - alo)])
                        left_index = i + 1
                        right_index = blo + (i - alo) + 1
                
                elif tag == 'replace':
                    # 替换的部分（内容不同）
                    max_lines = max(ahi - alo, bhi - blo)
                    for i in range(max_lines):
                        left_pos = alo + i
                        right_pos = blo + i
                        
                        if left_pos < ahi and right_pos < bhi:
                            # 两边都有内容，但不同
                            aligned_left_lines.append(left_lines[left_pos])
                            aligned_right_lines.append(right_lines[right_pos])
                            left_diff_types[len(aligned_left_lines)] = "≠"
                            right_diff_types[len(aligned_right_lines)] = "≠"
                        elif left_pos < ahi:
                            # 只有左边有内容
                            aligned_left_lines.append(left_lines[left_pos])
                            aligned_right_lines.append("")
                            left_diff_types[len(aligned_left_lines)] = "-"
                        else:
                            # 只有右边有内容
                            aligned_left_lines.append("")
                            aligned_right_lines.append(right_lines[right_pos])
                            right_diff_types[len(aligned_right_lines)] = "+"
                
                elif tag == 'delete':
                    # 删除的部分（左边独有）
                    for i in range(alo, ahi):
                        aligned_left_lines.append(left_lines[i])
                        aligned_right_lines.append("")
                        left_diff_types[len(aligned_left_lines)] = "-"
                        left_index = i + 1
                
                elif tag == 'insert':
                    # 插入的部分（右边独有）
                    for i in range(blo, bhi):
                        aligned_left_lines.append("")
                        aligned_right_lines.append(right_lines[i])
                        right_diff_types[len(aligned_right_lines)] = "+"
                        right_index = i + 1
            
            # 添加换行符
            aligned_left_lines = [line + "\n" for line in aligned_left_lines]
            aligned_right_lines = [line + "\n" for line in aligned_right_lines]
            
            self.logger.info(f"对比完成，找到 {len(left_diff_types) + len(right_diff_types)} 处差异")
            
            # 发送结果
            result = {
                'left_lines': aligned_left_lines,
                'right_lines': aligned_right_lines,
                'left_diff_types': left_diff_types,
                'right_diff_types': right_diff_types,
                'total_lines': len(aligned_left_lines)
            }
            self.finished.emit(result)
            
        except Exception as e:
            self.logger.error(f"对比过程出错: {str(e)}")
            self.error.emit(str(e))

class DiffHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 不同类型差异的格式
        self.formats = {
            "≠": self._create_format("#ffecec"),  # 修改的行（浅红色）
            "+": self._create_format("#e6ffe6"),  # 新增的行（浅绿色）
            "-": self._create_format("#ffe6e6"),  # 删除的行（浅红色）
        }
        self.diff_types = {}  # {行号: 差异类型}
        self.batch_size = 5000
        self.current_block = 0
        self.logger = Logger("DiffHighlighter")
        self.is_highlighting = False
        self._document = None
    
    def _create_format(self, color):
        """创建文本格式"""
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(color))
        return fmt
        
    def set_diff_types(self, diff_types):
        """设置差异类型并开始高亮处理"""
        self.diff_types = diff_types
        self.current_block = 0
        self._document = self.document()
        
        # 暂时禁用文档重绘
        if self._document:
            self._document.blockSignals(True)
        
        self.is_highlighting = True
        self.rehighlight_batch()

    def rehighlight_batch(self):
        """分批重新高亮文档"""
        if not self._document or not self.is_highlighting:
            return

        try:
            start_block = self.current_block
            end_block = min(start_block + self.batch_size, self._document.blockCount())
            
            self.logger.info(f"正在高亮第 {start_block} 至 {end_block} 块...")
            
            # 批量处理文本块
            blocks_to_highlight = []
            block = self._document.findBlockByNumber(start_block)
            
            while block.isValid() and block.blockNumber() < end_block:
                if (block.blockNumber() + 1) in self.diff_types:
                    blocks_to_highlight.append(block)
                block = block.next()
            
            # 批量应用高亮
            for block in blocks_to_highlight:
                self.rehighlightBlock(block)
            
            self.current_block = end_block
            
            # 如果还有未处理的块，继续处理下一批
            if end_block < self._document.blockCount():
                QThread.msleep(1)  # 减少暂停时间
                QTimer.singleShot(1, self.rehighlight_batch)  # 使用定时器异步处理下一批
            else:
                # 完成高亮处理
                self.is_highlighting = False
                if self._document:
                    self._document.blockSignals(False)
                    self._document = None
                self.logger.info("高亮处理完成")
                
        except Exception as e:
            self.logger.error(f"高亮处理出错: {str(e)}")
            self.is_highlighting = False
            if self._document:
                self._document.blockSignals(False)
                self._document = None

    def highlightBlock(self, text):
        """高亮单个文本块"""
        if not text:
            return
            
        block_number = self.currentBlock().blockNumber() + 1
        if block_number in self.diff_types:
            diff_type = self.diff_types[block_number]
            if diff_type in self.formats:
                self.setFormat(0, len(text), self.formats[diff_type])

    def clear_highlighting(self):
        """清除所有高亮"""
        self.diff_types = {}
        if self.document():
            self.document().blockSignals(True)
            # 重新应用空的高亮
            self.rehighlight()
            self.document().blockSignals(False)

class FileCompareUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件对比")
        self.setMinimumSize(1500, 800)
        self.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei, Arial;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 5px;
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
            QLabel {
                color: #2f3640;
            }
        """)
        self.logger = Logger("FileCompareUI")
        self.worker = None
        self.progress_dialog = None
        self.sync_scroll = True  # 添加同步滚动标志
        self._scrolling = False  # 添加滚动状态标志
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(layout)
        
        # ===== 文件选择区域 =====
        file_select_container = QFrame()
        file_select_container.setFixedHeight(80)  # 设置固定高度
        file_select_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        
        file_select_layout = QHBoxLayout(file_select_container)
        file_select_layout.setContentsMargins(10, 10, 10, 10)
        file_select_layout.setSpacing(10)
        
        # 文件选择行布局
        file_selection_layout = QHBoxLayout()
        file_selection_layout.setSpacing(10)
        
        # 左侧文件选择
        left_layout = QHBoxLayout()
        left_layout.setSpacing(5)
        
        left_label = QLabel("文件1")
        left_label.setFixedWidth(40)
        left_label.setFixedHeight(30)  # 固定高度与按钮一致
        left_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        left_label.setStyleSheet("font-weight: bold;")
        
        self.left_file_path = QLabel("未选择文件")
        self.left_file_path.setStyleSheet("""
            color: #6c757d; 
            background: white; 
            border: 1px solid #dee2e6; 
            border-radius: 4px;
            padding: 0px 10px;  /* 减小垂直内边距 */
        """)
        self.left_file_path.setMinimumWidth(300)
        self.left_file_path.setFixedHeight(30)  # 固定高度与按钮一致
        
        self.left_file_btn = QPushButton("选择文件")
        self.left_file_btn.setFixedSize(80, 30)
        self.left_file_btn.clicked.connect(lambda: self.select_file("left"))
        
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.left_file_path, 1)
        left_layout.addWidget(self.left_file_btn, 0)
        
        # 右侧文件选择
        right_layout = QHBoxLayout()
        right_layout.setSpacing(5)
        
        right_label = QLabel("文件2")
        right_label.setFixedWidth(40)
        right_label.setFixedHeight(30)  # 固定高度与按钮一致
        right_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_label.setStyleSheet("font-weight: bold;")
        
        self.right_file_path = QLabel("未选择文件")
        self.right_file_path.setStyleSheet("""
            color: #6c757d; 
            background: white; 
            border: 1px solid #dee2e6; 
            border-radius: 4px;
            padding: 0px 10px;  /* 减小垂直内边距 */
        """)
        self.right_file_path.setMinimumWidth(300)
        self.right_file_path.setFixedHeight(30)  # 固定高度与按钮一致
        
        self.right_file_btn = QPushButton("选择文件")
        self.right_file_btn.setFixedSize(80, 30)
        self.right_file_btn.clicked.connect(lambda: self.select_file("right"))
        
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.right_file_path, 1)
        right_layout.addWidget(self.right_file_btn, 0)
        
        # 将左右文件选择添加到文件选择布局
        file_selection_layout.addLayout(left_layout, 1)
        file_selection_layout.addLayout(right_layout, 1)
        
        # 对比按钮
        self.compare_btn = QPushButton("开始对比")
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.compare_btn.setFixedSize(90, 30)
        self.compare_btn.clicked.connect(self.compare_files)
        
        # 添加文件选择和对比按钮到主布局
        file_select_layout.addLayout(file_selection_layout, 1)
        file_select_layout.addWidget(self.compare_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        
        # 添加到主布局
        layout.addWidget(file_select_container)
        
        # 对比结果区域
        result_container = QFrame()
        result_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
            }
        """)
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(1, 1, 1, 1)  # 最小边距以显示边框
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #2f3640;
                width: 2px;
                margin-left: 2px;
                margin-right: 2px;
            }
            QSplitter::handle:hover {
                background: #3742fa;
                width: 2px;
            }
            QSplitter::handle:pressed {
                background: #1e90ff;
                width: 2px;
            }
        """)
        
        # 左侧文本框
        self.left_text = QPlainTextEdit()
        self.left_text.setReadOnly(True)
        self.left_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.left_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.left_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 13px;
                background-color: white;
                border: none;
                selection-background-color: #bdc3c7;
            }
        """)
        
        # 右侧文本框
        self.right_text = QPlainTextEdit()
        self.right_text.setReadOnly(True)
        self.right_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.right_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.right_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 13px;
                background-color: white;
                border: none;
                selection-background-color: #bdc3c7;
            }
        """)
        
        # 连接滚动条信号
        self.left_text.verticalScrollBar().valueChanged.connect(self.sync_left_vertical_scroll)
        self.right_text.verticalScrollBar().valueChanged.connect(self.sync_right_vertical_scroll)
        self.left_text.horizontalScrollBar().valueChanged.connect(self.sync_left_horizontal_scroll)
        self.right_text.horizontalScrollBar().valueChanged.connect(self.sync_right_horizontal_scroll)
        
        # 重写滚轮事件
        self.left_text.wheelEvent = self.on_left_wheel
        self.right_text.wheelEvent = self.on_right_wheel
        
        splitter.addWidget(self.left_text)
        splitter.addWidget(self.right_text)
        result_layout.addWidget(splitter)
        
        layout.addWidget(result_container)
        
        # 添加对比状态栏
        self.compare_status_label = QLabel("")
        self.compare_status_label.setStyleSheet("""
            QLabel {
                padding: 2px 5px;
                border: 1px solid #dcdde1;
                border-radius: 2px;
                background-color: #f5f5f5;
                min-height: 16px;
                max-height: 16px;
                font-size: 12px;
            }
        """)
        self.compare_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.compare_status_label)
        
        # 创建高亮器
        self.left_highlighter = DiffHighlighter(self.left_text.document())
        self.right_highlighter = DiffHighlighter(self.right_text.document())
        
        # 初始化文件路径
        self.left_file = ""
        self.right_file = ""
        
        # ======= 新增功能栏 =======
        feature_bar = QHBoxLayout()
        self.only_diff_checkbox = QCheckBox("仅显示不同内容")
        self.only_diff_checkbox.setChecked(False)
        self.only_diff_checkbox.stateChanged.connect(self.on_only_diff_changed)
        feature_bar.addWidget(self.only_diff_checkbox)
        feature_bar.addStretch(1)
        layout.addLayout(feature_bar)
        
    def select_file(self, side):
        self.logger.info(f"选择{side}侧文件")
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.logger.info(f"已选择文件: {file_path}")
            if side == "left":
                self.left_file = file_path
                self.left_file_path.setText(file_path)
            else:
                self.right_file = file_path
                self.right_file_path.setText(file_path)
    
    def compare_files(self):
        if not self.left_file or not self.right_file:
            self.logger.warning("未选择文件")
            return
            
        # 清除之前的高亮
        self.left_highlighter.clear_highlighting()
        self.right_highlighter.clear_highlighting()
        
        # 检查文件大小
        left_size = os.path.getsize(self.left_file) / (1024 * 1024)  # 转换为MB
        right_size = os.path.getsize(self.right_file) / (1024 * 1024)  # 转换为MB
        
        if left_size > 10 or right_size > 10:
            self.logger.warning("文件大小超过10MB，不予对比")
            self.left_text.setPlainText(f"错误：文件大小超过10MB限制，不予对比\n左侧文件: {left_size:.2f}MB\n右侧文件: {right_size:.2f}MB")
            self.right_text.setPlainText(f"错误：文件大小超过10MB限制，不予对比\n左侧文件: {left_size:.2f}MB\n右侧文件: {right_size:.2f}MB")
            return
            
        # 检查是否为文本文件
        if not self.is_text_file(self.left_file) or not self.is_text_file(self.right_file):
            self.logger.warning("非文本文件，不予对比")
            self.left_text.setPlainText("错误：只能对比文本文件，请确保选择的是文本文件")
            self.right_text.setPlainText("错误：只能对比文本文件，请确保选择的是文本文件")
            return
            
        self.logger.info("开始文件对比")
        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在对比文件...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("请稍候")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.show()
        
        # 创建并启动工作线程
        self.worker = CompareWorker(self.left_file, self.right_file)
        self.worker.finished.connect(self.on_compare_finished)
        self.worker.error.connect(self.on_compare_error)
        self.worker.progress.connect(self.update_progress)
        self.worker.start()
    
    def update_progress(self, message):
        """更新进度对话框信息"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
    
    def sync_left_vertical_scroll(self, value):
        """同步左侧垂直滚动到右侧"""
        if self._scrolling or not self.sync_scroll:
            return
        try:
            self._scrolling = True
            # 只同步垂直滚动条
            self.right_text.verticalScrollBar().setValue(value)
        finally:
            self._scrolling = False
    
    def sync_right_vertical_scroll(self, value):
        """同步右侧垂直滚动到左侧"""
        if self._scrolling or not self.sync_scroll:
            return
        try:
            self._scrolling = True
            # 只同步垂直滚动条
            self.left_text.verticalScrollBar().setValue(value)
        finally:
            self._scrolling = False
            
    def sync_left_horizontal_scroll(self, value):
        """同步左侧水平滚动到右侧"""
        if self._scrolling or not self.sync_scroll:
            return
        try:
            self._scrolling = True
            # 只同步水平滚动条
            self.right_text.horizontalScrollBar().setValue(value)
        finally:
            self._scrolling = False
    
    def sync_right_horizontal_scroll(self, value):
        """同步右侧水平滚动到左侧"""
        if self._scrolling or not self.sync_scroll:
            return
        try:
            self._scrolling = True
            # 只同步水平滚动条
            self.left_text.horizontalScrollBar().setValue(value)
        finally:
            self._scrolling = False
    
    def on_left_wheel(self, event):
        """处理左侧滚轮事件"""
        if self._scrolling:
            return
        try:
            self._scrolling = True
            QPlainTextEdit.wheelEvent(self.left_text, event)
            if self.sync_scroll:
                # 分别同步垂直和水平滚动位置
                v_value = self.left_text.verticalScrollBar().value()
                h_value = self.left_text.horizontalScrollBar().value()
                self.right_text.verticalScrollBar().setValue(v_value)
                self.right_text.horizontalScrollBar().setValue(h_value)
        finally:
            self._scrolling = False
    
    def on_right_wheel(self, event):
        """处理右侧滚轮事件"""
        if self._scrolling:
            return
        try:
            self._scrolling = True
            QPlainTextEdit.wheelEvent(self.right_text, event)
            if self.sync_scroll:
                # 分别同步垂直和水平滚动位置
                v_value = self.right_text.verticalScrollBar().value()
                h_value = self.right_text.horizontalScrollBar().value()
                self.left_text.verticalScrollBar().setValue(v_value)
                self.left_text.horizontalScrollBar().setValue(h_value)
        finally:
            self._scrolling = False
    
    def on_compare_finished(self, result):
        """对比完成的处理"""
        self.logger.info("文件对比完成，开始显示结果")
        if self.progress_dialog:
            self.progress_dialog.close()
        
        # 分批显示文本内容
        self.progress_dialog = QProgressDialog("正在显示结果...", None, 0, 100, self)
        self.progress_dialog.setWindowTitle("请稍候")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

        try:
            # 禁用更新和滚动条
            self.left_text.setUpdatesEnabled(False)
            self.right_text.setUpdatesEnabled(False)
            self.left_text.verticalScrollBar().setEnabled(False)
            self.right_text.verticalScrollBar().setEnabled(False)
            self.left_text.horizontalScrollBar().setEnabled(False)
            self.right_text.horizontalScrollBar().setEnabled(False)
            
            # 临时禁用同步滚动
            self.sync_scroll = False
            
            # 清空现有内容
            self.left_text.clear()
            self.right_text.clear()
            
            # 保存完整对比结果
            self._compare_result = result
            
            # 根据复选框状态显示内容
            self.filter_diff_lines(self.only_diff_checkbox.isChecked())
            
            # 重新启用更新和滚动条
            self.left_text.setUpdatesEnabled(True)
            self.right_text.setUpdatesEnabled(True)
            self.left_text.verticalScrollBar().setEnabled(True)
            self.right_text.verticalScrollBar().setEnabled(True)
            self.left_text.horizontalScrollBar().setEnabled(True)
            self.right_text.horizontalScrollBar().setEnabled(True)
            
            # 确保水平滚动条可见
            self.left_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.right_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            
            # 重新启用同步滚动
            self.sync_scroll = True
            
            self.progress_dialog.setValue(100)
            
            # 更新对比状态
            diff_indexes = set(result['left_diff_types'].keys()) | set(result['right_diff_types'].keys())
            total_diff_lines = len(diff_indexes)
            if total_diff_lines == 0:
                self.compare_status_label.setStyleSheet("""
                    QLabel {
                        padding: 2px 5px;
                        border: 1px solid #4CAF50;
                        border-radius: 2px;
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        min-height: 16px;
                        max-height: 16px;
                        font-size: 12px;
                    }
                """)
                self.compare_status_label.setText("全部一致")
            else:
                self.compare_status_label.setStyleSheet("""
                    QLabel {
                        padding: 2px 5px;
                        border: 1px solid #f44336;
                        border-radius: 2px;
                        background-color: #FFEBEE;
                        color: #C62828;
                        min-height: 16px;
                        max-height: 16px;
                        font-size: 12px;
                    }
                """)
                self.compare_status_label.setText(f"发现 {total_diff_lines} 行不一致")
            
        except Exception as e:
            self.logger.error(f"显示结果出错: {str(e)}")
        finally:
            if self.progress_dialog:
                self.progress_dialog.close()
            
        self.logger.info("文件对比结果显示完成")
    
    def on_compare_error(self, error_message):
        """对比出错的处理"""
        self.logger.error(f"对比出错: {error_message}")
        if self.progress_dialog:
            self.progress_dialog.close()
        
        error_text = f"错误：{error_message}"
        self.left_text.setText(error_text)
        self.right_text.setText(error_text)
    
    def is_text_file(self, file_path):
        """判断文件是否为文本文件"""
        try:
            # 读取文件前8192个字节用于检测
            with open(file_path, 'rb') as f:
                content = f.read(8192)
                
            # 检查是否包含空字节，文本文件通常不包含空字节
            if b'\x00' in content:
                return False
                
            # 尝试将内容解码为文本
            try:
                content.decode('utf-8')
                return True
            except UnicodeDecodeError:
                try:
                    content.decode('gbk')
                    return True
                except UnicodeDecodeError:
                    try:
                        content.decode('latin-1')
                        return True
                    except:
                        return False
                        
        except Exception as e:
            self.logger.error(f"检查文件类型时出错: {str(e)}")
            return False
            
        return True

    def on_only_diff_changed(self, state):
        only_diff = self.only_diff_checkbox.isChecked()
        self.filter_diff_lines(only_diff)

    def filter_diff_lines(self, only_diff):
        """根据复选框状态过滤显示内容"""
        if not hasattr(self, "_compare_result") or not self._compare_result:
            return

        result = self._compare_result
        left_lines = result['left_lines']
        right_lines = result['right_lines']
        left_diff_types = result['left_diff_types']
        right_diff_types = result['right_diff_types']

        if only_diff:
            # 只显示有差异的行
            diff_indexes = set(left_diff_types.keys()) | set(right_diff_types.keys())
            diff_indexes = sorted(diff_indexes)
            left_display = [left_lines[i-1] for i in diff_indexes]
            right_display = [right_lines[i-1] for i in diff_indexes]
            # 重新设置高亮
            left_types = {idx: left_diff_types.get(idx, "") for idx in diff_indexes}
            right_types = {idx: right_diff_types.get(idx, "") for idx in diff_indexes}
        else:
            # 显示全部
            left_display = left_lines
            right_display = right_lines
            left_types = left_diff_types
            right_types = right_diff_types

        # 更新文本内容
        self.left_text.setPlainText(''.join(left_display))
        self.right_text.setPlainText(''.join(right_display))
        # 更新高亮
        self.left_highlighter.set_diff_types(left_types)
        self.right_highlighter.set_diff_types(right_types) 