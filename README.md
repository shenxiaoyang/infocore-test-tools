# Windows Test Tools Suite

这是一个 Windows 测试工具集合，包含以下功能：

1. MD5 一致性计算器
   - 计算选定目录下文件的 MD5 值
   - 快速计算系统盘 Windows 目录下的 dll、sys、exe 文件的 MD5 值

2. 文件对比工具
   - 对比两个文件的内容差异

3. 本地文件产生器
   - 生成指定大小和数量的测试文件

4. 文件校验工具
   - 验证本地文件产生器产生的文件的完整性

## 环境要求

- Python 3.7+
- PyQt6 6.6.1
- pyinstaller 6.3.0

## 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/shenxiaoyang/infocore-test-tools.git
   ```

2. 安装依赖：
   ```bash
   pip install -r windows-tools-suite/requirements.txt
   ```

## 运行

直接运行主程序：
```bash
python windows-tools-suite/main.py
```

## 打包

使用 PyInstaller 打包成可执行文件：
```bash
pyinstaller windows-tools-suite/build.spec
```

## 许可证

© 2024 Windows工具集