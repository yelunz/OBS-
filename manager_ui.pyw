import json, os, subprocess, sys, time, threading, socket, collections, re, shutil, webbrowser, base64, io
import tkinter as tk
from tkinter import ttk, messagebox, Menu, scrolledtext
import customtkinter as ctk
from obswebsocket import obsws, requests
import psutil
from pynput import mouse, keyboard
import ctypes
from ctypes import wintypes
from web_remote import start_web_server, get_local_ip

# ==================== 双主题系统 ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 暗色主题 (Catppuccin Mocha)
DARK_THEME = {
    "PAGE_BG": "#1E1E2E",
    "CARD_BG": "#262636",
    "ELEVATED_BG": "#313146",
    "ACCENT": "#89B4FA",
    "ACCENT_HOVER": "#74A8F0",
    "SUCCESS": "#A6E3A1",
    "WARNING": "#F9E2AF",
    "DANGER": "#F38BA8",
    "TEXT_PRIMARY": "#CDD6F4",
    "TEXT_SECONDARY": "#9399B2",
    "BORDER": "#45475A",
    "SIDEBAR_BG": "#181825",
}

# 浅色主题 (Warm Light)
LIGHT_THEME = {
    "PAGE_BG": "#F0F0EB",
    "CARD_BG": "#FFFFFF",
    "ELEVATED_BG": "#E8E8E3",
    "ACCENT": "#3B82F6",
    "ACCENT_HOVER": "#2563EB",
    "SUCCESS": "#16A34A",
    "WARNING": "#CA8A04",
    "DANGER": "#DC2626",
    "TEXT_PRIMARY": "#1E1E2E",
    "TEXT_SECONDARY": "#6B7280",
    "BORDER": "#D1D5DB",
    "SIDEBAR_BG": "#E5E5DF",
}

# 当前主题
_current_theme = "dark"
PAGE_BG = DARK_THEME["PAGE_BG"]
CARD_BG = DARK_THEME["CARD_BG"]
ELEVATED_BG = DARK_THEME["ELEVATED_BG"]
ACCENT = DARK_THEME["ACCENT"]
ACCENT_HOVER = DARK_THEME["ACCENT_HOVER"]
SUCCESS = DARK_THEME["SUCCESS"]
WARNING = DARK_THEME["WARNING"]
DANGER = DARK_THEME["DANGER"]
TEXT_PRIMARY = DARK_THEME["TEXT_PRIMARY"]
TEXT_SECONDARY = DARK_THEME["TEXT_SECONDARY"]
BORDER = DARK_THEME["BORDER"]
SIDEBAR_BG = DARK_THEME["SIDEBAR_BG"]

# 字体系统
FONT_FAMILY = "Microsoft YaHei UI"  # 比 Segoe UI 对中文更友好
FONT_MONO = "Cascadia Code"  # 等宽字体用于日志
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_HEADING = (FONT_FAMILY, 12, "bold")
FONT_BODY = (FONT_FAMILY, 11)
FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
FONT_SMALL = (FONT_FAMILY, 10)
FONT_LARGE = (FONT_FAMILY, 24, "bold")
FONT_XL = (FONT_FAMILY, 26, "bold")

def switch_theme(theme_name):
    """切换主题并更新全局颜色变量"""
    global _current_theme, PAGE_BG, CARD_BG, ELEVATED_BG, ACCENT, ACCENT_HOVER
    global SUCCESS, WARNING, DANGER, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, SIDEBAR_BG
    src = LIGHT_THEME if theme_name == "light" else DARK_THEME
    _current_theme = theme_name
    for key in src:
        globals()[key] = src[key]
    ctk.set_appearance_mode(theme_name)
    _apply_ctk_theme()

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
    """设置 ttk.Treeview 暗色主题样式 - 彻底消除白框"""
    style = ttk.Style()
    style.theme_use("clam")
    
    # Treeview 主体
    style.configure("Treeview",
                    background=PAGE_BG,
                    foreground=TEXT_PRIMARY,
                    fieldbackground=PAGE_BG,
                    borderwidth=0,
                    highlightthickness=0,
                    font=FONT_BODY,
                    rowheight=30)
    style.configure("Treeview.Heading",
                    background=ELEVATED_BG,
                    foreground=TEXT_PRIMARY,
                    borderwidth=0,
                    relief="flat",
                    font=FONT_BODY_BOLD)
    
    # 选中行
    style.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#FFFFFF")],
              fieldbackground=[("selected", ACCENT)])
    style.map("Treeview.Heading",
              background=[("active", ACCENT_HOVER)])
    
    # 消除 Treeview 的虚线边框和空白边框
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.layout("Treeview.Heading", [
        ("Treeheading.cell", {"sticky": "nswe"}),
        ("Treeheading.border", {"sticky": "nswe", "children": [
            ("Treeheading.padding", {"sticky": "nswe", "children": [
                ("Treeheading.image", {"side": "right", "sticky": ""}),
                ("Treeheading.text", {"sticky": "we"})
            ]})
        ]})
    ])
    
    # CheckboxTreeview 专用样式
    style.configure("Checkbox.Treeview", background=PAGE_BG, foreground=TEXT_PRIMARY,
                    fieldbackground=PAGE_BG, borderwidth=0, highlightthickness=0)
    
    # 滚动条暗色主题
    style.configure("Vertical.TScrollbar",
                    background=ELEVATED_BG, troughcolor=PAGE_BG,
                    bordercolor=PAGE_BG, arrowcolor=TEXT_PRIMARY,
                    relief="flat", borderwidth=0)
    style.map("Vertical.TScrollbar",
              background=[("active", ACCENT)])
    
    # 消除 Treeview 的虚线边框
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

# ⚠ 不再在模块级调用 _apply_ttk_theme()，避免触发 TK 空白窗口
# 改为在 ManagerApp.__init__() 中调用

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

    def reconnect(self):
        """断线重连：先断开旧连接，再重新连接"""
        log("系统", "[OBS-重连] 开始尝试重连...")
        try:
            if self.ws:
                self.ws.disconnect()
        except:
            pass
        self.connected = False
        return self.connect()

    def is_alive(self):
        """检测 OBS WebSocket 是否仍然存活"""
        if not self.ws or not self.connected:
            return False
        try:
            self.ws.call(requests.GetVersion())
            return True
        except:
            return False

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

def _stream_process_monitor(player, obs_ref):
    """监控推流进程：进程退出时自动重启 (最多3次，每次间隔15秒)"""
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        time.sleep(15)
        try:
            # 检查选手是否仍在活跃池且 active
            if not player.get("active"):
                log("系统", f"[推流监控] {player['name']} 已关闭，停止监控")
                return
            if app and player not in app.active_players:
                log("系统", f"[推流监控] {player['name']} 已移出活跃池，停止监控")
                return
            pid = player.get("stream_pid")
            if not pid:
                log("系统", f"[推流监控] {player['name']} 无 stream_pid，停止监控")
                return
            # 检查进程是否存活
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    continue  # 进程正常，继续监控
            except psutil.NoSuchProcess:
                pass
            # 进程已退出 → 尝试重启
            retry_count += 1
            log("系统", f"[推流监控] {player['name']} 推流进程已退出，第 {retry_count}/{max_retries} 次自动重启...")
            player["stream_pid"] = None
            if not start_stream(player, obs_ref):
                time.sleep(3)
                if not start_stream(player, obs_ref):
                    log("系统", f"[推流监控] {player['name']} 第 {retry_count} 次重启失败")
            else:
                log("系统", f"[推流监控] {player['name']} 第 {retry_count} 次重启成功")
                retry_count = 0  # 重置计数器，允许无限次恢复
        except Exception as e:
            log("系统", f"[推流监控] {player['name']} 监控异常: {e}")
    log("系统", f"[推流监控] {player['name']} 连续 {max_retries} 次重启失败，停止监控")

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
        # bilibili / custom_web: 使用 OBS 浏览器源，无需 streamlink 管线
        log("系统", f"[推流-跳过] {name} 平台={plat} 使用 OBS 浏览器源，无需启动推流管线")
        return True

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
        ctk.CTkLabel(self.top, text="请填写 OBS WebSocket 服务器信息：", font=FONT_BODY).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5))
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
    def __init__(self, parent_app, parent_frame=None):
        self.app = parent_app
        self.embedded = parent_frame is not None
        
        if self.embedded:
            self.win = parent_frame
            # CTkFrame 没有 protocol() 方法，无需处理关闭
        else:
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
        self._closed = False  # 防止关闭后旧回调创建新网格

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

        if not self.embedded:
            toolbar = ctk.CTkFrame(self.win, fg_color=CARD_BG, corner_radius=8)
            toolbar.pack(fill=tk.X, side=tk.TOP, pady=2)
            ctk.CTkButton(toolbar, text="刷新所有", command=self.refresh_all, corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side=tk.LEFT, padx=5)

        # 使用 tk.Frame 替代 ttk.Frame，显式设置背景色以匹配主题 (修复白底板)
        bg_color = DARK_THEME["CARD_BG"] if _current_theme == "dark" else LIGHT_THEME["CARD_BG"]
        self.container = tk.Frame(self.win, bg=bg_color, highlightthickness=0)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.empty_label = ctk.CTkLabel(self.container, text="暂无推流", font=FONT_TITLE, text_color=TEXT_SECONDARY)
        self.win.bind("<Configure>", self._on_resize)
        self.after_id = None
        self._refresh_loop_id = None
        self._tk_widgets = []  # 需要主题更新的 tk 原生控件
        # 注册 container 到主题系统
        self._tk_widgets.append((self.container, "bg", LIGHT_THEME["CARD_BG"], DARK_THEME["CARD_BG"]))
        self.refresh()
        # 启动周期性刷新循环：每3秒检测新增/消失的活跃选手
        self._start_refresh_loop()

    def apply_theme(self):
        """主题切换时更新所有 tk 原生控件的颜色"""
        for widget, attr, light_val, dark_val in self._tk_widgets:
            try:
                val = light_val if _current_theme == "light" else dark_val
                widget.configure(**{attr: val})
            except:
                pass

    def _on_resize(self, event):
        if self._closed:
            return
        # 仅在窗口尺寸显著变化时触发 refresh，移动窗口位置或微小抖动不触发
        new_size = (event.width, event.height)
        if hasattr(self, '_last_size'):
            dw = abs(new_size[0] - self._last_size[0])
            dh = abs(new_size[1] - self._last_size[1])
            if dw < 5 and dh < 5:
                return
        self._last_size = new_size
        if self.after_id:
            try:
                self.win.after_cancel(self.after_id)
            except:
                pass
        self.after_id = self.win.after(200, self._safe_refresh)

    def _safe_refresh(self):
        """安全刷新：清除 after_id 后调用 refresh"""
        self.after_id = None
        try:
            self.refresh()
        except Exception as e:
            log("系统", f"[监视器-refresh异常] {e}")

    def _calculate_layout(self):
        n = len(self.players)
        if n == 0:
            return 1, 100, 100
        # 使用 win (CTkFrame/CTkToplevel) 的尺寸，而非 container (内部 tk.Frame)
        # CTkFrame 的尺寸由 grid 管理器控制，winfo 结果更可靠
        try:
            self.win.update_idletasks()
            width = self.win.winfo_width() - 20
            height = self.win.winfo_height() - 20
        except Exception:
            return 0, 0, 0
        # 容器未就绪时不渲染 (返回 0 触发调用方延迟重试)
        if width < 100 or height < 100:
            return 0, 0, 0
        # 选择最接近 16:9 宽高比的布局，同时惩罚空格子
        best_cols = 1
        best_score = float('inf')
        for cols in range(1, n + 1):
            rows = (n + cols - 1) // cols
            cell_w = width // cols
            cell_h = height // rows
            if cell_w < 80 or cell_h < 60:
                continue
            aspect = cell_w / max(cell_h, 1)
            # 偏差分数：越接近 16:9 (1.78) 越好
            score = abs(aspect - 1.78)
            # 惩罚空格子 (避免选择过多列导致大量空位)
            empty = rows * cols - n
            score += empty * 0.15
            if score < best_score:
                best_score = score
                best_cols = cols
        cols = best_cols
        rows = (n + cols - 1) // cols
        cell_w = width // cols
        cell_h = height // rows
        return cols, cell_w, cell_h

    def refresh(self):
        if self._closed:
            return
        # 过滤活跃选手并按名称去重 (防止 active_players 中重复条目导致空白网格位)
        seen = set()
        active = []
        for p in self.app.active_players:
            if p.get("active") and p["platform"] in ("twitch", "bilibili", "douyin", "custom_web"):
                if p["name"] not in seen:
                    seen.add(p["name"])
                    active.append(p)
        old_names = {p["name"] for p in self.players}
        new_names = {p["name"] for p in active}
        if old_names != new_names:
            log("系统", f"[监视器-refresh] 变化: old={old_names}, new={new_names}")

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

    def _full_cleanup(self):
        """完全清空所有监视器状态：VLC 实例、网格、管线、截图线程
        注意：本方法可能在子线程被调用，Tk 控件销毁必须通过 after 回到主线程执行
        """
        log("系统", "[监视器-全清] 开始清理所有状态")
        # 收集需要在子线程释放的 VLC 实例 (mp.stop/release 可能阻塞数秒)
        vlc_to_release = []
        for name in list(self.vlc_instances.keys()):
            _, mp, _ = self.vlc_instances.pop(name)
            vlc_to_release.append(mp)
        # 在子线程释放 VLC (避免 mp.stop() 阻塞)
        def _release_vlc_instances():
            for mp in vlc_to_release:
                try:
                    mp.stop()
                except:
                    pass
                try:
                    mp.release()
                except:
                    pass
        if vlc_to_release:
            threading.Thread(target=_release_vlc_instances, daemon=True).start()
        # 停止所有 B站管线
        for name in list(self.bilibili_procs.keys()):
            self._stop_bilibili_pipeline(name)
        # 停止所有截图轮询
        for name in list(self.screenshot_running.keys()):
            self._stop_screenshot_monitor(name)
        # 收集需要销毁的 Tk frame (必须在主线程执行)
        frames_to_destroy = []
        for name in list(self.grid_widgets.keys()):
            frame, canvas, label = self.grid_widgets.pop(name)
            frames_to_destroy.append(frame)
        # 清空 paused_players (历史遗留)
        paused_to_release = []
        for name in list(self.paused_players.keys()):
            data = self.paused_players.pop(name)
            paused_to_release.append(data)
        # 在子线程释放 paused_players 的 VLC
        def _release_paused_vlc():
            for data in paused_to_release:
                try:
                    if "mp" in data:
                        data["mp"].stop()
                        data["mp"].release()
                except:
                    pass
        if paused_to_release:
            threading.Thread(target=_release_paused_vlc, daemon=True).start()
            for data in paused_to_release:
                if "frame" in data:
                    frames_to_destroy.append(data["frame"])
        # 在主线程销毁 Tk 控件 (Tkinter 非线程安全)
        def _destroy_frames():
            for frame in frames_to_destroy:
                try:
                    frame.destroy()
                except:
                    pass
        if frames_to_destroy:
            try:
                self.win.after(0, _destroy_frames)
            except:
                # 如果 win 已销毁，直接尝试销毁
                _destroy_frames()
        # 清空截图相关
        self.screenshot_canvases.clear()
        with self.screenshot_lock:
            self.screenshot_frames.clear()
        # 重置 players 列表 (强制 refresh 重建所有网格)
        self.players = []
        log("系统", "[监视器-全清] 所有状态已清空")

    def _start_refresh_loop(self):
        """周期性刷新：检测新增/消失的活跃选手并自动渲染"""
        self._stop_refresh_loop()
        def _loop():
            if self._closed or not self.win or not self.win.winfo_exists():
                self._refresh_loop_id = None
                return
            try:
                self.refresh()
                self._check_vlc_health()
            except Exception:
                pass
            if not self._closed:
                self._refresh_loop_id = self.win.after(3000, _loop)
            else:
                self._refresh_loop_id = None
        self._refresh_loop_id = self.win.after(3000, _loop)

    def _stop_refresh_loop(self):
        if self._refresh_loop_id is not None:
            try:
                self.win.after_cancel(self._refresh_loop_id)
            except:
                pass
            self._refresh_loop_id = None

    def _check_vlc_health(self):
        """检查 VLC 实例健康状态，未播放的重试连接 (解决B站管线重启后VLC不自动重连)"""
        if not self.vlc_instance:
            return
        for name, (inst, mp, canvas) in list(self.vlc_instances.items()):
            if name not in self.grid_widgets:
                continue
            try:
                if mp.is_playing():
                    continue
                # VLC 未在播放，查找选手信息以获取 RTMP URL
                player = next((p for p in self.app.active_players if p["name"] == name), None)
                if not player:
                    continue
                plat = player["platform"]
                # 获取 RTMP URL
                if plat == "twitch":
                    stream_name = player.get("stream_name", f"player{player['id']}")
                    rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
                elif plat == "bilibili":
                    # B站：检查管线是否在运行 (本实例或其它实例)
                    pipeline_running = False
                    if name in self.bilibili_procs:
                        p1, _ = self.bilibili_procs[name]
                        pipeline_running = p1.poll() is None
                    elif hasattr(self.app, '_bilibili_pipelines') and name in self.app._bilibili_pipelines:
                        owner = self.app._bilibili_pipelines[name]
                        if owner is not self and hasattr(owner, 'bilibili_procs') and name in owner.bilibili_procs:
                            p1, _ = owner.bilibili_procs[name]
                            pipeline_running = p1.poll() is None
                    if not pipeline_running:
                        continue  # 管线未运行，暂不重试 VLC
                    stream_name = player.get("stream_name", f"player{player['id']}")
                    rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
                else:
                    continue
                # 重试 VLC 连接
                log("系统", f"[监视器-VLC健康检查] {name} 未播放，重试: {rtmp_url}")
                mp.stop()
                media = self.vlc_instance.media_new(rtmp_url)
                media.add_option(":network-caching=1000")
                media.add_option(":no-audio")
                mp.set_media(media)
                if canvas.winfo_exists():
                    mp.set_hwnd(canvas.winfo_id())
                mp.play()
            except Exception as e:
                log("系统", f"[监视器-VLC健康检查] {name} 异常: {e}")

    def _reposition_cells(self):
        if not self.players:
            return
        cols, cell_w, cell_h = self._calculate_layout()
        # 容器未就绪 (cols=0)：隐藏所有网格，安排延迟重试
        if cols == 0:
            for name in list(self.grid_widgets.keys()):
                frame, _, _ = self.grid_widgets[name]
                try:
                    frame.place_forget()
                except:
                    pass
            if not self._closed:
                try:
                    self.win.after(300, self._safe_refresh)
                except:
                    pass
            return
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

        # 已存在则不重复创建
        if name in self.grid_widgets:
            return

        # 使用 tk.Frame 替代 ttk.Frame，消除白边框
        frame = tk.Frame(self.container, bg=BORDER, highlightthickness=1, highlightbackground=BORDER)
        canvas = tk.Canvas(frame, bg=PAGE_BG, highlightthickness=0)
        name_label = tk.Label(frame, text=name, bg=ELEVATED_BG, fg=TEXT_PRIMARY, font=FONT_SMALL, highlightthickness=0)
        # 注册 tk 控件主题更新
        self._tk_widgets.append((canvas, "bg", LIGHT_THEME["PAGE_BG"], DARK_THEME["PAGE_BG"]))
        self._tk_widgets.append((name_label, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((name_label, "fg", LIGHT_THEME["TEXT_PRIMARY"], DARK_THEME["TEXT_PRIMARY"]))
        self._tk_widgets.append((frame, "bg", LIGHT_THEME["BORDER"], DARK_THEME["BORDER"]))
        self._tk_widgets.append((frame, "highlightbackground", LIGHT_THEME["BORDER"], DARK_THEME["BORDER"]))
        frame.place(x=0, y=0, width=100, height=100)
        canvas.place(x=0, y=0, width=100, height=75)
        name_label.place(x=0, y=75, width=100, height=25)
        # 原生点击绑定：点击 canvas 切换视角 (替代 pynput 全局监听器)
        canvas.bind("<Button-1>", lambda e, p=player: self.app.switch_to(p))
        self.grid_widgets[name] = (frame, canvas, name_label)
        log("系统", f"[监视器-显示-步骤2] 创建网格: {name}")

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
                canvas.create_text(150, 100, text="Pillow 未安装", fill="gray", font=FONT_SMALL)

    def _hide_grid(self, name):
        """隐藏并销毁指定视角的网格 (移除 paused_players 机制，直接销毁避免状态不一致)"""
        if name not in self.grid_widgets:
            return
        frame, canvas, label = self.grid_widgets.pop(name)
        log("系统", f"[监视器-隐藏] 销毁网格: {name}")

        # 停止 B站管线
        if name in self.bilibili_procs:
            self._stop_bilibili_pipeline(name)

        # 停止截图轮询
        if name in self.screenshot_running:
            self._stop_screenshot_monitor(name)

        # 停止并释放 VLC 实例
        if name in self.vlc_instances:
            inst, mp, _ = self.vlc_instances.pop(name)
            def _release_vlc():
                try:
                    mp.stop()
                except:
                    pass
                try:
                    mp.release()
                except:
                    pass
            # 在子线程释放 VLC，避免阻塞主线程
            threading.Thread(target=_release_vlc, daemon=True).start()

        # 销毁 frame
        try:
            frame.destroy()
        except:
            pass

    def _start_vlc(self, name, canvas, url):
        if not self.vlc_instance or not self.win.winfo_exists():
            return
        if name in self.vlc_instances:
            return
        # 检查 canvas 是否仍然有效 (避免 _hide_grid 销毁后延迟回调访问无效控件)
        if name not in self.grid_widgets:
            log("系统", f"[监视器-VLC] {name} 已不在网格中，取消 VLC 启动")
            return
        try:
            _, current_canvas, _ = self.grid_widgets[name]
            if current_canvas is not canvas:
                log("系统", f"[监视器-VLC] {name} canvas 已更换，取消旧 VLC 启动")
                return
            canvas.update_idletasks()
            hwnd = canvas.winfo_id()
            if not hwnd:
                return
            media = self.vlc_instance.media_new(url)
            media.add_option(":network-caching=1000")
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
                media.add_option(":network-caching=1000")
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

        # 全局协调：检查是否已有其他 MonitorWindow 实例启动了同一选手的 B站管线
        # 避免两个实例推送到相同 RTMP URL 导致 MediaMTX 冲突
        if hasattr(self.app, '_bilibili_pipelines'):
            with self.app._bilibili_lock:
                if name in self.app._bilibili_pipelines:
                    owner = self.app._bilibili_pipelines[name]
                    if owner is not self and hasattr(owner, 'bilibili_procs') and name in owner.bilibili_procs:
                        p1, p2 = owner.bilibili_procs[name]
                        if p1.poll() is None:
                            log("系统", f"[监视器-B站-跳过] {name} 管线已由其他实例运行，本实例仅启动 VLC")
                            stream_name = player.get("stream_name", f"player{player['id']}")
                            rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
                            self.win.after(1000, self._start_vlc, name, canvas, rtmp_url)
                            self.win.after(5000, self._retry_vlc, name, canvas, rtmp_url)
                            return
                # 注册本实例为管线拥有者
                self.app._bilibili_pipelines[name] = self
                log("系统", f"[监视器-B站-注册] {name} 管线由本实例管理")

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
        # 注销全局注册，允许其他实例重新启动管线
        if hasattr(self.app, '_bilibili_pipelines'):
            with self.app._bilibili_lock:
                if self.app._bilibili_pipelines.get(name) is self:
                    self.app._bilibili_pipelines.pop(name, None)
                    log("系统", f"[监视器-B站-注销] {name} 管线已注销全局注册")

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

            # 约 10fps (100ms) - 降低轮询频率以减少 OBS WebSocket 压力
            time.sleep(0.1)

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
                    pil_img = pil_img.resize((new_w, new_h), Image.BILINEAR)
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

        # 继续渲染循环 (100ms - 与截图频率一致)
        if self.screenshot_canvases:
            self.screenshot_render_id = self.win.after(100, self._screenshot_render_loop)
        else:
            self.screenshot_render_id = None

    def refresh_all(self):
        """刷新所有视角：在子线程清理 VLC/管线/截图，避免阻塞主线程"""
        log("系统", "[监视器-刷新所有] 开始 (子线程清理)")
        # 立即隐藏所有网格，避免清理过程中残留画面闪烁
        for name in list(self.grid_widgets.keys()):
            frame, _, _ = self.grid_widgets[name]
            try:
                frame.place_forget()
            except:
                pass
        def _do_cleanup():
            try:
                self._full_cleanup()
            except Exception as e:
                log("系统", f"[监视器-刷新所有] 清理异常: {e}")
            # 回到主线程重建网格 (使用 _safe_refresh 避免异常)
            try:
                self.win.after(0, self._safe_refresh)
                log("系统", "[监视器-刷新所有] 清理完成，已触发重建")
            except:
                pass
        threading.Thread(target=_do_cleanup, daemon=True).start()

    def on_close(self):
        log("系统", "[监视器-关闭] 开始清理资源")
        self._closed = True  # 标记已关闭，阻止旧回调创建新网格
        # 解绑 <Configure> 事件，防止窗口缩放触发旧 MonitorWindow 的 refresh
        try:
            self.win.unbind("<Configure>")
        except:
            pass
        # 停止周期性刷新循环
        self._stop_refresh_loop()
        # 停止截图渲染循环
        if self.screenshot_render_id:
            try:
                self.win.after_cancel(self.screenshot_render_id)
            except:
                pass
            self.screenshot_render_id = None
        # 完全清空所有状态 (VLC/管线/截图/网格/paased)
        self._full_cleanup()
        if not self.embedded:
            # 独立弹出窗口关闭时清理 popup_monitor (不影响嵌入监视器)
            if self.app.popup_monitor is self:
                self.app.popup_monitor = None
            try:
                # 使用 after 延迟销毁，避免 CTkToplevel 在协议回调中直接销毁导致的冲突
                self.win.after(0, self.win.destroy)
            except:
                pass
        else:
            # 嵌入监视器: 销毁 container 和 empty_label，防止残留 widget 累积
            # 每次切换页面创建新 MonitorWindow 时，旧 container 不销毁会导致
            # empty_label 残留，表现为监视器中空白项不断累积
            try:
                if self.empty_label:
                    self.empty_label.destroy()
                    self.empty_label = None
            except:
                pass
            try:
                if self.container:
                    self.container.destroy()
                    self.container = None
            except:
                pass
        log("系统", "[监视器-关闭] 资源清理完成")

    def update_if_open(self):
        if self._closed:
            return
        try:
            if self.win and self.win.winfo_exists():
                self.refresh()
        except Exception:
            pass

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
        self.tag_configure("checked", background=ACCENT, foreground="#FFFFFF")

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
        self.monitor_window = None       # 嵌入监视器 (主页面内)
        self.popup_monitor = None        # 独立弹出窗口 (与嵌入监视器完全独立)
        self._bilibili_pipelines = {}    # 全局 B站管线协调: name -> MonitorWindow 实例
        self._bilibili_lock = threading.Lock()
        self._pending_commands = []      # 跨线程命令队列 (Flask→主线程)
        self._command_lock = threading.Lock()
        self.pool_label = None
        self._theme_registry = []  # 主题色注册表: (widget, attr, light_value, dark_value)
        self.first_run = not os.path.exists(CONFIG_FILE)
        self.load_cfg()
        _apply_ttk_theme()  # 主题样式初始化（必须在 root 创建后调用）
        self.create_widgets()
        try:
            self.refresh_store_tree()
        except Exception as e:
            log("系统", f"[初始化-错误] refresh_store_tree 失败: {e}")
        try:
            self._update_log_combo()
        except Exception as e:
            log("系统", f"[初始化-错误] _update_log_combo 失败: {e}")
        if self.first_run or not self.obs_host:
            self.root.after(200, self.show_obs_login)
        self.root.after(100, self.async_connect_obs)
        self._cleanup_edge_profiles()
        self.refresh_loop()
        self.start_status_monitor()
        self.start_log_consumer()
        self._start_obs_watchdog()
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
        
        # 加载主题偏好
        saved_theme = cfg.get("theme", "dark")
        if saved_theme != _current_theme:
            switch_theme(saved_theme)
        
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
                "obs_source_name": "",  # 启动时清空，避免残留无效源名
                "active": False,
                "source_ok": None,
                "stream_pid": None,
                "window_title": f"OBS_Window_{p.get('name', '')}"
            }
            self.players.append(player_obj)
            # 启动时不自动加入活跃池，避免异常关闭后的残留数据导致卡死
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
            if hasattr(self, '_stat_values') and "OBS 状态" in self._stat_values:
                self._stat_values["OBS 状态"].configure(text="已连接", text_color=SUCCESS)
            self.setup_scene()
            self.refresh_ui()
        else:
            self.obs_status_label.configure(text="⚠ OBS 断开", text_color=DANGER)
            if hasattr(self, '_stat_values') and "OBS 状态" in self._stat_values:
                self._stat_values["OBS 状态"].configure(text="未连接", text_color=DANGER)

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
        self._register_theme(header, "fg_color", LIGHT_THEME["SIDEBAR_BG"], DARK_THEME["SIDEBAR_BG"])

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side=tk.LEFT, padx=(16, 0))
        ctk.CTkLabel(brand, text="OBS MultiView", font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)

        self.obs_status_label = ctk.CTkLabel(header, text="", font=FONT_SMALL)
        return header

    # ==================== Sidebar ====================
    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self.root, fg_color=SIDEBAR_BG, corner_radius=0, width=220)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self._register_theme(sidebar, "fg_color", LIGHT_THEME["SIDEBAR_BG"], DARK_THEME["SIDEBAR_BG"])
        sidebar.rowconfigure(4, weight=1)

        nav_items = [
            ("dashboard", "仪表盘"),
            ("players",   "选手管理"),
            ("monitor",   "监视器"),
            ("logs",      "日志"),
        ]

        self._nav_buttons = {}
        for i, (key, label) in enumerate(nav_items):
            btn = ctk.CTkButton(sidebar, text=label,
                                anchor="w", fg_color="transparent",
                                hover_color=ELEVATED_BG, text_color=TEXT_SECONDARY,
                                font=FONT_BODY, corner_radius=8,
                                height=40, command=lambda k=key: self._show_page(k))
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=3)
            self._nav_buttons[key] = btn

        # 底部 Web 遥控信息
        sep = ctk.CTkFrame(sidebar, fg_color=BORDER, height=1, corner_radius=0)
        sep.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

        web_info = ctk.CTkFrame(sidebar, fg_color="transparent")
        web_info.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 6))
        ctk.CTkLabel(web_info, text="手机遥控", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(anchor="w")
        
        # IP 地址行 + 复制按钮
        ip_row = ctk.CTkFrame(web_info, fg_color="transparent")
        ip_row.pack(fill=tk.X, pady=(2, 0))
        local_ip = get_local_ip()
        self.web_ip_label = ctk.CTkLabel(ip_row, text=f"{local_ip}:5000", font=FONT_BODY_BOLD,
                                          text_color=ACCENT)
        self.web_ip_label.pack(side=tk.LEFT)
        ctk.CTkButton(ip_row, text="复制", command=self._copy_web_ip,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                      font=FONT_SMALL, corner_radius=5, height=24, width=44).pack(side=tk.RIGHT)

        # 主题切换
        theme_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        theme_row.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.theme_btn = ctk.CTkButton(theme_row, text="☀ 浅色主题" if _current_theme == "dark" else "☾ 暗色主题",
                                        command=self._toggle_theme, fg_color=ELEVATED_BG,
                                        hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                                        font=FONT_SMALL, corner_radius=6, height=30)
        self.theme_btn.pack(fill=tk.X)

        # 设置按钮
        ctk.CTkButton(sidebar, text="设置", command=self.show_settings,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#FFFFFF",
                      font=FONT_BODY_BOLD, corner_radius=8, height=38).grid(row=8, column=0, sticky="ew", padx=16, pady=(4, 12))

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
        page.rowconfigure(2, weight=0)  # pool grid
        page.rowconfigure(3, weight=0)  # auto-detect

        # ── Stats Row ──
        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="stats")

        stats_data = [
            ("活跃选手", "0"),
            ("OBS 状态", "未连接"),
            ("当前视角", "无"),
            ("快捷键", "0"),
        ]
        self._stat_labels = {}
        self._stat_values = {}
        for i, (title, val) in enumerate(stats_data):
            card = ctk.CTkFrame(stats, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            self._register_frame(card, "card")
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)
            ctk.CTkLabel(inner, text=title, font=FONT_SMALL,
                         text_color=TEXT_SECONDARY).pack(anchor="w")
            val_lbl = ctk.CTkLabel(inner, text=val, font=FONT_LARGE, text_color=ACCENT)
            val_lbl.pack(anchor="w", pady=(2, 0))
            self._stat_values[title] = val_lbl

        # ── Current View Card ──
        cur_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=BORDER)
        cur_card.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        self._register_frame(cur_card, "card")
        cur_inner = ctk.CTkFrame(cur_card, fg_color="transparent")
        cur_inner.pack(fill=tk.BOTH, padx=20, pady=14)
        ctk.CTkLabel(cur_inner, text="当前播出视角", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(anchor="w")
        self.cur_label = ctk.CTkLabel(cur_inner, text="无", font=FONT_XL,
                                      text_color=ACCENT)
        self.cur_label.pack(anchor="w", pady=(4, 0))

        # ── Pool Grid (卡片式活跃池) ──
        pool_section = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        pool_section.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        self._register_frame(pool_section, "card")
        pool_inner = ctk.CTkFrame(pool_section, fg_color="transparent")
        pool_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        self.pool_label = ctk.CTkLabel(pool_inner, text="活跃池", font=FONT_BODY_BOLD,
                                       text_color=TEXT_PRIMARY)
        self.pool_label.pack(side=tk.LEFT)
        ctk.CTkButton(pool_inner, text="+ 添加视角", command=self.show_quick_add_popup,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                      font=FONT_BODY_BOLD, corner_radius=6, height=28).pack(side=tk.RIGHT)
        # 卡片网格容器
        self.pool_grid = ctk.CTkFrame(pool_inner, fg_color="transparent")
        self.pool_grid.pack(fill=tk.X, pady=(6, 0))
        self._pool_cards = {}  # name -> (frame, label)

        # ── Auto-detect ──
        auto_frame = ctk.CTkFrame(page, fg_color="transparent")
        auto_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkCheckBox(auto_frame, text="自动检测推流状态", variable=self.auto_detect,
                        font=FONT_SMALL, text_color=TEXT_SECONDARY,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        border_color=BORDER, checkmark_color="#FFFFFF").pack(side=tk.LEFT)

        return page

    def _refresh_pool_cards(self):
        """刷新活跃池卡片网格 (显示池中所有选手，含已关闭的)"""
        # 清除旧卡片
        for name in list(self._pool_cards.keys()):
            frame, _ = self._pool_cards.pop(name)
            frame.destroy()

        pool = list(self.active_players)
        if not pool:
            empty = ctk.CTkLabel(self.pool_grid, text="暂无活跃选手，点击「添加视角」按钮添加", font=FONT_SMALL,
                                 text_color=TEXT_SECONDARY)
            empty.grid(row=0, column=0, padx=4, pady=4, sticky="w")
            self._pool_cards["_empty"] = (empty, empty)
            return

        # 每行最多4个卡片
        cols = 4
        for i, p in enumerate(sorted(pool, key=lambda x: (isinstance(x.get("view_label"), int), x.get("view_label", "")))):
            row = i // cols
            col = i % cols

            is_active = p.get("active", False)
            border_c = ACCENT if is_active else BORDER
            card = ctk.CTkFrame(self.pool_grid, fg_color=ELEVATED_BG, corner_radius=8, border_width=1, border_color=border_c)
            card.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            self._register_frame(card, "elevated")
            # 让列等宽
            self.pool_grid.columnconfigure(col, weight=1, uniform="pool")

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill=tk.X, padx=10, pady=8)

            name_lbl = ctk.CTkLabel(card_inner, text=p["name"], font=FONT_BODY_BOLD,
                                    text_color=TEXT_PRIMARY)
            name_lbl.pack(anchor="w")

            status_text = f"视角 {p.get('view_label', '?')}  ● 推流中" if is_active else f"视角 {p.get('view_label', '?')}  ○ 已关闭"
            status_color = SUCCESS if is_active else TEXT_SECONDARY
            view_lbl = ctk.CTkLabel(card_inner, text=status_text,
                                    font=FONT_SMALL, text_color=status_color)
            view_lbl.pack(anchor="w")

            # 右键菜单
            card.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            card_inner.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            name_lbl.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            view_lbl.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))

            self._pool_cards[p["name"]] = (card, name_lbl)

    def _pool_card_menu(self, event, player):
        """活跃池卡片右键菜单"""
        menu = tk.Menu(self.root, tearoff=0, bg=ELEVATED_BG, fg=TEXT_PRIMARY,
                       activebackground=ACCENT, activeforeground="#FFFFFF",
                       font=FONT_BODY)
        if player.get("active"):
            menu.add_command(label="⏸ 关闭推流", command=lambda: self.deactivate_player(player))
        else:
            menu.add_command(label="▶ 启动推流", command=lambda: self.activate_player(player))
        menu.add_command(label="🎥 切换到此视角", command=lambda: self.switch_to(player))
        menu.add_command(label="🔄 刷新源", command=lambda: self.refresh_player(player))
        menu.add_separator()
        menu.add_command(label="✏ 编辑选手", command=lambda: self.edit_player(player))
        menu.add_command(label="🌐 打开直播间", command=lambda: self.open_player_url(player))
        menu.add_separator()
        menu.add_command(label="📤 移回仓库", command=lambda: self.move_to_store(player))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ==================== Players Page ====================
    def _create_players_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.rowconfigure(0, weight=0)  # toolbar
        page.rowconfigure(1, weight=6)  # store
        page.rowconfigure(2, weight=4)  # active
        page.columnconfigure(0, weight=1)

        # ── 工具栏 (所有操作按钮统一放在此处) ──
        toolbar = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        self._register_frame(toolbar, "card")
        toolbar_inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        toolbar_inner.pack(fill=tk.X, padx=10, pady=8)

        # 左侧：选手管理操作
        left_btns = ctk.CTkFrame(toolbar_inner, fg_color="transparent")
        left_btns.pack(side=tk.LEFT)
        ctk.CTkLabel(left_btns, text="选手操作", font=FONT_BODY_BOLD,
                     text_color=ACCENT).pack(side=tk.LEFT, padx=(0, 8))
        for t, cmd in [("添加选手", self.add), ("快速添加", self.quick_add), ("批量导入", self.bulk_import_window)]:
            ctk.CTkButton(left_btns, text=t, command=cmd, corner_radius=6,
                          fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                          font=FONT_BODY, height=32, width=80).pack(side=tk.LEFT, padx=(0, 6))

        # 分隔线
        ctk.CTkFrame(toolbar_inner, fg_color=BORDER, width=1, height=28).pack(side=tk.LEFT, padx=10)

        # 中间：批量推流 (仓库页仅保留批量推流，启动/关闭请在仪表盘活跃池操作)
        mid_btns = ctk.CTkFrame(toolbar_inner, fg_color="transparent")
        mid_btns.pack(side=tk.LEFT)
        ctk.CTkLabel(mid_btns, text="推流", font=FONT_BODY_BOLD,
                     text_color=ACCENT).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(mid_btns, text="批量推流", command=self.batch_move_to_active, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=FONT_BODY, height=32, width=80).pack(side=tk.LEFT, padx=(0, 6))

        # 右侧：系统操作
        ctk.CTkFrame(toolbar_inner, fg_color=BORDER, width=1, height=28).pack(side=tk.RIGHT, padx=10)
        right_btns = ctk.CTkFrame(toolbar_inner, fg_color="transparent")
        right_btns.pack(side=tk.RIGHT)
        for t, cmd in [("重连 OBS", self.reconnect_obs), ("重启服务", self.restart_services)]:
            ctk.CTkButton(right_btns, text=t, command=cmd, corner_radius=6,
                          fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                          font=FONT_BODY, height=32, width=80).pack(side=tk.LEFT, padx=(0, 6))

        # ── 选手仓库 (上) ──
        store_section = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        store_section.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self._register_frame(store_section, "card")

        store_header = ctk.CTkFrame(store_section, fg_color="transparent")
        store_header.pack(fill=tk.X, padx=12, pady=(10, 4))
        ctk.CTkLabel(store_header, text="选手仓库", font=FONT_HEADING,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)

        # 使用普通 Frame + 手动滚动条，避免 CTkScrollableFrame 与 Treeview 滚动冲突
        store_tree_frame = ctk.CTkFrame(store_section, fg_color="transparent")
        store_tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        store_tree_frame.columnconfigure(0, weight=1)
        store_tree_frame.rowconfigure(0, weight=1)
        
        self.store_tree = CheckboxTreeview(store_tree_frame, columns=("sel", "name", "platform", "status", "key"),
                                             checkbox_col="#1", show="headings", height=8)
        self.store_tree.grid(row=0, column=0, sticky="nsew")
        
        store_scrollbar = ttk.Scrollbar(store_tree_frame, orient="vertical", command=self.store_tree.yview)
        store_scrollbar.grid(row=0, column=1, sticky="ns")
        self.store_tree.configure(yscrollcommand=store_scrollbar.set)
        self.store_tree.bind("<Button-3>", self.on_store_right_click)

        # ── 选手仓库占满全页 ──
        # 视角列表已移除，仓库为唯一展示区

        return page

    # ==================== Monitor Page ====================
    def _create_monitor_page(self):
        page = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)  # embedded monitor
        page.rowconfigure(1, weight=0)  # bottom bar

        # 嵌入监视器容器
        self.monitor_container = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        self.monitor_container.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))
        self._register_frame(self.monitor_container, "card")
        self.monitor_placeholder = ctk.CTkLabel(self.monitor_container, text="多视角监控\n\n切换到监视器页面后将自动显示活跃选手画面",
                                                 font=FONT_TITLE, text_color=TEXT_SECONDARY, justify="center")
        self.monitor_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 底部操作栏
        bottom_bar = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 12))
        self._register_frame(bottom_bar, "card")
        bar_inner = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        bar_inner.pack(fill=tk.X, padx=12, pady=8)

        ctk.CTkButton(bar_inner, text="弹出独立窗口", command=self.toggle_monitor, corner_radius=6,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                      font=FONT_BODY, height=32, width=120).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(bar_inner, text="刷新", command=self._refresh_embedded_monitor, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=FONT_BODY, height=32, width=80).pack(side=tk.LEFT)

        ctk.CTkLabel(bar_inner, text="提示：点击选手画面可切换视角", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(side=tk.RIGHT)

        return page

    def _refresh_embedded_monitor(self):
        """刷新嵌入的监视器 (与独立窗口的刷新所有一致)"""
        if self.monitor_window and self.monitor_window.embedded:
            self.monitor_window.refresh_all()

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

        ctk.CTkLabel(filter_bar, text="日志", font=FONT_BODY_BOLD,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=12, pady=8)
        ctk.CTkLabel(filter_bar, text="筛选:", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(side=tk.LEFT, padx=(0, 4))
        self.log_combo = ctk.CTkComboBox(filter_bar, variable=self.current_log_player,
                                         state="readonly", values=["系统"], width=140,
                                         font=FONT_BODY, fg_color=ELEVATED_BG,
                                         border_color=BORDER, button_color=ACCENT,
                                         button_hover_color=ACCENT_HOVER,
                                         dropdown_fg_color=CARD_BG, dropdown_text_color=TEXT_PRIMARY)
        self.log_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.log_combo.configure(command=lambda v: self._refresh_log_view())
        self.log_combo.set("系统")

        ctk.CTkCheckBox(filter_bar, text="自动检测", variable=self.auto_detect,
                        font=FONT_SMALL, text_color=TEXT_SECONDARY,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        border_color=BORDER, checkmark_color="#FFFFFF").pack(side=tk.RIGHT, padx=12)

        # Log viewer
        log_container = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER)
        log_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self._register_frame(log_container, "card")

        self.log_text = ctk.CTkTextbox(log_container, font=FONT_BODY,
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
        self._register_theme(bar, "fg_color", LIGHT_THEME["SIDEBAR_BG"], DARK_THEME["SIDEBAR_BG"])

        ctk.CTkLabel(bar, textvariable=self.status_var, anchor="w",
                     text_color=TEXT_SECONDARY, font=FONT_SMALL).pack(side=tk.LEFT, padx=12)

        # 右侧指示器
        ctk.CTkLabel(bar, text="localhost:5000", text_color=ACCENT,
                     font=FONT_SMALL).pack(side=tk.RIGHT, padx=(0, 12))
        ctk.CTkLabel(bar, text="▸", text_color=TEXT_SECONDARY,
                     font=FONT_SMALL).pack(side=tk.RIGHT, padx=(0, 4))

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

        # 切换到监视器页面时，初始化嵌入监视器
        if name == "monitor":
            self._ensure_embedded_monitor()
        # 离开监视器页面时，清理嵌入监视器
        elif name != "monitor" and self.monitor_window and self.monitor_window.embedded:
            self.monitor_window.on_close()
            self.monitor_window = None
            if hasattr(self, 'monitor_placeholder'):
                self.monitor_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _ensure_embedded_monitor(self):
        """确保嵌入监视器已初始化 (与独立弹出窗口无关)"""
        if not VLC_AVAILABLE:
            return
        if self.monitor_window and self.monitor_window.embedded and not self.monitor_window._closed:
            self.monitor_window.refresh()
            return
        # 清理 CTkFrame 内残留的旧子控件 (前一个 MonitorWindow 的 container 等)
        # 防止切换页面累积残留 widget 导致空白项
        try:
            for child in self.monitor_container.winfo_children():
                if child is not getattr(self, 'monitor_placeholder', None):
                    child.destroy()
        except:
            pass
        # 创建嵌入监视器
        try:
            self.monitor_window = MonitorWindow(self, parent_frame=self.monitor_container)
        except Exception as e:
            log("系统", f"[_ensure_embedded_monitor] 创建异常: {e}")
            return
        if hasattr(self, 'monitor_placeholder'):
            self.monitor_placeholder.place_forget()
        # 延迟刷新，确保容器尺寸已就绪
        self.root.after(300, lambda: self.monitor_window and self.monitor_window.embedded and not self.monitor_window._closed and self.monitor_window.refresh())

    # ---------- 辅助获取勾选 ----------
    def get_selected_store_players(self):
        names = self.store_tree.get_checked_names()
        return [p for p in self.players if p["name"] in names]

    def batch_move_to_active(self):
        selected = self.get_selected_store_players()
        if not selected:
            messagebox.showinfo("提示", "请先在仓库中勾选选手")
            return
        for player in selected:
            self.move_to_active(player)
        self.store_tree.clear_checked()
        self.set_status(f"已添加 {len(selected)} 个选手到活跃池")

    def refresh_store_tree(self):
        checked_names = self.store_tree.get_checked_names()
        self.store_tree.delete(*self.store_tree.get_children())
        for p in sorted(self.players, key=lambda x: x["hotkey"]):
            self.store_tree.insert("", tk.END, values=("☐", p["name"], p["platform"], "📦 仓库中", p["hotkey"]))
        self.store_tree.set_checked_by_name(checked_names)

    def one_click_activate(self, player):
        if player["platform"] not in ("twitch",):
            messagebox.showinfo("提示", "该平台不支持直接启动")
            return
        self.move_to_active(player)

    def move_to_active(self, player):
        if not self.obs or not self.obs.connected:
            messagebox.showwarning("提示", "OBS 未连接")
            return
        with self.data_lock:
            if player in self.active_players:
                # 已在活跃池：若未激活则启动推流
                if not player.get("active"):
                    self.activate_player(player)
                return
            # 检查活跃池名额
            active_count = sum(1 for p in self.active_players if p.get("active"))
            if active_count >= self.max_streams:
                messagebox.showwarning("限制", f"活跃池已满 (最多{self.max_streams}个)")
                return
            self.active_players.append(player)
        self.save_config()
        self._update_log_combo()
        # activate_player 会设置 active=True、创建 OBS 源、启动推流管线
        self.activate_player(player)
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
                menu = Menu(self.root, tearoff=0,
                            bg=ELEVATED_BG, fg=TEXT_PRIMARY,
                            activebackground=ACCENT, activeforeground="#FFFFFF",
                            borderwidth=0, font=FONT_BODY)
                menu.add_command(label="✏ 编辑", command=lambda: self.edit_player(player))
                menu.add_command(label="🗑 删除", command=lambda: self.delete_player(player))
                menu.add_separator()
                if player["platform"] in ("bilibili", "custom_web"):
                    menu.add_command(label="🌐 打开直播间", command=lambda: self.open_player_url(player))
                menu.add_command(label="📥 添加到活跃池", command=lambda: self.move_to_active(player))
                if player["platform"] in ("twitch",):
                    menu.add_command(label="🚀 一键启动", command=lambda: self.one_click_activate(player))
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()

    # ==================== 仪表盘快速添加视角浮窗 ====================
    def show_quick_add_popup(self):
        top = ctk.CTkToplevel(self.root)
        top.title("添加视角到活跃池")
        top.geometry("360x420")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=CARD_BG)

        ctk.CTkLabel(top, text="添加视角到活跃池", font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text="勾选仓库中的选手，点击确定后自动添加并启动推流",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(0, 10))

        pool_names = {p["name"] for p in self.active_players}
        candidates = [p for p in self.players if p["name"] not in pool_names]

        if not candidates:
            ctk.CTkLabel(top, text="仓库中无可添加的选手", font=FONT_BODY,
                         text_color=TEXT_SECONDARY).pack(expand=True)
            ctk.CTkButton(top, text="关闭", command=top.destroy, corner_radius=6,
                          fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                          font=FONT_BODY).pack(pady=12)
            return
        
        list_frame = ctk.CTkScrollableFrame(top, fg_color="transparent")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
        
        check_vars = {}
        for p in candidates:
            row = ctk.CTkFrame(list_frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=2)
            var = tk.BooleanVar(value=False)
            check_vars[p["name"]] = var
            cb = ctk.CTkCheckBox(row, text=f"{p['name']} ({p['platform']})", variable=var,
                                 font=FONT_BODY, text_color=TEXT_PRIMARY,
                                 fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                 border_color=BORDER, checkmark_color="#FFFFFF")
            cb.pack(side=tk.LEFT)
        
        def confirm():
            added = []
            for p in candidates:
                if check_vars.get(p["name"], tk.BooleanVar()).get():
                    self.move_to_active(p)
                    added.append(p["name"])
            top.destroy()
            if added:
                self.set_status(f"已添加 {len(added)} 个选手到活跃池")
            self.refresh_ui()
        
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 12))
        ctk.CTkButton(btn_frame, text="确定", command=confirm, corner_radius=6,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                      font=FONT_BODY_BOLD, height=34).pack(side=tk.RIGHT, padx=(8, 0))
        ctk.CTkButton(btn_frame, text="取消", command=top.destroy, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=FONT_BODY, height=34).pack(side=tk.RIGHT)

    # ---------- 核心操作 ----------
    def activate_player(self, player):
        if player.get("active"):
            return
        if not self.obs or not self.obs.connected:
            messagebox.showwarning("提示", "OBS 未连接，无法启动")
            return
        active_count = sum(1 for p in self.active_players if p.get("active"))
        if active_count >= self.max_streams:
            messagebox.showwarning("限制", f"活跃池已满 (最多{self.max_streams}个)")
            return
        player["active"] = True
        log("系统", f"激活选手 {player['name']}，开始创建源并启动推流")
        # sync_player 含多次同步 OBS WebSocket 调用，必须在子线程执行避免冻结 UI
        def do_sync_and_start():
            try:
                self.sync_player(player)
            except Exception as e:
                log("系统", f"[激活-sync_player异常] {player['name']}: {e}")
            self.save_config()
            log("系统", f"启动推流线程: {player['name']}")
            if not start_stream(player, self.obs):
                time.sleep(2)
                if not start_stream(player, self.obs):
                    self.stream_status_cache[player["name"]] = False
                    log("系统", f"推流启动失败: {player['name']}")
            else:
                log("系统", f"推流启动成功: {player['name']}")
                # 启动推流进程监控 (仅 Twitch/抖音 需要，浏览器源平台无需)
                if player["platform"] in ("twitch", "douyin"):
                    threading.Thread(target=_stream_process_monitor, args=(player, self.obs), daemon=True).start()
            self.root.after(0, self.refresh_ui)
        threading.Thread(target=do_sync_and_start, daemon=True).start()
        # 注意: 不在此处同步调用 refresh_ui，因为 refresh_ui 内部调用
        # self.obs.get_all_source_names() (同步 OBS WebSocket)，当 OBS 正忙于
        # sync_player 时会冻结 UI。UI 刷新由后台线程完成后的 after 回调处理。

    def deactivate_player(self, player):
        if not player.get("active"):
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
        # 更新统计卡片
        if hasattr(self, '_stat_values'):
            active_count = sum(1 for p in self.active_players if p.get("active"))
            hotkey_count = len([p for p in self.players if p.get("hotkey")])
            if "活跃选手" in self._stat_values:
                self._stat_values["活跃选手"].configure(text=str(active_count))
            if "快捷键" in self._stat_values:
                self._stat_values["快捷键"].configure(text=str(hotkey_count))
            if "OBS 状态" in self._stat_values:
                if self.obs and self.obs.connected:
                    self._stat_values["OBS 状态"].configure(text="已连接", text_color=SUCCESS)
                else:
                    self._stat_values["OBS 状态"].configure(text="未连接", text_color=DANGER)
        
        if not self.obs or not self.obs.connected:
            self.refresh_store_tree()
            self._update_log_combo()
            return

        existing = self.obs.get_all_source_names()
        cur_name = self.get_current_display_name()
        self.cur_label.configure(text=cur_name or "无")
        if hasattr(self, '_stat_values') and "当前视角" in self._stat_values:
            self._stat_values["当前视角"].configure(text=cur_name or "无")

        with self.data_lock:
            to_remove = [p for p in self.active_players if p.get("obs_source_name") and p["obs_source_name"] not in existing and not (p["name"] == cur_name)]
            for p in to_remove:
                self.active_players.remove(p)

        self.refresh_store_tree()

        self._refresh_pool_cards()
        if self.pool_label:
            total = len(self.active_players)
            active_count = sum(1 for p in self.active_players if p.get("active"))
            self.pool_label.configure(text=f"活跃池 ({active_count}/{total} 推流中)")

        self._update_log_combo()
        self._update_monitor()

    def _update_monitor(self):
        if self.monitor_window and not self.monitor_window._closed:
            self.monitor_window.update_if_open()
        if self.popup_monitor and self.popup_monitor.win.winfo_exists():
            self.popup_monitor.update_if_open()

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
        # 仅当值发生变化时才更新，避免每2秒刷新导致下拉闪烁
        if not hasattr(self, '_log_combo_cache'):
            self._log_combo_cache = None
        if hasattr(self, 'log_combo') and names != self._log_combo_cache:
            self._log_combo_cache = list(names)
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
                try:
                    if self.auto_detect.get():
                        with self.data_lock:
                            snapshot = [p for p in self.active_players if p["platform"] in ("twitch",) and not p["active"]]
                        for p in snapshot:
                            check_source(p)
                except RuntimeError:
                    pass  # 非主线程调用 tkinter 变量时忽略
                time.sleep(AUTO_DETECT_INTERVAL)
        threading.Thread(target=monitor, daemon=True).start()

    def refresh_loop(self):
        self._process_pending_commands()
        if self.obs and self.obs.connected:
            self.refresh_ui()
        self.root.after(2000, self.refresh_loop)

    def _process_pending_commands(self):
        """处理来自其他线程 (如 Flask) 的待执行命令"""
        with self._command_lock:
            commands = list(self._pending_commands)
            self._pending_commands.clear()
        for cmd in commands:
            try:
                cmd()
            except Exception as e:
                log("系统", f"[命令队列] 执行异常: {e}")

    def submit_command(self, cmd):
        """从任意线程提交一个命令到主线程执行 (线程安全)"""
        with self._command_lock:
            self._pending_commands.append(cmd)

    def _start_obs_watchdog(self):
        """OBS 连接看门狗：每10秒检测，断线后自动重连"""
        def watchdog():
            consecutive_failures = 0
            while True:
                time.sleep(10)
                try:
                    if self.obs and self.obs.connected:
                        if self.obs.is_alive():
                            consecutive_failures = 0
                            continue
                        # 连接已断开
                        log("系统", "[OBS-看门狗] 检测到 OBS 连接断开")
                        self.obs.connected = False
                        try:
                            self.root.after(0, lambda: self._on_obs_disconnected())
                        except:
                            pass
                    # 尝试重连
                    consecutive_failures += 1
                    if consecutive_failures > 12:
                        log("系统", "[OBS-看门狗] 连续重连失败超过12次 (2分钟)，暂停自动重连")
                        continue
                    if not self.obs_host:
                        continue
                    log("系统", f"[OBS-看门狗] 第 {consecutive_failures} 次尝试重连...")
                    new_obs = OBSController(self.obs_host, self.obs_port, self.obs_pwd)
                    ok, err = new_obs.connect()
                    if ok:
                        log("系统", "[OBS-看门狗] OBS 重连成功!")
                        self.obs = new_obs
                        consecutive_failures = 0
                        try:
                            self.root.after(0, lambda: self._on_obs_reconnected())
                        except:
                            pass
                    else:
                        log("系统", f"[OBS-看门狗] 重连失败: {err}")
                except Exception as e:
                    log("系统", f"[OBS-看门狗] 异常: {e}")
        threading.Thread(target=watchdog, daemon=True).start()

    def _on_obs_disconnected(self):
        """OBS 断开时的 UI 更新"""
        try:
            self.obs_status_label.configure(text="⚠ OBS 断开 (重连中...)", text_color=DANGER)
            if hasattr(self, '_stat_values') and "OBS 状态" in self._stat_values:
                self._stat_values["OBS 状态"].configure(text="断开 (重连中...)", text_color=DANGER)
        except:
            pass

    def _on_obs_reconnected(self):
        """OBS 重连成功后的恢复操作"""
        try:
            self.obs_status_label.configure(text="✅ OBS 已重连", text_color=SUCCESS)
            if hasattr(self, '_stat_values') and "OBS 状态" in self._stat_values:
                self._stat_values["OBS 状态"].configure(text="已连接", text_color=SUCCESS)
            self.setup_scene()
            # 重新同步所有活跃选手的 OBS 源
            with self.data_lock:
                for p in self.active_players:
                    if p.get("active"):
                        try:
                            self.sync_player(p)
                        except Exception as e:
                            log("系统", f"[OBS-重连] 重新同步 {p['name']} 失败: {e}")
            self.refresh_ui()
            log("系统", "[OBS-重连] 所有活跃选手源已重新同步")
        except Exception as e:
            log("系统", f"[OBS-重连] 恢复操作异常: {e}")

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
            self.monitor_window = None
        if self.popup_monitor:
            self.popup_monitor.on_close()
            self.popup_monitor = None

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
        """弹出/关闭独立监视器窗口 (与嵌入监视器完全独立，互不影响)"""
        # 如果已有独立弹出窗口，关闭它
        if self.popup_monitor and self.popup_monitor.win.winfo_exists():
            self.popup_monitor.on_close()
            self.popup_monitor = None
            return
        if not VLC_AVAILABLE:
            messagebox.showwarning("缺少依赖", "监控功能需要 python-vlc 模块。\npip install python-vlc")
            return
        # 创建独立弹出窗口 (不影响嵌入监视器)
        self.popup_monitor = MonitorWindow(self)

    def _register_frame(self, widget, role="card"):
        """注册 CTkFrame 的主题色"""
        if role == "card":
            self._register_theme(widget, "fg_color", LIGHT_THEME["CARD_BG"], DARK_THEME["CARD_BG"])
        elif role == "elevated":
            self._register_theme(widget, "fg_color", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"])
        elif role == "sidebar":
            self._register_theme(widget, "fg_color", LIGHT_THEME["SIDEBAR_BG"], DARK_THEME["SIDEBAR_BG"])

    def _register_label(self, widget):
        """注册 CTkLabel 的文字色"""
        self._register_theme(widget, "text_color", LIGHT_THEME["TEXT_PRIMARY"], DARK_THEME["TEXT_PRIMARY"])

    def _register_theme(self, widget, attr, light_val, dark_val):
        """注册需要主题色更新的控件"""
        self._theme_registry.append((widget, attr, light_val, dark_val))

    def _register_tk(self, widget, light_bg, dark_bg, light_fg=None, dark_fg=None):
        """注册 tk 原生控件（Canvas/Label/Listbox）"""
        self._register_theme(widget, "bg", light_bg, dark_bg)
        if light_fg is not None:
            self._register_theme(widget, "fg", light_fg, dark_fg)

    def _apply_theme_colors(self):
        """直接更新所有已注册控件的颜色，无需重建 UI"""
        # 更新根窗口
        try:
            self.root.configure(fg_color=LIGHT_THEME["PAGE_BG"] if _current_theme == "light" else DARK_THEME["PAGE_BG"])
        except:
            pass
        # 更新所有注册控件
        for widget, attr, light_val, dark_val in self._theme_registry:
            try:
                val = light_val if _current_theme == "light" else dark_val
                widget.configure(**{attr: val})
            except Exception:
                pass
        # 更新监视器窗口 (嵌入和独立弹出窗口都更新)
        if self.monitor_window:
            self.monitor_window.apply_theme()
        if self.popup_monitor:
            self.popup_monitor.apply_theme()
        self.set_status(f"已切换为{'浅色' if _current_theme == 'light' else '暗色'}模式")

    def _copy_web_ip(self):
        """复制手机遥控地址到剪贴板"""
        ip = get_local_ip()
        addr = f"http://{ip}:5000"
        self.root.clipboard_clear()
        self.root.clipboard_append(addr)
        self.set_status(f"已复制: {addr}")

    def _toggle_theme(self):
        """切换主题（直接替换颜色，无重建）"""
        new_theme = "light" if _current_theme == "dark" else "dark"
        switch_theme(new_theme)
        _apply_ctk_theme()
        _apply_ttk_theme()
        self._apply_theme_colors()
        # 保存主题偏好
        try:
            cfg = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["theme"] = new_theme
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except:
            pass
        self.theme_btn.configure(text="☀ 浅色主题" if new_theme == "dark" else "☾ 暗色主题")

    def show_settings(self):
        top = ctk.CTkToplevel(self.root)
        top.title("系统设置")
        top.geometry("440x340")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=CARD_BG)
        
        # 标题
        header = ctk.CTkFrame(top, fg_color="transparent")
        header.pack(fill=tk.X, padx=20, pady=(16, 8))
        ctk.CTkLabel(header, text="系统设置", font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(header, text="修改配置后自动重启服务生效", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(anchor="w", pady=(2, 0))
        
        # 内容区
        content = ctk.CTkFrame(top, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # 最大活跃推流数
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill=tk.X, pady=6)
        ctk.CTkLabel(row1, text="最大活跃推流数", font=FONT_BODY,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        var_streams = tk.IntVar(value=self.max_streams)
        ctk.CTkEntry(row1, textvariable=var_streams, width=80, height=32,
                     font=FONT_BODY, fg_color=ELEVATED_BG, border_color=BORDER).pack(side=tk.RIGHT)
        
        # 快捷键修饰键
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill=tk.X, pady=6)
        ctk.CTkLabel(row2, text="快捷键修饰键", font=FONT_BODY,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        modifier_values = ["alt+shift", "alt", "ctrl+shift", "ctrl", "shift", "ctrl+alt"]
        var_mod = tk.StringVar(value=self.hotkey_modifiers)
        combo = ctk.CTkComboBox(row2, variable=var_mod, values=modifier_values, state="readonly",
                                width=140, height=32, font=FONT_BODY,
                                fg_color=ELEVATED_BG, border_color=BORDER,
                                button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                dropdown_fg_color=CARD_BG, dropdown_text_color=TEXT_PRIMARY)
        combo.pack(side=tk.RIGHT)
        
        # OBS 连接信息
        row3 = ctk.CTkFrame(content, fg_color="transparent")
        row3.pack(fill=tk.X, pady=6)
        ctk.CTkLabel(row3, text="OBS 地址", font=FONT_BODY,
                     text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        obs_label = ctk.CTkLabel(row3, text=f"{self.obs_host}:{self.obs_port}",
                                  font=FONT_BODY, text_color=TEXT_SECONDARY)
        obs_label.pack(side=tk.RIGHT)
        
        # 按钮
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 16))
        
        def save():
            try:
                val = int(var_streams.get())
                if val < 1:
                    raise ValueError
            except:
                messagebox.showwarning("错误", "请输入正整数", parent=top)
                return
            self.max_streams = val
            self.hotkey_modifiers = var_mod.get()
            if self.pool_label:
                self.pool_label.configure(text=f"活跃池 (最多{val}个)")
            self.save_config()
            self.restart_services()
            top.destroy()
            self.set_status(f"设置已更新，服务已重启")
        
        ctk.CTkButton(btn_frame, text="保存", command=save, corner_radius=6,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF",
                      font=FONT_BODY_BOLD, height=36, width=100).pack(side=tk.RIGHT, padx=(8, 0))
        ctk.CTkButton(btn_frame, text="取消", command=top.destroy, corner_radius=6,
                      fg_color=ELEVATED_BG, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY,
                      font=FONT_BODY, height=36, width=100).pack(side=tk.RIGHT)

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
        lbl = ctk.CTkLabel(top, text="请粘贴链接或频道名，每行一个：", font=FONT_SMALL)
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
    root.geometry("1220x950")
    root.minsize(1000, 700)
    ManagerApp(root)
    root.mainloop()