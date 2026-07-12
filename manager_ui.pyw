import json, os, subprocess, sys, time, threading, socket, collections, re, shutil, webbrowser, base64, io
import tkinter as tk
from tkinter import ttk, messagebox, Menu, scrolledtext
import customtkinter as ctk
from obswebsocket import obsws, requests
import psutil
from pynput import mouse, keyboard
import ctypes
from ctypes import wintypes
from web_remote import start_web_server

# ==================== 现代化 UI 主题 (shadcn/ui Dashboard 风格) ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 色彩常量
PAGE_BG = "#1E1E2E"       # 深紫灰底 - 亮度显著提升
CARD_BG = "#262636"       # 卡片背景 - 比页面稍亮
ELEVATED_BG = "#313146"   # 悬浮层/输入框
ACCENT = "#89B4FA"        # 柔蓝 - 猫ppuccin蓝
ACCENT_HOVER = "#74A8F0"  # 悬停蓝
SUCCESS = "#A6E3A1"       # 柔绿
WARNING = "#F9E2AF"       # 柔黄
DANGER = "#F38BA8"        # 柔红
TEXT_PRIMARY = "#CDD6F4"  # 主文字 - 高对比度
TEXT_SECONDARY = "#9399B2" # 次要文字
BORDER = "#45475A"        # 边框 - 清晰可见
SIDEBAR_BG = "#181825"    # 侧边栏 - 比页面深一点

# CTk 主题微调
def _apply_ctk_theme():
    from customtkinter import ThemeManager
    theme = ThemeManager.theme
    if "CTk" in theme:
        theme["CTk"]["fg_color"] = [PAGE_BG, PAGE_BG]
    if "CTkFrame" in theme:
        theme["CTkFrame"]["fg_color"] = [CARD_BG, CARD_BG]
        theme["CTkFrame"]["border_color"] = [BORDER, BORDER]
    if "CTkButton" in theme:
        theme["CTkButton"]["fg_color"] = [ACCENT, ACCENT]
        theme["CTkButton"]["hover_color"] = [ACCENT_HOVER, ACCENT_HOVER]
        theme["CTkButton"]["text_color"] = ["#FFFFFF", "#FFFFFF"]
    if "CTkLabel" in theme:
        theme["CTkLabel"]["text_color"] = [TEXT_PRIMARY, TEXT_PRIMARY]
    if "CTkEntry" in theme:
        theme["CTkEntry"]["fg_color"] = [ELEVATED_BG, ELEVATED_BG]
        theme["CTkEntry"]["border_color"] = [BORDER, BORDER]
        theme["CTkEntry"]["text_color"] = [TEXT_PRIMARY, TEXT_PRIMARY]
    if "CTkComboBox" in theme:
        theme["CTkComboBox"]["fg_color"] = [ELEVATED_BG, ELEVATED_BG]
        theme["CTkComboBox"]["border_color"] = [BORDER, BORDER]
        theme["CTkComboBox"]["text_color"] = [TEXT_PRIMARY, TEXT_PRIMARY]
        theme["CTkComboBox"]["button_color"] = [ACCENT, ACCENT]
        theme["CTkComboBox"]["button_hover_color"] = [ACCENT_HOVER, ACCENT_HOVER]
    if "CTkCheckBox" in theme:
        theme["CTkCheckBox"]["fg_color"] = [ACCENT, ACCENT]
        theme["CTkCheckBox"]["hover_color"] = [ACCENT_HOVER, ACCENT_HOVER]
        theme["CTkCheckBox"]["border_color"] = [BORDER, BORDER]
    if "CTkTextbox" in theme:
        theme["CTkTextbox"]["fg_color"] = [ELEVATED_BG, ELEVATED_BG]
        theme["CTkTextbox"]["border_color"] = [BORDER, BORDER]
        theme["CTkTextbox"]["text_color"] = [TEXT_PRIMARY, TEXT_PRIMARY]

_apply_ctk_theme()

def _apply_ttk_theme():
    """设置 ttk.Treeview 暗色主题样式"""
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview",
                    background=PAGE_BG,
                    foreground=TEXT_PRIMARY,
                    fieldbackground=PAGE_BG,
                    borderwidth=0,
                    font=("微软雅黑", 9))
    style.configure("Treeview.Heading",
                    background=CARD_BG,
                    foreground=TEXT_PRIMARY,
                    borderwidth=0,
                    font=("微软雅黑", 9, "bold"))
    style.map("Treeview",
              background=[("selected", ELEVATED_BG)],
              foreground=[("selected", TEXT_PRIMARY)])
    style.map("Treeview.Heading",
              background=[("active", ELEVATED_BG)])

_apply_ttk_theme()

# ==================== VLC 模块检测 ====================
VLC_AVAILABLE = False
try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    pass

# ==================== Pillow 模块检测（监视器截图用） ====================
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    pass

# ==================== 每次启动清空日志 ====================
LOG_FILE = os.path.join(r"C:\myobs", "debug.log")
try:
    open(LOG_FILE, "w").close()
except:
    pass

_log_file_lock = threading.Lock()

def file_log(msg):
    try:
        with _log_file_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

# ==================== 全局日志更新标记 ====================
_log_update_flag = False
player_logs = {}

def log(player_name, msg):
    global _log_update_flag
    if player_name not in player_logs:
        player_logs[player_name] = collections.deque(maxlen=500)
    timestamp = time.strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    player_logs[player_name].append(line)
    _log_update_flag = True
    file_log(f"[{player_name}] {msg}")

# ==================== OBS 控制 ====================
class OBSController:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connected = False
        self.scene_name = None

    def connect(self):
        try:
            self.ws = obsws(self.host, self.port, self.password)
            self.ws.connect()
            self.connected = True
            self.scene_name = self.ws.call(requests.GetCurrentProgramScene()).getSceneName()
            log("系统", "OBS 连接成功")
            return True, ""
        except Exception as e:
            self.connected = False
            log("系统", f"OBS 连接失败: {e}")
            return False, str(e)

    def disconnect(self):
        if self.ws:
            self.ws.disconnect()
            self.connected = False

    def source_exists(self, name):
        items = self.ws.call(requests.GetSceneItemList(sceneName=self.scene_name)).getSceneItems()
        return any(i["sourceName"] == name for i in items)

    def create_vlc(self, name, url):
        log("系统", f"创建 VLC 源: {name} URL: {url}")
        playlist = [{"value": url, "hidden": False}]
        settings = {
            "playlist": playlist,
            "loop": True,
            "shuffle": False,
            "network_caching": 400,
            "playback_behavior": "always_play"
        }
        try:
            self.ws.call(requests.CreateInput(
                sceneName=self.scene_name,
                inputName=name,
                inputKind="vlc_source",
                inputSettings=settings,
                sceneItemEnabled=False
            ))
            log("系统", f"CreateInput 成功: {name}")
        except Exception as e:
            log("系统", f"CreateInput 失败: {name} - {e}")
            return
        try:
            self.ws.call(requests.SetInputSettings(
                inputName=name,
                inputSettings={"playback_behavior": "always_play"},
                overlay=True
            ))
            log("系统", f"SetInputSettings (always_play) 成功: {name}")
        except Exception as e:
            log("系统", f"SetInputSettings 失败: {name} - {e}")
        self.ws.call(requests.SetInputMute(inputName=name, inputMuted=True))
        self.set_visibility(name, False)
        log("系统", f"VLC 源 {name} 已静音并隐藏")

    def update_vlc_url(self, name, url):
        log("系统", f"刷新 OBS 源: {name} 新 URL: {url}")
        try:
            cur = self.ws.call(requests.GetInputSettings(inputName=name)).getInputSettings()
            cur["playlist"] = [{"value": url, "hidden": False}]
            cur["playback_behavior"] = "always_play"
            self.ws.call(requests.SetInputSettings(inputName=name, inputSettings=cur, overlay=True))
            log("系统", f"刷新成功: {name}")
        except Exception as e:
            log("系统", f"刷新失败: {name} - {e}")

    def restart_vlc(self, name):
        try:
            self.ws.call(requests.TriggerMediaInputAction(
                inputName=name,
                mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
            ))
            log("系统", f"强制重启源成功: {name}")
            return True
        except Exception as e:
            log("系统", f"强制重启失败: {name} - {e}")
            return False

    def create_window_capture(self, name, window_title=""):
        settings = {
            "window": window_title,
            "capture_mode": "window",
            "priority": "title",
            "capture_audio": True
        }
        log("系统", f"创建窗口采集源: {name} 匹配窗口: '{window_title}'")
        try:
            self.ws.call(requests.CreateInput(
                sceneName=self.scene_name,
                inputName=name,
                inputKind="window_capture",
                inputSettings=settings,
                sceneItemEnabled=False
            ))
            self.ws.call(requests.SetInputAudioMonitorType(inputName=name, monitorType="none"))
            log("系统", f"窗口采集源创建成功: {name}")
        except Exception as e:
            log("系统", f"窗口采集源创建失败: {name} - {e}")

    def create_browser_source(self, name, url, width=1920, height=1080):
        """
        创建 OBS 浏览器源
        参数: 1920x1080 标准分辨率, reroute_audio=True 用于独立音频控制
        """
        log("系统", f"[创建浏览器源-步骤1] 开始为 {name} 创建浏览器源, URL: {url}")
        settings = {
            "url": url,
            "width": width,
            "height": height,
            "fps": 30,
            "reroute_audio": True,
            "restart_when_active": False,
            "shutdown": False,
        }
        try:
            self.ws.call(requests.CreateInput(
                sceneName=self.scene_name,
                inputName=name,
                inputKind="browser_source",
                inputSettings=settings,
                sceneItemEnabled=False
            ))
            log("系统", f"[创建浏览器源-步骤2-完成] 浏览器源 {name} 创建成功 ({width}x{height}, 音频独立路由)")
        except Exception as e:
            log("系统", f"[创建浏览器源-步骤2-失败] 浏览器源创建失败: {name} - {e}")

    def get_source_screenshot(self, name, width=480, height=270, quality=50):
        """
        获取 OBS 源的截图 (返回 base64 编码的 JPEG 字符串)
        用于监视器实时预览，降低分辨率以提高帧率
        """
        try:
            resp = self.ws.call(requests.GetSourceScreenshot(
                sourceName=name,
                imageFormat="jpeg",
                imageWidth=width,
                imageHeight=height,
                imageCompressionQuality=quality
            ))
            img_data = resp.getImageData()
            if img_data:
                return img_data  # base64 string, 去掉 "data:image/jpeg;base64," 前缀
            return None
        except Exception as e:
            # 截图失败不频繁打日志，避免刷屏
            return None

    def remove_source(self, name):
        try:
            self.ws.call(requests.RemoveInput(inputName=name))
            log("系统", f"删除源成功: {name}")
        except Exception as e:
            log("系统", f"删除源失败: {name} - {e}")

    def get_scene_item_map(self):
        items = self.ws.call(requests.GetSceneItemList(sceneName=self.scene_name)).getSceneItems()
        return {item["sourceName"]: {"id": item["sceneItemId"], "enabled": item["sceneItemEnabled"]} for item in items}

    def get_visible(self, name):
        m = self.get_scene_item_map()
        return m.get(name, {}).get("enabled", False)

    def set_visibility(self, name, visible):
        m = self.get_scene_item_map()
        if name in m:
            self.ws.call(requests.SetSceneItemEnabled(
                sceneName=self.scene_name,
                sceneItemId=m[name]["id"],
                sceneItemEnabled=visible
            ))

    def set_mute(self, source_name, mute):
        try:
            self.ws.call(requests.SetInputMute(inputName=source_name, inputMuted=mute))
        except:
            pass

    def rename_source(self, old_name, new_name):
        try:
            self.ws.call(requests.SetInputName(inputName=old_name, newInputName=new_name))
            log("系统", f"重命名源: {old_name} -> {new_name}")
            return True
        except Exception as e:
            log("系统", f"重命名失败: {old_name} -> {new_name} - {e}")
            return False

    def get_all_source_names(self):
        return list(self.get_scene_item_map().keys())

    def create_scene(self, name):
        try:
            self.ws.call(requests.CreateScene(sceneName=name))
            return True
        except:
            return False

    def remove_scene(self, name):
        try:
            self.ws.call(requests.RemoveScene(sceneName=name))
            return True
        except:
            return False

    def switch_scene(self, name):
        self.ws.call(requests.SetCurrentProgramScene(sceneName=name))
        self.scene_name = name

    def scene_exists(self, name):
        scenes = self.ws.call(requests.GetSceneList()).getScenes()
        return any(s["sceneName"] == name for s in scenes)

# ==================== 基础配置 ====================
BASE_DIR = r"C:\myobs"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
MEDIAMTX_EXE = os.path.join(BASE_DIR, "mediamtx.exe")
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
mediamtx_proc = None
AUTO_DETECT_INTERVAL = 120
DEDICATED_SCENE = "多视角切换"
DEFAULT_MAX_STREAMS = 6
DEFAULT_HOTKEY_MODIFIERS = "alt+shift"

# ==================== 进程管理 ====================
def read_stream_output(proc, prefix, player_name, obs_ref=None, stream_name=None):
    triggered = False
    def reader():
        nonlocal triggered
        try:
            for line in iter(proc.stdout.readline, b''):
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    log(player_name, f"{prefix}{decoded}")
                    if not triggered and "Output #0, flv, to '" in decoded:
                        triggered = True
                        log("系统", f"[刷新触发] 在 {player_name} 的输出中检测到流已开始推送")
                        if obs_ref:
                            found = False
                            for p in app.active_players:
                                if p.get("stream_name") == stream_name:
                                    src = p.get("obs_source_name")
                                    if src:
                                        log("系统", f"[刷新] 找到匹配选手 {p['name']}，源名称: {src}")
                                        log("系统", f"[刷新] 等待 2 秒后尝试重启源 {src}")
                                        time.sleep(2)
                                        log("系统", f"[刷新] 第一次尝试 update_vlc_url")
                                        obs_ref.update_vlc_url(src, f"rtmp://localhost:1935/live/{stream_name}")
                                        time.sleep(1)
                                        log("系统", f"[刷新] 第二次尝试 restart_vlc")
                                        if obs_ref.restart_vlc(src):
                                            log("系统", f"[刷新] 重启命令已发送")
                                        else:
                                            log("系统", f"[刷新] 重启命令失败")
                                    else:
                                        log("系统", f"[刷新] 选手 {p['name']} 的 obs_source_name 为空")
                                    found = True
                                    break
                            if not found:
                                log("系统", f"[刷新] 未找到 stream_name={stream_name} 的活跃选手")
        except:
            pass
    threading.Thread(target=reader, daemon=True).start()

def wait_for_mediamtx(host='localhost', port=1935, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except:
            time.sleep(0.5)
    return False

def start_stream(player, obs=None):
    pid = player["id"]
    sn = player.get("stream_name", f"player{pid}")
    rtmp = f"rtmp://localhost:1935/live/{sn}"
    plat = player.get("platform")
    qual = player.get("quality", "best")
    name = player["name"]

    global mediamtx_proc
    if not mediamtx_proc or mediamtx_proc.poll() is not None:
        start_mediamtx()
    wait_for_mediamtx()

    if plat == "twitch":
        twitch_input = player.get("twitch_url", "") or player.get("channel", "")
        if not twitch_input:
            return False
        if not twitch_input.startswith("http"):
            twitch_input = f"https://www.twitch.tv/{twitch_input}"
        cmd1 = ["streamlink", twitch_input, qual, "--retry-max", "5", "--retry-streams", "5", "-O"]
        cmd2 = [FFMPEG, "-re", "-i", "pipe:0", "-c", "copy", "-f", "flv", rtmp]
        p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        p1.stdout.close()
        player["stream_pid"] = p2.pid
        read_stream_output(p2, "", name, obs, sn)
    elif plat == "douyin":
        du = player.get("douyin_url", "")
        if not du:
            return False
        cmd = [FFMPEG, "-user_agent", "Mozilla/5.0", "-i", du, "-c", "copy", "-f", "flv", rtmp]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        player["stream_pid"] = p.pid
        read_stream_output(p, "", name, obs, sn)
    else:
        return False

    return True

def stop_stream(player):
    if player.get("stream_pid"):
        try:
            psutil.Process(player["stream_pid"]).terminate()
        except:
            pass
        player["stream_pid"] = None

def check_twitch_source(url):
    try:
        p = subprocess.run(f'streamlink {url} best --retry-max 0 --stream-url', shell=True, capture_output=True, timeout=10)
        return p.returncode == 0 and p.stdout.strip() != b""
    except:
        return False

def check_douyin_source(url):
    try:
        p = subprocess.run(f'"{FFPROBE}" -v quiet -print_format json -show_streams "{url}"', shell=True, capture_output=True, timeout=10)
        import json as j
        data = j.loads(p.stdout)
        return bool(data.get("streams"))
    except:
        return False

def check_source(player):
    plat = player["platform"]
    if plat == "twitch":
        url = player.get("twitch_url", "") or f"https://www.twitch.tv/{player.get('channel', '')}"
        if not url:
            return
        ok = check_twitch_source(url)
        player["source_ok"] = ok
    elif plat == "douyin":
        du = player.get("douyin_url", "")
        if not du:
            return
        ok = check_douyin_source(du)
        player["source_ok"] = ok

def start_mediamtx():
    global mediamtx_proc
    if mediamtx_proc and mediamtx_proc.poll() is None:
        return  # 已在运行，不重复启动
    # 先杀掉所有残留的 MediaMTX 进程，避免端口冲突
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "mediamtx" in proc.info["name"].lower():
                proc.kill()
                log("系统", f"[MediaMTX-清理] 已终止残留进程 PID={proc.info['pid']}")
        except:
            pass
    time.sleep(0.5)
    yml_path = os.path.join(BASE_DIR, "mediamtx.yml")
    # 始终生成全量路径 (player1-50)，覆盖所有可能的选手 ID
    paths = {}
    for i in range(1, 51):
        paths[f"live/player{i}"] = {"source": "publisher"}
    yml = "rtmpAddress: :1935\nhlsAddress: :8888\nhlsSegmentDuration: 1s\nhlsSegmentCount: 7\npaths:\n"
    for k, v in paths.items():
        yml += f'  "{k}": {{ source: publisher }}\n'
    with open(yml_path, "w", encoding="utf-8") as f:
        f.write(yml)
    log("系统", "[MediaMTX-启动] 已生成 YML 配置 (player1-50)")
    proc = subprocess.Popen([MEDIAMTX_EXE], cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    mediamtx_proc = proc
    read_stream_output(proc, "[MediaMTX] ", "MediaMTX")

def stop_mediamtx():
    global mediamtx_proc
    if mediamtx_proc and mediamtx_proc.poll() is None:
        mediamtx_proc.terminate()
        mediamtx_proc = None

def start_switcher():
    try:
        proc = subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "switcher.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        read_stream_output(proc, "[切换器] ", "Switcher")
        time.sleep(1)
        if proc.poll() is not None:
            log("系统", "警告: switcher.py 进程启动后立即退出")
        return proc
    except Exception as e:
        log("系统", f"启动 switcher.py 失败: {e}")
        return None

def get_all_stream_statuses(players):
    active = {}
    for p in players:
        if p.get("active") and p["platform"] in ("twitch",):
            pid = p.get("stream_pid")
            active[p["name"]] = pid and psutil.pid_exists(pid)
    return active

# ==================== 快速添加 ====================
def parse_clipboard_url(url_string):
    clip = url_string.strip()
    if not clip:
        return None
    douyin_stream_match = re.search(r'https?://(?:pull-flv-[a-z0-9]+\.douyincdn\.com|[\w-]+\.douyinliving\.com)/\S+', clip)
    if douyin_stream_match:
        return {"platform": "douyin", "douyin_url": douyin_stream_match.group(0), "browser_url": "", "name": "抖音选手", "hotkey": ""}
    douyin_match = re.search(r'https?://(?:live\.douyin|www\.douyin|lv\.douyin|v\.douyin)\.com/\S+', clip)
    if douyin_match:
        url = douyin_match.group(0)
        log("系统", f"[URL解析-步骤1] 检测到抖音直播间: {url}，将使用 Browser Source 直接打开")
        return {"platform": "douyin", "douyin_url": "", "browser_url": url, "name": "抖音选手", "hotkey": ""}
    bili_match = re.search(r'live\.bilibili\.com/(\d+)', clip)
    if bili_match:
        rid = bili_match.group(1)
        clean_url = f"https://live.bilibili.com/{rid}"
        return {"platform": "bilibili", "room_id": rid, "browser_url": clean_url, "name": f"B站{rid}", "hotkey": ""}
    twitch_match = re.search(r'twitch\.tv/([\w-]+)', clip)
    if twitch_match:
        ch = twitch_match.group(1)
        return {"platform": "twitch", "twitch_url": f"https://www.twitch.tv/{ch}", "name": ch, "hotkey": ""}
    if clip.startswith("http"):
        return {"platform": "custom_web", "browser_url": clip, "name": "自定义网页", "hotkey": ""}
    return None

def get_next_view_label(players):
    existing = set()
    for p in players:
        vl = p.get("view_label", 0)
        if isinstance(vl, int):
            existing.add(vl)
        elif isinstance(vl, str) and vl.isdigit():
            existing.add(int(vl))
    for i in range(1, 1000):
        if i not in existing:
            return i
    return None

def normalize_view_label(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0

# ==================== 编辑对话框 ====================
class PlayerDialog:
    def __init__(self, parent, players, current_player=None, prefill=None):
        self.top = ctk.CTkToplevel(parent)
        self.top.title("编辑选手" if current_player else "添加选手")
        self.result = None
        self.players = players
        self.current_player = current_player
        if prefill and not current_player:
            name = prefill.get("name", "")
            plat = prefill.get("platform", "bilibili")
            room_id = prefill.get("room_id", "")
            twitch_url = prefill.get("twitch_url", "")
            douyin_url = prefill.get("douyin_url", "")
            browser_url = prefill.get("browser_url", "")
        elif current_player:
            name = current_player["name"]
            plat = current_player["platform"]
            room_id = current_player.get("room_id", "")
            twitch_url = current_player.get("twitch_url", "") or current_player.get("channel", "")
            douyin_url = current_player.get("douyin_url", "")
            browser_url = current_player.get("browser_url", "")
        else:
            name = ""
            plat = "bilibili"
            room_id = ""
            twitch_url = ""
            douyin_url = ""
            browser_url = ""
        self.name_var = tk.StringVar(value=name)
        self.plat_var = tk.StringVar(value=plat)
        self.hotkey_var = tk.StringVar(value=current_player["hotkey"] if current_player else "")
        self.room_var = tk.StringVar(value=room_id)
        self.twitch_var = tk.StringVar(value=twitch_url)
        self.douyin_var = tk.StringVar(value=douyin_url)
        self.qual_var = tk.StringVar(value=current_player.get("quality", "best") if current_player else "best")
        self.url_var = tk.StringVar(value=browser_url)
        ctk.CTkLabel(self.top, text="显示名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ctk.CTkEntry(self.top, textvariable=self.name_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.top, text="快捷键 (单字符):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ctk.CTkEntry(self.top, textvariable=self.hotkey_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.top, text="平台:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        combo = ctk.CTkComboBox(self.top, variable=self.plat_var, values=["bilibili", "twitch", "douyin", "custom_web"], state="readonly")
        combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        combo.configure(command=self.on_plat)
        self.frame = ctk.CTkFrame(self.top, fg_color="transparent")
        self.frame.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        self.on_plat()
        ctk.CTkLabel(self.top, text="清晰度 (推流):").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ctk.CTkComboBox(self.top, variable=self.qual_var, values=["best", "worst", "720p60", "480p", "360p"], state="readonly").grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
        ctk.CTkButton(self.top, text="确定", command=self.ok).grid(row=5, column=0, columnspan=2, pady=10)

    def on_plat(self, event=None):
        for w in self.frame.winfo_children():
            w.destroy()
        p = self.plat_var.get()
        if p in ("bilibili", "custom_web"):
            ctk.CTkLabel(self.frame, text="房间号 (选填):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ctk.CTkEntry(self.frame, textvariable=self.room_var, width=20).grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkLabel(self.frame, text="完整URL:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
            ctk.CTkEntry(self.frame, textvariable=self.url_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        elif p == "twitch":
            ctk.CTkLabel(self.frame, text="频道名或完整URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ctk.CTkEntry(self.frame, textvariable=self.twitch_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        elif p == "douyin":
            ctk.CTkLabel(self.frame, text="直播间URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ctk.CTkEntry(self.frame, textvariable=self.douyin_var, width=50).grid(row=0, column=1, padx=5, pady=5)

    def ok(self):
        hotkey = self.hotkey_var.get().strip()
        if not self.name_var.get().strip() or not hotkey:
            messagebox.showwarning("错误", "请填写名称和快捷键", parent=self.top)
            return
        if len(hotkey) != 1 or not hotkey.isalnum():
            messagebox.showwarning("错误", "快捷键只能是单个字母或数字", parent=self.top)
            return
        for p in self.players:
            if p is self.current_player:
                continue
            if p.get("hotkey") == hotkey:
                messagebox.showwarning("错误", f"快捷键已被 {p['name']} 占用", parent=self.top)
                return
        self.result = {
            "name": self.name_var.get().strip(),
            "hotkey": hotkey,
            "platform": self.plat_var.get(),
            "room_id": self.room_var.get().strip(),
            "twitch_url": self.twitch_var.get().strip() if self.plat_var.get() == "twitch" else "",
            "douyin_url": self.douyin_var.get().strip() if self.plat_var.get() == "douyin" else "",
            "quality": self.qual_var.get(),
            "browser_url": self.url_var.get().strip() if self.plat_var.get() in ("bilibili", "custom_web") else (self.douyin_var.get().strip() if self.plat_var.get() == "douyin" else "")
        }
        self.top.destroy()

# ==================== OBS 登录框 ====================
class OBSLoginDialog:
    def __init__(self, parent, host="localhost", port=4455, password=""):
        self.top = ctk.CTkToplevel(parent)
        self.top.title("配置 OBS 连接")
        self.top.resizable(False, False)
        self.result = None
        ctk.CTkLabel(self.top, text="请填写 OBS WebSocket 服务器信息：", font=("微软雅黑", 10)).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5))
        ctk.CTkLabel(self.top, text="主机:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.host_var = tk.StringVar(value=host)
        ctk.CTkEntry(self.top, textvariable=self.host_var, width=20).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.top, text="端口:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.IntVar(value=port)
        ctk.CTkEntry(self.top, textvariable=self.port_var, width=20).grid(row=2, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.top, text="密码:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.pwd_var = tk.StringVar(value=password)
        ctk.CTkEntry(self.top, textvariable=self.pwd_var, width=20, show="*").grid(row=3, column=1, padx=5, pady=5)
        btn_frame = ctk.CTkFrame(self.top, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="连接", command=self.ok).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="取消", command=self.top.destroy).pack(side=tk.LEFT, padx=10)
        self.top.grab_set()
        parent.wait_window(self.top)

    def ok(self):
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get())
        except:
            messagebox.showwarning("错误", "端口必须是数字", parent=self.top)
            return
        if not host:
            messagebox.showwarning("错误", "主机不能为空", parent=self.top)
            return
        self.result = (host, port, self.pwd_var.get())
        self.top.destroy()

# ==================== 监视器窗口 ====================
class MonitorWindow:
    def __init__(self, parent_app):
        self.app = parent_app
        self.win = ctk.CTkToplevel(parent_app.root)
        self.win.title("多视角监控")
        self.win.geometry("960x600")
        self.win.minsize(400, 300)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        self.players = []
        self.grid_widgets = {}
        self.vlc_instances = {}
        self.paused_players = {}
        self.vlc_instance = None
        self.mouse_listener = None
        self.columns = 3
        self.cell_width = 300
        self.cell_height = 200
        self.empty_label = None

        # B站监视器管线 (streamlink + ffmpeg → RTMP)
        self.bilibili_procs = {}      # name -> (p1, p2) subprocess
        # 截图监视器 (抖音/自定义网页)
        self.screenshot_canvases = {}  # name -> canvas
        self.screenshot_frames = {}    # name -> bytes (latest JPEG frame)
        self.screenshot_running = {}   # name -> bool
        self.screenshot_lock = threading.Lock()
        self.screenshot_render_id = None

        if VLC_AVAILABLE:
            try:
                self.vlc_instance = vlc.Instance("--no-audio", "--intf", "dummy", "--vout", "directx")
            except:
                self.vlc_instance = None

        toolbar = ctk.CTkFrame(self.win, fg_color=CARD_BG, corner_radius=8)
        toolbar.pack(fill=tk.X, side=tk.TOP, pady=2)
        ctk.CTkButton(toolbar, text="🔄 刷新所有", command=self.refresh_all, corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side=tk.LEFT, padx=5)

        self.container = ttk.Frame(self.win)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.empty_label = ctk.CTkLabel(self.container, text="暂无推流", font=("微软雅黑", 16), text_color=TEXT_SECONDARY)
        self._start_mouse_listener()
        self.win.bind("<Configure>", self._on_resize)
        self.after_id = None
        self.refresh()

    def _on_resize(self, event):
        if self.after_id:
            self.win.after_cancel(self.after_id)
        self.after_id = self.win.after(100, self.refresh)

    def _calculate_layout(self):
        n = len(self.players)
        if n == 0:
            return 1, 100, 100
        width = self.container.winfo_width() - 20
        height = self.container.winfo_height() - 20
        if width < 100 or height < 100:
            width, height = 960, 600
        best_cols = 1
        best_area = 0
        for cols in range(1, n + 1):
            rows = (n + cols - 1) // cols
            cell_w = width // cols
            cell_h = height // rows
            area = cell_w * cell_h
            if area > best_area:
                best_area = area
                best_cols = cols
        cols = best_cols
        rows = (n + cols - 1) // cols
        cell_w = width // cols
        cell_h = height // rows
        return cols, cell_w, cell_h

    def refresh(self):
        active = [p for p in self.app.active_players if p.get("active") and p["platform"] in ("twitch", "bilibili", "douyin", "custom_web")]
        old_names = {p["name"] for p in self.players}
        new_names = {p["name"] for p in active}

        for name in old_names - new_names:
            self._hide_grid(name)
        for name in new_names - old_names:
            player = next(p for p in active if p["name"] == name)
            self._show_grid(player)
        self.players = active
        self._reposition_cells()

        if self.players:
            if self.empty_label:
                self.empty_label.place_forget()
        else:
            if self.empty_label:
                self.empty_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _reposition_cells(self):
        if not self.players:
            return
        cols, cell_w, cell_h = self._calculate_layout()
        self.columns = cols
        self.cell_width = cell_w
        self.cell_height = cell_h

        for idx, player in enumerate(self.players):
            name = player["name"]
            if name not in self.grid_widgets:
                continue
            row = idx // cols
            col = idx % cols
            x = 10 + col * cell_w
            y = 10 + row * cell_h
            frame, canvas, label = self.grid_widgets[name]
            frame.place(x=x, y=y, width=cell_w, height=cell_h)
            label_height = 25
            canvas.place(x=0, y=0, width=cell_w, height=cell_h - label_height)
            label.place(x=0, y=cell_h - label_height, width=cell_w, height=label_height)

    def _show_grid(self, player):
        name = player["name"]
        plat = player["platform"]
        log("系统", f"[监视器-显示-步骤1] 平台={plat}, 选手={name}")

        if name in self.paused_players:
            data = self.paused_players.pop(name)
            frame, canvas, label = data["frame"], data["canvas"], data["label"]
            self.grid_widgets[name] = (frame, canvas, label)
            mp = data.get("mp")
            if mp:
                try:
                    mp.play()
                except:
                    pass
            log("系统", f"[监视器-显示-步骤2] 从暂停恢复: {name}")
            # B站恢复后需重启管线
            if plat == "bilibili":
                self._start_bilibili_pipeline(name, canvas)
            return

        if name in self.grid_widgets:
            return

        frame = ttk.Frame(self.container, borderwidth=1, relief=tk.SUNKEN)
        canvas = tk.Canvas(frame, bg=PAGE_BG)
        name_label = tk.Label(frame, text=name, bg=ELEVATED_BG, fg=TEXT_PRIMARY, font=("微软雅黑", 9))
        frame.place(x=0, y=0, width=100, height=100)
        canvas.place(x=0, y=0, width=100, height=75)
        name_label.place(x=0, y=75, width=100, height=25)
        self.grid_widgets[name] = (frame, canvas, name_label)
        log("系统", f"[监视器-显示-步骤3] 创建网格: {name}")

        if plat == "twitch":
            # Twitch: VLC 播放已有 RTMP 流
            if name not in self.vlc_instances:
                default_sn = f"player{player['id']}"
                stream_name = player.get("stream_name", default_sn)
                rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
                self.win.after(2000, self._start_vlc, name, canvas, rtmp_url)
                log("系统", f"[监视器-显示-Twitch] 安排 VLC 启动: {name} -> {rtmp_url}")

        elif plat == "bilibili":
            # B站: streamlink + ffmpeg → RTMP → VLC
            if name not in self.vlc_instances:
                self._start_bilibili_pipeline(name, canvas)
                log("系统", f"[监视器-显示-B站] 启动 streamlink 管线: {name}")

        elif plat in ("douyin", "custom_web"):
            # 抖音/自定义网页: OBS 截图轮询
            if PIL_AVAILABLE:
                self._start_screenshot_monitor(name, canvas)
                log("系统", f"[监视器-显示-截图] 启动截图轮询: {name}")
            else:
                log("系统", f"[监视器-显示-截图-失败] Pillow 未安装，无法截图预览: {name}")
                canvas.create_text(150, 100, text="Pillow 未安装", fill="gray", font=("微软雅黑", 10))

    def _hide_grid(self, name):
        if name not in self.grid_widgets:
            return
        frame, canvas, label = self.grid_widgets.pop(name)
        frame.place_forget()
        log("系统", f"[监视器-隐藏] 隐藏网格: {name}")

        # 停止 B站管线
        if name in self.bilibili_procs:
            self._stop_bilibili_pipeline(name)

        # 停止截图轮询
        if name in self.screenshot_running:
            self._stop_screenshot_monitor(name)

        if name in self.vlc_instances:
            inst, mp, _ = self.vlc_instances[name]
            try:
                mp.pause()
            except:
                pass
            self.paused_players[name] = {
                "frame": frame, "canvas": canvas, "label": label,
                "inst": inst, "mp": mp, "canvas_widget": canvas
            }
        else:
            frame.destroy()

    def _start_vlc(self, name, canvas, url):
        if not self.vlc_instance or not self.win.winfo_exists():
            return
        if name in self.vlc_instances:
            return
        try:
            canvas.update_idletasks()
            hwnd = canvas.winfo_id()
            if not hwnd:
                return
            media = self.vlc_instance.media_new(url)
            media.add_option(":network-caching=300")
            media.add_option(":no-audio")
            mp = self.vlc_instance.media_player_new()
            mp.set_media(media)
            mp.set_hwnd(hwnd)
            mp.play()
            self.vlc_instances[name] = (self.vlc_instance, mp, canvas)
        except Exception as e:
            log("系统", f"监视器启动失败 {name}: {e}")

    def _retry_vlc(self, name, canvas, url):
        """兜底重试：检查 VLC 是否在播放，若未播放则重新连接"""
        if name not in self.vlc_instances:
            log("系统", f"[监视器-VLC重试] {name} VLC 实例不存在，跳过")
            return
        if not self.win.winfo_exists():
            return
        try:
            _, mp, _ = self.vlc_instances[name]
            if not mp.is_playing():
                log("系统", f"[监视器-VLC重试] {name} 未在播放，重新连接 RTMP")
                mp.stop()
                media = self.vlc_instance.media_new(url)
                media.add_option(":network-caching=300")
                media.add_option(":no-audio")
                mp.set_media(media)
                mp.set_hwnd(canvas.winfo_id())
                mp.play()
            else:
                log("系统", f"[监视器-VLC重试] {name} 已在播放，无需重试")
        except Exception as e:
            log("系统", f"[监视器-VLC重试] {name} 重试异常: {e}")

    # ==================== B站监视器管线 ====================
    def _start_bilibili_pipeline(self, name, canvas):
        """启动 B站 streamlink + ffmpeg → RTMP 管线"""
        log("系统", f"[监视器-B站-步骤1] 查找选手 {name} 的 URL")
        player = next((p for p in self.app.active_players if p["name"] == name), None)
        if not player:
            log("系统", f"[监视器-B站-失败] 未找到活跃选手: {name}")
            return
        url = player.get("browser_url", "")
        if not url:
            log("系统", f"[监视器-B站-失败] {name} 没有 browser_url")
            return

        stream_name = player.get("stream_name", f"player{player['id']}")
        rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
        log("系统", f"[监视器-B站-步骤2] URL={url}, RTMP={rtmp_url}")

        # 确保 MediaMTX 运行（由主程序管理，此处仅检查）
        global mediamtx_proc
        if not mediamtx_proc or mediamtx_proc.poll() is not None:
            log("系统", f"[监视器-B站-步骤3] MediaMTX 未运行，等待主程序启动")
            wait_for_mediamtx()
        else:
            log("系统", f"[监视器-B站-步骤3] MediaMTX 已在运行")

        try:
            log("系统", f"[监视器-B站-步骤4] 启动 streamlink + ffmpeg 管线")
            cmd1 = ["streamlink", url, "best", "--retry-max", "5", "--retry-streams", "5", "-O"]
            cmd2 = [FFMPEG, "-re", "-i", "pipe:0", "-c", "copy", "-f", "flv", rtmp_url]
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            p1.stdout.close()
            self.bilibili_procs[name] = (p1, p2)
            log("系统", f"[监视器-B站-步骤5] 管线已启动: {name}")
        except Exception as e:
            log("系统", f"[监视器-B站-失败] 启动管线异常: {name} - {e}")
            return

        # 延迟启动 VLC（等待管线推流稳定，B站流需要约4-5秒）
        self.win.after(6000, self._start_vlc, name, canvas, rtmp_url)
        # 兜底重试：如果流未就绪导致 VLC 连接失败，10秒后重试
        self.win.after(10000, self._retry_vlc, name, canvas, rtmp_url)
        log("系统", f"[监视器-B站-步骤6] 安排 VLC 启动 (6s) + 兜底重试 (10s): {name}")

    def _stop_bilibili_pipeline(self, name):
        """停止 B站 streamlink 管线"""
        log("系统", f"[监视器-B站-停止] 停止管线: {name}")
        if name in self.bilibili_procs:
            p1, p2 = self.bilibili_procs.pop(name)
            for proc in (p1, p2):
                try:
                    proc.terminate()
                except:
                    pass
            log("系统", f"[监视器-B站-停止] 管线已终止: {name}")

    # ==================== 截图监视器 (抖音/自定义网页) ====================
    def _start_screenshot_monitor(self, name, canvas):
        """启动 OBS 截图轮询线程"""
        log("系统", f"[监视器-截图-步骤1] 开始截图轮询: {name}")
        self.screenshot_canvases[name] = canvas
        self.screenshot_running[name] = True
        t = threading.Thread(target=self._screenshot_thread, args=(name,), daemon=True)
        t.start()
        log("系统", f"[监视器-截图-步骤2] 截图线程已启动: {name}")
        # 启动渲染循环（如果尚未启动）
        self._ensure_screenshot_render_loop()

    def _stop_screenshot_monitor(self, name):
        """停止截图轮询"""
        log("系统", f"[监视器-截图-停止] 停止截图轮询: {name}")
        self.screenshot_running[name] = False
        self.screenshot_canvases.pop(name, None)
        with self.screenshot_lock:
            self.screenshot_frames.pop(name, None)

    def _screenshot_thread(self, name):
        """截图轮询线程: 持续调用 GetSourceScreenshot，存储最新帧"""
        log("系统", f"[监视器-截图-线程] 线程启动: {name}")
        fail_count = 0
        while self.screenshot_running.get(name, False) and self.win.winfo_exists():
            try:
                obs = self.app.obs
                if not obs or not obs.connected:
                    time.sleep(0.5)
                    continue

                # 获取选手的 OBS 源名称
                player = next((p for p in self.app.active_players if p["name"] == name), None)
                if not player:
                    time.sleep(0.5)
                    continue
                src_name = player.get("obs_source_name", "")
                if not src_name:
                    time.sleep(0.5)
                    continue

                # 调用截图 API (480x270, JPEG 质量 50)
                img_b64 = obs.get_source_screenshot(src_name, 480, 270, 50)
                if img_b64:
                    # 去掉可能的 data:image/jpeg;base64, 前缀
                    if img_b64.startswith("data:"):
                        img_b64 = img_b64.split(",", 1)[-1]
                    img_bytes = base64.b64decode(img_b64)
                    with self.screenshot_lock:
                        self.screenshot_frames[name] = img_bytes
                    fail_count = 0
                else:
                    fail_count += 1
                    if fail_count == 1:
                        log("系统", f"[监视器-截图-线程] {name} 截图返回空 (源可能尚未就绪)")
            except Exception as e:
                fail_count += 1
                if fail_count == 1:
                    log("系统", f"[监视器-截图-线程] {name} 截图异常: {e}")

            # 约 30fps (33ms)
            time.sleep(0.033)

        log("系统", f"[监视器-截图-线程] 线程退出: {name}")

    def _ensure_screenshot_render_loop(self):
        """确保截图渲染循环在运行"""
        if self.screenshot_render_id is not None:
            return
        self._screenshot_render_loop()

    def _screenshot_render_loop(self):
        """主线程渲染循环: 每 33ms 将最新截图帧渲染到 Canvas"""
        if not self.win.winfo_exists():
            self.screenshot_render_id = None
            return

        with self.screenshot_lock:
            items = list(self.screenshot_frames.items())

        for name, img_bytes in items:
            canvas = self.screenshot_canvases.get(name)
            if not canvas or not canvas.winfo_exists():
                with self.screenshot_lock:
                    self.screenshot_frames.pop(name, None)
                continue
            try:
                w = canvas.winfo_width()
                h = canvas.winfo_height()
                if w > 1 and h > 1:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    # 保持宽高比缩放 (letterbox)
                    img_w, img_h = pil_img.size
                    scale = min(w / img_w, h / img_h)
                    new_w, new_h = int(img_w * scale), int(img_h * scale)
                    pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(pil_img)
                    canvas.delete("all")
                    # 居中绘制
                    x = (w - new_w) // 2
                    y = (h - new_h) // 2
                    canvas.create_image(x, y, anchor=tk.NW, image=photo)
                    # 保持引用防止 GC
                    canvas._photo_ref = photo
            except Exception:
                pass

        # 继续渲染循环
        if self.screenshot_canvases:
            self.screenshot_render_id = self.win.after(33, self._screenshot_render_loop)
        else:
            self.screenshot_render_id = None

    def refresh_all(self):
        log("系统", "[监视器-刷新所有] 停止所有 VLC 实例")
        for name in list(self.vlc_instances.keys()):
            _, mp, _ = self.vlc_instances.pop(name)
            try:
                mp.stop()
                mp.release()
            except:
                pass
        # 停止所有 B站管线
        for name in list(self.bilibili_procs.keys()):
            self._stop_bilibili_pipeline(name)
        # 停止所有截图轮询
        for name in list(self.screenshot_running.keys()):
            self._stop_screenshot_monitor(name)
        self.refresh()

    def _start_mouse_listener(self):
        def on_click(x, y, button, pressed):
            if not pressed or button != mouse.Button.left:
                return True
            if not self.win.winfo_exists():
                return True
            rel_x = x - self.container.winfo_rootx()
            rel_y = y - self.container.winfo_rooty()
            cols = self.columns
            if cols <= 0:
                return True
            for idx, player in enumerate(self.players):
                row = idx // cols
                col = idx % cols
                x0 = 10 + col * self.cell_width
                y0 = 10 + row * self.cell_height
                if x0 <= rel_x <= x0 + self.cell_width and y0 <= rel_y <= y0 + self.cell_height:
                    self.app.root.after(0, self.app.switch_to, player)
                    break
            return True
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def on_close(self):
        log("系统", "[监视器-关闭] 开始清理资源")
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        # 停止截图渲染循环
        if self.screenshot_render_id:
            self.win.after_cancel(self.screenshot_render_id)
            self.screenshot_render_id = None
        # 停止所有截图轮询线程
        for name in list(self.screenshot_running.keys()):
            self._stop_screenshot_monitor(name)
        # 停止所有 B站管线
        for name in list(self.bilibili_procs.keys()):
            self._stop_bilibili_pipeline(name)
        # 停止所有 VLC 实例
        for name in list(self.vlc_instances.keys()):
            _, mp, _ = self.vlc_instances[name]
            try:
                mp.stop()
                mp.release()
            except:
                pass
        self.vlc_instances.clear()
        for name in list(self.paused_players.keys()):
            data = self.paused_players[name]
            try:
                if "mp" in data:
                    data["mp"].stop()
                    data["mp"].release()
            except:
                pass
            data["frame"].destroy()
        self.paused_players.clear()
        self.screenshot_canvases.clear()
        self.screenshot_frames.clear()
        self.bilibili_procs.clear()
        self.win.destroy()
        log("系统", "[监视器-关闭] 资源清理完成")

    def update_if_open(self):
        if self.win and self.win.winfo_exists():
            self.refresh()

# ==================== 带复选框的 Treeview ====================
class CheckboxTreeview(ttk.Treeview):
    def __init__(self, parent, columns, checkbox_col="#1", **kwargs):
        super().__init__(parent, columns=columns, selectmode="browse", **kwargs)
        self.checkbox_col = checkbox_col
        self.checked = set()
        self.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        region = self.identify_region(event.x, event.y)
        if region != "cell":
            return
        column = self.identify_column(event.x)
        if column != self.checkbox_col:
            return
        item = self.identify_row(event.y)
        if not item:
            return
        if item in self.checked:
            self.checked.remove(item)
        else:
            self.checked.add(item)
        self._update_checkbox(item)
        self._refresh_tag()

    def _update_checkbox(self, item):
        values = list(self.item(item, "values"))
        if item in self.checked:
            values[0] = "☑"
        else:
            values[0] = "☐"
        self.item(item, values=values)

    def insert(self, parent, index, **kwargs):
        kwargs.setdefault("values", ["☐"])
        item = super().insert(parent, index, **kwargs)
        self._update_checkbox(item)
        return item

    def _refresh_tag(self):
        for child in self.get_children():
            self.item(child, tags=())
        for item in self.checked:
            if self.exists(item):
                self.item(item, tags=("checked",))
        self.tag_configure("checked", background="#a0d2ff")

    def get_checked_names(self):
        names = []
        for item in self.checked:
            if self.exists(item):
                vals = self.item(item, "values")
                if len(vals) >= 2:
                    names.append(vals[1])
        return names

    def set_checked_by_name(self, names):
        self.checked.clear()
        for child in self.get_children():
            if self.exists(child):
                vals = self.item(child, "values")
                if len(vals) >= 2 and vals[1] in names:
                    self.checked.add(child)
        for child in self.get_children():
            if self.exists(child):
                self._update_checkbox(child)
        self._refresh_tag()

    def clear_checked(self):
        self.checked.clear()
        for child in self.get_children():
            if self.exists(child):
                values = list(self.item(child, "values"))
                values[0] = "☐"
                self.item(child, values=values)
        self._refresh_tag()

# ==================== 主界面 ====================
class ManagerApp:
    def __init__(self, root):
        global app
        app = self
        self.root = root
        self.root.title("多视角切换管理器 Pro")
        self.players = []
        self.active_players = []
        self.next_id = 1
        self.obs = None
        self.max_streams = DEFAULT_MAX_STREAMS
        self.hotkey_modifiers = DEFAULT_HOTKEY_MODIFIERS
        self._drag_data = {"player": None, "source_widget": None}
        self.stream_status_cache = {}
        self.switcher_proc = None
        self.drag_label = None
        self.auto_detect = tk.BooleanVar(value=True)
        self.data_lock = threading.Lock()
        self.current_log_player = tk.StringVar(value="系统")
        self.status_var = tk.StringVar(value="就绪")
        self.original_scene = None
        self.monitor_window = None
        self.pool_label = None
        self.first_run = not os.path.exists(CONFIG_FILE)
        self.load_cfg()
        self.create_widgets()
        self.refresh_store_tree()
        self._update_log_combo()
        if self.first_run or not self.obs_host:
            self.show_obs_login()
        self.root.after(100, self.async_connect_obs)
        self._cleanup_edge_profiles()
        self.refresh_loop()
        self.start_status_monitor()
        self.start_log_consumer()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(2000, self.all_start)

        # 启动 Web 远程控制服务器
        def _start_web():
            url = start_web_server(self)
            log("系统", f"[Web遥控] 服务器已启动: {url}")
        self.root.after(3000, _start_web)

    def load_cfg(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            log("系统", "配置文件加载成功")
        except FileNotFoundError:
            cfg = {"obs_host": "localhost", "obs_port": 4455, "obs_password": "", "players": [], "max_active_streams": DEFAULT_MAX_STREAMS, "hotkey_modifiers": DEFAULT_HOTKEY_MODIFIERS}
            log("系统", "配置文件不存在，创建默认配置")
        except json.JSONDecodeError:
            backup = CONFIG_FILE + ".backup"
            if os.path.exists(backup):
                with open(backup, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                log("系统", "配置文件损坏，已从备份恢复")
            else:
                cfg = {"obs_host": "localhost", "obs_port": 4455, "obs_password": "", "players": [], "max_active_streams": DEFAULT_MAX_STREAMS, "hotkey_modifiers": DEFAULT_HOTKEY_MODIFIERS}
                log("系统", "配置文件损坏且无备份，使用默认配置")
        except Exception as e:
            cfg = {"obs_host": "localhost", "obs_port": 4455, "obs_password": "", "players": [], "max_active_streams": DEFAULT_MAX_STREAMS, "hotkey_modifiers": DEFAULT_HOTKEY_MODIFIERS}
            log("系统", f"读取配置文件异常: {e}")

        self.obs_host = cfg.get("obs_host", "localhost")
        self.obs_port = cfg.get("obs_port", 4455)
        self.obs_pwd = cfg.get("obs_password", "")
        self.max_streams = cfg.get("max_active_streams", DEFAULT_MAX_STREAMS)
        self.hotkey_modifiers = cfg.get("hotkey_modifiers", DEFAULT_HOTKEY_MODIFIERS)

        players_raw = cfg.get("players", [])
        self.players = []
        self.active_players = []
        max_id = 0
        for p in players_raw:
            pid = p.get("id", 0)
            if not pid:
                max_id += 1
                pid = max_id
            else:
                max_id = max(max_id, pid)
            player_obj = {
                "id": pid,
                "name": p.get("name", ""),
                "hotkey": p.get("hotkey", ""),
                "platform": p.get("platform", "bilibili"),
                "room_id": p.get("room_id", ""),
                "twitch_url": p.get("twitch_url", "") or p.get("channel", ""),
                "douyin_url": p.get("douyin_url", ""),
                "quality": p.get("quality", "best"),
                "browser_url": p.get("browser_url", ""),
                "view_label": normalize_view_label(p.get("view_label", 0)),
                "stream_name": p.get("stream_name", f"player{pid}"),
                "obs_source_name": p.get("obs_source_name", ""),
                "active": False,
                "source_ok": None,
                "stream_pid": None,
                "window_title": f"OBS_Window_{p.get('name', '')}"
            }
            self.players.append(player_obj)
            if player_obj["obs_source_name"]:
                self.active_players.append(player_obj)
        self.next_id = max_id + 1
        self.reorder_all_view_labels()
        self.save_config()

    def reorder_all_view_labels(self):
        if not self.players:
            return
        sorted_p = sorted(self.players, key=lambda p: (isinstance(p["view_label"], int), p["view_label"] if isinstance(p["view_label"], int) else 9999))
        for idx, p in enumerate(sorted_p, start=1):
            if p["view_label"] != idx:
                p["view_label"] = idx
                p["obs_source_name"] = f"{p['name']}_{idx}_{p['hotkey']}"

    def async_connect_obs(self):
        def _connect():
            self.obs = OBSController(self.obs_host, self.obs_port, self.obs_pwd)
            ok, err = self.obs.connect()
            self.root.after(0, lambda: self._on_obs_connected(ok, err))
        threading.Thread(target=_connect, daemon=True).start()

    def _on_obs_connected(self, ok, err):
        if ok:
            self.original_scene = self.obs.scene_name
            self.obs_status_label.configure(text="✅ OBS 已连接", text_color=SUCCESS)
            self.setup_scene()
            self.refresh_ui()
        else:
            self.obs_status_label.configure(text="⚠ OBS 断开", text_color=DANGER)

    def setup_scene(self):
        if not self.obs or not self.obs.connected:
            return
        try:
            if not self.obs.scene_exists(DEDICATED_SCENE):
                self.obs.create_scene(DEDICATED_SCENE)
            if self.obs.scene_name != DEDICATED_SCENE:
                self.obs.switch_scene(DEDICATED_SCENE)
        except Exception as e:
            log("系统", f"场景设置失败: {e}")

    def create_widgets(self):
        """构建 Broadcast Control Console 界面"""
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        self._create_header()       # row 0, col 0-1
        self._create_sidebar()      # row 1, col 0
        self._create_content()      # row 1, col 1
        self._create_statusbar()    # row 2, col 0-1

        self._show_page("dashboard")

    # ==================== Header ====================
    def _create_header(self):
        header = ctk.CTkFrame(self.root, fg_color=SIDEBAR_BG, corner_radius=0, height=48)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        # 品牌区
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side=tk.LEFT, padx=(16, 0))
        ctk.CTkLabel(brand, text="◈", font=("微软雅黑", 20), text_color=ACCENT).pack(side=tk.LEFT)
        ctk.CTkLabel(brand, text="  OBS MultiView", font=("微软雅黑", 13, "bold"),
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(6, 0))

        # 右侧状态区
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side=tk.RIGHT, padx=(0, 12))

        self.obs_status_label = ctk.CTkLabel(right, text="● OBS 未连接", text_color=TEXT_SECONDARY,
                                             font=("微软雅黑", 10))
        self.obs_status_label.pack(side=tk.RIGHT, padx=(0, 12))

        ctk.CTkButton(right, text="⚙", width=32, height=32, corner_radius=6,
                      fg_color="transparent", hover_color=ELEVATED_BG,
                      text_color=TEXT_SECONDARY, font=("微软雅黑", 14),
                      command=self.show_settings).pack(side=tk.RIGHT)

        return header

    # ==================== Sidebar ====================
    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self.root, fg_color=SIDEBAR_BG, corner_radius=0, width=200)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(4, weight=1)

        nav_items = [
            ("dashboard", "仪表盘", "📊"),
            ("players",   "选手管理", "👥"),
            ("monitor",   "监视器", "🖥"),
            ("logs",      "日志", "📋"),
        ]

        self._nav_buttons = {}
        for i, (key, label, icon) in enumerate(nav_items):
            btn = ctk.CTkButton(sidebar, text=f"  {icon}  {label}",
                                anchor="w", fg_color="transparent",
                                hover_color=ELEVATED_BG, text_color=TEXT_SECONDARY,
                                font=("微软雅黑", 11), corner_radius=8,
                                height=36, command=lambda k=key: self._show_page(k))
            btn.grid(row=i, column=0, sticky="ew", padx=8, pady=2)
            self._nav_buttons[key] = btn

        # 底部 Web 遥控信息
        sep = ctk.CTkFrame(sidebar, fg_color=BORDER, height=1, corner_radius=0)
        sep.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))

        web_info = ctk.CTkFrame(sidebar, fg_color="transparent")
        web_info.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkLabel(web_info, text="Web 遥控", font=("微软雅黑", 9),
                     text_color=TEXT_SECONDARY).pack(anchor="w")
        ctk.CTkLabel(web_info, text="localhost:5000", font=("微软雅黑", 9, "bold"),
                     text_color=ACCENT).pack(anchor="w")

        return sidebar

    # ==================== Content Area ====================
    def _create_content(self):
        self._content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self._content_frame.grid(row=1, column=1, sticky="nsew")
        self._content_frame.columnconfigure(0, weight=1)
        self._content_frame.rowconfigure(0, weight=1)

        self._pages = {}
        self._pages["dashboard"] = self._create_dashboard_page()
        self._pages["players"]   = self._create_players_page()
        self._pages["monitor"]   = self._create_monitor_page()
        self._pages["logs"]      = self._create_logs_page()

    # ==================== Dashboard Page ====================
    def _create_dashboard_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=0)  # stats
        page.rowconfigure(1, weight=0)  # current view
        page.rowconfigure(2, weight=1)  # pool + actions

        # ── Stats Row ──
        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="stats")

        stats_data = [
            ("活跃选手", "0", "📡"),
            ("OBS 状态", "未连接", "🔌"),
            ("当前视角", "无", "🎯"),
            ("快捷键", "0", "⌨"),
        ]
        self._stat_labels = {}
        self._stat_values = {}
        for i, (title, val, icon) in enumerate(stats_data):
            card = ctk.CTkFrame(stats, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
            ctk.CTkLabel(inner, text=icon, font=("微软雅黑", 16)).pack(anchor="w")
            ctk.CTkLabel(inner, text=title, font=("微软雅黑", 9),
                         text_color=TEXT_SECONDARY).pack(anchor="w", pady=(2, 0))
            val_lbl = ctk.CTkLabel(inner, text=val, font=("微软雅黑", 22, "bold"), text_color=ACCENT)
            val_lbl.pack(anchor="w", pady=(2, 0))
            self._stat_values[title] = val_lbl

        # ── Current View Card ──
        cur_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=BORDER)
        cur_card.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        cur_inner = ctk.CTkFrame(cur_card, fg_color="transparent")
        cur_inner.pack(fill=tk.BOTH, padx=20, pady=16)
        ctk.CTkLabel(cur_inner, text="当前播出视角", font=("微软雅黑", 9),
                     text_color=TEXT_SECONDARY).pack(anchor="w")
        self.cur_label = ctk.CTkLabel(cur_inner, text="无", font=("微软雅黑", 24, "bold"),
                                      text_color=ACCENT)
        self.cur_label.pack(anchor="w", pady=(4, 0))

        # ── Pool + Actions ──
        bottom = ctk.CTkFrame(page, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=0)

        # Pool list
        pool_frame = ctk.CTkFrame(bottom, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        pool_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        pool_inner = ctk.CTkFrame(pool_frame, fg_color="transparent")
        pool_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        self.pool_label = ctk.CTkLabel(pool_inner, text="活跃池", font=("微软雅黑", 10, "bold"),
                                       text_color=TEXT_PRIMARY)
        self.pool_label.pack(anchor="w")
        self.pool_list = tk.Listbox(pool_inner, bg=PAGE_BG, fg=TEXT_PRIMARY,
                                    selectbackground=ACCENT, selectforeground="#FFFFFF",
                                    font=("微软雅黑", 10), activestyle="none",
                                    borderwidth=0, highlightthickness=0)
        self.pool_list.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        # Action buttons
        actions = ctk.CTkFrame(bottom, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew")

        btn_specs = [
            ("添加选手", self.add, ACCENT, ACCENT_HOVER),
            ("快速添加", self.quick_add, ACCENT, ACCENT_HOVER),
            ("批量导入", self.bulk_import_window, ELEVATED_BG, CARD_BG),
            ("批量▸视角", self.batch_move_to_active, ELEVATED_BG, CARD_BG),
            ("上源", self.batch_activate, SUCCESS, "#8BCF8A"),
            ("下源", self.batch_deactivate, DANGER, "#E07A8A"),
            ("重连OBS", self.reconnect_obs, ELEVATED_BG, CARD_BG),
            ("重启服务", self.restart_services, ELEVATED_BG, CARD_BG),
            ("监视器", self.toggle_monitor, ELEVATED_BG, CARD_BG),
            ("帮助", self.show_help, ELEVATED_BG, CARD_BG),
        ]

        row1 = ctk.CTkFrame(actions, fg_color="transparent")
        row1.pack(fill=tk.X, pady=(0, 3))
        row2 = ctk.CTkFrame(actions, fg_color="transparent")
        row2.pack(fill=tk.X)

        for i, (text, cmd, fg, hov) in enumerate(btn_specs[:5]):
            ctk.CTkButton(row1, text=text, command=cmd, corner_radius=7,
                          fg_color=fg, hover_color=hov, text_color="#FFFFFF" if fg != ELEVATED_BG else TEXT_PRIMARY,
                          font=("微软雅黑", 10), height=30).pack(side=tk.LEFT, padx=(0, 4))
        for i, (text, cmd, fg, hov) in enumerate(btn_specs[5:]):
            ctk.CTkButton(row2, text=text, command=cmd, corner_radius=7,
                          fg_color=fg, hover_color=hov, text_color="#FFFFFF" if fg != ELEVATED_BG else TEXT_PRIMARY,
                          font=("微软雅黑", 10), height=30).pack(side=tk.LEFT, padx=(0, 4))

        # Auto-detect checkbox
        auto_frame = ctk.CTkFrame(actions, fg_color="transparent")
        auto_frame.pack(fill=tk.X, pady=(4, 0))
        ctk.CTkCheckBox(auto_frame, text="自动检测推流状态", variable=self.auto_detect,
                        font=("微软雅黑", 9), text_color=TEXT_SECONDARY,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        border_color=BORDER, checkmark_color="#FFFFFF").pack(side=tk.LEFT)

        return page

    # ==================== Players Page ====================
    def _create_players_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.rowconfigure(0, weight=6)
        page.rowconfigure(1, weight=4)
        page.columnconfigure(0, weight=1)

        # ── 选手仓库 (上) ──
        store_section = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        store_section.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))

        store_header = ctk.CTkFrame(store_section, fg_color="transparent")
        store_header.pack(fill=tk.X, padx=12, pady=(10, 4))
        ctk.CTkLabel(store_header, text="选手仓库", font=("微软雅黑", 11, "bold"),
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        for t, cmd in [("添加", self.add), ("快速", self.quick_add), ("导入", self.bulk_import_window)]:
            ctk.CTkButton(store_header, text=t, command=cmd, corner_radius=6,
                          fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                          font=("微软雅黑", 9), height=26, width=52).pack(side=tk.RIGHT, padx=(0, 4))

        store_scroll = ctk.CTkScrollableFrame(store_section, fg_color="transparent")
        store_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.store_tree = CheckboxTreeview(store_scroll, columns=("sel", "name", "platform", "status", "key"),
                                             checkbox_col="#1", show="headings")
        self.store_tree.pack(fill=tk.BOTH, expand=True)
        self.store_tree.bind("<Button-3>", self.on_store_right_click)

        # ── 视角列表 (下) ──
        active_section = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        active_section.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

        active_header = ctk.CTkFrame(active_section, fg_color="transparent")
        active_header.pack(fill=tk.X, padx=12, pady=(10, 4))
        ctk.CTkLabel(active_header, text="视角列表", font=("微软雅黑", 11, "bold"),
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        for t, cmd in [("上源", self.batch_activate), ("下源", self.batch_deactivate), ("▸视角", self.batch_move_to_active)]:
            fg = SUCCESS if t == "上源" else (DANGER if t == "下源" else ELEVATED_BG)
            hv = "#8BCF8A" if t == "上源" else ("#E07A8A" if t == "下源" else ACCENT_HOVER)
            tc = "#FFFFFF" if t in ("上源", "下源") else TEXT_PRIMARY
            ctk.CTkButton(active_header, text=t, command=cmd, corner_radius=6,
                          fg_color=fg, hover_color=hv, text_color=tc,
                          font=("微软雅黑", 9), height=26, width=52).pack(side=tk.RIGHT, padx=(0, 4))

        active_scroll = ctk.CTkScrollableFrame(active_section, fg_color="transparent")
        active_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.active_tree = CheckboxTreeview(active_scroll, columns=("sel", "name", "platform", "source", "status", "key"),
                                              checkbox_col="#1", show="headings")
        self.active_tree.pack(fill=tk.BOTH, expand=True)
        self.active_tree.bind("<Button-3>", self.on_active_right_click)

        return page

    # ==================== Monitor Page ====================
    def _create_monitor_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=BORDER,
                         width=400, height=300)
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ctk.CTkLabel(card, text="🖥", font=("微软雅黑", 48)).pack(pady=(30, 0))
        ctk.CTkLabel(card, text="多视角监控", font=("微软雅黑", 18, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(8, 4))
        ctk.CTkLabel(card, text="实时查看所有活跃选手的直播画面\n支持 B站 / Twitch / 抖音 / 自定义网页",
                     font=("微软雅黑", 10), text_color=TEXT_SECONDARY, justify="center").pack(pady=(0, 16))

        ctk.CTkButton(card, text="打开监视器", command=self.toggle_monitor,
                      corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#FFFFFF", font=("微软雅黑", 12, "bold"),
                      height=40, width=180).pack(pady=(0, 12))

        srvc = ctk.CTkFrame(card, fg_color="transparent")
        srvc.pack(pady=(0, 20))
        ctk.CTkButton(srvc, text="重连 OBS", command=self.reconnect_obs, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=("微软雅黑", 10), height=28, width=100).pack(side=tk.LEFT, padx=4)
        ctk.CTkButton(srvc, text="重启服务", command=self.restart_services, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=("微软雅黑", 10), height=28, width=100).pack(side=tk.LEFT, padx=4)

        return page

    # ==================== Logs Page ====================
    def _create_logs_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.rowconfigure(0, weight=0)
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        # Filter bar
        filter_bar = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        filter_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkLabel(filter_bar, text="日志", font=("微软雅黑", 11, "bold"),
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=12, pady=8)
        ctk.CTkLabel(filter_bar, text="筛选:", font=("微软雅黑", 9),
                     text_color=TEXT_SECONDARY).pack(side=tk.LEFT, padx=(0, 4))
        self.log_combo = ctk.CTkComboBox(filter_bar, variable=self.current_log_player,
                                         state="readonly", values=["系统"], width=140,
                                         font=("微软雅黑", 9), fg_color=ELEVATED_BG,
                                         border_color=BORDER, button_color=ACCENT,
                                         button_hover_color=ACCENT_HOVER,
                                         dropdown_fg_color=CARD_BG, dropdown_text_color=TEXT_PRIMARY)
        self.log_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.log_combo.configure(command=lambda v: self._refresh_log_view())
        self.log_combo.set("系统")

        ctk.CTkCheckBox(filter_bar, text="自动检测", variable=self.auto_detect,
                        font=("微软雅黑", 9), text_color=TEXT_SECONDARY,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        border_color=BORDER, checkmark_color="#FFFFFF").pack(side=tk.RIGHT, padx=12)

        # Log viewer
        log_container = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        log_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

        self.log_text = ctk.CTkTextbox(log_container, font=("Consolas", 10),
                                       fg_color="transparent", text_color=TEXT_PRIMARY,
                                       border_width=0, wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

        return page

    # ==================== StatusBar ====================
    def _create_statusbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=SIDEBAR_BG, corner_radius=0, height=28)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)

        ctk.CTkLabel(bar, textvariable=self.status_var, anchor="w",
                     text_color=TEXT_SECONDARY, font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=12)

        # 右侧指示器
        ctk.CTkLabel(bar, text="localhost:5000", text_color=ACCENT,
                     font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=(0, 12))
        ctk.CTkLabel(bar, text="▸", text_color=TEXT_SECONDARY,
                     font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=(0, 4))

        return bar

    def _show_page(self, name):
        """切换主内容区页面"""
        for page_name, page in self._pages.items():
            page.grid_remove()
        if name in self._pages:
            self._pages[name].grid()
        for btn_name, btn in self._nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=ACCENT, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

    # ---------- 辅助获取勾选 ----------
    def get_selected_store_players(self):
        names = self.store_tree.get_checked_names()
        return [p for p in self.players if p["name"] in names]

    def get_selected_active_players(self):
        names = self.active_tree.get_checked_names()
        return [p for p in self.active_players if p["name"] in names]

    def batch_move_to_active(self):
        selected = self.get_selected_store_players()
        if not selected:
            messagebox.showinfo("提示", "请先在仓库中勾选选手")
            return
        for player in selected:
            self.move_to_active(player)
        self.store_tree.clear_checked()
        self.set_status(f"已添加 {len(selected)} 个选手到视角列表")

    def batch_activate(self):
        selected = self.get_selected_active_players()
        if not selected:
            messagebox.showinfo("提示", "请先在视角列表中勾选选手")
            return
        to_activate = [p for p in selected if p["platform"] in ("twitch",) and not p["active"]]
        if not to_activate:
            messagebox.showinfo("提示", "所选选手无需上源或平台不支持")
            return
        current_active = sum(1 for p in self.active_players if p.get("active"))
        free = self.max_streams - current_active
        if len(to_activate) > free:
            messagebox.showwarning("限制", f"活跃池剩余 {free} 个名额，只能上源 {free} 个选手")
            to_activate = to_activate[:free]
        for player in to_activate:
            self.activate_player(player)
        self.active_tree.clear_checked()
        self.set_status(f"已上源 {len(to_activate)} 个选手")

    def batch_deactivate(self):
        selected = self.get_selected_active_players()
        if not selected:
            messagebox.showinfo("提示", "请先在视角列表中勾选选手")
            return
        to_deactivate = [p for p in selected if p["platform"] in ("twitch",) and p["active"]]
        for player in to_deactivate:
            self.deactivate_player(player)
        self.active_tree.clear_checked()
        self.set_status(f"已下源 {len(to_deactivate)} 个选手")

    def refresh_store_tree(self):
        checked_names = self.store_tree.get_checked_names()
        self.store_tree.delete(*self.store_tree.get_children())
        for p in sorted(self.players, key=lambda x: x["hotkey"]):
            self.store_tree.insert("", tk.END, values=("☐", p["name"], p["platform"], "📦 仓库中", p["hotkey"]))
        self.store_tree.set_checked_by_name(checked_names)

    def one_click_activate(self, player):
        if player["platform"] not in ("twitch",):
            messagebox.showinfo("提示", "该平台不支持直接上源")
            return
        self.move_to_active(player)
        self.activate_player(player)

    def move_to_active(self, player):
        if not self.obs or not self.obs.connected:
            messagebox.showwarning("提示", "OBS 未连接")
            return
        with self.data_lock:
            if player in self.active_players:
                return
            self.active_players.append(player)
        player["active"] = True
        if player["platform"] in ("bilibili", "douyin", "custom_web", "twitch"):
            self.sync_player(player)
        self.save_config()
        self._update_log_combo()
        self.refresh_ui()

    def move_to_store(self, player):
        if not self.obs or not self.obs.connected:
            return
        with self.data_lock:
            if player not in self.active_players:
                return
        def do_move():
            if self.get_current_display_name() == player["name"]:
                if player.get("obs_source_name"):
                    self.obs.set_visibility(player["obs_source_name"], False)
                    self.obs.set_mute(player["obs_source_name"], True)
            # 浏览器源不需要额外静音，OBS 原生 mute 已处理
            stop_stream(player)
            if player["obs_source_name"]:
                self.obs.remove_source(player["obs_source_name"])
            with self.data_lock:
                if player in self.active_players:
                    self.active_players.remove(player)
            player["active"] = False
            player["obs_source_name"] = ""
            self.save_config()
            self._update_log_combo()
            self.root.after(0, self.refresh_ui)
        threading.Thread(target=do_move, daemon=True).start()

    def on_store_right_click(self, event):
        item = self.store_tree.identify_row(event.y)
        if item:
            name = self.store_tree.item(item, "values")[1]
            player = self.find_player_in_any(name)
            if player:
                menu = Menu(self.root, tearoff=0)
                menu.add_command(label="✏ 编辑", command=lambda: self.edit_player(player))
                menu.add_command(label="🗑 删除", command=lambda: self.delete_player(player))
                menu.add_separator()
                if player["platform"] in ("bilibili", "custom_web"):
                    menu.add_command(label="🌐 打开直播间", command=lambda: self.open_player_url(player))
                menu.add_command(label="📥 添加到视角列表", command=lambda: self.move_to_active(player))
                if player["platform"] in ("twitch",):
                    menu.add_command(label="🚀 一键上源", command=lambda: self.one_click_activate(player))
                menu.post(event.x_root, event.y_root)

    def on_active_right_click(self, event):
        item = self.active_tree.identify_row(event.y)
        if item:
            name = self.active_tree.item(item, "values")[1]
            player = self.find_player_in_any(name)
            if player:
                menu = Menu(self.root, tearoff=0)
                menu.add_command(label="✏ 编辑", command=lambda: self.edit_player(player))
                if player["platform"] in ("twitch",):
                    if player.get("active"):
                        menu.add_command(label="⏸ 下源", command=lambda: self.deactivate_player(player))
                    else:
                        menu.add_command(label="▶ 上源", command=lambda: self.activate_player(player))
                    menu.add_separator()
                    menu.add_command(label="🔄 刷新源", command=lambda: self.refresh_player(player))
                    menu.add_command(label="🔍 检测源", command=lambda: self.detect_source(player))
                else:
                    menu.add_command(label="🌐 打开直播间", command=lambda: self.open_player_url(player))
                menu.add_separator()
                menu.add_command(label="📤 移回仓库", command=lambda: self.move_to_store(player))
                menu.add_command(label="🎥 切换到此视角", command=lambda: self.switch_to(player))
                batch_menu = Menu(menu, tearoff=0)
                selected = self.get_selected_active_players()
                if selected:
                    batch_menu.add_command(label="批量上源", command=self.batch_activate)
                    batch_menu.add_command(label="批量下源", command=self.batch_deactivate)
                    batch_menu.add_command(label="批量移回仓库", command=lambda: [self.move_to_store(p) for p in selected])
                menu.add_cascade(label="📋 批量操作", menu=batch_menu)
                menu.post(event.x_root, event.y_root)

    # ---------- 核心操作 ----------
    def activate_player(self, player):
        if player["platform"] not in ("twitch",) or player.get("active"):
            return
        if not self.obs or not self.obs.connected:
            messagebox.showwarning("提示", "OBS 未连接，无法上源")
            return
        active_count = sum(1 for p in self.active_players if p.get("active"))
        if active_count >= self.max_streams:
            messagebox.showwarning("限制", f"活跃池已满 (最多{self.max_streams}个)")
            return
        player["active"] = True
        log("系统", f"激活选手 {player['name']}，开始创建源并启动推流")
        self.sync_player(player)
        self.save_config()
        def do_start():
            log("系统", f"启动推流线程: {player['name']}")
            if not start_stream(player, self.obs):
                time.sleep(2)
                if not start_stream(player, self.obs):
                    self.stream_status_cache[player["name"]] = False
                    log("系统", f"推流启动失败: {player['name']}")
            self.root.after(0, self.refresh_ui)
        threading.Thread(target=do_start, daemon=True).start()
        self.refresh_ui()

    def deactivate_player(self, player):
        if player["platform"] not in ("twitch",):
            return
        if self.get_current_display_name() == player["name"]:
            if player.get("obs_source_name"):
                self.obs.set_visibility(player["obs_source_name"], False)
                self.obs.set_mute(player["obs_source_name"], True)
        player["active"] = False
        stop_stream(player)
        self.refresh_ui()

    def switch_to(self, player):
        if not self.obs or not self.obs.connected:
            return
        cur_name = self.get_current_display_name()
        if cur_name == player["name"]:
            return

        src_name = player.get("obs_source_name")
        if not src_name or not self.obs.source_exists(src_name):
            log("系统", f"切换失败，源不存在: {src_name}")
            return

        # 静音并隐藏所有其他源（统一处理所有平台）
        with self.data_lock:
            for p in self.active_players:
                if p.get("obs_source_name") and p["obs_source_name"] != src_name:
                    self.obs.set_mute(p["obs_source_name"], True)
                    self.obs.set_visibility(p["obs_source_name"], False)

        # 显示并取消静音目标源
        self.obs.set_visibility(src_name, True)
        self.obs.set_mute(src_name, False)
        log("系统", f"切换视角至 {player['name']}")

        self.current_log_player.set(player["name"])
        self.root.after(1, self.refresh_ui)

    def refresh_player(self, player):
        if player["platform"] not in ("twitch",):
            return
        if not player.get("active"):
            self.activate_player(player)
            return
        self.deactivate_player(player)
        def delayed_activate():
            time.sleep(2)
            self.activate_player(player)
        threading.Thread(target=delayed_activate, daemon=True).start()

    # ---------- 通用方法 ----------
    def find_player_in_any(self, name):
        for p in self.players:
            if p["name"] == name:
                return p
        return None

    def get_current_display_name(self):
        if not self.obs or not self.obs.connected:
            return None
        for p in self.active_players:
            if p.get("obs_source_name") and self.obs.get_visible(p["obs_source_name"]):
                return p["name"]
        return None

    def sync_player(self, player):
        if not self.obs or not self.obs.connected:
            return
        plat = player["platform"]

        # ---------- Twitch: 保持 VLC 源 (RTMP 推流) ----------
        if plat == "twitch":
            desired = f"{player['name']}_{player['view_label']}_{player['hotkey']}"
            old = player.get("obs_source_name")
            if old and self.obs.source_exists(old):
                if old != desired:
                    if self.obs.source_exists(desired):
                        self.obs.remove_source(desired)
                    if not self.obs.rename_source(old, desired):
                        self.obs.remove_source(old)
                        self.obs.create_vlc(desired, f"rtmp://localhost:1935/live/{player['stream_name']}")
            elif not self.obs.source_exists(desired):
                self.obs.create_vlc(desired, f"rtmp://localhost:1935/live/{player['stream_name']}")
            player["obs_source_name"] = desired
            log("系统", f"sync_player 完成: {player['name']} -> {desired} (推流)")

        # ---------- B站 / 抖音 / 自定义网页: 统一使用 Browser Source ----------
        elif plat in ("bilibili", "douyin", "custom_web"):
            desired = f"{player['name']}_{player['view_label']}_{player['hotkey']}"
            # 获取浏览器 URL: 优先用 browser_url, 兜底用 douyin_url
            url = player.get("browser_url", "") or player.get("douyin_url", "")
            if not url:
                log("系统", f"[sync_player-失败] 选手 {player['name']} 没有 browser_url，无法创建浏览器源")
                return
            old = player.get("obs_source_name")
            log("系统", f"[sync_player-步骤1] 选手 {player['name']} 平台={plat}, URL={url}")
            if old and self.obs.source_exists(old):
                if old != desired:
                    if self.obs.source_exists(desired):
                        self.obs.remove_source(desired)
                    if not self.obs.rename_source(old, desired):
                        self.obs.remove_source(old)
                        self.obs.create_browser_source(desired, url)
            elif not self.obs.source_exists(desired):
                log("系统", f"[sync_player-步骤2] 创建浏览器源: {desired}")
                self.obs.create_browser_source(desired, url)
            player["obs_source_name"] = desired
            log("系统", f"[sync_player-完成] {player['name']} -> {desired} (浏览器源)")

    def _cleanup_edge_profiles(self):
        profiles_dir = os.path.join(BASE_DIR, "edge_profiles")
        if not os.path.isdir(profiles_dir):
            return
        current_ids = {str(p["id"]) for p in self.players}
        for folder_name in os.listdir(profiles_dir):
            if folder_name.startswith("player"):
                if folder_name[6:] not in current_ids:
                    try:
                        shutil.rmtree(os.path.join(profiles_dir, folder_name))
                    except:
                        pass

    # ---------- UI 刷新 ----------
    def refresh_ui(self):
        if not self.obs or not self.obs.connected:
            self.refresh_store_tree()
            self._update_log_combo()
            return

        existing = self.obs.get_all_source_names()
        cur_name = self.get_current_display_name()
        self.cur_label.configure(text=cur_name or "无")

        with self.data_lock:
            to_remove = [p for p in self.active_players if p.get("obs_source_name") and p["obs_source_name"] not in existing and not (p["name"] == cur_name)]
            for p in to_remove:
                self.active_players.remove(p)

        self.refresh_store_tree()

        checked_names = self.active_tree.get_checked_names()

        self.active_tree.delete(*self.active_tree.get_children())
        for p in sorted(self.active_players, key=lambda x: (isinstance(x["view_label"], int), x["view_label"])):
            plat = p["platform"]
            status = "运行中"
            if plat in ("twitch",):
                if p.get("active"):
                    alive = self.stream_status_cache.get(p["name"], True)
                    status = "● 推流中" if alive else "✕ 推流中断"
                else:
                    ok = p.get("source_ok")
                    if ok is True:
                        status = "✅ 源可播放"
                    elif ok is False:
                        status = "❌ 源不可用"
                    else:
                        status = "⏸ 未检测"
            elif plat in ("bilibili", "douyin", "custom_web"):
                status = "🌐 网页"
            if cur_name == p["name"]:
                status = "★ 当前视角"
            self.active_tree.insert("", tk.END, values=("☐", p["name"], plat, p.get("obs_source_name", ""), status, p["hotkey"]))

        self.active_tree.set_checked_by_name(checked_names)

        self.pool_list.delete(0, tk.END)
        for p in self.active_players:
            if p.get("active"):
                self.pool_list.insert(tk.END, f"{p['name']} ({p['view_label']})")

        self._update_log_combo()
        self._update_monitor()

    def _update_monitor(self):
        if self.monitor_window:
            self.monitor_window.update_if_open()

    # ---------- 其他 UI 方法 ----------
    def add(self):
        dlg = PlayerDialog(self.root, self.players)
        self.root.wait_window(dlg.top)
        if dlg.result:
            self._commit_new_player(dlg.result)

    def quick_add(self):
        try:
            clip = self.root.clipboard_get().strip()
        except:
            return
        if not clip:
            return
        self.set_status("正在解析链接...")
        def do_parse():
            prefill = parse_clipboard_url(clip)
            if prefill:
                self.root.after(0, lambda: self._finish_quick_add(prefill))
            else:
                self.root.after(0, lambda: messagebox.showwarning("解析失败", "无法识别"))
        threading.Thread(target=do_parse, daemon=True).start()

    def _finish_quick_add(self, prefill):
        dlg = PlayerDialog(self.root, self.players, None, prefill=prefill)
        self.root.wait_window(dlg.top)
        if dlg.result:
            self._commit_new_player(dlg.result)

    def _commit_new_player(self, data):
        p = data
        p["id"] = self.next_id
        self.next_id += 1
        p["view_label"] = get_next_view_label(self.players)
        p["stream_name"] = f"player{p['id']}"
        p["active"] = False
        p["source_ok"] = None
        p["stream_pid"] = None
        p["obs_source_name"] = ""
        p["window_title"] = f"OBS_Window_{p['name']}"
        with self.data_lock:
            self.players.append(p)
        self.restart_services()
        self.save_config()
        self._update_log_combo()
        self.refresh_ui()

    def edit_player(self, player):
        dlg = PlayerDialog(self.root, self.players, player)
        self.root.wait_window(dlg.top)
        if dlg.result:
            for k, v in dlg.result.items():
                player[k] = v
            if player in self.active_players:
                self.sync_player(player)
            self.save_config()
            self._update_log_combo()
            self.refresh_ui()

    def delete_player(self, player):
        with self.data_lock:
            if player in self.active_players:
                if self.get_current_display_name() == player["name"]:
                    if player.get("obs_source_name"):
                        self.obs.set_visibility(player["obs_source_name"], False)
                        self.obs.set_mute(player["obs_source_name"], True)
                self.stop_process(player)
                if player["obs_source_name"]:
                    self.obs.remove_source(player["obs_source_name"])
                self.active_players.remove(player)
            self.players.remove(player)
        self.restart_services()
        self.save_config()
        self._update_log_combo()
        self.refresh_ui()

    def open_player_url(self, player):
        url = player.get("browser_url", "")
        if url:
            webbrowser.open(url)

    def detect_source(self, player):
        threading.Thread(target=lambda: (check_source(player), self.root.after(0, self.refresh_ui)), daemon=True).start()

    # ---------- 日志与状态 ----------
    def _update_log_combo(self):
        names = ["系统"] + [p["name"] for p in self.players] + ["MediaMTX", "Switcher"]
        self.log_combo.configure(values=names)
        if self.current_log_player.get() not in names:
            self.current_log_player.set("系统")

    def _refresh_log_view(self):
        if not hasattr(self, 'log_text'):
            return
        target = self.current_log_player.get()
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        if target in player_logs:
            for line in player_logs[target]:
                self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def start_log_consumer(self):
        def updater():
            global _log_update_flag
            while True:
                if _log_update_flag:
                    _log_update_flag = False
                    self.root.after(0, self._refresh_log_view)
                time.sleep(0.8)
        threading.Thread(target=updater, daemon=True).start()

    def start_status_monitor(self):
        def monitor():
            while True:
                if self.auto_detect.get():
                    with self.data_lock:
                        snapshot = [p for p in self.active_players if p["platform"] in ("twitch",) and not p["active"]]
                    for p in snapshot:
                        check_source(p)
                time.sleep(AUTO_DETECT_INTERVAL)
        threading.Thread(target=monitor, daemon=True).start()

    def refresh_loop(self):
        if self.obs and self.obs.connected:
            self.refresh_ui()
        self.root.after(2000, self.refresh_loop)

    def set_status(self, m, t=3000):
        self.status_var.set(m)
        self.root.after(t, lambda: self.status_var.set("就绪"))

    # ---------- 系统操作 ----------
    def all_start(self):
        if not self.obs or not self.obs.connected:
            return
        self.setup_scene()
        if not mediamtx_proc or mediamtx_proc.poll() is not None:
            start_mediamtx()
        self.switcher_proc = start_switcher()

    def all_stop(self):
        if self.switcher_proc:
            self.switcher_proc.terminate()
        for p in self.active_players:
            self.stop_process(p)
        stop_mediamtx()
        if self.monitor_window:
            self.monitor_window.on_close()

    def start_process(self, player):
        if player["platform"] in ("twitch",) and player.get("active"):
            url = f"rtmp://localhost:1935/live/{player['stream_name']}"
            if not self.obs.source_exists(player["obs_source_name"]):
                self.obs.create_vlc(player["obs_source_name"], url)
            else:
                self.obs.update_vlc_url(player["obs_source_name"], url)
            start_stream(player, self.obs)

    def stop_process(self, player):
        if player["platform"] in ("twitch",) and player.get("active"):
            stop_stream(player)

    def restart_services(self):
        if self.switcher_proc:
            self.switcher_proc.terminate()
        stop_mediamtx()
        start_mediamtx()
        self.switcher_proc = start_switcher()

    def reconnect_obs(self):
        def _reconnect():
            dlg = OBSLoginDialog(self.root, self.obs_host, self.obs_port, self.obs_pwd)
            if dlg.result:
                self.obs_host, self.obs_port, self.obs_pwd = dlg.result
                self.save_config()
                self.root.after(0, self.async_connect_obs)
        threading.Thread(target=_reconnect, daemon=True).start()

    def toggle_monitor(self):
        if self.monitor_window and self.monitor_window.win.winfo_exists():
            self.monitor_window.win.destroy()
            self.monitor_window = None
        else:
            if not VLC_AVAILABLE:
                messagebox.showwarning("缺少依赖", "监控功能需要 python-vlc 模块。\npip install python-vlc")
                return
            self.monitor_window = MonitorWindow(self)

    def show_settings(self):
        top = ctk.CTkToplevel(self.root)
        top.title("系统设置")
        top.resizable(False, False)
        top.grab_set()
        ctk.CTkLabel(top, text="最大活跃推流数:", font=("微软雅黑", 10)).grid(row=0, column=0, padx=10, pady=(10, 5), sticky=tk.W)
        var_streams = tk.IntVar(value=self.max_streams)
        ctk.CTkEntry(top, textvariable=var_streams, width=10).grid(row=0, column=1, padx=10, pady=(10, 5))
        ctk.CTkLabel(top, text="快捷键修饰键:", font=("微软雅黑", 10)).grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        modifier_values = ["alt+shift", "alt", "ctrl+shift"]
        var_mod = tk.StringVar(value=self.hotkey_modifiers)
        combo = ctk.CTkComboBox(top, variable=var_mod, values=modifier_values, state="readonly", width=10)
        combo.grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(top, text="(保存后自动重启服务生效)", text_color=TEXT_SECONDARY).grid(row=2, column=0, columnspan=2, pady=(0, 10))

        def save():
            try:
                val = int(var_streams.get())
                if val < 1:
                    raise ValueError
            except:
                messagebox.showwarning("错误", "请输入正整数")
                return
            self.max_streams = val
            self.hotkey_modifiers = var_mod.get()
            if self.pool_label:
                self.pool_label.configure(text=f"活跃池 (最多{val}个)")
            self.save_config()
            self.restart_services()
            top.destroy()
            self.set_status(f"设置已更新，服务已重启")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        ctk.CTkButton(btn_frame, text="保存", command=save).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="取消", command=top.destroy).pack(side=tk.LEFT, padx=10)
        self.root.wait_window(top)

    def show_help(self):
        help_text = "帮助内容省略"
        top = ctk.CTkToplevel(self.root)
        top.title("使用帮助")
        top.geometry("500x300")
        text = ctk.CTkTextbox(top, wrap="word")
        text.insert(tk.END, help_text)
        text.configure(state="disabled")
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ctk.CTkButton(top, text="关闭", command=top.destroy).pack(pady=(0, 10))

    def bulk_import_window(self):
        top = ctk.CTkToplevel(self.root)
        top.title("批量导入选手")
        top.geometry("600x500")
        top.resizable(True, True)
        lbl = ctk.CTkLabel(top, text="请粘贴链接或频道名，每行一个：", font=("微软雅黑", 10))
        lbl.pack(padx=10, pady=(10, 5), anchor=tk.W)
        text_area = ctk.CTkTextbox(top, wrap="word", font=("Consolas", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        status_var = tk.StringVar(value="就绪")
        status_label = ctk.CTkLabel(top, textvariable=status_var, text_color=TEXT_SECONDARY)
        status_label.pack(padx=10, pady=5, anchor=tk.W)

        def process_import():
            content = text_area.get("1.0", tk.END).strip()
            if not content:
                messagebox.showwarning("提示", "文本为空")
                return
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                messagebox.showwarning("提示", "没有有效行")
                return
            status_var.set("正在解析...")
            btn.configure(state="disabled")

            def worker():
                success = 0
                fail = 0
                skipped = 0
                used_hotkeys = set(p["hotkey"] for p in self.players if p.get("hotkey"))
                used_names = set(p["name"] for p in self.players)
                existing_urls = set()
                for p in self.players:
                    url = p.get("twitch_url") or p.get("douyin_url") or p.get("browser_url")
                    if url:
                        existing_urls.add(url)

                def get_next_hotkey():
                    for ch in [str(i) for i in range(0, 10)] + [chr(i) for i in range(ord('a'), ord('z') + 1)]:
                        if ch not in used_hotkeys:
                            return ch
                    return None

                new_players = []
                for idx, line in enumerate(lines):
                    prefill = parse_clipboard_url(line)
                    if not prefill:
                        fail += 1
                        log("系统", f"批量导入第{idx+1}行无法识别: {line}")
                        continue
                    url = prefill.get("twitch_url") or prefill.get("douyin_url") or prefill.get("browser_url")
                    if url and url in existing_urls:
                        skipped += 1
                        log("系统", f"批量导入第{idx+1}行重复，已跳过: {line}")
                        continue
                    if url:
                        existing_urls.add(url)

                    name = prefill["name"]
                    if name in used_names:
                        base = name
                        counter = 1
                        while f"{base}_{counter}" in used_names:
                            counter += 1
                        name = f"{base}_{counter}"
                        prefill["name"] = name
                    used_names.add(name)

                    hk = get_next_hotkey()
                    if hk is None:
                        fail += 1
                        log("系统", "所有可用快捷键已用完，无法导入更多选手")
                        break
                    used_hotkeys.add(hk)

                    pid = self.next_id
                    self.next_id += 1
                    view_label = get_next_view_label(self.players + new_players)
                    player_obj = {
                        "id": pid,
                        "name": name,
                        "hotkey": hk,
                        "platform": prefill["platform"],
                        "room_id": prefill.get("room_id", ""),
                        "twitch_url": prefill.get("twitch_url", ""),
                        "douyin_url": prefill.get("douyin_url", ""),
                        "quality": prefill.get("quality", "best"),
                        "browser_url": prefill.get("browser_url", ""),
                        "view_label": view_label,
                        "stream_name": f"player{pid}",
                        "obs_source_name": "",
                        "active": False,
                        "source_ok": None,
                        "stream_pid": None,
                        "window_title": f"OBS_Window_{name}"
                    }
                    new_players.append(player_obj)
                    success += 1
                    log("系统", f"批量导入成功: {name} (快捷键: {hk})")

                def update_ui():
                    with self.data_lock:
                        self.players.extend(new_players)
                    self.restart_services()
                    self.save_config()
                    self._update_log_combo()
                    self.refresh_ui()
                    status_var.set(f"完成：成功 {success}，跳过 {skipped}，失败 {fail}")
                    btn.configure(state="normal")
                    msg = f"成功 {success} 个"
                    if skipped > 0:
                        msg += f"，跳过 {skipped} 个重复"
                    if fail > 0:
                        msg += f"，失败 {fail} 个"
                    if not get_next_hotkey():
                        msg += "\n注意：单字符快捷键已用尽，无法再导入新选手。"
                    messagebox.showinfo("导入完成", msg)
                self.root.after(0, update_ui)

            threading.Thread(target=worker, daemon=True).start()

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        btn = ctk.CTkButton(btn_frame, text="导入", command=process_import)
        btn.pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="关闭", command=top.destroy).pack(side=tk.LEFT, padx=10)

    def save_config(self):
        cfg = {
            "obs_host": self.obs_host,
            "obs_port": self.obs_port,
            "obs_password": self.obs_pwd,
            "max_active_streams": self.max_streams,
            "hotkey_modifiers": self.hotkey_modifiers,
            "players": self.players,
            "scene_name": DEDICATED_SCENE
        }
        with open(CONFIG_FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        os.replace(CONFIG_FILE + ".tmp", CONFIG_FILE)

    def show_obs_login(self):
        dlg = OBSLoginDialog(self.root, self.obs_host, self.obs_port, self.obs_pwd)
        if dlg.result:
            self.obs_host, self.obs_port, self.obs_pwd = dlg.result
            self.save_config()

    def on_close(self):
        log("系统", "正在关闭...")
        if self.obs and self.obs.connected:
            try:
                if self.original_scene and self.original_scene != DEDICATED_SCENE:
                    self.obs.switch_scene(self.original_scene)
                if self.obs.scene_exists(DEDICATED_SCENE):
                    self.obs.remove_scene(DEDICATED_SCENE)
            except:
                pass
        try:
            from web_remote import stop_screenshot_push
            stop_screenshot_push()
        except:
            pass
        self.all_stop()
        self.save_config()
        if self.obs:
            self.obs.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1200x950")
    root.minsize(1000, 700)
    ManagerApp(root)
    root.mainloop()