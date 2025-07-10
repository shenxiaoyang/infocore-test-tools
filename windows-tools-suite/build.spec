# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('C:\\Windows\\System32\\vcruntime140.dll', '.')
    ],
    datas=[
        ('src/utils', 'src/utils'),
        ('src/core', 'src/core'),
        ('src/ui', 'src/ui'),
        ('src/resources', 'src/resources'),
    ],
    hiddenimports=[
        'PyQt5',
        'concurrent.futures',
        'yaml'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pydoc', 'doctest', 'email', 'html', 'http', 'xml', 'xmlrpc', 'sqlite3', 'asyncio', 'distutils', 'setuptools'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Windows工具集-v1.1.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
    icon='src/resources/icons/app.ico',  # 可以添加图标文件路径
    uac_admin=True  # 请求管理员权限
) 