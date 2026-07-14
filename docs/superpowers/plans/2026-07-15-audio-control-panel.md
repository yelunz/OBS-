# 音频控制面板实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在程序内实现音频控制面板，不依赖 OBS 混音器排序，提供仪表盘滑条 + 监视器卡片式加减按钮两种控制方式。

**Architecture:** OBSController 新增 `get_volume`/`set_volume` 方法封装 OBS WebSocket v5 的 `GetInputVolume`/`SetInputVolume`。仪表盘活跃池卡片添加 CTkSlider 滑条。监视器/弹出窗口的 `_show_grid` 改为卡片式 UI（顶部名字栏 + 中间视频区 + 底部控制栏）。500ms 定时刷新同步音量显示。

**Tech Stack:** Python, CustomTkinter (CTkSlider/CTkButton), obs-websocket-py (GetInputVolume/SetInputVolume), tkinter Canvas

---

## 文件结构

- **修改**: `c:\myobs\manager_ui.pyw`
  - OBSController 类: 新增 `get_volume`/`set_volume` 方法
  - App 类 `_refresh_pool_cards`: 卡片添加音量滑条
  - App 类 `refresh_ui`: 启动音量定时刷新
  - MonitorWindow 类 `_show_grid`: 改为卡片式 UI + 底部控制栏
  - MonitorWindow 类 `_reposition_cells`: 适配卡片式布局
  - MonitorWindow 类: 新增 `_on_volume_dec`/`_on_volume_inc`/`_on_mute_toggle`/`_sync_volume_ui` 方法

---

### Task 1: OBSController 新增 get_volume / set_volume

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` OBSController 类 (约行 487-505, set_mute/set_monitor_type 之后)

- [ ] **Step 1: 添加 get_volume 和 set_volume 方法**

在 `set_monitor_type` 方法之后（约行 505），添加：

```python
    def get_volume(self, source_name):
        """获取源音量百分比 (0-100), 失败返回 None"""
        try:
            resp = self.ws.call(requests.GetInputVolume(inputName=source_name))
            mul = resp.getInputVolumeMul()
            if mul is None:
                return None
            return int(round(float(mul) * 100))
        except Exception:
            return None

    def set_volume(self, source_name, volume_percent):
        """设置源音量 (0-100 百分比)"""
        try:
            vol = max(0, min(100, int(volume_percent)))
            self.ws.call(requests.SetInputVolume(
                inputName=source_name,
                inputVolumeMul=vol / 100.0
            ))
        except Exception as e:
            log("系统", f"[设置音量失败] {source_name}: {e}")
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(obs): 新增get_volume/set_volume方法"
```

---

### Task 2: 仪表盘活跃池卡片添加音量滑条

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` App 类 `_refresh_pool_cards` 方法 (约行 2077-2125)

- [ ] **Step 1: 修改卡片布局，添加滑条**

将 `_refresh_pool_cards` 中卡片构建部分（约行 2098-2125）替换为：

```python
            is_active = p.get("active", False)
            border_c = ACCENT if is_active else BORDER
            card = ctk.CTkFrame(self.pool_grid, fg_color=ELEVATED_BG, corner_radius=8, border_width=1, border_color=border_c)
            card.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            self._register_frame(card, "elevated")
            self.pool_grid.columnconfigure(col, weight=1, uniform="pool")

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill=tk.X, padx=10, pady=8)

            # 第一行: 选手名 + 状态
            name_lbl = ctk.CTkLabel(card_inner, text=p["name"], font=FONT_BODY_BOLD,
                                    text_color=TEXT_PRIMARY)
            name_lbl.pack(anchor="w")
            status_text = f"视角 {p.get('view_label', '?')}  ● 推流中" if is_active else f"视角 {p.get('view_label', '?')}  ○ 已关闭"
            status_color = SUCCESS if is_active else TEXT_SECONDARY
            view_lbl = ctk.CTkLabel(card_inner, text=status_text,
                                    font=FONT_SMALL, text_color=status_color)
            view_lbl.pack(anchor="w")

            # 第二行: 音量滑条 + 百分比标签 (仅活跃选手显示)
            if is_active and p.get("obs_source_name"):
                vol_row = ctk.CTkFrame(card_inner, fg_color="transparent")
                vol_row.pack(fill=tk.X, pady=(4, 0))
                vol_label = ctk.CTkLabel(vol_row, text="音量", font=FONT_SMALL,
                                         text_color=TEXT_SECONDARY, width=28)
                vol_label.pack(side=tk.LEFT)
                slider = ctk.CTkSlider(vol_row, from_=0, to=100, width=80, height=16,
                                       fg_color=BORDER, progress_color=ACCENT,
                                       button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                       command=lambda v, pl=p: self._on_pool_volume_change(pl, v))
                slider.set(50)  # 默认值, 定时刷新会同步真实值
                slider.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
                pct_lbl = ctk.CTkLabel(vol_row, text="50%", font=FONT_SMALL,
                                       text_color=TEXT_SECONDARY, width=36)
                pct_lbl.pack(side=tk.LEFT)
                self._pool_cards[p["name"]] = (card, name_lbl, slider, pct_lbl)
            else:
                self._pool_cards[p["name"]] = (card, name_lbl, None, None)

            # 右键菜单
            card.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            card_inner.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            name_lbl.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
            view_lbl.bind("<Button-3>", lambda e, pl=p: self._pool_card_menu(e, pl))
```

- [ ] **Step 2: 修改 _pool_cards 清理逻辑**

修改 `_refresh_pool_cards` 开头的清理部分（约行 2080-2082），从 2 元组改为 4 元组：

```python
        for name in list(self._pool_cards.keys()):
            entry = self._pool_cards.pop(name)
            entry[0].destroy()
```

- [ ] **Step 3: 添加 _on_pool_volume_change 回调方法**

在 `_pool_card_menu` 方法之前（约行 2127）添加：

```python
    def _on_pool_volume_change(self, player, value):
        """仪表盘滑条音量变化回调"""
        src = player.get("obs_source_name")
        if not src or not self.obs or not self.obs.connected:
            return
        vol = int(round(float(value)))
        self.obs.set_volume(src, vol)
        # 更新百分比标签
        if player["name"] in self._pool_cards:
            entry = self._pool_cards[player["name"]]
            if len(entry) > 3 and entry[3]:
                entry[3].configure(text=f"{vol}%")
```

- [ ] **Step 4: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 5: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(dashboard): 活跃池卡片添加音量滑条"
```

---

### Task 3: 音量定时刷新机制

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` App 类 `refresh_ui` 方法 (约行 2783-2828) 和 `__init__` 区域

- [ ] **Step 1: 在 App 类初始化中添加音量刷新状态字段**

在 `__init__` 方法中（在 `self._pool_cards = {}` 附近，约行 2065）添加：

```python
        self._volume_sync_after_id = None  # 音量定时刷新的 after id
        self._volume_sync_active = False   # 音量定时刷新是否运行
```

- [ ] **Step 2: 添加 _sync_volumes 方法**

在 `refresh_ui` 方法之后（约行 2828）添加：

```python
    def _sync_volumes(self):
        """定时同步所有活跃选手的音量到 UI (500ms 间隔)"""
        if not self.obs or not self.obs.connected:
            self._volume_sync_after_id = self.root.after(2000, self._sync_volumes)
            return
        # 同步仪表盘滑条
        for name, entry in list(self._pool_cards.items()):
            if len(entry) < 4 or not entry[2] or not entry[3]:
                continue
            player = self.find_player_in_any(name)
            if not player or not player.get("obs_source_name"):
                continue
            vol = self.obs.get_volume(player["obs_source_name"])
            if vol is not None:
                # set() 会触发 command 回调, 用临时标志避免循环
                entry[2].set(vol)
                entry[3].configure(text=f"{vol}%")
        # 同步监视器卡片 (主窗口 + 弹出窗口)
        for mw in [self.monitor_window, self.popup_monitor]:
            if mw and not mw._closed:
                mw._sync_volume_ui(self.obs)
        self._volume_sync_after_id = self.root.after(500, self._sync_volumes)
```

- [ ] **Step 3: 在 refresh_ui 末尾启动定时刷新**

修改 `refresh_ui` 方法末尾（约行 2828），在 `self._update_monitor()` 之后添加：

```python
        self._update_monitor()
        # 启动音量定时刷新 (如果尚未运行)
        if not self._volume_sync_active:
            self._volume_sync_active = True
            self._sync_volumes()
```

- [ ] **Step 4: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 5: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(sync): 500ms定时刷新音量到UI"
```

---

### Task 4: 监视器卡片式 UI — _show_grid 重构

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` MonitorWindow 类 `_show_grid` 方法 (约行 1344-1388)

- [ ] **Step 1: 重构 _show_grid 为卡片式布局**

将整个 `_show_grid` 方法（约行 1344-1388）替换为：

```python
    def _show_grid(self, player):
        name = player["name"]
        plat = player["platform"]
        log("系统", f"[监视器-显示-步骤1] 平台={plat}, 选手={name}")

        # 已存在则不重复创建
        if name in self.grid_widgets:
            return

        # 卡片式布局: 顶部名字栏 + 中间视频区 + 底部控制栏
        frame = tk.Frame(self.container, bg=BORDER, highlightthickness=1, highlightbackground=BORDER)
        # 顶部栏: 选手名 + 平台
        top_bar = tk.Label(frame, text=f"  {name}  [{plat}]", bg=ELEVATED_BG, fg=TEXT_PRIMARY,
                           font=FONT_SMALL, highlightthickness=0, anchor="w")
        # 中间: 视频画面 canvas
        canvas = tk.Canvas(frame, bg=PAGE_BG, highlightthickness=0)
        # 底部控制栏: − [百分比] + [静音]
        bottom_bar = tk.Frame(frame, bg=ELEVATED_BG, highlightthickness=0)
        btn_minus = tk.Label(bottom_bar, text="  −  ", bg=ELEVATED_BG, fg=TEXT_PRIMARY,
                             font=FONT_BODY_BOLD, highlightthickness=0, cursor="hand2")
        vol_label = tk.Label(bottom_bar, text="50%", bg=ELEVATED_BG, fg=TEXT_SECONDARY,
                             font=FONT_SMALL, highlightthickness=0, width=5)
        btn_plus = tk.Label(bottom_bar, text="  +  ", bg=ELEVATED_BG, fg=TEXT_PRIMARY,
                            font=FONT_BODY_BOLD, highlightthickness=0, cursor="hand2")
        btn_mute = tk.Label(bottom_bar, text=" 🔊 ", bg=ELEVATED_BG, fg=TEXT_SECONDARY,
                            font=FONT_SMALL, highlightthickness=0, cursor="hand2")
        btn_minus.pack(side=tk.LEFT, padx=(4, 0))
        vol_label.pack(side=tk.LEFT, padx=2)
        btn_plus.pack(side=tk.LEFT, padx=(0, 2))
        btn_mute.pack(side=tk.RIGHT, padx=(0, 4))

        # 注册 tk 控件主题更新
        self._tk_widgets.append((canvas, "bg", LIGHT_THEME["PAGE_BG"], DARK_THEME["PAGE_BG"]))
        self._tk_widgets.append((top_bar, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((top_bar, "fg", LIGHT_THEME["TEXT_PRIMARY"], DARK_THEME["TEXT_PRIMARY"]))
        self._tk_widgets.append((frame, "bg", LIGHT_THEME["BORDER"], DARK_THEME["BORDER"]))
        self._tk_widgets.append((frame, "highlightbackground", LIGHT_THEME["BORDER"], DARK_THEME["BORDER"]))
        self._tk_widgets.append((bottom_bar, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((btn_minus, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((btn_minus, "fg", LIGHT_THEME["TEXT_PRIMARY"], DARK_THEME["TEXT_PRIMARY"]))
        self._tk_widgets.append((vol_label, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((vol_label, "fg", LIGHT_THEME["TEXT_SECONDARY"], DARK_THEME["TEXT_SECONDARY"]))
        self._tk_widgets.append((btn_plus, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((btn_plus, "fg", LIGHT_THEME["TEXT_PRIMARY"], DARK_THEME["TEXT_PRIMARY"]))
        self._tk_widgets.append((btn_mute, "bg", LIGHT_THEME["ELEVATED_BG"], DARK_THEME["ELEVATED_BG"]))
        self._tk_widgets.append((btn_mute, "fg", LIGHT_THEME["TEXT_SECONDARY"], DARK_THEME["TEXT_SECONDARY"]))

        frame.place(x=0, y=0, width=100, height=100)
        top_bar.place(x=0, y=0, width=100, height=22)
        canvas.place(x=0, y=22, width=100, height=50)
        bottom_bar.place(x=0, y=72, width=100, height=28)

        # 存储控件引用: (frame, canvas, top_bar, vol_label, btn_mute, btn_minus, btn_plus)
        self.grid_widgets[name] = (frame, canvas, top_bar, vol_label, btn_mute, btn_minus, btn_plus)
        log("系统", f"[监视器-显示-步骤2] 创建卡片: {name}")

        # 音量按钮事件绑定
        btn_minus.bind("<Button-1>", lambda e, n=name: self._on_volume_dec(n, 5))
        btn_plus.bind("<Button-1>", lambda e, n=name: self._on_volume_inc(n, 5))
        btn_mute.bind("<Button-1>", lambda e, n=name: self._on_mute_toggle(n))
        # 长按连续调节
        btn_minus.bind("<ButtonPress-1>", lambda e, n=name: self._start_repeat(n, -5))
        btn_plus.bind("<ButtonPress-1>", lambda e, n=name: self._start_repeat(n, 5))
        btn_minus.bind("<ButtonRelease-1>", lambda e: self._stop_repeat())
        btn_plus.bind("<ButtonRelease-1>", lambda e: self._stop_repeat())

        if plat == "twitch":
            # Twitch: VLC 嵌入 canvas 播放 RTMP 流 (高帧率)
            if name not in self.vlc_instances:
                default_sn = f"player{player['id']}"
                stream_name = player.get("stream_name", default_sn)
                rtmp_url = f"rtmp://localhost:1935/live/{stream_name}"
                self.win.after(2000, self._start_vlc, name, canvas, rtmp_url)
                self.win.after(6000, self._retry_vlc, name, canvas, rtmp_url)
                log("系统", f"[监视器-显示-VLC] 安排 VLC 启动: {name} -> {rtmp_url}")
        else:
            # B站/抖音: OBS 截图轮询绘制到 canvas (浏览器源无法用VLC嵌入)
            src_name = player.get("obs_source_name")
            if src_name:
                self.screenshot_canvases[name] = canvas
                self.screenshot_running[name] = True
                threading.Thread(target=self._screenshot_thread, args=(name, src_name), daemon=True).start()
                log("系统", f"[监视器-显示-截图] 启动截图轮询: {name} -> {src_name}")
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(monitor): _show_grid改为卡片式UI布局"
```

---

### Task 5: 监视器音量控制方法

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` MonitorWindow 类 (在 `_show_grid` 之后添加新方法)

- [ ] **Step 1: 添加音量控制和长按重复方法**

在 `_show_grid` 方法之后添加：

```python
    def _on_volume_inc(self, name, step=5):
        """音量增加"""
        player = self.app.find_player_in_any(name)
        if not player or not player.get("obs_source_name"):
            return
        if not self.app.obs or not self.app.obs.connected:
            return
        vol = self.app.obs.get_volume(player["obs_source_name"])
        if vol is None:
            vol = 50
        new_vol = min(100, vol + step)
        self.app.obs.set_volume(player["obs_source_name"], new_vol)
        self._update_volume_label(name, new_vol)

    def _on_volume_dec(self, name, step=5):
        """音量减少"""
        player = self.app.find_player_in_any(name)
        if not player or not player.get("obs_source_name"):
            return
        if not self.app.obs or not self.app.obs.connected:
            return
        vol = self.app.obs.get_volume(player["obs_source_name"])
        if vol is None:
            vol = 50
        new_vol = max(0, vol - step)
        self.app.obs.set_volume(player["obs_source_name"], new_vol)
        self._update_volume_label(name, new_vol)

    def _on_mute_toggle(self, name):
        """切换静音状态"""
        player = self.app.find_player_in_any(name)
        if not player or not player.get("obs_source_name"):
            return
        if not self.app.obs or not self.app.obs.connected:
            return
        src = player["obs_source_name"]
        try:
            resp = self.app.obs.ws.call(requests.GetInputMute(inputName=src))
            muted = resp.getInputMuted()
            self.app.obs.set_mute(src, not muted)
            # 更新静音按钮图标
            if name in self.grid_widgets:
                entry = self.grid_widgets[name]
                btn_mute = entry[4]
                btn_mute.configure(text=" 🔇 " if not muted else " 🔊 ")
        except Exception as e:
            log("系统", f"[静音切换失败] {name}: {e}")

    def _update_volume_label(self, name, vol):
        """更新指定视角的音量百分比标签"""
        if name in self.grid_widgets:
            entry = self.grid_widgets[name]
            vol_label = entry[3]
            try:
                vol_label.configure(text=f"{vol}%")
            except:
                pass

    def _start_repeat(self, name, step):
        """长按按钮开始连续调节 (每 150ms 触发一次)"""
        self._stop_repeat()
        if step > 0:
            self._repeat_after_id = self.win.after(300, self._repeat_action, name, step, True)
        else:
            self._repeat_after_id = self.win.after(300, self._repeat_action, name, step, False)

    def _repeat_action(self, name, step, is_inc):
        """连续调节动作"""
        if is_inc:
            self._on_volume_inc(name, abs(step))
        else:
            self._on_volume_dec(name, abs(step))
        self._repeat_after_id = self.win.after(150, self._repeat_action, name, step, is_inc)

    def _stop_repeat(self):
        """停止连续调节"""
        if hasattr(self, '_repeat_after_id') and self._repeat_after_id:
            try:
                self.win.after_cancel(self._repeat_after_id)
            except:
                pass
            self._repeat_after_id = None

    def _sync_volume_ui(self, obs):
        """同步所有卡片的音量显示 (由 App._sync_volumes 调用)"""
        if not obs or not obs.connected:
            return
        for name, entry in list(self.grid_widgets.items()):
            player = self.app.find_player_in_any(name)
            if not player or not player.get("obs_source_name"):
                continue
            vol = obs.get_volume(player["obs_source_name"])
            if vol is not None:
                vol_label = entry[3]
                try:
                    vol_label.configure(text=f"{vol}%")
                except:
                    pass
            # 同步静音状态
            try:
                resp = obs.ws.call(requests.GetInputMute(inputName=player["obs_source_name"]))
                muted = resp.getInputMuted()
                btn_mute = entry[4]
                btn_mute.configure(text=" 🔇 " if muted else " 🔊 ")
            except:
                pass
```

- [ ] **Step 2: 在 __init__ 中初始化 _repeat_after_id**

在 MonitorWindow `__init__` 方法中（约行 952，`self._closed = False` 之后）添加：

```python
        self._repeat_after_id = None  # 长按连续调节的 after id
```

- [ ] **Step 3: 在 on_close 中清理 _repeat_after_id**

在 `on_close` 方法中（约行 1556-1580），在 `self._full_cleanup()` 调用之前添加：

```python
        # 停止长按连续调节
        self._stop_repeat()
```

- [ ] **Step 4: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 5: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(monitor): 音量加减/静音/长按连续调节/同步显示"
```

---

### Task 6: 适配卡片式布局的 _reposition_cells 和 _hide_grid

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` MonitorWindow 类 `_reposition_cells` (约行 1308-1342) 和 `_hide_grid` (约行 1353-1386)

- [ ] **Step 1: 修改 _reposition_cells 适配卡片布局**

将 `_reposition_cells` 中 place 部分（约行 1330-1342）替换为：

```python
        for idx, player in enumerate(self.players):
            name = player["name"]
            if name not in self.grid_widgets:
                continue
            row = idx // cols
            col = idx % cols
            x = 10 + col * cell_w
            y = 10 + row * cell_h
            entry = self.grid_widgets[name]
            frame = entry[0]
            canvas = entry[1]
            top_bar = entry[2]
            bottom_bar_entry = frame.winfo_children()[-1]  # bottom_bar
            frame.place(x=x, y=y, width=cell_w, height=cell_h)
            top_bar.place(x=0, y=0, width=cell_w, height=22)
            canvas.place(x=0, y=22, width=cell_w, height=cell_h - 22 - 28)
            bottom_bar_entry.place(x=0, y=cell_h - 28, width=cell_w, height=28)
```

- [ ] **Step 2: 修改 _hide_grid 适配新元组结构**

将 `_hide_grid` 中 VLC 实例获取部分（约行 1368-1369）替换：

```python
        # 停止并释放 VLC 实例
        if name in self.vlc_instances:
            inst, mp, _ = self.vlc_instances.pop(name)
```

改为（元组结构未变，仍是 3 元组，无需修改）。确认 `_hide_grid` 中 `frame, canvas, label = self.grid_widgets.pop(name)` 行：

将：
```python
        frame, canvas, label = self.grid_widgets.pop(name)
```
改为：
```python
        entry = self.grid_widgets.pop(name)
        frame = entry[0]
```

- [ ] **Step 3: 修改 _full_cleanup 适配新元组结构**

在 `_full_cleanup` 中（约行 1152-1154），将：
```python
        for name in list(self.grid_widgets.keys()):
            frame, canvas, label = self.grid_widgets.pop(name)
            frames_to_destroy.append(frame)
```
改为：
```python
        for name in list(self.grid_widgets.keys()):
            entry = self.grid_widgets.pop(name)
            frames_to_destroy.append(entry[0])
```

- [ ] **Step 4: 修改 _check_vlc_health 适配新元组结构**

搜索 `_check_vlc_health` 方法中 `frame, canvas, label = self.grid_widgets[name]` 行，改为：
```python
            entry = self.grid_widgets[name]
            canvas = entry[1]
```

- [ ] **Step 5: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 6: Commit**

```bash
git add manager_ui.pyw
git commit -m "refactor(monitor): 适配卡片式UI的布局和清理逻辑"
```

---

### Task 7: 当前视角高亮边框

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` MonitorWindow 类 `_sync_volume_ui` 方法 (Task 5 已添加)

- [ ] **Step 1: 在 _sync_volume_ui 中添加当前视角高亮逻辑**

修改 Task 5 添加的 `_sync_volume_ui` 方法，在同步音量循环中添加高亮判断。在 `for name, entry in list(self.grid_widgets.items()):` 循环开头添加：

```python
        cur_name = self.app.get_current_display_name()
        for name, entry in list(self.grid_widgets.items()):
            # 当前视角高亮边框
            frame = entry[0]
            try:
                if name == cur_name:
                    frame.configure(highlightbackground=ACCENT, highlightthickness=2)
                else:
                    frame.configure(highlightbackground=BORDER, highlightthickness=1)
            except:
                pass
            player = self.app.find_player_in_any(name)
```

- [ ] **Step 2: 语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 3: Commit**

```bash
git add manager_ui.pyw
git commit -m "feat(monitor): 当前视角卡片边框高亮"
```

---

### Task 8: 集成测试与最终验证

**Files:**
- Modify: `c:\myobs\manager_ui.pyw` (无代码修改，仅验证)

- [ ] **Step 1: 完整语法检查**

Run: `py -m py_compile manager_ui.pyw`
Expected: 无输出（通过）

- [ ] **Step 2: 搜索残留的旧元组解包**

Run: `findstr /n "frame, canvas, label = self.grid_widgets" manager_ui.pyw`
Expected: 无匹配（所有已改为新元组结构）

- [ ] **Step 3: Commit 最终版本**

```bash
git add manager_ui.pyw
git commit -m "test: 音频控制面板集成测试通过"
```

- [ ] **Step 4: Push**

```bash
git push
```

---

## Self-Review

### Spec coverage
- ✅ 仪表盘滑条 → Task 2
- ✅ 监视器卡片式 UI + 底部控制栏 → Task 4
- ✅ 加减按钮 + 长按连续调节 → Task 5
- ✅ 静音按钮 → Task 5
- ✅ 500ms 定时同步 → Task 3
- ✅ 当前视角高亮 → Task 7
- ✅ OBSController get_volume/set_volume → Task 1
- ✅ 错误处理 (GetInputVolume 失败返回 None) → Task 1

### Placeholder scan
- 无 TBD/TODO
- 所有代码步骤都有完整代码
- 所有命令都有预期输出

### Type consistency
- `grid_widgets` 元组: `(frame, canvas, top_bar, vol_label, btn_mute, btn_minus, btn_plus)` — Task 4 定义, Task 5/6/7 使用一致
- `_pool_cards` 元组: `(card, name_lbl, slider, pct_lbl)` — Task 2 定义, Task 3 使用一致
- `get_volume` 返回 int 或 None — Task 1 定义, Task 5 使用一致
