# Windows工具套件

> 一个功能丰富、界面友好的Windows系统工具集合，为系统管理员和开发者提供便捷的文件处理、系统配置和代理管理功能。

![版本](https://img.shields.io/badge/版本-v1.1.22-blue)
![平台](https://img.shields.io/badge/平台-Windows-lightgrey)
![Python](https://img.shields.io/badge/Python-3.7+-green)

## ✨ 功能特性

### 📊 文件处理工具
- **MD5一致性计算器** - 批量计算文件/文件夹MD5值，支持扩展名过滤、关键字排除、按时间过滤，结果自动保存为CSV
- **快速系统盘计算** - 一键计算系统盘Windows目录下dll/sys/exe文件的MD5值
- **MD5计算器** - 单文件哈希计算与校验工具，支持MD5/SHA1/SHA256/SHA512，支持文件拖拽和哈希值比对验证
- **文件对比工具** - 对比两个文件内容差异，适合一致性和变更检测
- **本地文件产生器** - 批量生成指定大小、数量的测试文件，支持循环/单次模式
- **文件校验工具** - 校验本地文件产生器生成的文件完整性，支持批量校验

### 🖥️ 系统配置管理
- **驱动签名验证管理** - 一键切换testsigning和nointegritychecks状态，实时显示验证状态
- **Windows更新重置** - 一键重置Windows更新配置，支持二级确认防止误操作
- **系统缓存刷新** - 一键运行sync.exe刷新系统缓存

### 🌐 代理管理工具
- **Windows代理配置**
  - EIMVssProvider日志配置：启用/关闭日志记录，自动重启服务
  - 程序文件签名检查：检查程序文件的数字签名状态
  - 代理下载安装：从SMB服务器自动下载最新的HostAgent代理文件
- **Linux代理管理**
  - 代理服务器管理：添加、删除、监控Linux代理服务器
  - 系统信息获取：自动获取操作系统类型、内核版本、代理版本
  - 状态监控：实时监控代理服务器的在线状态
  - 代理安装/更新：自动安装和更新HostAgent代理

### 🔧 第三方工具集成
- **磁盘扇区查看** - 一键启动diskprobe.exe查看磁盘扇区内容
- **磁盘信息查看** - 一键启动DiskGenius进行磁盘管理和数据恢复
- **网络异常模拟** - 一键启动clumsy.exe模拟网络延迟、丢包等异常情况

## 🚀 快速开始

### 系统要求
- Windows 7/8/10/11
- Python 3.7或更高版本
- PyQt5

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone http://192.168.4.254/shenxiaoyang/infocore-test-tools.git
   cd infocore-test-tools/windows-tools-suite
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python src/main.py
   ```

## 📦 自动打包与发布

本项目提供了自动化打包脚本，支持一键完成版本管理和程序打包：

### 功能特性
- ✅ 自动递增版本号
- ✅ 自动更新build.spec中的exe名称
- ✅ 调用pyinstaller生成新版exe
- ✅ 自动拷贝到共享目录
- ✅ 企业微信消息推送
- ✅ 自动合并changelog

### 使用方法
```bash
python patch.py
```

打包完成后，生成的exe位于`dist`目录下，并自动尝试拷贝到共享目录。

## 📝 使用说明

### 基本操作
1. 启动程序后，主界面显示所有可用工具模块
2. 点击相应按钮打开对应的功能模块
3. 每个模块都有详细的操作说明和进度提示
4. 支持拖拽文件到相应区域进行快速操作

### 注意事项
- 🔸 处理大量文件时可能需要较长时间，请耐心等待
- 🔸 可以随时点击"停止"按钮中断操作
- 🔸 某些功能需要管理员权限，程序会自动请求UAC提权
- 🔸 建议在使用前备份重要数据

## 🔄 版本历史

查看 [changelog.md](changelog.md) 了解详细的版本更新记录。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request来帮助改进这个项目。

## 📞 联系方式

如有问题或建议，请联系开发团队。
