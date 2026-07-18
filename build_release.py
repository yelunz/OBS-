"""
build_release.py - 自动版本递增 + PyInstaller + Inno Setup 打包

每次执行:
  1. 读取 version.txt 获取当前版本号
  2. 版本号递增 (1.00→1.01→1.02→...)
  3. 更新 installer.iss 中的版本字符串
  4. 运行 PyInstaller 打包
  5. 运行 Inno Setup 编译安装包
  6. 写入新版本号到 version.txt
"""

import os
import sys
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
INSTALLER_ISS = os.path.join(BASE_DIR, "installer.iss")
BUILD_BAT = os.path.join(BASE_DIR, "build.bat")


def read_version():
    """从 version.txt 读取当前版本号"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        ver = f.read().strip()
    return ver


def write_version(ver):
    """写入新版本号到 version.txt"""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(ver + "\n")


def increment_version(ver):
    """版本递增: 1.00 → 1.01 → 1.02 → ... (两位小数)"""
    parts = ver.split(".")
    if len(parts) == 2:
        major = int(parts[0])
        minor = int(parts[1])
        minor += 1
        if minor >= 100:
            major += 1
            minor = 0
        return f"{major}.{minor:02d}"
    # fallback: 如果格式不符, 使用简单累加
    try:
        num = float(ver)
        num = round(num + 0.01, 2)
        return f"{num:.2f}"
    except ValueError:
        print(f"[错误] 无法解析版本号: {ver}")
        sys.exit(1)


def patch_installer_iss(old_ver, new_ver):
    """更新 installer.iss 中的所有版本字符串"""
    with open(INSTALLER_ISS, "r", encoding="utf-8") as f:
        content = f.read()

    old_ver_dot = old_ver.replace("_", ".")  # 兼容 1_00 格式
    new_ver_dot = new_ver.replace("_", ".")

    # 替换 #define MyAppVersion "..."
    content = re.sub(
        r'(#define MyAppVersion\s+")[^"]*(")',
        f'\\g<1>{new_ver_dot}\\g<2>',
        content,
    )

    # 替换 OutputBaseFilename 中的版本号 (直接匹配 v 后面的数字, 不依赖旧值)
    content = re.sub(
        r'(OBS多视角切换器_安装包_v)[\d.]+',
        f'\\g<1>{new_ver_dot}',
        content,
    )

    with open(INSTALLER_ISS, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  installer.iss 已更新: {old_ver_dot} → {new_ver_dot}")


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print("\n[1/3] PyInstaller 打包...")
    result = subprocess.run(
        [
            sys.executable or "py", "-m", "PyInstaller",
            "--noconfirm", "--clean", "--windowed",
            "--name", "OBS多视角切换器",
            "--icon", "app_icon.ico",
            "--add-data", "app_icon.ico;.",
            "--add-data", "templates;templates",
            "--add-data", "mediamtx.exe;.",
            "--hidden-import", "vlc",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL.Image",
            "--hidden-import", "PIL.ImageTk",
            "--hidden-import", "pynput.mouse",
            "--hidden-import", "pynput.keyboard",
            "--collect-all", "simple_websocket",
            "--collect-all", "engineio",
            "--collect-all", "flask_socketio",
            "--distpath", "dist",
            "--workpath", "build",
            "OBS多视角切换器.pyw",
        ],
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        print("[错误] PyInstaller 打包失败!")
        sys.exit(1)
    print("  PyInstaller 完成")


def run_iscc(new_ver):
    """执行 Inno Setup 编译"""
    print("\n[2/3] Inno Setup 编译安装包...")
    iscc = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    result = subprocess.run([iscc, INSTALLER_ISS], cwd=BASE_DIR)
    if result.returncode != 0:
        print("[错误] Inno Setup 编译失败!")
        sys.exit(1)
    print("  Inno Setup 完成")


def show_result(new_ver):
    """显示打包结果"""
    output_exe = os.path.join(BASE_DIR, "installer_output", f"OBS多视角切换器_安装包_v{new_ver}.exe")
    print("\n" + "=" * 50)
    print(f"  全部完成!  版本: v{new_ver}")
    print(f"  安装包: {output_exe}")
    print("=" * 50)


def main():
    print("=" * 50)
    print("  OBS多视角切换器 - 自动打包构建")
    print("=" * 50)

    # 1. 版本递增
    old_ver = read_version()
    new_ver = increment_version(old_ver)
    print(f"\n版本: {old_ver} → {new_ver}")

    # 2. 更新 installer.iss
    patch_installer_iss(old_ver, new_ver)

    # 3. PyInstaller
    run_pyinstaller()

    # 4. Inno Setup
    run_iscc(new_ver)

    # 5. 保存新版本
    write_version(new_ver)

    # 6. 显示结果
    show_result(new_ver)


if __name__ == "__main__":
    main()
