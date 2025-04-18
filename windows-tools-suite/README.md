# Windows工具套件

这是一个Windows工具套件，包含以下功能：

1. MD5计算器
   - 支持批量计算文件MD5值
   - 支持文件扩展名过滤
   - 支持关键字排除
   - 支持按时间过滤（修改时间/创建时间/访问时间）
   - 结果自动保存为CSV文件

2. 文件生成器
   - 支持生成指定大小的文件
   - 支持批量生成多个文件
   - 生成的文件使用.md5file扩展名
   - 实时显示生成进度

## 系统要求

- Windows 10或更高版本
- Python 3.8或更高版本
- PyQt5

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/shenxiaoyang/infocore-test-tools.git
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

### MD5计算器

1. 选择要扫描的目录
2. 输入要处理的文件扩展名（如：.exe, .dll）
3. 可选：输入要排除的关键字
4. 选择时间过滤类型和时间范围
5. 点击"开始"按钮开始计算
6. 结果将自动保存到选择目录下的results目录中

### 文件生成器

1. 选择文件生成目录
2. 设置单个文件的大小（字节）
3. 设置要生成的文件数量
4. 点击"开始生成"按钮
5. 生成的文件将保存在选择的目录中

## 注意事项

1. 处理大量文件时可能需要较长时间，请耐心等待
2. 可以随时点击"停止"按钮中断操作

## 许可证

MIT License