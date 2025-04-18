import os
import sys

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将当前目录添加到系统路径
sys.path.append(current_dir)

build_spec_path = os.path.join(current_dir, "build.spec")

try:
    print(f"开始执行 build.spec: {build_spec_path}")
    cmd = f"pyinstaller {build_spec_path}"
    result = os.system(cmd)
    
    if result == 0:
        print("build.spec 执行完成")
        print(f"生成的文件应该在 {os.path.join(current_dir, 'dist')} 目录下")
    else:
        print(f"执行失败，错误码: {result}")
except Exception as e:
    print(f"发生错误: {str(e)}")
