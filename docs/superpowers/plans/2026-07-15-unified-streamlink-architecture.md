# 统一 Streamlink 架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将三平台（Twitch/B站/抖音）直播流获取方式统一为 Streamlink + RTMP + VLC，移除OBS浏览器源和截图轮询，恢复"只显示当前视角"的传统开关逻辑，修复VLC源不刷新不显示的bug。

**Architecture:** Streamlink 解析网页链接获取最高画质流 → ffmpeg 转封装为RTMP → MediaMTX → OBS VLC源(显示) + 监视器VLC嵌入(预览)。所有平台统一代码路径，OBS切换时正常隐藏/显示所有源。

**Tech Stack:** Python, Streamlink, ffmpeg, MediaMTX, OBS WebSocket v5, python-vlc, pynput, Tkinter

**Spec:** `docs/superpowers/specs/2026-07-15-unified-streamlink-architecture-design.md`

---

## 文件结构

**修改文件:**
- `c:\myobs\manager_ui.pyw` — 主应用，所有核心变更集中在此

**不修改文件:**
- `c:\myobs\switcher.py` — 快捷键监听器，依赖 `obs_source_name`（保持不变）
- `c:\myobs\web_remote.py` — Flask 遥控（保持不变）
- `c:\myobs\config.json` — 由程序运行时管理，不在代码中硬编码

**关键代码位置（修改前）:**
- `OBSController.create_vlc` — 行 280-313（需增强：主动触发播放）
- `OBSController.create_browser_source` — 行 359-384（将不再调用，保留方法以防万一）
- `start_stream` — 行 587-626（需重写：统一三平台）
- `_stream_process_monitor` — 行 536-574（需修改：抖音无限重试）
- `MonitorWindow.__init__` 截图相关字段 — 行 934-937（需移除）
- `MonitorWindow._full_cleanup` — 行 1107（需清理截图字段引用）
- `MonitorWindow._check_vlc_health` — 行 1207（保持，已恢复调用）
- `MonitorWindow._show_grid` — 行 1293-1340（需重写：统一VLC嵌入）
- `MonitorWindow._start_screenshot_monitor` — 行 1544-1620（需移除）
- `MonitorWindow._ensure_screenshot_render_loop` / `_screenshot_render_loop` — 行 1620-1663（需移除）
- `ManagerApp.load_cfg` — 行 1889-1954（需增加配置迁移）
- `ManagerApp._switch_thread` — 行 2716-2759（需重写：恢复全部隐藏）
- `ManagerApp.refresh_player` — 行 2761-2771（需重写：三平台通用刷新）
- `ManagerApp.sync_player` — 行 2788-2830（需重写：统一VLC源）
- `ManagerApp.activate_player` — 行 2645-2679（需修改：所有平台启动进程监控）

---

### Task 1: 新增 OBSController 媒体控制方法

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (OBSController 类，行 313 之后插入)

**目的**: 为 VLC 源主动触发播放/重启/检查状态，解决"不刷新不显示"的根因。

- [ ] **Step 1: 在 OBSController 类中新增三个方法**

在 `set_visibility` 方法（约行 414-422）之后，插入以下方法：

```python
    def trigger_media_play(self, name):
        """主动触发VLC源播放，解决 always_play 不生效导致画面不显示的问题"""
        try:
            self.ws.call(requests.TriggerMediaInputAction(
                inputName=name,
                mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY"
            ))
            log("系统", f"[OBS-触发播放] {name}")
        except Exception as e:
            log("系统", f"[OBS-触发播放失败] {name}: {e}")

    def trigger_media_restart(self, name):
        """重启VLC源播放，用于刷新功能"""
        try:
            self.ws.call(requests.TriggerMediaInputAction(
                inputName=name,
                mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
            ))
            log("系统", f"[OBS-重启播放] {name}")
        except Exception as e:
            log("系统", f"[OBS-重启播放失败] {name}: {e}")

    def get_media_state(self, name):
        """获取VLC源播放状态，返回 None 或状态字符串"""
        try:
            resp = self.ws.call(requests.GetMediaInputStatus(inputName=name))
            return resp.getMediaState()
        except Exception:
            return None
```

- [ ] **Step 2: 增强 create_vlc 方法，创建后主动触发播放**

将 `create_vlc` 方法（行 280-313）末尾的静音隐藏之后，追加主动触发播放逻辑。修改后的完整方法：

```python
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
        # 主动触发播放: always_play 有时不生效，用 TriggerMediaInputAction 兜底
        self.trigger_media_play(name)
```

- [ ] **Step 3: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 4: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(obs): 新增TriggerMediaInputAction主动触发播放，修复VLC源不显示"
```

---

### Task 2: 重写 start_stream 统一三平台 Streamlink 推流

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 587-626)

**目的**: 三平台统一用 streamlink 解析网页链接 → ffmpeg 转封装 → RTMP 推流。

- [ ] **Step 1: 重写 start_stream 函数**

将行 587-626 的 `start_stream` 函数完整替换为：

```python
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

    # 统一三平台: streamlink 解析网页链接 → ffmpeg 转封装为 RTMP
    # Twitch: twitch.tv/频道名 (streamlink 原生支持)
    # B站: live.bilibili.com/房间号 (streamlink bilibili 插件)
    # 抖音: live.douyin.com/房间号 (streamlink douyin 插件, 自动处理token)
    url = player.get("url", "")
    if not url:
        log("系统", f"[推流-失败] {name} 无 url 字段")
        return False

    cmd1 = ["streamlink", url, qual, "--retry-max", "5", "--retry-streams", "5", "-O"]
    cmd2 = [FFMPEG, "-re", "-i", "pipe:0", "-c", "copy", "-f", "flv", rtmp]
    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    p1.stdout.close()
    player["stream_pid"] = p2.pid
    read_stream_output(p2, "", name, obs, sn)
    log("系统", f"[推流-启动] {name} 平台={plat} URL={url} -> {rtmp}")

    return True
```

- [ ] **Step 2: 修改 _stream_process_monitor，抖音无限重试**

将行 536-574 的 `_stream_process_monitor` 函数中的 `max_retries = 3` 改为按平台区分。修改后的完整函数：

```python
def _stream_process_monitor(player, obs_ref):
    """监控推流进程：进程退出时自动重启
    抖音流token约30分钟过期，属于正常现象，无限重试
    其他平台重试3次后停止"""
    plat = player.get("platform")
    max_retries = 999999 if plat == "douyin" else 3  # 抖音无限重试
    retry_count = 0
    while retry_count < max_retries:
        time.sleep(15)
        try:
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
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    continue
            except psutil.NoSuchProcess:
                pass
            retry_count += 1
            log_label = f"第 {retry_count} 次" if plat != "douyin" else f"第 {retry_count} 次 (抖音token刷新)"
            log("系统", f"[推流监控] {player['name']} 推流进程已退出，{log_label} 自动重启...")
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
```

- [ ] **Step 3: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 4: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(stream): 统一三平台Streamlink推流，抖音token无限重试"
```

---

### Task 3: 配置迁移 — 统一 url 字段

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 1925-1950, load_cfg 中的选手加载循环)

**目的**: 将旧的 `twitch_url`/`douyin_url`/`browser_url`/`channel` 字段合并到统一的 `url` 字段。

- [ ] **Step 1: 修改 load_cfg 中的选手对象构建**

将行 1932-1949 的 `player_obj` 构建替换为（增加 url 字段迁移逻辑，移除旧字段）：

```python
            # 配置迁移: 统一 url 字段，兼容旧配置
            url = p.get("url", "")
            if not url:
                # 旧配置迁移: 按平台从旧字段提取 URL
                if p.get("platform") == "twitch":
                    url = p.get("twitch_url", "") or p.get("channel", "")
                    if url and not url.startswith("http"):
                        url = f"https://www.twitch.tv/{url}"
                elif p.get("platform") == "douyin":
                    url = p.get("douyin_url", "")
                elif p.get("platform") in ("bilibili", "custom_web"):
                    url = p.get("browser_url", "")
            player_obj = {
                "id": pid,
                "name": p.get("name", ""),
                "hotkey": p.get("hotkey", ""),
                "platform": p.get("platform", "bilibili"),
                "room_id": p.get("room_id", ""),
                "url": url,  # 统一字段
                "quality": p.get("quality", "best"),
                "view_label": normalize_view_label(p.get("view_label", 0)),
                "stream_name": p.get("stream_name", f"player{pid}"),
                "obs_source_name": "",  # 启动时清空，避免残留无效源名
                "active": False,
                "source_ok": None,
                "stream_pid": None,
                "window_title": f"OBS_Window_{p.get('name', '')}"
            }
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(config): 统一url字段，迁移旧配置(twitch_url/douyin_url/browser_url)"
```

---

### Task 4: 重写 sync_player 统一VLC源创建

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 2788-2830)

**目的**: 所有平台统一调用 `create_vlc` 创建VLC源，移除浏览器源分支。

- [ ] **Step 1: 重写 sync_player 方法**

将行 2788-2830 的 `sync_player` 方法完整替换为：

```python
    def sync_player(self, player):
        if not self.obs or not self.obs.connected:
            return
        # 统一所有平台: 创建 VLC 源读取 RTMP 流
        # URL 由 streamlink 解析网页链接获得，OBS VLC 源读取本地 RTMP 流
        desired = f"{player['name']}_{player['view_label']}_{player['hotkey']}"
        rtmp_url = f"rtmp://localhost:1935/live/{player['stream_name']}"
        old = player.get("obs_source_name")
        if old and self.obs.source_exists(old):
            if old != desired:
                if self.obs.source_exists(desired):
                    self.obs.remove_source(desired)
                if not self.obs.rename_source(old, desired):
                    self.obs.remove_source(old)
                    self.obs.create_vlc(desired, rtmp_url)
        elif not self.obs.source_exists(desired):
            log("系统", f"[sync_player] 创建 VLC 源: {desired}")
            self.obs.create_vlc(desired, rtmp_url)
        player["obs_source_name"] = desired
        log("系统", f"sync_player 完成: {player['name']} -> {desired} (VLC源)")
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(sync): 统一sync_player创建VLC源，移除浏览器源分支"
```

---

### Task 5: 重写 _switch_thread 恢复全部隐藏逻辑

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 2716-2759)

**目的**: 切换视角时隐藏并静音所有其他源（包括B站/抖音），显示当前源后主动触发播放。

- [ ] **Step 1: 重写 _switch_thread 方法**

将行 2716-2759 的 `_switch_thread` 方法完整替换为：

```python
    def _switch_thread(self, player):
        """后台线程执行 OBS 切换: 恢复传统开关逻辑，所有非当前源隐藏并静音"""
        try:
            src_name = player.get("obs_source_name")
            if not src_name:
                return
            item_map = self.obs.get_scene_item_map()
            if src_name not in item_map:
                log("系统", f"[切换-失败] 源不在场景中: {src_name}")
                return

            with self.data_lock:
                active_snapshot = list(self.active_players)

            # 1. 隐藏并静音所有其他源 (恢复传统逻辑, 不再保留浏览器源可见)
            for p in active_snapshot:
                p_src = p.get("obs_source_name")
                if not p_src or p_src == src_name or p_src not in item_map:
                    continue
                self.obs.set_mute(p_src, True)
                self.obs.set_visibility(p_src, False)

            # 2. 显示并取消静音当前源
            self.obs.set_visibility(src_name, True)
            self.obs.set_mute(src_name, False)

            # 3. 主动触发播放 (解决 always_play 不生效)
            self.obs.trigger_media_play(src_name)

            log("系统", f"[切换-完成] 视角至 {player['name']}")
            self.current_log_player.set(player["name"])
            self.root.after(1, self.refresh_ui)
        except Exception as e:
            log("系统", f"[切换-异常] {player['name']}: {e}")
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "fix(switch): 恢复全部隐藏逻辑，切换后主动触发播放"
```

---

### Task 6: 重写 _show_grid 统一VLC嵌入

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 1293-1340)

**目的**: 所有平台统一用VLC嵌入canvas播放RTMP流，移除截图轮询分支。

- [ ] **Step 1: 重写 _show_grid 方法**

将行 1293-1340 的 `_show_grid` 方法完整替换为：

```python
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
        # 注意: 不在 canvas/frame/label 上绑定 <Button-1>,
        # 改由 pynput 全局鼠标钩子统一处理点击跳转 (VLC 嵌入的 Win32 子窗口
        # 会拦截 Tkinter 事件, pynput 是 OS 级钩子不受影响)
        self.grid_widgets[name] = (frame, canvas, name_label)
        log("系统", f"[监视器-显示-步骤2] 创建网格: {name}")

        # 统一所有平台: VLC 嵌入 canvas 播放 RTMP 流
        # (不再使用 OBS 截图轮询, VLC 帧率远高于截图)
        if name not in self.vlc_instances:
            default_sn = f"player{player['id']}"
            stream_name = player.get("stream_name", default_sn)
            rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
            self.win.after(2000, self._start_vlc, name, canvas, rtmp_url)
            # 6s 后兜底重试 (流未就绪时 VLC 可能连接失败)
            self.win.after(6000, self._retry_vlc, name, canvas, rtmp_url)
            log("系统", f"[监视器-显示-VLC] 安排 VLC 启动: {name} -> {rtmp_url}")
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(monitor): 统一_show_grid为VLC嵌入，移除截图轮询分支"
```

---

### Task 7: 移除截图轮询相关代码

**Files:**
- Modify: `c:\myobs\manager_ui.pyw`

**目的**: 移除不再使用的截图轮询相关方法和字段，保持代码整洁。

- [ ] **Step 1: 移除 _start_screenshot_monitor 方法**

用 Edit 工具删除 `_start_screenshot_monitor` 方法（约行 1544-1553）。将整个方法替换为空（删除方法定义）。

old_string (匹配整个方法):
```python
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

```
new_string: (空字符串)

- [ ] **Step 2: 移除 _stop_screenshot_monitor 方法**

同样删除 `_stop_screenshot_monitor` 方法（约行 1555-1561）。

- [ ] **Step 3: 移除 _screenshot_thread 方法**

用 Grep 定位 `_screenshot_thread` 的行范围，删除整个方法（从 `def _screenshot_thread` 到下一个 `def` 之前）。

- [ ] **Step 4: 移除 _ensure_screenshot_render_loop 和 _screenshot_render_loop 方法**

同样用 Grep 定位并删除这两个方法。

- [ ] **Step 5: 修改 _hide_grid 中的截图停止调用**

在 `_hide_grid` 方法（行 1342）中，移除对 `_stop_screenshot_monitor` 的调用。用 Grep 找到 `if name in self.screenshot_running:` 这段代码，移除截图停止逻辑（VLC 清理逻辑保留）。

- [ ] **Step 6: 修改 _full_cleanup 中的截图字段清理**

在 `_full_cleanup` 方法（行 1107）中，移除对 `screenshot_canvases`/`screenshot_frames`/`screenshot_running` 的清理（这些字段将不再存在）。保留 VLC 清理逻辑。

- [ ] **Step 7: 移除 MonitorWindow.__init__ 中的截图字段初始化**

在 `__init__`（行 934-937）中，移除以下四行：
```python
        self.screenshot_canvases = {}  # name -> canvas
        self.screenshot_frames = {}    # name -> bytes (latest JPEG frame)
        self.screenshot_running = {}   # name -> bool
        self.screenshot_lock = threading.Lock()
```

- [ ] **Step 8: 移除文件顶部的 PIL_AVAILABLE 检测**

在文件顶部（约行 189-192），移除：
```python
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    pass
```

- [ ] **Step 9: 全局搜索确认无残留引用**

Run: 用 Grep 搜索 `screenshot_canvases|screenshot_frames|screenshot_running|screenshot_lock|_start_screenshot|_stop_screenshot|_screenshot_thread|_ensure_screenshot_render|_screenshot_render_loop|PIL_AVAILABLE`
Expected: 无匹配（或只在注释中出现）

- [ ] **Step 10: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 11: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(cleanup): 移除截图轮询相关代码(PIL/screenshot_*)"
```

---

### Task 8: 修改 activate_player 启动所有平台的进程监控

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 2672-2674)

**目的**: 所有平台现在都用 streamlink 推流，都需要进程监控。

- [ ] **Step 1: 修改 activate_player 中的进程监控启动条件**

将行 2672-2674：
```python
                # 启动推流进程监控 (仅 Twitch/抖音 需要，浏览器源平台无需)
                if player["platform"] in ("twitch", "douyin"):
                    threading.Thread(target=_stream_process_monitor, args=(player, self.obs), daemon=True).start()
```
替换为：
```python
                # 启动推流进程监控 (所有平台都用 streamlink 推流，都需要监控)
                threading.Thread(target=_stream_process_monitor, args=(player, self.obs), daemon=True).start()
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "fix(activate): 所有平台启动进程监控(统一streamlink推流)"
```

---

### Task 9: 重写 refresh_player 三平台通用刷新

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (行 2761-2771)

**目的**: 刷新功能支持所有平台，重启推流管线 + 重启OBS VLC源 + 重连监视器VLC。

- [ ] **Step 1: 重写 refresh_player 方法**

将行 2761-2771 的 `refresh_player` 方法完整替换为：

```python
    def refresh_player(self, player):
        """刷新选手推流: 重启推流管线 + 重启OBS VLC源 + 重连监视器VLC
        三平台通用，不再仅限 Twitch"""
        if not player.get("active"):
            self.activate_player(player)
            return
        name = player["name"]
        log("系统", f"[刷新-开始] {name} 平台={player['platform']}")
        def do_refresh():
            try:
                # 1. 停止并重启推流管线
                stop_stream(player)
                time.sleep(1)
                if not start_stream(player, self.obs):
                    log("系统", f"[刷新-推流失败] {name}")
                    self.root.after(0, lambda: messagebox.showwarning("刷新", f"{name} 推流重启失败"))
                    return
                # 2. 重启 OBS VLC 源播放
                src_name = player.get("obs_source_name")
                if src_name and self.obs and self.obs.connected:
                    self.obs.trigger_media_restart(src_name)
                # 3. 重连监视器 VLC 实例
                if self.monitor_window and not self.monitor_window._closed:
                    if name in self.monitor_window.vlc_instances:
                        try:
                            _, mp, canvas = self.monitor_window.vlc_instances[name]
                            mp.stop()
                            time.sleep(0.5)
                            mp.play()
                            log("系统", f"[刷新-监视器VLC重连] {name}")
                        except Exception as e:
                            log("系统", f"[刷新-监视器VLC异常] {name}: {e}")
                log("系统", f"[刷新-完成] {name}")
                self.root.after(0, self.refresh_ui)
            except Exception as e:
                log("系统", f"[刷新-异常] {name}: {e}")
        threading.Thread(target=do_refresh, daemon=True).start()
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(refresh): 三平台通用刷新功能(重启推流+OBS源+监视器VLC)"
```

---

### Task 10: 移除 set_source_index 和 _make_vlc_clickthrough 死代码

**Files:**
- Modify: `c:\myobs\manager_ui.pyw`

**目的**: 清理不再使用的层级覆盖和点击穿透方法。

- [ ] **Step 1: 用 Grep 定位 set_source_index 方法**

Run: Grep `def set_source_index`

- [ ] **Step 2: 删除 set_source_index 方法**

删除整个方法（从 `def set_source_index` 到下一个 `def` 之前）。

- [ ] **Step 3: 用 Grep 定位 _make_vlc_clickthrough 方法**

Run: Grep `def _make_vlc_clickthrough`

- [ ] **Step 4: 删除 _make_vlc_clickthrough 方法**

删除整个方法。

- [ ] **Step 5: 确认无残留调用**

Run: Grep `set_source_index|_make_vlc_clickthrough`
Expected: 无匹配

- [ ] **Step 6: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 7: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(cleanup): 移除set_source_index和_make_vlc_clickthrough死代码"
```

---

### Task 11: 集成测试与最终验证

**Files:**
- Test: 手动功能测试 + 语法检查

- [ ] **Step 1: 完整语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（成功）

- [ ] **Step 2: 搜索所有残留的旧字段引用**

Run: Grep `douyin_url|browser_url|twitch_url|create_browser_source`
Expected: 只在 `create_browser_source` 方法定义中出现（保留方法但不调用），其他无匹配

- [ ] **Step 3: 搜索所有残留的截图引用**

Run: Grep `screenshot_|PIL_AVAILABLE|_make_vlc_clickthrough|set_source_index`
Expected: 无匹配

- [ ] **Step 4: 推送到远程**

```bash
git push
```

- [ ] **Step 5: 手动功能测试清单**

请用户重启应用并验证以下场景：

**必测项:**
1. [ ] Twitch选手推流：OBS显示画面 + 监视器显示画面
2. [ ] B站选手推流：OBS显示画面 + 监视器显示画面（画质与浏览器源方案相同）
3. [ ] 抖音选手推流：OBS显示画面 + 监视器显示画面
4. [ ] 三平台混合：同时推流，OBS和监视器都正常
5. [ ] 切换视角：点击监视器网格，OBS只显示当前视角，音频面板干净
6. [ ] 刷新源：右键刷新任意平台选手，画面重启正常（无需手动点OBS刷新）
7. [ ] 监视器点击跳转：pynput全局钩子正常工作
8. [ ] OBS快捷键：switcher.py切换视角正常

**观察项:**
9. [ ] 抖音推流30分钟后，流断开是否自动重连（查看日志 [推流监控] 抖音token刷新）
10. [ ] 监视器帧率：VLC嵌入是否比之前的截图方式更流畅

- [ ] **Step 6: 最终Commit（如有测试修复）**

```bash
git add manager_ui.pyw
git commit -m "test: 集成测试验证通过"
git push
```

---

## Self-Review 检查

**Spec覆盖检查:**
- ✅ 组件1 推流管线 → Task 2
- ✅ 组件2 OBS源管理+刷新修复 → Task 1, 5, 9
- ✅ 组件3 监视器预览 → Task 6, 7
- ✅ 组件4 进程监控 → Task 2 (Step 2), Task 8
- ✅ 组件5 sync_player统一 → Task 4
- ✅ 配置迁移 → Task 3
- ✅ 死代码清理 → Task 10
- ✅ 测试 → Task 11

**类型一致性检查:**
- `trigger_media_play` / `trigger_media_restart` / `get_media_state` 在 Task 1 定义，Task 5/9 调用 ✓
- `url` 字段在 Task 3 定义，Task 2 的 `start_stream` 使用 ✓
- `_stream_process_monitor` 在 Task 2 修改，Task 8 启动 ✓

**无占位符**: 所有步骤包含完整代码 ✓
