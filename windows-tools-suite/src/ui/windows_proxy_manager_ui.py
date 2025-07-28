from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QPushButton, 
                             QHBoxLayout, QMessageBox, QLabel, QFileDialog, QInputDialog)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import winreg
import subprocess
import os
import platform
from smb.SMBConnection import SMBConnection
from src.utils.logger import get_logger
from src.ui.signature_checker_dialog import SignatureCheckerDialog

logger = get_logger(__name__)

class ProxyDownloadThread(QThread):
    """代理下载线程"""
    progress_signal = pyqtSignal(str)  # 进度信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号，参数：是否成功，消息
    
    def __init__(self, custom_path=None):
        super().__init__()
        self.smb_server = "192.168.1.20"
        self.smb_share = "ALLPackages"
        self.smb_path = "hostagent/x86_64/Windows/6.2"
        self.username = "xiaoyang.shen"
        self.password = "infocores"
        
        # 如果提供了自定义路径，则解析并更新
        if custom_path:
            self.update_path_from_custom(custom_path)
    
    def update_path_from_custom(self, custom_path):
        """从自定义路径更新SMB连接参数"""
        try:
            # 解析路径格式：\\server\share\path
            if custom_path.startswith('\\\\'):
                path_parts = custom_path[2:].split('\\')
                if len(path_parts) >= 2:
                    self.smb_server = path_parts[0]
                    self.smb_share = path_parts[1]
                    self.smb_path = '\\'.join(path_parts[2:]) if len(path_parts) > 2 else ""
        except Exception as e:
            logger.error(f"解析自定义路径失败: {str(e)}")
        
    def run(self):
        try:
            self.progress_signal.emit("正在连接SMB服务器...")
            
            # 尝试不同的认证方式
            auth_methods = [
                {'use_ntlm_v2': True, 'is_direct_tcp': True, 'name': 'Direct TCP'},
                {'use_ntlm_v2': True, 'name': 'NTLMv2'},
                {'use_ntlm_v2': False, 'name': 'NTLMv1'}
            ]
            
            conn = None
            for auth_method in auth_methods:
                try:
                    self.progress_signal.emit(f"尝试使用{auth_method['name']}认证...")
                    
                    conn = SMBConnection(self.username, self.password, 
                                       "client", self.smb_server, 
                                       use_ntlm_v2=auth_method.get('use_ntlm_v2', True),
                                       is_direct_tcp=auth_method.get('is_direct_tcp', False))
                    
                    if conn.connect(self.smb_server, 445, timeout=10):
                        self.progress_signal.emit(f"使用{auth_method['name']}认证成功")
                        break
                    else:
                        conn.close()
                        conn = None
                        
                except Exception as auth_e:
                    logger.warning(f"使用{auth_method['name']}认证失败: {str(auth_e)}")
                    if conn:
                        conn.close()
                        conn = None
                    continue
            
            if not conn:
                self.finished_signal.emit(False, "所有认证方式都失败，请检查用户名密码和网络连接")
                return
                
            self.progress_signal.emit("正在获取文件列表...")
            
            try:
                # 获取目录列表
                files = conn.listPath(self.smb_share, self.smb_path)
            except Exception as list_e:
                logger.error(f"获取目录列表失败: {str(list_e)}")
                self.finished_signal.emit(False, f"无法访问共享目录，请检查权限: {str(list_e)}")
                conn.close()
                return
            
            # 过滤exe文件
            exe_files = [f for f in files if f.filename.endswith('.exe')]
            
            if not exe_files:
                self.finished_signal.emit(False, "未找到exe文件")
                conn.close()
                return
                
            # 根据系统架构选择文件
            system_arch = platform.architecture()[0]
            if system_arch == '32bit':
                target_files = [f for f in exe_files if 'x86' in f.filename.lower()]
            else:
                target_files = [f for f in exe_files if 'x64' in f.filename.lower()]
                
            if not target_files:
                self.finished_signal.emit(False, f"未找到适合{system_arch}架构的文件")
                conn.close()
                return
                
            # 按修改时间排序，获取最新文件
            target_files.sort(key=lambda x: x.last_write_time, reverse=True)
            latest_file = target_files[0]
            
            self.progress_signal.emit(f"找到最新文件: {latest_file.filename}")
            
            # 设置下载目录为桌面
            download_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
            local_path = os.path.join(download_dir, latest_file.filename)
            
            self.progress_signal.emit("正在下载文件...")
            
            try:
                # 下载文件
                with open(local_path, 'wb') as local_file:
                    conn.retrieveFile(self.smb_share, 
                                    os.path.join(self.smb_path, latest_file.filename), 
                                    local_file)
                
                conn.close()
                self.finished_signal.emit(True, f"下载完成！文件保存在: {local_path}")
                
            except Exception as download_e:
                logger.error(f"下载文件失败: {str(download_e)}")
                conn.close()
                self.finished_signal.emit(False, f"下载文件失败: {str(download_e)}")
            
        except Exception as e:
            logger.error(f"下载过程中出错: {str(e)}")
            error_msg = str(e)
            
            # 根据错误类型提供更具体的提示
            if "10054" in error_msg:
                error_msg = "连接被远程主机强制关闭，可能原因：\n1. 用户名密码错误\n2. 权限不足\n3. 服务器限制连接数\n4. 防火墙阻止"
            elif "10060" in error_msg:
                error_msg = "连接超时，请检查网络连接和服务器地址"
            elif "10061" in error_msg:
                error_msg = "无法连接到服务器，请检查服务器是否运行和端口是否开放"
            
            self.finished_signal.emit(False, f"下载失败: {error_msg}")

class WindowsProxyConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Windows代理配置")
        self.setMinimumWidth(400)
        self.download_thread = None
        self.current_smb_path = "\\\\192.168.1.20\\ALLPackages\\hostagent\\x86_64\\Windows\\6.2"
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

        # 新增：程序文件签名检查QGroupBox
        sig_group = QGroupBox("程序文件签名检查")
        sig_layout = QHBoxLayout()
        self.signature_btn = QPushButton("打开签名检查")
        self.signature_btn.clicked.connect(self.open_signature_checker)
        sig_layout.addWidget(self.signature_btn)
        sig_group.setLayout(sig_layout)
        layout.addWidget(sig_group)
        
        # 新增：代理下载安装QGroupBox
        windows_proxy_group = QGroupBox("Windows代理下载")
        windows_proxy_layout = QVBoxLayout()
        
        # 添加说明文字
        self.path_info_label = QLabel("默认获取新包路径\n\\\\192.168.1.20\\ALLPackages\\hostagent\\x86_64\\Windows\\6.2")
        self.path_info_label.setWordWrap(True)
        self.path_info_label.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 5px;")
        windows_proxy_layout.addWidget(self.path_info_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 路径配置按钮
        path_btn = QPushButton()
        path_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons', 'open_dirs.png')))
        path_btn.setToolTip("更改默认下载路径")
        path_btn.setFixedSize(40, 40)
        path_btn.clicked.connect(self.change_download_path)
        button_layout.addWidget(path_btn)
        
        # 下载按钮
        self.windows_proxy_download_btn = QPushButton("最新代理下载")
        self.windows_proxy_download_btn.clicked.connect(self.download_latest_windows_proxy)
        button_layout.addWidget(self.windows_proxy_download_btn)
        
        windows_proxy_layout.addLayout(button_layout)
        windows_proxy_group.setLayout(windows_proxy_layout)
        layout.addWidget(windows_proxy_group)
        
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

    def open_signature_checker(self):
        logger = get_logger(__name__)
        try:
            logger.info("尝试打开SignatureCheckerDialog")
            dlg = SignatureCheckerDialog(self)
            dlg.exec_()
            logger.info("SignatureCheckerDialog已关闭")
        except Exception as e:
            logger.error(f"打开SignatureCheckerDialog异常: {e}", exc_info=True)

    def change_download_path(self):
        """更改下载路径"""
        # 创建自定义对话框以获得更好的控制
        dialog = QInputDialog(self)
        dialog.setWindowTitle("更改下载路径")
        dialog.setLabelText("请输入SMB路径 (格式: \\\\server\\share\\path):")
        dialog.setTextValue(self.current_smb_path)
        dialog.resize(500, 150)  # 设置对话框宽度为500像素，高度为150像素
        
        ok = dialog.exec_()
        new_path = dialog.textValue()
        
        if ok and new_path.strip():
            # 验证路径格式
            if new_path.startswith('\\\\'):
                self.current_smb_path = new_path.strip()
                # 更新显示
                self.path_info_label.setText(f"默认获取新包路径\n{self.current_smb_path}")
                logger.info(f"下载路径已更改为: {self.current_smb_path}")
                QMessageBox.information(self, "成功", "下载路径已更新")
            else:
                QMessageBox.warning(self, "格式错误", "路径格式应为: \\\\server\\share\\path")
    
    def download_latest_windows_proxy(self):
        """最新代理下载功能"""
        logger.info("开始下载最新Windows代理")
        
        # 禁用按钮并显示下载中状态
        self.windows_proxy_download_btn.setEnabled(False)
        self.windows_proxy_download_btn.setText("下载中...")
        
        # 创建并启动下载线程，传入自定义路径
        self.download_thread = ProxyDownloadThread(self.current_smb_path)
        self.download_thread.progress_signal.connect(self.on_download_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_progress(self, message):
        """下载进度回调"""
        logger.info(f"下载进度: {message}")
        # 可以在这里添加进度显示，比如更新按钮文本或显示进度条
    
    def on_download_finished(self, success, message):
        """下载完成回调"""
        # 恢复按钮状态
        self.windows_proxy_download_btn.setEnabled(True)
        self.windows_proxy_download_btn.setText("最新代理下载")
        
        if success:
            QMessageBox.information(self, "下载成功", message)
        else:
            QMessageBox.warning(self, "下载失败", message)
        
        logger.info(f"下载完成: {message}")
