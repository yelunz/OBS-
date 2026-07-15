"""
switcher.py - OBS多视角切换器的热键监听服务

可作为独立脚本运行 (python switcher.py)，也可作为模块导入:
    from switcher import SwitcherService
    svc = SwitcherService(log_callback=...)
    svc.start()
    ...
    svc.stop()

设计说明:
    原本主程序通过 subprocess.Popen([sys.executable, "switcher.py"]) 启动本脚本。
    但在 PyInstaller 打包模式下, sys.executable 指向主程序 exe,
    会导致再次启动主UI (而非 switcher), 形成无限循环。
    因此重构为可导入模块, 由主程序以线程方式运行。
"""

import json, os, sys, time, threading, io

# 独立运行时设置 UTF-8 输出 (导入模式下不需要, 主程序已处理)
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pynput import keyboard
from obswebsocket import obsws, requests

# ==================== 路径配置 ====================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_user_data_dir():
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        return os.path.join(appdata, "OBS多视角切换器")
    return os.path.join(BASE_DIR, "data")

USER_DATA_DIR = get_user_data_dir()
os.makedirs(USER_DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.json")


def _default_log(msg):
    """默认日志输出 (独立运行时使用)"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 热键监听器 ====================
class HotkeyListener:
    """监听全局热键, 触发 OBS 视角切换"""

    def __init__(self, modifier, switcher):
        self.modifier = modifier
        self.switcher = switcher          # SwitcherService 引用
        self.alt = False
        self.ctrl = False
        self.shift = False
        self.listener = None

    def start(self):
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.switcher._log(f"热键监听已启动 ({self.modifier}+快捷键)")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
            self.switcher._log("监听已停止")

    def restart(self, new_mod):
        self.stop()
        self.modifier = new_mod
        self.alt = self.ctrl = self.shift = False
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.switcher._log(f"热键监听已重启 ({self.modifier}+快捷键)")

    def main_ok(self):
        """检查主修饰键是否按下"""
        if "alt" in self.modifier and not self.alt:
            return False
        if "ctrl" in self.modifier and not self.ctrl:
            return False
        return True

    def on_press(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            self.alt = True
        elif key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl = True
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift = True
        if not self.main_ok():
            return
        if "shift" in self.modifier and not self.shift:
            return
        if hasattr(key, 'char') and key.char is not None:
            k = key.char
            if k in self.switcher.hotkey_map:
                try:
                    self.switcher.switch_to(self.switcher.hotkey_map[k])
                except Exception as e:
                    self.switcher._log(f"切换错误 {k}: {e}")

    def on_release(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            self.alt = False
        elif key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl = False
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift = False


# ==================== 切换器服务 ====================
class SwitcherService:
    """
    可嵌入主程序的切换器服务 (线程模式)。
    替代原 subprocess.Popen 启动 switcher.py 的方式,
    避免 PyInstaller 打包后 sys.executable 指向主程序 exe 导致的无限循环问题。
    """

    def __init__(self, log_callback=None):
        self._log_cb = log_callback or _default_log
        self.ws = None
        self.listener = None
        self._watcher_thread = None
        self._running = False
        self.SCENE_NAME = None
        self.MODIFIER = "alt+shift"
        self.hotkey_map = {}
        self.source_to_id = {}
        # OBS 连接参数 (start 时从配置加载)
        self._obs_host = None
        self._obs_port = None
        self._obs_password = None

    def _log(self, msg):
        """统一日志接口"""
        try:
            self._log_cb(msg)
        except Exception:
            _default_log(msg)

    # ---------- OBS 连接 ----------
    def _connect_obs(self):
        """连接 OBS WebSocket, 失败返回 False"""
        cfg = load_config()
        self._obs_host = cfg["obs_host"]
        self._obs_port = cfg["obs_port"]
        self._obs_password = cfg["obs_password"]
        self.SCENE_NAME = cfg.get("scene_name")
        self.MODIFIER = cfg.get("hotkey_modifiers", "alt+shift")

        self.ws = obsws(self._obs_host, self._obs_port, self._obs_password)
        try:
            self.ws.connect()
            self._log("OBS 连接成功")
            return True
        except Exception as e:
            self._log(f"OBS 连接失败: {e}")
            return False

    def _setup_scene(self):
        """设置当前场景"""
        if self.SCENE_NAME:
            try:
                self.ws.call(requests.SetCurrentProgramScene(sceneName=self.SCENE_NAME))
            except Exception:
                self.SCENE_NAME = self.ws.call(requests.GetCurrentProgramScene()).getSceneName()
        else:
            self.SCENE_NAME = self.ws.call(requests.GetCurrentProgramScene()).getSceneName()
        self._log(f"场景: {self.SCENE_NAME}  修饰键: {self.MODIFIER}")

    def ensure_obs_connected(self):
        """检查 OBS 连接, 断线时自动重连"""
        try:
            self.ws.call(requests.GetVersion())
            return True
        except Exception:
            try:
                self.ws.disconnect()
            except Exception:
                pass
            try:
                self.ws = obsws(self._obs_host, self._obs_port, self._obs_password)
                self.ws.connect()
                if self.SCENE_NAME:
                    self.ws.call(requests.SetCurrentProgramScene(sceneName=self.SCENE_NAME))
                self.refresh_hotkey_map()
                self._log("OBS 重连成功")
                return True
            except Exception as e:
                self._log(f"OBS 重连失败: {e}")
                return False

    # ---------- 热键映射 ----------
    def refresh_hotkey_map(self):
        """从配置文件刷新热键映射和源ID映射"""
        cfg = load_config()
        players = cfg["players"]
        hotkey_map = {}
        for p in players:
            hk = p.get("hotkey", "")
            if len(hk) == 1 and hk.isalnum():
                hotkey_map[hk] = p
        items = self.ws.call(requests.GetSceneItemList(sceneName=self.SCENE_NAME)).getSceneItems()
        source_to_id = {item["sourceName"]: item["sceneItemId"] for item in items}
        self.hotkey_map = hotkey_map
        self.source_to_id = source_to_id
        return hotkey_map, source_to_id

    # ---------- OBS 源操作 ----------
    def set_mute(self, source_name, mute):
        try:
            self.ws.call(requests.SetInputMute(inputName=source_name, inputMuted=mute))
        except Exception as e:
            self._log(f"静音设置失败 {source_name}: {e}")

    def set_visible(self, name, visible):
        id_ = self.source_to_id.get(name)
        if id_ is None:
            self._log(f"源 {name} 不存在")
            return
        self.ws.call(requests.SetSceneItemEnabled(sceneName=self.SCENE_NAME, sceneItemId=id_, sceneItemEnabled=visible))

    def switch_to(self, target_player):
        """切换至目标视角: 隐藏并静音其他源, 显示并取消静音目标源"""
        if not self.ensure_obs_connected():
            self._log("OBS 不可用")
            return

        name = target_player["name"]
        target_name = target_player.get("obs_source_name")
        if not target_name or target_name not in self.source_to_id:
            self._log(f"源 {target_name} 不存在")
            return

        # 统一处理所有平台: 隐藏并静音其他源, 显示并取消静音目标源
        for p in self.hotkey_map.values():
            src = p.get("obs_source_name")
            if src and src != target_name and src in self.source_to_id:
                self.set_mute(src, True)
                self.set_visible(src, False)

        self.set_mute(target_name, False)
        self.set_visible(target_name, True)
        self._log(f"已切换至 {name}")

    # ---------- 配置监控 ----------
    def _watch_config(self):
        """每3秒检查配置文件变化, 自动刷新热键映射和修饰键"""
        last_mtime = os.path.getmtime(CONFIG_FILE)
        while self._running:
            time.sleep(3)
            if not self._running:
                break
            if not self.ensure_obs_connected():
                continue
            try:
                mtime = os.path.getmtime(CONFIG_FILE)
                if mtime != last_mtime:
                    cfg = load_config()
                    new_scene = cfg.get("scene_name")
                    new_mod = cfg.get("hotkey_modifiers", "alt+shift")
                    if new_scene and new_scene != self.SCENE_NAME:
                        self.ws.call(requests.SetCurrentProgramScene(sceneName=new_scene))
                        self.SCENE_NAME = new_scene
                    self.refresh_hotkey_map()
                    last_mtime = mtime
                    if new_mod != self.MODIFIER:
                        self.MODIFIER = new_mod
                        if self.listener:
                            self.listener.restart(new_mod)
                    self._log("快捷键映射已更新")
            except Exception as e:
                self._log(f"监控配置出错: {e}")

    # ---------- 生命周期 ----------
    def start(self):
        """启动切换器服务 (非阻塞): 连接OBS, 启动热键监听和配置监控线程"""
        if self._running:
            self._log("Switcher 服务已在运行")
            return True
        if not self._connect_obs():
            return False
        self._setup_scene()
        self.refresh_hotkey_map()

        # 启动热键监听
        self.listener = HotkeyListener(self.MODIFIER, self)
        self.listener.start()

        # 启动配置监控线程
        self._running = True
        self._watcher_thread = threading.Thread(target=self._watch_config, daemon=True)
        self._watcher_thread.start()
        self._log("Switcher 服务已启动")
        return True

    def stop(self):
        """停止切换器服务: 停止热键监听, 断开OBS, 停止监控线程"""
        self._running = False
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
        if self.ws:
            try:
                self.ws.disconnect()
            except Exception:
                pass
            self.ws = None
        self._log("Switcher 服务已停止")


# ==================== 独立运行入口 ====================
if __name__ == "__main__":
    service = SwitcherService()
    if service.start():
        _default_log("Switcher 运行中")
        try:
            while service._running:
                time.sleep(1)
        except KeyboardInterrupt:
            service.stop()
    else:
        sys.exit(1)
