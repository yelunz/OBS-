"""沙盒测试：验证 B站监视器管线 + 截图 API"""
import subprocess, time, sys, os

BASE_DIR = r"C:\myobs"
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
TEST_URL = "https://live.bilibili.com/13308358"
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label} {detail}")
        failed += 1

# ============ 测试 1: streamlink 提取 B站流 ============
print("\n[测试1] streamlink 提取 B站流 URL")
try:
    r = subprocess.run(
        ["streamlink", TEST_URL, "best", "--stream-url", "--retry-max", "2"],
        capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW
    )
    url = r.stdout.decode().strip()
    check("streamlink 返回码=0", r.returncode == 0, f"returncode={r.returncode}")
    check("返回了流 URL", url.startswith("http"), f"url={url[:80]}...")
    print(f"  流 URL: {url[:100]}...")
except Exception as e:
    check("streamlink 无异常", False, str(e))

# ============ 测试 2: MediaMTX 端口监听 ============
print("\n[测试2] MediaMTX RTMP 端口 1935")
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(3)
    s.connect(("127.0.0.1", 1935))
    check("端口 1935 可连接", True)
    s.close()
except:
    check("端口 1935 可连接", False, "MediaMTX 未运行")

# ============ 测试 3: ffmpeg 推流到 player8 路径 ============
print("\n[测试3] ffmpeg 推流到 rtmp://localhost:1935/live/player8")
try:
    cmd = [
        FFMPEG, "-f", "lavfi", "-i", "color=c=red:s=320x240:d=5:r=10",
        "-f", "flv", "rtmp://localhost:1935/live/player8"
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(4)
    p.terminate()
    time.sleep(1)
    stderr = p.stderr.read().decode(errors="replace")
    # 检查是否成功推流（没有 "not configured" 错误）
    has_not_configured = "not configured" in stderr
    check("RTMP 路径 player8 被接受", not has_not_configured,
          "路径被拒绝" if has_not_configured else "推流成功")
    if has_not_configured:
        print(f"  MediaMTX 错误: {stderr[-300:]}")
except Exception as e:
    check("ffmpeg 推流无异常", False, str(e))

# ============ 测试 4: Python 语法完整性 ============
print("\n[测试4] manager_ui.pyw 语法检查")
try:
    import py_compile
    py_compile.compile(os.path.join(BASE_DIR, "manager_ui.pyw"), doraise=True)
    check("manager_ui.pyw 编译通过", True)
except py_compile.PyCompileError as e:
    check("manager_ui.pyw 编译通过", False, str(e))

# ============ 测试 5: Pillow 可用性 ============
print("\n[测试5] Pillow 模块可用")
try:
    from PIL import Image, ImageTk
    check("PIL.Image 导入", True)
    check("PIL.ImageTk 导入", True)
except:
    check("Pillow 可用", False, "请 pip install Pillow")

# ============ 测试 6: base64/io 导入 ============
print("\n[测试6] 截图相关标准库导入")
try:
    import base64, io
    check("base64 + io", True)
except:
    check("base64 + io", False)

# ============ 结果 ============
print(f"\n{'='*40}")
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 项")
if failed == 0:
    print("全部测试通过！")
else:
    print(f"有 {failed} 项失败，需要修复")
    sys.exit(1)