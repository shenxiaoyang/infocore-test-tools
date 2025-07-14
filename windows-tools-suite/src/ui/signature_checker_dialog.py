from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QCheckBox, QMenu
)
import os
from src.utils.logger import get_logger
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
import subprocess
import shlex
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = get_logger(__name__)

class SignatureCheckerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("程序文件签名检查")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.init_ui()
        
    def closeEvent(self, event):
        """窗口关闭时停止扫描"""
        if self.is_scanning:
            logger.info("窗口关闭，停止扫描")
            self.stop_scan()
        event.accept()

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
        self.scan_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scan_btn.customContextMenuRequested.connect(self.show_directory_menu)

        self.start_btn = QPushButton()
        self.scan_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "scan.png")
        self.stop_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "stop.png")
        self.start_btn.setIcon(QIcon(self.scan_icon_path))
        self.start_btn.setToolTip("开始扫描")
        self.start_btn.setFixedSize(28, 28)
        self.start_btn.clicked.connect(self.on_start_scan)
        self.start_btn.setEnabled(False)
        self.is_scanning = False
        self.is_manually_stopped = False  # 添加手动停止标志

        top_layout.addWidget(dir_label)
        top_layout.addWidget(self.dir_edit, 1)
        top_layout.addWidget(self.scan_btn)
        top_layout.addWidget(self.start_btn)
        top_layout.setSpacing(8)
        top_layout.setContentsMargins(4, 8, 4, 8)
        layout.addLayout(top_layout)

        # 过滤复选框
        filter_layout = QHBoxLayout()
        self.exclude_ms_checkbox = QCheckBox("排除微软文件")
        self.exclude_ms_checkbox.setChecked(False)
        self.exclude_ms_checkbox.stateChanged.connect(self.on_filter_changed)
        
        self.only_unsigned_checkbox = QCheckBox("仅显示未签名")
        self.only_unsigned_checkbox.setChecked(False)
        self.only_unsigned_checkbox.stateChanged.connect(self.on_filter_changed)
        
        filter_layout.addWidget(self.exclude_ms_checkbox)
        filter_layout.addWidget(self.only_unsigned_checkbox)
        filter_layout.addStretch()  # 右侧添加弹性空间
        layout.addLayout(filter_layout)

        # 表格
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件名", "签名状态", "签名者姓名", "修改时间"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setStretchLastSection(True)  # 最后一列自动拉伸
        layout.addWidget(self.table)

        # 状态标签 - 放在表格下面，靠左
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(8, 4, 8, 8)  # 设置边距
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; padding: 4px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()  # 右侧添加弹性空间，让状态标签靠左
        layout.addLayout(status_layout)

        self.setLayout(layout)
        self.dir_edit.textChanged.connect(self.on_dir_edit_changed)
        default_dir = r"C:\Program Files\Enterprise Information Management\HostAgent"
        self.dir_edit.setText(default_dir)
        logger.info(f"设置默认目录: {default_dir}")
        logger.info(f"默认目录是否存在: {os.path.isdir(default_dir)}")
        # 存储所有结果
        self._all_rows = []

    def on_dir_edit_changed(self, text):
        is_valid = os.path.isdir(text.strip())
        logger.info(f"目录输入变化: '{text.strip()}' - 有效: {is_valid}")
        self.start_btn.setEnabled(is_valid)

    def show_directory_menu(self, position):
        menu = QMenu()
        
        # 常用目录选项
        common_dirs = [
            ("Program Files", r"C:\Program Files"),
            ("Program Files (x86)", r"C:\Program Files (x86)"),
            ("Windows System32", r"C:\Windows\System32"),
            ("Windows SysWOW64", r"C:\Windows\SysWOW64"),
            ("当前目录", os.getcwd()),
        ]
        
        for name, path in common_dirs:
            if os.path.exists(path):
                action = menu.addAction(name)
                action.triggered.connect(lambda checked, p=path: self.set_directory(p))
        
        if menu.actions():
            menu.addSeparator()
        
        # 添加自定义选择选项
        custom_action = menu.addAction("自定义选择...")
        custom_action.triggered.connect(self.choose_directory)
        
        menu.exec_(self.scan_btn.mapToGlobal(position))

    def set_directory(self, dir_path):
        self.dir_edit.setText(dir_path)
        self.table.setRowCount(0)
        self.status_label.setText("准备就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        logger.info(f"设置目录: {dir_path}")

    def adjust_table_size(self):
        """自适应表格大小"""
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        width = sum([self.table.columnWidth(i) for i in range(self.table.columnCount())]) + 60
        height = min(600, self.table.verticalHeader().length() + 120)
        self.resize(width, height)

    def on_filter_changed(self):
        """复选框状态变化时的处理"""
        self.apply_filter()
        # 每次过滤后都调整列宽
        self.adjust_table_size()

    def choose_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if dir_path:
            self.set_directory(dir_path)

    def on_start_scan(self):
        if not self.is_scanning:
            # 开始扫描
            logger.info("开始扫描按钮被点击")
            dir_path = self.dir_edit.text().strip()
            logger.info(f"扫描目录: {dir_path}")
            if not dir_path or not os.path.isdir(dir_path):
                logger.warning(f"无效目录: {dir_path}")
                QMessageBox.warning(self, "无效目录", "请输入或选择一个有效的扫描目录！")
                return
            logger.info("开始扫描和显示")
            self.status_label.setText("正在扫描...")
            self.status_label.setStyleSheet("color: #0078d4; font-size: 12px;")
            self.scan_and_display(dir_path)
        else:
            # 停止扫描
            logger.info("停止扫描按钮被点击")
            self.stop_scan()

    def scan_and_display(self, dir_path):
        logger.info("开始扫描和显示方法")
        self.table.setRowCount(0)
        self._all_rows = []
        self.is_scanning = True
        self.is_manually_stopped = False  # 重置手动停止标志
        self.start_btn.setIcon(QIcon(self.stop_icon_path))
        self.start_btn.setToolTip("停止扫描")
        self.scan_btn.setEnabled(False)
        logger.info("创建扫描工作线程")
        self.worker = SignatureScanWorker(dir_path)
        self.worker.result_signal.connect(self.add_signature_row)
        self.worker.finished_signal.connect(self.on_scan_finished)
        logger.info("启动扫描工作线程")
        self.worker.start()

    def stop_scan(self):
        logger.info("停止扫描")
        self.is_scanning = False
        self.is_manually_stopped = True  # 设置手动停止标志
        
        # 计算已扫描的文件数量
        scanned_count = len(self._all_rows)
        if scanned_count > 0:
            self.status_label.setText(f"已手动停止，已扫描 {scanned_count} 个文件")
        else:
            self.status_label.setText("已手动停止")
        self.status_label.setStyleSheet("color: #d83b01; font-size: 12px;")
        
        # 立即恢复按钮状态，提供即时反馈
        self.start_btn.setIcon(QIcon(self.scan_icon_path))
        self.start_btn.setToolTip("开始扫描")
        self.scan_btn.setEnabled(True)
        
        # 停止工作线程
        if hasattr(self, 'worker') and self.worker:
            logger.info("发送停止信号给工作线程")
            self.worker.stop()
        
        # 扫描停止后调整列宽
        self.adjust_table_size()
        
        logger.info("停止扫描完成")

    def add_signature_row(self, file_path, status, signer, modify_time):
        # 检查是否是空信号（表示没有找到文件）
        if not file_path and not status and not signer and not modify_time:
            logger.info("收到空信号，表示没有找到可执行文件")
            return
            
        logger.info(f"添加签名行: {file_path} - {status} - {signer} - {modify_time}")
        self._all_rows.append((file_path, status, signer, modify_time))
        self.apply_filter()

    def apply_filter(self):
        # 重新填充表格，按过滤条件
        self.table.setSortingEnabled(False)  # 临时禁用排序，避免在填充时触发排序
        self.table.setRowCount(0)
        exclude_ms = self.exclude_ms_checkbox.isChecked()
        only_unsigned = self.only_unsigned_checkbox.isChecked()
        
        filtered_count = 0
        for file_path, status, signer, modify_time in self._all_rows:
            # 排除微软文件
            if exclude_ms and ("Microsoft Corporation" in signer.strip() or "Microsoft Windows" in signer.strip()):
                continue
            # 仅显示未签名
            if only_unsigned and status != "未签名":
                continue
            filtered_count += 1
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(file_path))
            self.table.setItem(row, 1, QTableWidgetItem(status))
            self.table.setItem(row, 2, QTableWidgetItem(signer))
            self.table.setItem(row, 3, QTableWidgetItem(modify_time))
            if status == "未签名":
                for col in range(4):
                    self.table.item(row, col).setBackground(QColor(255, 220, 220))
        
        self.table.setSortingEnabled(True)  # 重新启用排序
        
        # 只有在扫描完成或停止时才调整列宽
        if not self.is_scanning:
            self.adjust_table_size()
        
        # 更新状态标签显示过滤结果
        if not self.is_scanning and len(self._all_rows) > 0:
            total_count = len(self._all_rows)
            if self.is_manually_stopped:
                # 手动停止的情况
                if filtered_count == total_count:
                    self.status_label.setText(f"已手动停止，已扫描 {total_count} 个文件")
                else:
                    self.status_label.setText(f"已手动停止，已扫描 {total_count} 个文件，过滤后显示 {filtered_count} 个")
            else:
                # 正常完成的情况
                if filtered_count == total_count:
                    self.status_label.setText(f"扫描完成，找到 {total_count} 个文件")
                else:
                    self.status_label.setText(f"扫描完成，找到 {total_count} 个文件，过滤后显示 {filtered_count} 个")

    def on_scan_finished(self):
        logger.info("扫描完成")
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        
        # 恢复按钮状态
        self.start_btn.setIcon(QIcon(self.scan_icon_path))
        self.start_btn.setToolTip("开始扫描")
        
        # 更新状态标签
        if self.is_manually_stopped:
            # 手动停止的情况
            scanned_count = len(self._all_rows)
            if scanned_count > 0:
                self.status_label.setText(f"已手动停止，已扫描 {scanned_count} 个文件")
            else:
                self.status_label.setText("已手动停止")
            self.status_label.setStyleSheet("color: #d83b01; font-size: 12px;")
        else:
            # 正常完成的情况
            if len(self._all_rows) == 0:
                self.status_label.setText("未找到可执行文件 (.exe, .dll)")
                self.status_label.setStyleSheet("color: #d83b01; font-size: 12px;")
            else:
                self.status_label.setText(f"扫描完成，找到 {len(self._all_rows)} 个文件")
                self.status_label.setStyleSheet("color: #107c10; font-size: 12px;")
        
        # 扫描完成后调整列宽
        self.adjust_table_size()

class SignatureScanWorker(QThread):
    result_signal = pyqtSignal(str, str, str, str)  # file_path, status, signer, modify_time
    finished_signal = pyqtSignal()
    def __init__(self, dir_path, max_workers=6):
        super().__init__()
        self.dir_path = dir_path
        self.max_workers = max_workers
        self._is_running = True
        logger.info(f"SignatureScanWorker初始化: 目录={dir_path}, 最大工作线程={max_workers}")
    
    def stop_flag(self):
        """返回停止标志，类似FileGenerator的设计"""
        return not self._is_running
    
    def run(self):
        logger.info("SignatureScanWorker开始运行")
        start_time = datetime.now()
        file_list = []
        try:
            # 收集文件列表
            for root, _, files in os.walk(self.dir_path):
                for f in files:
                    if f.lower().endswith((".exe", ".dll")):
                        file_path = os.path.join(root, f)
                        file_list.append(file_path)
            logger.info(f"找到 {len(file_list)} 个可执行文件")
            
            if not file_list:
                logger.warning("没有找到任何可执行文件")
                # 发送一个特殊信号表示没有找到文件
                self.result_signal.emit("", "", "", "")
                self.finished_signal.emit()
                return
                
            # 逐个处理文件，类似FileGenerator的方式
            processed_count = 0
            success_count = 0
            error_count = 0
            
            for file_path in file_list:
                if not self._is_running:
                    logger.info("扫描被中断，停止处理剩余文件")
                    break
                
                try:
                    # 检查是否被停止
                    if self.stop_flag():
                        logger.info("扫描被中断，停止处理剩余文件")
                        break
                    
                    status, signer, modify_time = self.get_signature_info(file_path)
                    if status != "无法解析":
                        success_count += 1
                        logger.info(f"处理文件成功: {file_path} - {status}")
                    else:
                        error_count += 1
                        logger.warning(f"处理文件失败: {file_path} - {status}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理文件异常: {file_path} - 错误: {e}")
                    status, signer, modify_time = "无法解析", "-", "-"
                
                self.result_signal.emit(file_path, status, signer, modify_time)
                processed_count += 1
                if processed_count % 10 == 0:
                    logger.info(f"已处理 {processed_count}/{len(file_list)} 个文件 (成功: {success_count}, 失败: {error_count})")
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            logger.info(f"扫描完成统计: 总耗时 {total_duration:.2f}秒, 成功 {success_count} 个, 失败 {error_count} 个, 总计 {processed_count} 个文件")
                
        except Exception as e:
            logger.error(f"SignatureScanWorker运行异常: {e}")
        finally:
            logger.info("SignatureScanWorker完成")
            self.finished_signal.emit()
    
    def stop(self):
        logger.info("停止SignatureScanWorker")
        self._is_running = False 

    def get_signature_info(self, file_path, max_retries=3):
        start_time = datetime.now()
        logger.info(f"开始计算签名: {file_path}")
        try:
            stat = os.stat(file_path)
            modify_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            modify_time = "-"
        ps_cmd = (
            f"$sig=Get-AuthenticodeSignature -FilePath {shlex.quote(file_path)};"
            "if ($sig.SignerCertificate -ne $null) { "
            "($sig.SignerCertificate.Subject -split ',')[0] -replace 'CN=', '' "
            "} else { '' }"
        )
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
        for attempt in range(max_retries):
            if self.stop_flag():
                logger.info(f"签名计算被中断: {file_path}")
                return "无法解析", "-", modify_time
            try:
                logger.info(f"尝试第 {attempt + 1} 次计算签名: {file_path}")
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True, text=True, timeout=10, encoding="gbk", errors="replace",
                    creationflags=creationflags
                )
                logger.info(f"Powershell签名解析结果: {result.stdout}")
                signer = result.stdout.strip()
                status = "已签名" if signer else "未签名"
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"签名计算完成: {file_path} - 耗时: {duration:.2f}秒 - 状态: {status} - 尝试次数: {attempt + 1}")
                return status, signer if signer else "-", modify_time
            except subprocess.TimeoutExpired as e:
                logger.warning(f"签名计算超时 (第 {attempt + 1} 次): {file_path} - 错误: {e}")
                if attempt == max_retries - 1:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    logger.error(f"签名计算最终失败 (超时): {file_path} - 总耗时: {duration:.2f}秒 - 尝试次数: {max_retries}")
                    return "无法解析", "-", modify_time
                else:
                    logger.info(f"准备重试签名计算: {file_path}")
            except Exception as e:
                logger.warning(f"签名计算异常 (第 {attempt + 1} 次): {file_path} - 错误: {e}")
                if attempt == max_retries - 1:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    logger.error(f"签名计算最终失败: {file_path} - 总耗时: {duration:.2f}秒 - 尝试次数: {max_retries} - 错误: {e}")
                    return "无法解析", "-", modify_time
                else:
                    logger.info(f"准备重试签名计算: {file_path}")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.error(f"签名计算完全失败: {file_path} - 总耗时: {duration:.2f}秒 - 尝试次数: {max_retries}")
        return "无法解析", "-", modify_time 