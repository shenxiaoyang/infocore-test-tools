# Windows工具套件

这是一个Windows工具套件，包含以下功能：

1. **MD5一致性计算器**
   - 批量计算文件/文件夹MD5值，支持扩展名过滤、关键字排除、按时间过滤
   - 结果自动保存为CSV
   - 支持一键快速计算系统盘 Windows 目录下 dll/sys/exe 文件的MD5

2. **MD5计算器**
   - 单文件哈希计算与校验工具，支持MD5/SHA1/SHA256/SHA512
   - 支持文件拖拽，显示文件详细信息（大小、创建/修改/访问时间）
   - 支持哈希值比对验证，匹配时高亮显示

3. **文件对比工具**
   - 对比两个文件内容差异，适合一致性和变更检测

4. **本地文件产生器**
   - 批量生成指定大小、数量的测试文件，支持循环/单次模式
   - 可自动恢复上次配置

5. **文件校验工具**
   - 校验本地文件产生器生成的文件完整性，支持批量校验

6. **第三方工具集成**
   - **磁盘扇区查看**：一键启动 diskprobe.exe，查看磁盘扇区内容
   - **磁盘信息查看**：一键启动 DiskGenius，进行磁盘管理和数据恢复
   - **系统缓存刷新**：一键运行 sync.exe，刷新系统缓存
   - **网络异常模拟**：一键启动 clumsy.exe，模拟网络延迟、丢包等异常情况

7. **HostAgent 配置工具**
   - **EIMVssProvider日志配置**：启用/关闭日志记录，自动重启服务
   - **程序文件签名检查**：检查程序文件的数字签名状态
   - **代理下载安装**：从SMB服务器自动下载最新的HostAgent代理文件
     - 支持x86/x64架构自动识别
     - 异步下载，不阻塞界面
     - 自动选择最新版本文件
   - **驱动签名验证管理**：一键切换 testsigning 和 nointegritychecks 状态
     - 实时显示当前验证状态（已打开/已关闭）
     - 显示详细的 testsigning 和 nointegritychecks 状态
     - 异步操作，支持自动UAC提权
   - **Windows更新重置**：一键重置Windows更新配置
     - 停止并禁用Windows更新服务
     - 清理更新缓存目录
     - 重新启用并启动更新服务
     - 支持二级确认，防止误操作

## 系统要求

- Windows
- Python 3.7或更高版本
- PyQt5

## 安装

1. 克隆仓库：
```bash
git clone http://192.168.4.254/shenxiaoyang/infocore-test-tools.git
cd infocore-test-tools/windows-tools-suite
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

运行主程序：
```bash
python src/main.py
```

## 注意事项

1. 处理大量文件时可能需要较长时间，请耐心等待
2. 可以随时点击"停止"按钮中断操作

## 自动打包与发布

本项目提供了自动化打包脚本 `patch.py`，可一键完成以下操作：

- 自动递增版本号（version.txt）
- 自动更新 build.spec 中的 exe 名称
- 调用 pyinstaller 生成新版 exe
- 自动将生成的 exe 拷贝到共享目录（如有权限）

### 使用方法

1. 确保已安装依赖（见下方 requirements.txt）
2. 在 `windows-tools-suite` 目录下运行：
   ```bash
   python patch.py
   ```
3. 打包完成后，生成的 exe 位于 `dist` 目录下，并自动尝试拷贝到共享目录。

如拷贝失败，请手动从 `dist` 目录获取 exe。

## 许可证

MIT License