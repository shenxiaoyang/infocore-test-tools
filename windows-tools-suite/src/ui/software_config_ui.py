import sys
import os
import winreg
import yaml
import platform
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QPushButton, QMessageBox, QCheckBox, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from smb.SMBConnection import SMBConnection
from src.utils.logger import get_logger

logger = get_logger(__name__)

def extract_version_from_filename(filename):
    """从文件名中提取版本号"""
    try:
        if '-v' in filename:
            version_part = filename.split('-v')[1]
            if '-' in version_part:
                return version_part.split('-')[0]
            else:
                return version_part.split('.exe')[0]
        return None
    except Exception:
        return None

def compare_versions(version1, version2):
    """比较两个版本号，返回True如果version1 >= version2"""
    if not version1 or not version2:
        return False
    
    try:
        # 将版本号分割成数字列表进行比较
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # 补齐长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        # 比较每个部分
        for i in range(max_len):
            if v1_parts[i] > v2_parts[i]:
                return True
            elif v1_parts[i] < v2_parts[i]:
                return False
        
        return True  # 相等
    except Exception:
        return False

class SoftwareUpdateThread(QThread):
    """软件更新下载线程"""
    progress_signal = pyqtSignal(str)  # 进度信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号，参数：是否成功，消息
    
    def __init__(self, current_version=None):
        super().__init__()
        self.current_version = current_version
        self.smb_server = "192.168.1.20"
        self.smb_share = "测试部（日志和iso）"
        self.smb_path = "软件类/自研/Windows工具集"
        self.username = "xiaoyang.shen"
        self.password = "infocores"
        
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
                # 根据系统架构选择目录
                system_arch = platform.architecture()[0]
                if system_arch == '32bit':
                    arch_dir = "x86"
                else:
                    arch_dir = "x64"
                
                # 获取对应架构目录下的文件列表
                arch_path = f"{self.smb_path}/{arch_dir}"
                files = conn.listPath(self.smb_share, arch_path)
            except Exception as list_e:
                logger.error(f"获取目录列表失败: {str(list_e)}")
                self.finished_signal.emit(False, f"无法访问共享目录，请检查权限: {str(list_e)}")
                conn.close()
                return
            
            # 过滤exe文件
            exe_files = [f for f in files if f.filename.endswith('.exe')]
            
            if not exe_files:
                self.finished_signal.emit(False, f"在{arch_dir}目录下未找到exe文件")
                conn.close()
                return
                
            # 按修改时间排序，获取最新文件
            exe_files.sort(key=lambda x: x.last_write_time, reverse=True)
            latest_file = exe_files[0]
            
            self.progress_signal.emit(f"找到最新文件: {latest_file.filename}")
            
            # 版本对比逻辑
            if self.current_version and self.current_version != "unknown":
                try:
                    # 从文件名中提取版本号
                    latest_version = extract_version_from_filename(latest_file.filename)
                    
                    if latest_version:
                        self.progress_signal.emit(f"当前版本: {self.current_version}, 最新版本: {latest_version}")
                        
                        # 版本对比 - 如果当前版本 >= 最新版本，则无需更新
                        if compare_versions(self.current_version, latest_version):
                            conn.close()
                            if self.current_version == latest_version:
                                self.finished_signal.emit(True, f"当前版本 {self.current_version} 已是最新版本，无需更新！")
                            else:
                                self.finished_signal.emit(True, f"当前版本 {self.current_version} 比服务器版本 {latest_version} 更新，无需更新！")
                            return
                        
                        self.progress_signal.emit(f"发现新版本 {latest_version}，准备下载...")
                    else:
                        self.progress_signal.emit("无法解析服务器版本号，继续下载...")
                        
                except Exception as version_e:
                    logger.warning(f"版本对比失败: {str(version_e)}")
                    self.progress_signal.emit("版本对比失败，继续下载...")
            
            # 设置下载目录为桌面
            download_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
            local_path = os.path.join(download_dir, latest_file.filename)
            
            self.progress_signal.emit("正在下载文件...")
            
            try:
                # 下载文件
                with open(local_path, 'wb') as local_file:
                    conn.retrieveFile(self.smb_share, 
                                    f"{arch_path}/{latest_file.filename}", 
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

class SoftwareConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # 保存主窗口引用
        self.setWindowTitle("工具集配置")
        self.setMinimumWidth(400)
        self.update_thread = None
        self.init_ui()
        self.check_startup_status()
        self.check_auto_exec_status()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 软件自启注册分组
        startup_group = QGroupBox("本软件开机自启注册")
        startup_layout = QVBoxLayout()
        
        # 添加说明文案
        startup_note = QLabel("注意：因为Windows限制，即使注册自启后，也需要界面登录才能自动打开软件。建议打开Windows自动登录功能，这样就可实现开机后自动打开软件。Windows自动登录功能请往 [Windows系统配置] -> [Windows系统自动登录]中配置。")
        startup_note.setWordWrap(True)
        startup_layout.addWidget(startup_note)
        
        self.register_startup_btn = QPushButton()
        self.register_startup_btn.clicked.connect(self.register_startup)
        startup_layout.addWidget(self.register_startup_btn)
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        # 自动执行模块分组
        auto_exec_group = QGroupBox("打开软件时自动执行模块注册")
        auto_exec_layout = QVBoxLayout()
        
        # 自动执行快速计算系统盘
        self.auto_system_disk_cb = QCheckBox("自动执行快速计算系统盘")
        auto_exec_layout.addWidget(self.auto_system_disk_cb)
        
        # 自动执行本地文件产生器
        self.auto_filegen_cb = QCheckBox("自动执行本地文件产生器")
        auto_exec_layout.addWidget(self.auto_filegen_cb)
        
        # 自动执行文件校验
        self.auto_fileverify_cb = QCheckBox("自动执行文件校验")
        auto_exec_layout.addWidget(self.auto_fileverify_cb)
        
        # 仅在本地应急时自动执行
        self.emergency_only_cb = QCheckBox("仅在本地应急时自动执行")
        auto_exec_layout.addWidget(self.emergency_only_cb)
        
        # 保存配置按钮
        save_auto_config_btn = QPushButton("保存自动执行配置")
        save_auto_config_btn.clicked.connect(self.save_auto_exec_config)
        auto_exec_layout.addWidget(save_auto_config_btn)
        
        auto_exec_group.setLayout(auto_exec_layout)
        layout.addWidget(auto_exec_group)
        
        # 软件更新分组
        update_group = QGroupBox("本软件更新")
        update_layout = QVBoxLayout()
        
        # 添加说明文案
        update_note = QLabel("从服务器下载最新版本的Windows工具集软件包。")
        update_note.setWordWrap(True)
        update_layout.addWidget(update_note)
        
        self.update_btn = QPushButton("下载最新版")
        self.update_btn.clicked.connect(self.download_latest_version)
        update_layout.addWidget(self.update_btn)
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        layout.addStretch()
        self.setLayout(layout)

    def check_startup_status(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            )
            value, _ = winreg.QueryValueEx(key, "EIMFilegen")
            winreg.CloseKey(key)
            if "autorun" in value:
                self.register_startup_btn.setText("取消开机自启")
                try:
                    self.register_startup_btn.clicked.disconnect()
                except Exception:
                    pass
                self.register_startup_btn.clicked.connect(self.unregister_startup)
            else:
                self.register_startup_btn.setText("注册自启")
                try:
                    self.register_startup_btn.clicked.disconnect()
                except Exception:
                    pass
                self.register_startup_btn.clicked.connect(self.register_startup)
        except FileNotFoundError:
            self.register_startup_btn.setText("注册自启")
            try:
                self.register_startup_btn.clicked.disconnect()
            except Exception:
                pass
            self.register_startup_btn.clicked.connect(self.register_startup)
        except Exception:
            self.register_startup_btn.setText("注册自启")
            try:
                self.register_startup_btn.clicked.disconnect()
            except Exception:
                pass
            self.register_startup_btn.clicked.connect(self.register_startup)

    def check_auto_exec_status(self):
        """检查自动执行配置状态"""
        program_data = os.environ.get('ProgramData', r'C:\ProgramData')
        config_dir = os.path.join(program_data, "InfoCoreTestTools")
        config_file = os.path.join(config_dir, "auto_exec_config.yaml")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        self.auto_system_disk_cb.setChecked(config.get('auto_system_disk', False))
                        self.auto_filegen_cb.setChecked(config.get('auto_filegen', False))
                        self.auto_fileverify_cb.setChecked(config.get('auto_fileverify', False))
                        self.emergency_only_cb.setChecked(config.get('emergency_only', False))
            except Exception as e:
                print(f"加载自动执行配置失败: {str(e)}")

    def save_auto_exec_config(self):
        """保存自动执行配置"""
        # 检查文件产生器和文件校验的配置文件是否存在
        program_data = os.environ.get('ProgramData', r'C:\ProgramData')
        config_dir = os.path.join(program_data, "InfoCoreTestTools")
        
        # 检查文件产生器配置
        filegen_config = os.path.join(config_dir, "filegen_config.yaml")
        if self.auto_filegen_cb.isChecked() and not os.path.exists(filegen_config):
            QMessageBox.warning(self, "警告", "本地文件产生器没有保存的配置文件，无法设置自动执行！")
            self.auto_filegen_cb.setChecked(False)
            return
        
        # 检查文件校验配置
        fileverify_config = os.path.join(config_dir, "fileverify_config.yaml")
        if self.auto_fileverify_cb.isChecked() and not os.path.exists(fileverify_config):
            QMessageBox.warning(self, "警告", "文件校验没有保存的配置文件，无法设置自动执行！")
            self.auto_fileverify_cb.setChecked(False)
            return
        
        # 保存配置
        config = {
            'auto_system_disk': self.auto_system_disk_cb.isChecked(),
            'auto_filegen': self.auto_filegen_cb.isChecked(),
            'auto_fileverify': self.auto_fileverify_cb.isChecked(),
            'emergency_only': self.emergency_only_cb.isChecked(),
        }
        
        try:
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "auto_exec_config.yaml")
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, allow_unicode=True)
            QMessageBox.information(self, "保存成功", "自动执行配置已保存成功！")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存自动执行配置失败：{str(e)}")

    def register_startup(self):
        exe_path = os.path.abspath(sys.argv[0])
        autorun_cmd = f'"{exe_path}" autorun'
        try:
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            )
            winreg.SetValueEx(key, "EIMFilegen", 0, winreg.REG_SZ, autorun_cmd)
            winreg.CloseKey(key)
            QMessageBox.information(self, "注册成功", f"已注册开机自启：{autorun_cmd}")
        except Exception as e:
            QMessageBox.critical(self, "注册失败", f"注册开机自启失败：{str(e)}")
        self.check_startup_status()

    def unregister_startup(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "EIMFilegen")
            winreg.CloseKey(key)
            QMessageBox.information(self, "取消成功", "已取消开机自启。")
        except FileNotFoundError:
            QMessageBox.information(self, "无需操作", "未设置开机自启。")
        except Exception as e:
            QMessageBox.critical(self, "取消失败", f"取消开机自启失败：{str(e)}")
        self.check_startup_status()

    def download_latest_version(self):
        """下载最新版本功能"""
        logger.info("开始下载最新版本")
        
        # 获取当前版本信息
        current_version = None
        if self.parent_window and hasattr(self.parent_window, 'version'):
            current_version = self.parent_window.version
        
        # 禁用按钮并显示下载中状态
        self.update_btn.setEnabled(False)
        self.update_btn.setText("检查更新中...")
        
        # 创建并启动下载线程
        self.update_thread = SoftwareUpdateThread(current_version)
        self.update_thread.progress_signal.connect(self.on_update_progress)
        self.update_thread.finished_signal.connect(self.on_update_finished)
        self.update_thread.start()
    
    def on_update_progress(self, message):
        """更新进度回调"""
        logger.info(f"更新进度: {message}")
        
        # 当开始下载时更新按钮文本
        if "正在下载文件" in message:
            self.update_btn.setText("下载中...")
        elif "发现新版本" in message:
            self.update_btn.setText("下载中...")
        # 可以在这里添加进度显示，比如更新按钮文本或显示进度条
    
    def on_update_finished(self, success, message):
        """更新完成回调"""
        # 恢复按钮状态
        self.update_btn.setEnabled(True)
        self.update_btn.setText("下载最新版")
        
        if success:
            QMessageBox.information(self, "下载成功", message)
        else:
            QMessageBox.warning(self, "下载失败", message)
        
        logger.info(f"更新完成: {message}")
