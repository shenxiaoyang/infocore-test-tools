import os
import sys
import re
import platform
import shutil
import requests
import json
import subprocess
import hashlib

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


if __name__ == "__main__":
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
        
        os.chdir(current_dir)
        
        cmd = f"pyinstaller {build_spec_path}"
        result = os.system(cmd)
        
        if result == 0:
            print("build.spec 执行完成")
            print(f"生成的文件应该在 {os.path.join(current_dir, 'dist')} 目录下")
            exe_name = f"Windows工具集-v{new_version}.exe"
            exe_path = os.path.join(current_dir, 'dist', exe_name)
            changelog_path = os.path.join(current_dir, 'changelog.md')
            patch_md_path = os.path.join(current_dir, 'patch.md')

            # 获取架构
            arch = platform.machine().lower()
            if 'amd64' in arch or 'x86_64' in arch:
                arch_dir = 'x64'
            elif 'arm' in arch:
                arch_dir = 'arm64'
            elif 'x86' in arch:
                arch_dir = 'x86'
            else:
                arch_dir = arch  # 兜底

            # 拼接目标路径
            target_dir = r'\\192.168.1.20\测试部（日志和iso）\软件类\自研\Windows工具集\{}'.format(arch_dir)
            target_path = os.path.join(target_dir, exe_name)
            target_path_str = target_path.replace('\\', '\\\\')
            changelog_target_path = os.path.join(target_dir, 'changelog.md')

            try:
                shutil.copy(exe_path, target_path)
                print(f"已将 {exe_name} 拷贝到 {target_path}")
                
                # 合并 patch.md 到 changelog.md 顶部
                try:
                    if os.path.exists(patch_md_path):
                        with open(patch_md_path, 'r', encoding='utf-8') as f:
                            patch_content = f.read().strip()
                    else:
                        patch_content = ''
                    # 有内容则合并，无内容只写版本号
                    if patch_content:
                        changelog_entry = f'## v{new_version}\n' + patch_content + '\n\n'
                    else:
                        changelog_entry = f'## v{new_version}\n\n'
                    # 读取原changelog
                    if os.path.exists(changelog_path):
                        with open(changelog_path, 'r', encoding='utf-8') as f:
                            old_changelog = f.read()
                    else:
                        old_changelog = ''
                    # 新日志在前
                    with open(changelog_path, 'w', encoding='utf-8') as f:
                        f.write(changelog_entry + old_changelog)
                    # 清空patch.md
                    with open(patch_md_path, 'w', encoding='utf-8') as f:
                        f.write('')
                    print('已将 patch.md 合并到 changelog.md（无内容则只记录版本号）')
                except Exception as ce:
                    print(f'patch.md 合并到 changelog 失败: {ce}')

                shutil.copy(changelog_path, changelog_target_path)
                print(f"已将 {changelog_path} 拷贝到 {changelog_target_path}")
                
                # 发送企业微信消息
                webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=30bd8711-f692-4b71-8953-66ae6f6cd058"
                msg = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": (
                            f"# 🎉 Windows工具集更新\n\n"
                            f"> 版本号： v{new_version}\n"
                            f"> 路径：{target_path_str}\n"
                        )
                    }
                }
                try:
                    resp = requests.post(webhook_url, data=json.dumps(msg), headers={"Content-Type": "application/json"})
                    if resp.status_code == 200:
                        print("企业微信通知已发送")
                    else:
                        print(f"企业微信通知发送失败: {resp.text}")
                except Exception as we:
                    print(f"企业微信通知异常: {we}")
            except Exception as e:
                print(f"拷贝到共享目录失败: {e}")
        else:
            print(f"执行失败，错误码: {result}")
    except Exception as e:
        print(f"发生错误: {str(e)}")
