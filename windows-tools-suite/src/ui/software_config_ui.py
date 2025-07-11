import sys
import os
import winreg
import yaml
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QPushButton, QMessageBox, QCheckBox, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer

class SoftwareConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("工具集配置")
        self.setMinimumWidth(400)
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
