import sys
import os
import json
import time
import socket
import paramiko
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QPushButton, QLineEdit, QMessageBox, QSizePolicy, QWidget, QSpacerItem, QStatusBar
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent
import re
import tempfile
from smb.SMBConnection import SMBConnection
from src.utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".linux_proxy_config.json")

def execute_ssh_command(ssh, command, timeout=30, interactive_input=None):
    """
    执行SSH命令并检查结果
    
    Args:
        ssh: paramiko.SSHClient实例
        command: 要执行的命令
        timeout: 超时时间（秒）
        interactive_input: 交互式输入（如需要输入'y'）
    
    Returns:
        tuple: (success, stdout, stderr, exit_code)
    """
    try:
        logger.info(f"执行SSH命令: {command}")
        
        if interactive_input:
            # 对于需要交互式输入的命令，使用get_pty=True
            stdin, stdout, stderr = ssh.exec_command(command, get_pty=True, timeout=timeout)
            
            # 等待输出并发送交互式输入
            import time
            time.sleep(1)  # 等待命令开始执行
            
            # 发送交互式输入
            if stdin:
                stdin.write(interactive_input + '\n')
                stdin.flush()
                logger.info(f"发送交互式输入: {interactive_input}")
            
            # 等待命令完成
            exit_code = stdout.channel.recv_exit_status()
        else:
            # 普通命令执行
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
        
        stdout_content = stdout.read().decode(errors='ignore')
        stderr_content = stderr.read().decode(errors='ignore')
        
        success = exit_code == 0
        
        logger.info(f"命令执行完成: 退出码={exit_code}, 成功={success}")
        if stdout_content:
            logger.debug(f"标准输出: {stdout_content}")
        if stderr_content:
            logger.debug(f"错误输出: {stderr_content}")
        
        return success, stdout_content, stderr_content, exit_code
        
    except Exception as e:
        logger.error(f"执行SSH命令失败: {command}, 错误: {e}")
        return False, "", str(e), -1

APPLE_BTN_STYLE = """
QPushButton {
    font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', 'Helvetica', 'PingFang SC', 'Hiragino Sans GB', 'sans-serif';
    background-color: #f0f0f0;
    color: #222;
    border-radius: 6px;
    font-size: 12px;
    padding: 2px 10px;
    min-height: 22px;
    min-width: 40px;
    max-height: 26px;
    max-width: 70px;
    border: 1px solid #e0e0e0;
}
QPushButton:hover {
    background-color: #e5e5ea;
}
QPushButton:pressed {
    background-color: #cccccc;
}
QPushButton:disabled {
    background-color: #f5f5f5;
    color: #bfbfbf;
}
"""
APPLE_BTN_STYLE_BLUE = """
QPushButton {
    font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', 'Helvetica', 'PingFang SC', 'Hiragino Sans GB', 'sans-serif';
    background-color: #007AFF;
    color: #fff;
    border-radius: 6px;
    font-size: 12px;
    padding: 2px 10px;
    min-height: 22px;
    min-width: 40px;
    max-height: 26px;
    max-width: 70px;
    border: none;
}
QPushButton:hover {
    background-color: #0051a8;
}
QPushButton:pressed {
    background-color: #003e7e;
}
QPushButton:disabled {
    background-color: #b0cfff;
    color: #f5f5f5;
}
"""

class SSHConnectThread(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, ip, user, pwd):
        super().__init__()
        self.ip = ip
        self.user = user
        self.pwd = pwd
        logger.info(f"SSHConnectThread初始化: IP={ip}, User={user}")
    def run(self):
        try:
            logger.info(f"开始SSH连接: {self.ip}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user, password=self.pwd, timeout=5)
            ssh.close()
            logger.info(f"SSH连接成功: {self.ip}")
            self.result_signal.emit(True, "连接成功")
        except Exception as e:
            logger.error(f"SSH连接失败: {self.ip}, 错误: {e}")
            self.result_signal.emit(False, str(e))

class AddLinuxProxyDialog(QDialog):
    def __init__(self, parent=None, existing_ips=None):
        super().__init__(parent)
        self.setWindowTitle("添加Linux代理")
        self.setFixedSize(320, 220)
        self.existing_ips = set(existing_ips) if existing_ips else set()
        layout = QVBoxLayout()
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP地址")
        self.user_edit = QLineEdit("root")
        self.user_edit.setReadOnly(True)
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setPlaceholderText("密码")
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("IP地址："))
        layout.addWidget(self.ip_edit)
        layout.addWidget(QLabel("用户名："))
        layout.addWidget(self.user_edit)
        layout.addWidget(QLabel("密码："))
        layout.addWidget(self.pwd_edit)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.add_btn = QPushButton("添加")
        self.add_btn.setStyleSheet(APPLE_BTN_STYLE_BLUE)
        self.add_btn.setFixedWidth(60)
        self.add_btn.setFixedHeight(24)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(APPLE_BTN_STYLE)
        self.cancel_btn.setFixedWidth(60)
        self.cancel_btn.setFixedHeight(24)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.add_btn.clicked.connect(self.try_add)
        self.cancel_btn.clicked.connect(self.reject)
        self.ssh_thread = None
    def get_data(self):
        return self.ip_edit.text().strip(), self.user_edit.text().strip(), self.pwd_edit.text().strip()
    def try_add(self):
        ip, user, pwd = self.get_data()
        logger.info(f"尝试添加代理: IP={ip}, User={user}")
        if not ip or not pwd:
            logger.warning("IP地址或密码为空")
            QMessageBox.warning(self, "输入错误", "IP地址和密码不能为空！")
            return
        if ip in self.existing_ips:
            logger.warning(f"IP地址已存在: {ip}")
            QMessageBox.warning(self, "重复IP", "该IP地址已存在，不能重复添加！")
            return
        # 禁用交互
        self.setEnabled(False)
        self.add_btn.setText("正在连接...")
        self.add_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        # 启动线程
        logger.info(f"启动SSH连接线程: {ip}")
        self.ssh_thread = SSHConnectThread(ip, user, pwd)
        self.ssh_thread.result_signal.connect(self.on_ssh_result)
        self.ssh_thread.start()
    def on_ssh_result(self, success, msg):
        logger.info(f"SSH连接结果: 成功={success}, 消息={msg}")
        # 恢复交互
        self.setEnabled(True)
        self.add_btn.setText("添加")
        self.add_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "连接失败", f"SSH连接失败: {msg}")

class UpdateInfoThread(QThread):
    result_signal = pyqtSignal(int, dict, str)  # row, info_dict, error_msg
    def __init__(self, row, ip, user, pwd):
        super().__init__()
        self.row = row
        self.ip = ip
        self.user = user
        self.pwd = pwd
        logger.info(f"UpdateInfoThread初始化: Row={row}, IP={ip}")
    def run(self):
        info = {'type': '', 'kernel': '', 'version': ''}
        error_msg = ''
        try:
            logger.info(f"开始更新代理信息: Row={self.row}, IP={self.ip}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user, password=self.pwd, timeout=8)
            
            # 获取类型
            success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'cat /etc/os-release')
            if success:
                os_type = ''
                for line in stdout_content.splitlines():
                    if line.startswith('ID='):
                        os_type = line.split('=', 1)[1].replace('"', '').strip()
                        break
                info['type'] = os_type or '未知'
                logger.info(f"获取到系统类型: {info['type']}")
            else:
                logger.warning(f"获取系统类型失败: {stderr_content}")
                info['type'] = '未知'
            
            # 获取内核
            success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'uname -r')
            if success:
                info['kernel'] = stdout_content.strip()
                logger.info(f"获取到内核版本: {info['kernel']}")
            else:
                logger.warning(f"获取内核版本失败: {stderr_content}")
                info['kernel'] = '未知'
            
            # 获取代理版本
            success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'cat /usr/local/eim/hostagent/install/product_info')
            if success:
                version = '未安装'
                for line in stdout_content.splitlines():
                    if line.startswith('VERSION='):
                        version = line.split('=', 1)[1].strip()
                        break
                info['version'] = version
                logger.info(f"获取到代理版本: {info['version']}")
            else:
                logger.warning(f"获取代理版本失败: {stderr_content}")
                info['version'] = '未安装'
            
            ssh.close()
            logger.info(f"代理信息更新完成: Row={self.row}, 类型={info['type']}, 内核={info['kernel']}, 版本={info['version']}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"更新代理信息失败: Row={self.row}, IP={self.ip}, 错误: {e}")
        self.result_signal.emit(self.row, info, error_msg)

# SMB获取最新代理版本线程
class LatestVersionThread(QThread):
    result_signal = pyqtSignal(str, str, list)  # version, error_msg, version_packages
    
    def __init__(self, target_os_type=None):
        super().__init__()
        self.target_os_type = target_os_type
        logger.info(f"LatestVersionThread初始化，目标系统类型: {target_os_type}")
    
    def run(self):
        try:
            logger.info("开始获取最新代理版本")
            user = 'xiaoyang.shen'
            pwd = 'infocores'
            server = '192.168.1.20'
            share = 'ALLPackages'
            path = 'hostagent/all/Linux/Packages/6.2'
            logger.info(f"连接SMB服务器: {server}")
            conn = SMBConnection(user, pwd, 'client', server, use_ntlm_v2=True, is_direct_tcp=True)
            if not conn.connect(server, 445, timeout=10):
                logger.error("SMB连接失败")
                self.result_signal.emit('', 'SMB连接失败', [])
                return
            logger.info("SMB连接成功，开始列出文件")
            files = conn.listPath(share, path)
            run_files = [f for f in files if f.filename.endswith('.run') and not f.isDirectory]
            logger.info(f"找到{len(run_files)}个.run文件")
            if not run_files:
                logger.warning("未找到.run文件")
                self.result_signal.emit('', '未找到.run文件', [])
                conn.close()
                return
            
            # 1. 首先找到最新的.ALL.包，提取版本信息
            all_files = [f for f in run_files if '.ALL.' in f.filename]
            if not all_files:
                logger.warning("未找到.ALL.包")
                self.result_signal.emit('', '未找到.ALL.包', [])
                conn.close()
                return
            
            # 按时间排序，找到最新的.ALL.包
            all_files.sort(key=lambda x: x.last_write_time, reverse=True)
            latest_all_file = all_files[0]
            logger.info(f"找到最新的.ALL.包: {latest_all_file.filename}")
            
            # 从.ALL.包名中提取版本信息
            version = parse_version_from_filename(latest_all_file.filename)
            if not version:
                logger.error("无法从文件名中提取版本信息")
                self.result_signal.emit('', '无法提取版本信息', [])
                conn.close()
                return
            
            logger.info(f"提取的版本信息: {version}")
            
            # 2. 收集该版本的所有相关包
            version_packages = []
            for file in run_files:
                if version in file.filename:
                    version_packages.append(file.filename)
                    logger.info(f"找到该版本的包: {file.filename}")
            
            logger.info(f"该版本共有{len(version_packages)}个包")
            conn.close()
            self.result_signal.emit(version, '', version_packages)
        except Exception as e:
            logger.error(f"获取最新版本失败: {e}")
            self.result_signal.emit('', str(e), [])

class StatusCheckThread(QThread):
    status_signal = pyqtSignal(int, str)  # row, status
    def __init__(self, proxy_list):
        super().__init__()
        self.proxy_list = proxy_list
        self._running = True
        self._force_check = False
        logger.info(f"StatusCheckThread初始化，代理数量: {len(proxy_list)}")
    def run(self):
        logger.info("状态检查线程开始运行")
        while self._running:
            self.check_all()
            for _ in range(100):
                if not self._running:
                    break
                if self._force_check:
                    self._force_check = False
                    break
                time.sleep(0.1)
        logger.info("状态检查线程结束")
    def check_all(self):
        import paramiko
        logger.debug("开始检查所有代理状态")
        for row, item in enumerate(self.proxy_list):
            ip = item.get('ip')
            user = item.get('user')
            pwd = item.get('pwd')
            status = '离线'
            try:
                logger.debug(f"检查代理状态: Row={row}, IP={ip}")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username=user, password=pwd, timeout=4)
                
                # 执行一个简单的命令来验证连接
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'echo "test"', timeout=5)
                if success:
                    status = '在线'
                    logger.debug(f"代理在线: Row={row}, IP={ip}")
                else:
                    logger.debug(f"代理连接失败: Row={row}, IP={ip}, 错误: {stderr_content}")
                    status = '离线'
                
                ssh.close()
            except Exception as e:
                logger.debug(f"代理离线: Row={row}, IP={ip}, 错误: {e}")
                status = '离线'
            self.status_signal.emit(row, status)
    def force_check(self):
        logger.info("强制检查状态")
        self._force_check = True
    def stop(self):
        logger.info("停止状态检查线程")
        self._running = False

def parse_version_from_filename(filename):
    # 例如 HostAgent-6.2.11-880-R.ALL.x64-20250626.run -> 6.2.11-880
    # 支持多种格式的包名
    patterns = [
        r'HostAgent-(\d+\.\d+\.\d+-\d+)',  # 基本格式
        r'HostAgent-(\d+\.\d+\.\d+-\d+)-R',  # 带-R后缀
    ]
    
    for pattern in patterns:
        m = re.search(pattern, filename)
        if m:
            return m.group(1)
    
    logger.warning(f"无法从文件名中提取版本信息: {filename}")
    return ''

def version_compare(v1, v2):
    # v1, v2: 6.2.10-868
    def split_version(v):
        if not v:
            return [0,0,0,0]
        parts = v.split('-')
        nums = parts[0].split('.') + [parts[1]] if len(parts)>1 else parts[0].split('.')+['0']
        return [int(x) for x in nums]
    a = split_version(v1)
    b = split_version(v2)
    return (a > b) - (a < b)

class InstallUpdateAgentThread(QThread):
    progress_signal = pyqtSignal(int, str)  # row, progress_text
    def __init__(self, row, ip, user, pwd, smb_filename, update=False):
        super().__init__()
        self.row = row
        self.ip = ip
        self.user = user
        self.pwd = pwd
        self.smb_filename = smb_filename
        self.update = update
        logger.info(f"InstallUpdateAgentThread初始化: Row={row}, IP={ip}, 文件={smb_filename}, 更新={update}")
    def run(self):
        try:
            logger.info(f"开始安装/更新代理: Row={self.row}, IP={self.ip}")
             
            # 1. 建立SSH连接
            self.progress_signal.emit(self.row, '连接服务器...')
            logger.info("开始SSH连接")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user, password=self.pwd, timeout=10)
            logger.info("SSH连接成功")
            
            # 2. 直接从SMB传输到目标服务器
            self.progress_signal.emit(self.row, '传输安装包...')
            logger.info("开始从NAS直接传输文件")
            
            # 尝试多种方式从NAS直接传输到目标服务器
            remote_path = '/root/' + self.smb_filename
            
            # 方法1: 尝试使用curl从HTTP服务下载（如果NAS有HTTP服务）
            http_url = f"http://192.168.1.20/sc/ALLPackages/hostagent/all/Linux/Packages/6.2/{self.smb_filename}"
            logger.info("尝试方法1: curl从HTTP服务下载")
            success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                ssh, f'curl -u xiaoyang.shen:infocores "{http_url}" -o {remote_path}', timeout=300
            )
            
            if not success:
                logger.warning("HTTP下载失败，尝试方法2: 使用smbclient")
                # 方法2: 使用smbclient（Linux系统通常都有）
                smb_command = f'smbclient //192.168.1.20/ALLPackages -U xiaoyang.shen%infocores -c "get hostagent/all/Linux/Packages/6.2/{self.smb_filename} {remote_path}"'
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                    ssh, smb_command, timeout=300
                )
            
            if not success:
                logger.warning("smbclient下载失败，尝试方法3: 使用wget")
                # 方法3: 尝试使用wget
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                    ssh, f'wget --user=xiaoyang.shen --password=infocores "{http_url}" -O {remote_path}', timeout=300
                )
            
            if not success:
                logger.warning("wget也失败，尝试方法4: 使用rsync")
                # 方法4: 尝试使用rsync（如果目标服务器支持）
                rsync_command = f'rsync -avz --progress xiaoyang.shen@192.168.1.20:/ALLPackages/hostagent/all/Linux/Packages/6.2/{self.smb_filename} {remote_path}'
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                    ssh, rsync_command, timeout=300
                )
            
            if not success:
                logger.warning("wget也失败，回退到本地下载方式")
                # 回退到原来的方式：先下载到本地，再上传
                self.progress_signal.emit(self.row, '回退到本地下载方式...')
                logger.info("开始SMB下载到本地")
                smb_user = 'xiaoyang.shen'
                smb_pwd = 'infocores'
                smb_server = '192.168.1.20'
                smb_share = 'ALLPackages'
                smb_path = 'hostagent/all/Linux/Packages/6.2/' + self.smb_filename
                conn = SMBConnection(smb_user, smb_pwd, 'client', smb_server, use_ntlm_v2=True, is_direct_tcp=True)
                if not conn.connect(smb_server, 445, timeout=10):
                    logger.error("SMB连接失败")
                    self.progress_signal.emit(self.row, 'SMB连接失败')
                    ssh.close()
                    return
                tmp_dir = tempfile.gettempdir()
                local_path = os.path.join(tmp_dir, self.smb_filename)
                logger.info(f"下载文件到: {local_path}")
                with open(local_path, 'wb') as f:
                    conn.retrieveFile(smb_share, smb_path, f)
                conn.close()
                logger.info("SMB下载完成")
                
                # SFTP上传
                self.progress_signal.emit(self.row, '上传安装包...')
                logger.info("开始SFTP上传")
                sftp = ssh.open_sftp()
                logger.info(f"上传文件到: {remote_path}")
                sftp.put(local_path, remote_path)
                sftp.close()
                logger.info("SFTP上传完成")
                
                # 清理本地文件
                try:
                    os.remove(local_path)
                    logger.info("清理本地临时文件")
                except:
                    pass
            else:
                logger.info("直接从NAS传输成功")
                self.progress_signal.emit(self.row, '安装包传输完成')
            # 3. 更新流程（如需）
            if self.update:
                logger.info("开始更新流程")
                self.progress_signal.emit(self.row, '开始更新代理...')
                
                # 检查卸载脚本
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'ls /usr/sbin/uninstall_hostagent.sh')
                if success and stdout_content.strip():
                    logger.info("找到uninstall_hostagent.sh脚本")
                    self.progress_signal.emit(self.row, '执行卸载脚本...')
                    
                    # 执行交互式卸载脚本，自动输入'y'
                    success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                        ssh, 'bash /usr/sbin/uninstall_hostagent.sh', 
                        timeout=60, interactive_input='y'
                    )
                    
                    if success:
                        logger.info("uninstall_hostagent.sh执行成功")
                        self.progress_signal.emit(self.row, '卸载脚本执行成功')
                    else:
                        logger.warning(f"uninstall_hostagent.sh执行失败: {stderr_content}")
                        self.progress_signal.emit(self.row, f'卸载脚本执行失败: {stderr_content}')
                        
                else:
                    # 尝试其他卸载脚本
                    success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'ls /usr/bin/osnstmclient_uninst.sh')
                    if success and stdout_content.strip():
                        logger.info("找到osnstmclient_uninst.sh脚本")
                        self.progress_signal.emit(self.row, '执行osnstmclient_uninst.sh...')
                        
                        success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                            ssh, 'bash /usr/bin/osnstmclient_uninst.sh clean', 
                            timeout=60, interactive_input='y'
                        )
                        
                        if success:
                            logger.info("osnstmclient_uninst.sh执行成功")
                            self.progress_signal.emit(self.row, '卸载脚本执行成功')
                        else:
                            logger.warning(f"osnstmclient_uninst.sh执行失败: {stderr_content}")
                            self.progress_signal.emit(self.row, f'卸载脚本执行失败: {stderr_content}')
                    else:
                        logger.warning("未找到卸载脚本")
                        self.progress_signal.emit(self.row, '未找到卸载脚本，跳过卸载')
                
                # 尝试卸载驱动
                self.progress_signal.emit(self.row, '卸载驱动...')
                success, stdout_content, stderr_content, exit_code = execute_ssh_command(ssh, 'rmmod osnhm')
                if success:
                    logger.info("驱动卸载成功")
                else:
                    logger.warning(f"驱动卸载失败: {stderr_content}")
            # 4. 安装
            self.progress_signal.emit(self.row, '安装代理中...')
            logger.info("开始安装代理")
            
            success, stdout_content, stderr_content, exit_code = execute_ssh_command(
                ssh, f'bash {remote_path}', timeout=120, interactive_input='y'
            )
            
            if success:
                logger.info("安装完成")
                self.progress_signal.emit(self.row, '安装完成，等待刷新...')
            else:
                logger.error(f"安装失败: 退出码={exit_code}, 错误: {stderr_content}")
                self.progress_signal.emit(self.row, f'安装失败: {stderr_content}')
            
            ssh.close()
        except Exception as e:
            logger.error(f"安装/更新代理失败: Row={self.row}, IP={self.ip}, 错误: {e}")
            self.progress_signal.emit(self.row, f'失败: {e}')

class LinuxProxyManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Linux代理管理")
        self.setMinimumSize(800, 400)
        self.latest_version_packages = []  # 初始化版本包列表
        self.init_ui()
        self.load_config()
        self.get_latest_version()
        self.status_thread = StatusCheckThread(self.proxy_list)
        self.status_thread.status_signal.connect(self.on_status_update)
        self.status_thread.start()

    def init_ui(self):
        layout = QVBoxLayout()
        # 按钮行
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.add_btn.setStyleSheet(APPLE_BTN_STYLE_BLUE)
        self.add_btn.setFixedWidth(60)
        self.add_btn.setFixedHeight(24)
        self.add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_layout.addWidget(self.add_btn)
        self.refresh_all_btn = QPushButton("刷新")
        self.refresh_all_btn.setStyleSheet(APPLE_BTN_STYLE)
        self.refresh_all_btn.setFixedWidth(60)
        self.refresh_all_btn.setFixedHeight(24)
        self.refresh_all_btn.setToolTip('刷新所有代理信息')
        btn_layout.addWidget(self.refresh_all_btn)
        btn_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(btn_layout)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.refresh_all_btn.clicked.connect(self.refresh_all_and_version)
        # 表格
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["IP地址", "类型", "内核版本", "代理版本", "状态"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        layout.addWidget(self.table)
        # 状态栏（只保留左对齐文字）
        status_layout = QHBoxLayout()
        self.status_bar = QLabel("最新代理版本：获取中...")
        self.status_bar.setStyleSheet("color: #222; font-size: 12px; padding: 0 0 0 0;")
        self.status_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status_layout.addWidget(self.status_bar)
        status_layout.addStretch(1)
        layout.addLayout(status_layout)
        self.setLayout(layout)

    def load_config(self):
        logger.info("开始加载配置")
        self.proxy_list = []
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.proxy_list = json.load(f)
                logger.info(f"成功加载配置，代理数量: {len(self.proxy_list)}")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                self.proxy_list = []
        else:
            logger.info("配置文件不存在，使用空列表")
        self.refresh_table()

    def save_config(self):
        try:
            logger.info(f"保存配置，代理数量: {len(self.proxy_list)}")
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.proxy_list, f, ensure_ascii=False, indent=2)
            logger.info("配置保存成功")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            QMessageBox.warning(self, "保存失败", f"保存配置失败: {e}")

    def refresh_table(self):
        logger.info(f"刷新表格，行数: {len(self.proxy_list)}")
        self.table.setRowCount(len(self.proxy_list))
        for row, item in enumerate(self.proxy_list):
            ip_item = QTableWidgetItem(item.get('ip', ''))
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, ip_item)
            type_item = QTableWidgetItem(item.get('type', ''))
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, type_item)
            kernel_item = QTableWidgetItem(item.get('kernel', ''))
            self.table.setItem(row, 2, kernel_item)
            version_item = QTableWidgetItem(item.get('version', ''))
            version_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, version_item)
            status_item = QTableWidgetItem(item.get('status', ''))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, status_item)
        # 设置列宽（1字符≈9px，适当留余量）
        self.table.setColumnWidth(0, 12*9)   # IP地址
        self.table.setColumnWidth(1, 10*9)   # 类型
        self.table.setColumnWidth(2, 30*9)   # 内核
        self.table.setColumnWidth(3, 20*9)   # 代理版本
        self.table.setColumnWidth(4, 10*9)   # 状态
        # 主动触发一次状态检测
        if hasattr(self, 'status_thread') and self.status_thread.isRunning():
            logger.info("触发强制状态检查")
            self.status_thread.force_check()

    def on_add_clicked(self):
        logger.info("用户点击添加按钮")
        existing_ips = set(item.get('ip') for item in self.proxy_list)
        logger.info(f"现有IP列表: {existing_ips}")
        dlg = AddLinuxProxyDialog(self, existing_ips=existing_ips)
        if dlg.exec_() == QDialog.Accepted:
            ip, user, pwd = dlg.get_data()
            logger.info(f"添加新代理: IP={ip}, User={user}")
            # 添加到配置
            self.proxy_list.append({'ip': ip, 'user': user, 'pwd': pwd})
            self.save_config()
            self.refresh_table()
            QMessageBox.information(self, "添加成功", f"{ip} 添加成功！")
            # 自动获取一次信息
            row = len(self.proxy_list) - 1
            if row >= 0:
                logger.info(f"自动获取代理信息: Row={row}, IP={ip}")
                version_item = QTableWidgetItem('更新中...')
                version_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, version_item)  # 只写到代理版本列
                ip = self.proxy_list[row].get('ip')
                user = self.proxy_list[row].get('user')
                pwd = self.proxy_list[row].get('pwd')
                thread = UpdateInfoThread(row, ip, user, pwd)
                thread.result_signal.connect(self.on_update_info_result)
                thread.start()
                if not hasattr(self, '_update_threads'):
                    self._update_threads = []
                self._update_threads.append(thread)

    def show_table_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        selected_rows = set(idx.row() for idx in self.table.selectedIndexes())
        if not selected_rows:
            return
        menu = QMenu(self.table)
        row = list(selected_rows)[0]
        version = self.table.item(row, 3).text() if self.table.item(row, 3) else ''
        
        # 获取最新版本信息
        latest_version = ''
        if hasattr(self, 'status_bar') and self.status_bar.text().startswith('最新代理版本：'):
            latest_version = self.status_bar.text().replace('最新代理版本：', '').strip()
        
        # 动态菜单
        if version == '未安装' or not version or version.startswith('失败'):
            install_action = menu.addAction("安装代理")
            install_action.setEnabled(True)
            
            # 添加分隔线
            menu.addSeparator()
            
            # 添加删除选项
            delete_action = menu.addAction("删除")
            
            action = menu.exec_(self.table.viewport().mapToGlobal(pos))
            if action == delete_action:
                self.delete_selected_rows()
            elif action == install_action:
                self.install_or_update_agent(row)  # 不传递文件名，让方法自动选择
        else:
            update_action = menu.addAction("更新代理")
            if latest_version and version_compare(version, latest_version) >= 0:
                update_action.setEnabled(False)
            else:
                update_action.setEnabled(True)
            
            # 添加分隔线
            menu.addSeparator()
            
            # 添加删除选项
            delete_action = menu.addAction("删除")
            
            action = menu.exec_(self.table.viewport().mapToGlobal(pos))
            if action == delete_action:
                self.delete_selected_rows()
            elif action == update_action and update_action.isEnabled():
                self.install_or_update_agent(row, update=True)  # 不传递文件名，让方法自动选择

    def update_selected_info(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not selected_rows:
            return
        for row in selected_rows:
            if 0 <= row < len(self.proxy_list):
                self.table.setItem(row, 3, QTableWidgetItem('更新中...'))  # 代理版本列
                ip = self.proxy_list[row].get('ip')
                user = self.proxy_list[row].get('user')
                pwd = self.proxy_list[row].get('pwd')
                thread = UpdateInfoThread(row, ip, user, pwd)
                thread.result_signal.connect(self.on_update_info_result)
                thread.start()
                # 保存线程引用，防止被回收
                if not hasattr(self, '_update_threads'):
                    self._update_threads = []
                self._update_threads.append(thread)

    def on_update_info_result(self, row, info, error_msg):
        logger.info(f"收到代理信息更新结果: Row={row}, 错误={error_msg}")
        if error_msg:
            logger.error(f"更新代理信息失败: Row={row}, 错误: {error_msg}")
            version_item = QTableWidgetItem(f'失败: {error_msg}')
            version_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, version_item)
        else:
            logger.info(f"更新代理信息成功: Row={row}, 类型={info.get('type')}, 内核={info.get('kernel')}, 版本={info.get('version')}")
            type_item = QTableWidgetItem(info.get('type', ''))
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, type_item)
            self.table.setItem(row, 2, QTableWidgetItem(info.get('kernel', '')))
            version_item = QTableWidgetItem(info.get('version', ''))
            version_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, version_item)
            # 保存到本地配置
            if 0 <= row < len(self.proxy_list):
                self.proxy_list[row]['type'] = info.get('type', '')
                self.proxy_list[row]['kernel'] = info.get('kernel', '')
                self.proxy_list[row]['version'] = info.get('version', '')
                self.save_config()
        # 清理线程引用
        if hasattr(self, '_update_threads'):
            self._update_threads = [t for t in self._update_threads if t.isRunning()]

    def delete_selected_rows(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        if not selected_rows:
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的{len(selected_rows)}项吗？", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for row in selected_rows:
            if 0 <= row < len(self.proxy_list):
                self.proxy_list.pop(row)
        self.save_config()
        self.refresh_table()

    def get_latest_version(self):
        logger.info("开始获取最新版本")
        self.status_bar.setText("最新代理版本：获取中...")
        self.latest_thread = LatestVersionThread()
        self.latest_thread.result_signal.connect(self.on_latest_version_result)
        self.latest_thread.start()

    def on_latest_version_result(self, version, error_msg, version_packages):
        if version:
            logger.info(f"获取最新版本成功: {version}")
            logger.info(f"该版本包含的包: {version_packages}")
            self.status_bar.setText(f"最新代理版本：{version}")
            # 保存版本包信息供后续使用
            self.latest_version_packages = version_packages
        else:
            logger.error(f"获取最新版本失败: {error_msg}")
            self.status_bar.setText(f"最新代理版本：获取失败（{error_msg}）")
            self.latest_version_packages = []

    def on_status_update(self, row, status):
        logger.debug(f"状态更新: Row={row}, Status={status}")
        if 0 <= row < self.table.rowCount():
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, status_item)

    def refresh_all_info(self):
        for row, item in enumerate(self.proxy_list):
            self.table.setItem(row, 3, QTableWidgetItem('更新中...'))
            ip = item.get('ip')
            user = item.get('user')
            pwd = item.get('pwd')
            thread = UpdateInfoThread(row, ip, user, pwd)
            thread.result_signal.connect(self.on_update_info_result)
            thread.start()
            if not hasattr(self, '_update_threads'):
                self._update_threads = []
            self._update_threads.append(thread)

    def refresh_all_and_version(self):
        self.refresh_all_info()
        self.get_latest_version()

    def select_package_for_system(self, os_type):
        """
        根据系统类型选择合适的包
        
        Args:
            os_type: 系统类型（如 'centos', 'ubuntu' 等）
            
        Returns:
            str: 选择的包文件名，如果没有找到合适的包则返回None
        """
        if not hasattr(self, 'latest_version_packages') or not self.latest_version_packages:
            logger.warning("没有可用的版本包列表")
            return None
        
        # 系统类型映射
        os_type_mapping = {
            'centos': 'centos',
            'rhel': 'centos',  # Red Hat Enterprise Linux 通常使用 centos 包
            'rocky': 'rocky', 
            'kylin': 'kylin',
            'openeuler': 'openeuler',
            'oracle': 'oraclelinux',
            'ubuntu': 'ubuntu',
            'oraclelinux': 'oraclelinux',
            'uos': 'uos',
            'debian': 'debian',
        }
        
        mapped_os_type = os_type_mapping.get(os_type.lower(), os_type.lower())
        logger.info(f"查找系统特定包，系统类型: {os_type} -> {mapped_os_type}")
        
        # 1. 首先查找系统特定包
        for package in self.latest_version_packages:
            if mapped_os_type in package.lower():
                logger.info(f"找到系统特定包: {package}")
                return package
        
        # 2. 如果没有找到系统特定包，查找.ALL.包
        logger.info("未找到系统特定包，查找.ALL.包")
        for package in self.latest_version_packages:
            if '.ALL.' in package:
                logger.info(f"找到.ALL.包: {package}")
                return package
        
        logger.warning("未找到合适的包")
        return None

    def install_or_update_agent(self, row, smb_filename=None, update=False):
        logger.info(f"开始安装/更新代理: Row={row}, 文件={smb_filename}, 更新={update}")
        
        # 如果没有指定文件名，根据系统类型选择
        if not smb_filename:
            if 0 <= row < len(self.proxy_list):
                os_type = self.proxy_list[row].get('type', '')
                if os_type:
                    smb_filename = self.select_package_for_system(os_type)
                    if not smb_filename:
                        logger.error(f"无法为系统类型 {os_type} 找到合适的包")
                        QMessageBox.warning(self, "包选择失败", f"无法为系统类型 {os_type} 找到合适的包")
                        return
                    logger.info(f"选择的包: {smb_filename}")
                else:
                    logger.error("系统类型未知，无法选择包")
                    QMessageBox.warning(self, "包选择失败", "系统类型未知，请先刷新代理信息")
                    return
            else:
                logger.error("行索引超出范围")
                return
        
        # 进度初始
        version_item = QTableWidgetItem('准备中...')
        version_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 3, version_item)
        ip = self.proxy_list[row].get('ip')
        user = self.proxy_list[row].get('user')
        pwd = self.proxy_list[row].get('pwd')
        thread = InstallUpdateAgentThread(row, ip, user, pwd, smb_filename, update=update)
        thread.progress_signal.connect(self.on_agent_install_progress)
        thread.start()
        if not hasattr(self, '_agent_threads'):
            self._agent_threads = []
        self._agent_threads.append(thread)

    def on_agent_install_progress(self, row, text):
        logger.info(f"安装进度更新: Row={row}, 进度={text}")
        version_item = QTableWidgetItem(text)
        version_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 3, version_item)
        
        # 如果安装完成，自动刷新该行的代理信息
        if text == '安装完成，等待刷新...':
            logger.info(f"安装完成，开始刷新代理信息: Row={row}")
            # 延迟一点时间，确保安装完全完成
            time.sleep(2)
            
            # 刷新该行的代理信息
            if 0 <= row < len(self.proxy_list):
                ip = self.proxy_list[row].get('ip')
                user = self.proxy_list[row].get('user')
                pwd = self.proxy_list[row].get('pwd')
                thread = UpdateInfoThread(row, ip, user, pwd)
                thread.result_signal.connect(self.on_update_info_result)
                thread.start()
                if not hasattr(self, '_update_threads'):
                    self._update_threads = []
                self._update_threads.append(thread)

    def closeEvent(self, event):
        logger.info("Linux代理管理对话框关闭")
        if hasattr(self, 'status_thread') and self.status_thread.isRunning():
            logger.info("停止状态检查线程")
            self.status_thread.stop()
            self.status_thread.wait()
        super().closeEvent(event) 