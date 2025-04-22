import os
import sys
import re

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将当前目录添加到系统路径
sys.path.append(current_dir)

def read_version():
    version_file = os.path.join(current_dir, "version.txt")
    with open(version_file, 'r') as f:
        return f.read().strip()

def increment_version(version):
    major, minor, patch = map(int, version.split('.'))
    patch += 1
    return f"{major}.{minor}.{patch}"

def update_version(new_version):
    version_file = os.path.join(current_dir, "version.txt")
    with open(version_file, 'w') as f:
        f.write(new_version)

def update_spec_file(version):
    build_spec_path = os.path.join(current_dir, "build.spec")
    with open(build_spec_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新exe名称
    new_content = re.sub(
        r'name=[\'"](.*?)[\'"]',
        f'name=\'Windows工具集-v{version}\'',
        content
    )
    
    with open(build_spec_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

try:
    # 读取并更新版本号
    current_version = read_version()
    new_version = increment_version(current_version)
    update_version(new_version)
    
    # 更新spec文件中的exe名称
    update_spec_file(new_version)
    
    build_spec_path = os.path.join(current_dir, "build.spec")
    print(f"当前版本: v{new_version}")
    print(f"开始执行 build.spec: {build_spec_path}")
    
    cmd = f"pyinstaller {build_spec_path}"
    result = os.system(cmd)
    
    if result == 0:
        print("build.spec 执行完成")
        print(f"生成的文件应该在 {os.path.join(current_dir, 'dist')} 目录下")
        print(f"文件名: Windows工具集-v{new_version}.exe")
    else:
        print(f"执行失败，错误码: {result}")
except Exception as e:
    print(f"发生错误: {str(e)}")
