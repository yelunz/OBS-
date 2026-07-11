import json, os, sys, time, threading, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pynput import keyboard
from obswebsocket import obsws, requests

# 尝试导入窗口控制库
GW_AVAILABLE = False
try:
    import pygetwindow as gw
    GW_AVAILABLE = True
except:
    pass
import ctypes

BASE_DIR = r"C:\myobs"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def mute_browser_window(window_title, mute=True):
    """模拟 Ctrl+M 静音/取消静音浏览器窗口"""
    if not GW_AVAILABLE:
        return
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return
        win = windows[0]
        prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SetForegroundWindow(win._hWnd)
        time.sleep(0.1)
        kb = keyboard.Controller()
        kb.press(keyboard.Key.ctrl)
        kb.press('m')
        kb.release('m')
        kb.release(keyboard.Key.ctrl)
        time.sleep(0.1)
        if prev_hwnd:
            ctypes.windll.user32.SetForegroundWindow(prev_hwnd)
        action = "静音" if mute else "取消静音"
        log(f"已对窗口 {window_title} 执行{action}")
    except Exception as e:
        log(f"静音操作失败: {e}")

cfg = load_config()
OBS_HOST = cfg["obs_host"]
OBS_PORT = cfg["obs_port"]
OBS_PASSWORD = cfg["obs_password"]
SCENE_NAME = cfg.get("scene_name", None)
MODIFIER = cfg.get("hotkey_modifiers", "alt+shift")

ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
try:
    ws.connect()
    log("OBS 连接成功")
except Exception as e:
    log(f"OBS 连接失败: {e}")
    sys.exit(1)

if SCENE_NAME:
    try:
        ws.call(requests.SetCurrentProgramScene(sceneName=SCENE_NAME))
    except:
        SCENE_NAME = ws.call(requests.GetCurrentProgramScene()).getSceneName()
else:
    SCENE_NAME = ws.call(requests.GetCurrentProgramScene()).getSceneName()
log(f"场景: {SCENE_NAME}  修饰键: {MODIFIER}")

def refresh_hotkey_map():
    cfg = load_config()
    players = cfg["players"]
    hotkey_map = {}
    for p in players:
        hk = p.get("hotkey", "")
        if len(hk) == 1 and hk.isalnum():
            hotkey_map[hk] = p
    items = ws.call(requests.GetSceneItemList(sceneName=SCENE_NAME)).getSceneItems()
    source_to_id = {item["sourceName"]: item["sceneItemId"] for item in items}
    return hotkey_map, source_to_id

hotkey_map, source_to_id = refresh_hotkey_map()

def ensure_obs_connected():
    global ws, SCENE_NAME, hotkey_map, source_to_id
    try:
        ws.call(requests.GetVersion())
        return True
    except:
        try:
            ws.disconnect()
        except:
            pass
        try:
            ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            ws.connect()
            if SCENE_NAME:
                ws.call(requests.SetCurrentProgramScene(sceneName=SCENE_NAME))
            hotkey_map, source_to_id = refresh_hotkey_map()
            log("OBS 重连成功")
            return True
        except Exception as e:
            log(f"OBS 重连失败: {e}")
            return False

def set_mute(source_name, mute):
    try:
        ws.call(requests.SetInputMute(inputName=source_name, inputMuted=mute))
    except Exception as e:
        log(f"静音设置失败 {source_name}: {e}")

def set_visible(name, visible):
    id_ = source_to_id.get(name)
    if id_ is None:
        log(f"源 {name} 不存在")
        return
    ws.call(requests.SetSceneItemEnabled(sceneName=SCENE_NAME, sceneItemId=id_, sceneItemEnabled=visible))

def switch_to(target_player):
    if not ensure_obs_connected():
        log("OBS 不可用")
        return

    plat = target_player["platform"]
    name = target_player["name"]

    # 网页源（bilibili / custom_web）
    if plat in ("bilibili", "custom_web"):
        target_name = target_player.get("obs_source_name")
        if not target_name or target_name not in source_to_id:
            log(f"网页源 {target_name} 不存在")
            return

        # 先静音之前的网页源（如果有）
        for p in hotkey_map.values():
            if p["platform"] in ("bilibili", "custom_web") and p.get("obs_source_name"):
                src = p["obs_source_name"]
                if src != target_name and src in source_to_id:
                    # 静音浏览器窗口
                    mute_browser_window(p.get("window_title", ""), mute=True)
                    set_mute(src, True)
                    set_visible(src, False)

        # 取消静音当前网页源
        mute_browser_window(target_player.get("window_title", ""), mute=False)
        set_mute(target_name, False)
        set_visible(target_name, True)
        log(f"已切换至网页模式 ({name})")
        return

    # Twitch / 抖音
    if plat not in ("twitch", "douyin"):
        return

    target_name = target_player.get("obs_source_name")
    if not target_name or target_name not in source_to_id:
        log(f"源 {target_name} 不存在")
        return

    # 关闭所有其他源（包括网页源）
    for p in hotkey_map.values():
        src = p.get("obs_source_name")
        if src and src != target_name and src in source_to_id:
            if p["platform"] in ("bilibili", "custom_web"):
                mute_browser_window(p.get("window_title", ""), mute=True)
            set_mute(src, True)
            set_visible(src, False)

    set_mute(target_name, False)
    set_visible(target_name, True)
    log(f"已切换至 {name}")

class HotkeyListener:
    def __init__(self, modifier):
        self.modifier = modifier
        self.alt = False; self.ctrl = False; self.shift = False
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        log(f"热键监听已启动 ({self.modifier}+快捷键)")

    def stop(self):
        if self.listener:
            self.listener.stop()
            log("监听已停止")

    def restart(self, new_mod):
        self.stop()
        self.modifier = new_mod
        self.alt = self.ctrl = self.shift = False
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        log(f"热键监听已重启 ({self.modifier}+快捷键)")

    def main_ok(self):
        if "alt" in self.modifier and not self.alt: return False
        if "ctrl" in self.modifier and not self.ctrl: return False
        return True

    def on_press(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr): self.alt = True
        elif key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r): self.ctrl = True
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r): self.shift = True
        if not self.main_ok(): return
        if "shift" in self.modifier and not self.shift: return
        if hasattr(key, 'char') and key.char is not None:
            k = key.char
            if k in hotkey_map:
                try:
                    switch_to(hotkey_map[k])
                except Exception as e:
                    log(f"切换错误 {k}: {e}")

    def on_release(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr): self.alt = False
        elif key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r): self.ctrl = False
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r): self.shift = False

listener = HotkeyListener(MODIFIER)

def watch_config():
    global hotkey_map, source_to_id, SCENE_NAME, MODIFIER, listener
    last_mtime = os.path.getmtime(CONFIG_FILE)
    while True:
        time.sleep(3)
        if not ensure_obs_connected():
            continue
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime != last_mtime:
                cfg = load_config()
                new_scene = cfg.get("scene_name")
                new_mod = cfg.get("hotkey_modifiers", "alt+shift")
                if new_scene and new_scene != SCENE_NAME:
                    ws.call(requests.SetCurrentProgramScene(sceneName=new_scene))
                    SCENE_NAME = new_scene
                hotkey_map, source_to_id = refresh_hotkey_map()
                last_mtime = mtime
                if new_mod != MODIFIER:
                    MODIFIER = new_mod
                    listener.restart(MODIFIER)
                log("快捷键映射已更新")
        except Exception as e:
            log(f"监控配置出错: {e}")

threading.Thread(target=watch_config, daemon=True).start()
log("Switcher 运行中")
listener.listener.join()
ws.disconnect()