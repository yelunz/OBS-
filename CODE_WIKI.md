# 多视角切换管理器 (Multi-View Stream Switcher) — Code Wiki

> 版本: v1.0 | 更新时间: 2026-07-11

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [目录与文件结构](#3-目录与文件结构)
4. [核心模块详解](#4-核心模块详解)
   - [4.1 manager_ui.pyw — 主管理界面](#41-manager_uipyw--主管理界面)
   - [4.2 switcher.py — 快捷键切换器](#42-switcherpy--快捷键切换器)
   - [4.3 config.json — 配置文件](#43-configjson--配置文件)
   - [4.4 mediamtx.yml — RTMP 服务器配置](#44-mediamtxyaml--rtmp-服务器配置)
   - [4.5 外部工具与二进制](#45-外部工具与二进制)
5. [关键类与函数说明](#5-关键类与函数说明)
6. [数据流与运行流程](#6-数据流与运行流程)
7. [依赖关系](#7-依赖关系)
8. [项目运行方式](#8-项目运行方式)
9. [配置说明](#9-配置说明)

---

## 1. 项目概述

**多视角切换管理器** 是一个基于 OBS Studio 的直播流多源管理与切换工具。它允许用户：

- 管理多个直播源（Twitch、Bilibili、抖音、自定义网页）
- 通过全局快捷键或 GUI 界面在 OBS 中切换不同视角
- 将外部直播流通过本地 RTMP 服务器中继到 OBS
- 支持多平台流源检测、推流状态监控、多视角预览

**技术栈**: Python 3 + Tkinter + OBS WebSocket + MediaMTX + Streamlink + FFmpeg + VLC

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       manager_ui.pyw (主进程)                     │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  ManagerApp    │  │ OBSController│  │  MonitorWindow       │  │
│  │  (Tkinter GUI) │  │ (obswebsocket)│  │  (VLC 多画面预览)    │  │
│  └───────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │              │
│          │    ┌────────────┼──────────────────────┘              │
│          │    │            │                                     │
│  ┌───────┴────┴────┐  ┌───┴──────────┐                          │
│  │  config.json    │  │ 进程管理模块   │                          │
│  │  (持久化配置)    │  │ (streamlink   │                          │
│  └────────────────┘  │  + ffmpeg)    │                          │
│                      └───┬──────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───────┐ ┌──▼──────────┐
       │  MediaMTX   │ │ switcher │ │ OBS Studio  │
       │  RTMP 服务器 │ │  .py     │ │(WebSocket)  │
       │  :1935      │ │(快捷键)   │ │  :4455      │
       └─────────────┘ └──────────┘ └─────────────┘
```

### 架构分层

| 层级 | 组件 | 职责 |
|------|------|------|
| **表现层** | `ManagerApp` (Tkinter GUI) | 用户交互界面、选手管理、视角切换 |
| **业务逻辑层** | `OBSController`、进程管理函数 | OBS 源操控、推流生命周期管理、源检测 |
| **服务层** | MediaMTX、switcher.py | RTMP 中继服务、全局快捷键监听 |
| **数据层** | `config.json` | 选手配置、OBS 连接信息、系统参数 |
| **外部依赖** | OBS Studio、Streamlink、FFmpeg、VLC | 直播推流、流拉取、转码、预览播放 |

---

## 3. 目录与文件结构

```
c:\myobs\
├── manager_ui.pyw      # 主程序入口 (GUI 管理界面, ~2000 行)
├── switcher.py         # 全局快捷键切换器 (独立进程, ~250 行)
├── config.json         # 选手与系统配置文件
├── mediamtx.yml        # MediaMTX RTMP 服务器配置文件 (自动生成)
├── mediamtx.exe        # MediaMTX RTMP 服务器可执行文件
├── auto.crt            # SSL 证书 (用于 RTMPS)
├── auto.key            # SSL 私钥
├── debug.log           # 调试日志文件
├── python/             # Python 虚拟环境目录 (空)
└── CODE_WIKI.md        # 本文档
```

---

## 4. 核心模块详解

### 4.1 manager_ui.pyw — 主管理界面

**文件路径**: [manager_ui.pyw](file:///c:/myobs/manager_ui.pyw)

**作用**: 整个系统的核心入口，提供 Tkinter GUI 界面，负责选手管理、OBS 连接控制、推流生命周期管理和多视角监控。

**主要代码结构**:

| 代码区域 | 行号 | 功能 |
|---------|------|------|
| 导入与模块检测 | 1-24 | 检测 VLC、pygetwindow 等可选依赖 |
| 日志系统 | 26-55 | 全局日志收集、文件日志写入 |
| `OBSController` 类 | 58-231 | OBS WebSocket 操作封装 |
| 进程管理函数 | 245-469 | Streamlink + FFmpeg 推流、MediaMTX 启停 |
| 快速添加/解析 | 479-528 | 剪贴板 URL 解析、选手信息提取 |
| 对话框类 | 531-659 | 选手编辑对话框、OBS 登录框 |
| 监视器窗口 | 662-894 | 多画面 RTMP 预览 (VLC 嵌入) |
| 带复选框的 Treeview | 897-971 | 自定义 Treeview 组件 |
| 主界面类 | 974-1998 | 核心 GUI 逻辑与业务协调 |

#### 4.1.1 OBSController 类 (第 58-231 行)

封装了所有 OBS WebSocket 操作，是系统与 OBS Studio 交互的唯一通道。

| 方法 | 行号 | 功能 |
|------|------|------|
| `__init__(host, port, password)` | 59-65 | 初始化连接参数 |
| `connect()` | 67-78 | 建立 WebSocket 连接，获取当前场景名 |
| `disconnect()` | 80-83 | 断开 WebSocket 连接 |
| `source_exists(name)` | 85-87 | 检查指定源是否存在于当前场景 |
| `create_vlc(name, url)` | 89-122 | 创建 VLC 视频源（用于 Twitch/抖音推流） |
| `update_vlc_url(name, url)` | 124-133 | 更新 VLC 源的播放 URL |
| `restart_vlc(name)` | 135-145 | 强制重启 VLC 源播放 |
| `create_window_capture(name, window_title)` | 147-166 | 创建窗口采集源（用于网页平台） |
| `remove_source(name)` | 168-173 | 删除 OBS 源 |
| `get_scene_item_map()` | 175-177 | 获取场景中所有源的映射表 |
| `get_visible(name)` | 179-181 | 获取源的可见性状态 |
| `set_visibility(name, visible)` | 183-190 | 设置源的可见性 |
| `set_mute(source_name, mute)` | 192-196 | 设置源的静音状态 |
| `rename_source(old_name, new_name)` | 198-205 | 重命名 OBS 源 |
| `get_all_source_names()` | 207-208 | 获取所有源名称列表 |
| `create_scene(name)` / `remove_scene(name)` | 210-226 | 场景管理 |
| `switch_scene(name)` / `scene_exists(name)` | 224-230 | 场景切换与检测 |

#### 4.1.2 进程管理函数 (第 245-469 行)

负责外部流源的拉取与推流。

| 函数 | 行号 | 功能 |
|------|------|------|
| `read_stream_output(proc, prefix, ...)` | 273-310 | 异步读取子进程 stdout，检测推流开始事件 |
| `wait_for_mediamtx(host, port, timeout)` | 312-321 | 等待 MediaMTX 服务器就绪 |
| `start_stream(player, obs)` | 323-360 | 启动一个选手的推流（streamlink → ffmpeg → RTMP） |
| `stop_stream(player)` | 362-368 | 停止选手的推流进程 |
| `open_browser_window(player)` | 370-387 | 为网页平台选手打开独立 Edge 浏览器窗口 |
| `check_twitch_source(url)` | 389-394 | 检测 Twitch 源是否在线 |
| `check_douyin_source(url)` | 396-403 | 检测抖音源是否可用 |
| `check_source(player)` | 405-418 | 根据平台类型分发源检测 |
| `start_mediamtx()` | 420-445 | 动态生成配置并启动 MediaMTX RTMP 服务器 |
| `stop_mediamtx()` | 447-451 | 停止 MediaMTX 服务器 |
| `start_switcher()` | 453-469 | 启动 switcher.py 子进程 |
| `get_all_stream_statuses(players)` | 471-477 | 获取所有推流状态快照 |

#### 4.1.3 快速添加与 URL 解析 (第 479-528 行)

| 函数 | 行号 | 功能 |
|------|------|------|
| `parse_clipboard_url(url_string)` | 480-508 | 解析剪贴板 URL，识别平台并提取信息 |
| `get_next_view_label(players)` | 510-521 | 分配下一个可用的视角标签编号 |
| `normalize_view_label(value)` | 523-528 | 归一化视角标签值为整数 |

#### 4.1.4 对话框类 (第 531-659 行)

| 类 | 行号 | 功能 |
|------|------|------|
| `PlayerDialog` | 531-622 | 选手添加/编辑弹窗，支持动态表单 |
| `OBSLoginDialog` | 625-659 | OBS WebSocket 连接配置弹窗 |

#### 4.1.5 监视器窗口 (第 662-894 行)

| 类 | 行号 | 功能 |
|------|------|------|
| `MonitorWindow` | 662-894 | 多画面 RTMP 实时预览窗口，使用 VLC 嵌入 Canvas 播放 |

关键方法:
- `_calculate_layout()` — 自适应网格布局计算
- `refresh()` — 根据活跃选手更新网格
- `_start_vlc(name, canvas, url)` — 在指定 Canvas 上启动 VLC 播放
- `_start_mouse_listener()` — 鼠标点击切换视角

#### 4.1.6 带复选框的 Treeview (第 897-971 行)

| 类 | 行号 | 功能 |
|------|------|------|
| `CheckboxTreeview` | 897-971 | 扩展 Tkinter Treeview，支持复选框多选 |

#### 4.1.7 ManagerApp 主界面类 (第 974-1998 行)

核心方法:

| 方法 | 行号 | 功能 |
|------|------|------|
| `__init__(root)` | 975-1009 | 初始化应用、加载配置、启动后台服务 |
| `load_cfg()` | 1011-1072 | 加载/恢复配置文件 |
| `create_widgets()` | 1110-1209 | 构建完整 GUI 布局 |
| `activate_player(player)` | 1370-1393 | 激活选手：创建 OBS 源 + 启动推流 |
| `deactivate_player(player)` | 1395-1404 | 停用选手：停止推流 |
| `switch_to(player)` | 1406-1459 | 切换当前视角到指定选手 |
| `sync_player(player)` | 1488-1518 | 同步选手 OBS 源（创建/重命名/更新） |
| `refresh_ui()` | 1534-1583 | 刷新所有 UI 组件 |
| `save_config()` | 1957-1969 | 安全保存配置（先写临时文件再替换） |
| `all_start()` | 1725-1731 | 启动所有服务（MediaMTX + Switcher） |
| `all_stop()` | 1733-1740 | 停止所有服务 |
| `on_close()` | 1977-1991 | 窗口关闭清理 |

---

### 4.2 switcher.py — 快捷键切换器

**文件路径**: [switcher.py](file:///c:/myobs/switcher.py)

**作用**: 独立进程，监听全局快捷键（修饰键 + 单字符），通过 OBS WebSocket 切换当前显示的视角。

**核心类与函数**:

| 名称 | 行号 | 功能 |
|------|------|------|
| `log(msg)` | 18-19 | 控制台日志输出 |
| `load_config()` | 21-23 | 加载配置文件 |
| `mute_browser_window(window_title, mute)` | 25-48 | 通过模拟 Ctrl+M 静音浏览器窗口 |
| `refresh_hotkey_map()` | 74-84 | 从配置刷新快捷键映射和 OBS 源 ID 映射 |
| `ensure_obs_connected()` | 88-108 | 检测并重连 OBS WebSocket |
| `set_mute(source_name, mute)` | 110-114 | 设置 OBS 源静音 |
| `set_visible(name, visible)` | 116-121 | 设置 OBS 源可见性 |
| `switch_to(target_player)` | 123-175 | 执行视角切换（核心逻辑） |
| `HotkeyListener` 类 | 177-221 | 全局快捷键监听器 |
| `watch_config()` | 224-249 | 后台监控配置文件变更并热更新 |

**`switch_to()` 切换逻辑** (第 123-175 行):

1. 判断目标平台类型
2. **网页平台** (bilibili/custom_web): 先静音其他网页源（浏览器 Ctrl+M + OBS mute），再取消静音目标源
3. **流媒体平台** (twitch/douyin): 遍历所有其他源，执行静音+隐藏，然后显示+取消静音目标源

**`HotkeyListener` 类** (第 177-221 行):

| 方法 | 行号 | 功能 |
|------|------|------|
| `__init__(modifier)` | 178-183 | 初始化并启动键盘监听 |
| `stop()` | 185-188 | 停止监听 |
| `restart(new_mod)` | 190-196 | 以新修饰键重启监听 |
| `main_ok()` | 198-201 | 检查修饰键是否按下 |
| `on_press(key)` | 203-215 | 按键按下处理，匹配快捷键并调用 switch_to |
| `on_release(key)` | 217-220 | 按键释放处理 |

---

### 4.3 config.json — 配置文件

**文件路径**: [config.json](file:///c:/myobs/config.json)

**结构说明**:

```json
{
    "obs_host": "OBS WebSocket 主机地址",
    "obs_port": OBS WebSocket 端口,
    "obs_password": "OBS WebSocket 密码",
    "max_active_streams": 最大同时推流数,
    "hotkey_modifiers": "快捷键修饰键组合",
    "players": [
        {
            "id": 选手唯一编号,
            "name": "显示名称",
            "hotkey": "快捷键字符(单字符)",
            "platform": "平台(twitch|bilibili|douyin|custom_web)",
            "room_id": "B站房间号",
            "twitch_url": "Twitch 频道 URL",
            "douyin_url": "抖音拉流 URL",
            "quality": "清晰度(best|worst|720p60|...)",
            "browser_url": "浏览器访问 URL",
            "view_label": 视角标签编号,
            "stream_name": "RTMP 流名称",
            "obs_source_name": "OBS 源名称",
            "active": 是否活跃推流中,
            "source_ok": 源是否可用,
            "stream_pid": 推流进程 PID,
            "window_title": "浏览器窗口标题"
        }
    ],
    "scene_name": "OBS 场景名称"
}
```

---

### 4.4 mediamtx.yml — RTMP 服务器配置

**文件路径**: [mediamtx.yml](file:///c:/myobs/mediamtx.yml)

由 `manager_ui.pyw` 的 `start_mediamtx()` 函数动态生成，根据 config.json 中的选手列表自动创建对应的 RTMP 路径。

```yaml
rtmpAddress: :1935        # RTMP 监听端口
hlsAddress: :8888          # HLS 监听端口
hlsSegmentDuration: 1s     # HLS 分片时长
hlsSegmentCount: 7         # HLS 分片数量
paths:
  "live/player1": { source: publisher }
  "live/player2": { source: publisher }
  ...
```

---

### 4.5 外部工具与二进制

| 文件 | 用途 |
|------|------|
| `mediamtx.exe` | MediaMTX RTMP 服务器，用于本地流中继 |
| `auto.crt` / `auto.key` | SSL 证书，用于 RTMPS 加密传输 |
| `debug.log` | 调试日志，每次启动自动清空 |

---

## 5. 关键类与函数说明

### 5.1 类关系图

```
ManagerApp (主界面)
├── 拥有 → OBSController (OBS 操控)
├── 拥有 → MonitorWindow (多画面预览)
├── 使用 → PlayerDialog (选手编辑)
├── 使用 → OBSLoginDialog (连接配置)
├── 使用 → CheckboxTreeview (选手列表)
├── 启动 → MediaMTX 进程
├── 启动 → switcher.py 子进程
└── 管理 → players[] (选手数据)

HotkeyListener (switcher.py)
├── 监听全局键盘
└── 调用 → switch_to() → OBS WebSocket

MonitorWindow
├── 嵌入 VLC 播放器
└── 监听鼠标点击切换
```

### 5.2 核心函数调用链

```
用户点击"上源" / 一键上源
  → ManagerApp.activate_player(player)
    → ManagerApp.sync_player(player)         # 创建/更新 OBS 源
      → OBSController.create_vlc()            # 创建 VLC 源
    → start_stream(player, obs)               # 启动物理推流
      → start_mediamtx()                      # 确保 MediaMTX 运行
      → subprocess: streamlink → ffmpeg → RTMP
      → read_stream_output()                  # 监控输出，检测推流开始
        → OBSController.update_vlc_url()      # 刷新 VLC 源 URL
        → OBSController.restart_vlc()         # 重启 VLC 播放

用户按键切换视角
  → HotkeyListener.on_press()
    → switch_to(target_player)
      → OBSController.set_visibility()        # 隐藏其他源
      → OBSController.set_mute()              # 静音其他源
      → OBSController.set_visibility()        # 显示目标源
      → OBSController.set_mute()              # 取消静音目标源
```

### 5.3 推流数据流

```
外部直播平台 (Twitch/抖音)
    │
    ▼
streamlink (拉流) ──pipe──▶ ffmpeg (转码/复制) ──flv──▶ MediaMTX (:1935)
                                                           │
                                              ┌────────────┼────────────┐
                                              ▼            ▼            ▼
                                        OBS VLC源    MonitorWindow   其他消费者
                                                        (VLC预览)
```

---

## 6. 数据流与运行流程

### 6.1 启动流程

```
1. 启动 manager_ui.pyw
2. 加载 config.json
3. 弹出 OBS 登录对话框（首次运行）
4. 异步连接 OBS WebSocket
5. 创建专用场景 "多视角切换"
6. 启动 MediaMTX RTMP 服务器
7. 启动 switcher.py 子进程（快捷键监听）
8. 启动后台线程：
   - refresh_loop          (每 2 秒刷新 UI)
   - status_monitor        (每 120 秒检测源状态)
   - log_consumer          (每 0.8 秒刷新日志)
   - watch_config          (每 3 秒检测配置文件变更)
```

### 6.2 选手生命周期

```
添加选手 (仓库)
  → 移动到视角列表 (active_players)
    → 上源 (activate)
      → 创建 OBS 源 (VLC / 窗口采集)
      → 启动推流进程 (streamlink + ffmpeg)
      → 加入活跃池
    → 下源 (deactivate)
      → 停止推流进程
      → 保留 OBS 源 (可重新上源)
  → 移回仓库 (move_to_store)
    → 删除 OBS 源
    → 从视角列表移除
```

### 6.3 支持的平台及处理方式

| 平台 | 拉流方式 | OBS 源类型 | 浏览器窗口 |
|------|---------|-----------|-----------|
| **Twitch** | streamlink + ffmpeg → RTMP | VLC 源 | 不需要 |
| **抖音** | ffmpeg 直接拉流 → RTMP | VLC 源 | 不需要 |
| **Bilibili** | 无拉流（浏览器播放） | 窗口采集 | 独立 Edge 窗口 |
| **custom_web** | 无拉流（浏览器播放） | 窗口采集 | 独立 Edge 窗口 |

---

## 7. 依赖关系

### 7.1 Python 包依赖

| 包名 | 用途 | 必需 |
|------|------|------|
| `tkinter` | GUI 界面框架 | 是 |
| `obswebsocket` | OBS WebSocket 通信 | 是 |
| `pynput` | 全局键盘/鼠标监听 | 是 |
| `psutil` | 进程管理 | 是 |
| `pygetwindow` | 窗口查找与操作 | 可选 (浏览器静音) |
| `python-vlc` | VLC 播放器嵌入 | 可选 (监控窗口) |
| `ctypes` | Windows API 调用 | 是 (内置) |

### 7.2 外部工具依赖

| 工具 | 用途 | 预期路径 |
|------|------|---------|
| **OBS Studio 28+** | 直播推流软件，需开启 WebSocket 服务 | 系统安装 |
| **MediaMTX** | RTMP 服务器 | `c:\myobs\mediamtx.exe` |
| **FFmpeg** | 流转码与推流 | `c:\ffmpeg\bin\ffmpeg.exe` |
| **Streamlink** | Twitch 直播流拉取 | 系统 PATH |
| **Microsoft Edge** | 网页平台浏览器窗口 | 系统安装 |

### 7.3 安装命令参考

```powershell
# Python 包
pip install obswebsocket pynput psutil pygetwindow python-vlc

# FFmpeg (需下载并放到 c:\ffmpeg\)
# https://ffmpeg.org/download.html

# Streamlink
pip install streamlink
# 或: winget install streamlink

# MediaMTX (已内置在项目目录)
# https://github.com/bluenviron/mediamtx/releases
```

---

## 8. 项目运行方式

### 8.1 前置条件

1. 安装 Python 3.8+
2. 安装 OBS Studio 28+ 并开启 WebSocket 服务
   - OBS → 工具 → WebSocket 服务器设置 → 启用
   - 默认端口: 4455
3. 安装 FFmpeg 到 `c:\ffmpeg\bin\`
4. 安装 Streamlink 到系统 PATH
5. 安装所需 Python 包

### 8.2 启动方式

```powershell
# 方式一：直接运行
python c:\myobs\manager_ui.pyw

# 方式二：双击 manager_ui.pyw 文件
```

### 8.3 首次运行配置

1. 启动后弹出 OBS 连接配置对话框
2. 输入 OBS WebSocket 主机、端口、密码
3. 点击连接
4. 系统自动创建 "多视角切换" 场景
5. 通过 "添加选手" 或 "快速添加" 导入直播源

### 8.4 基本操作流程

1. **添加选手**: 工具栏 → "添加选手" 或 "快速添加"（粘贴链接）
2. **移至视角列表**: 右键仓库选手 → "添加到视角列表"
3. **上源**: 勾选视角列表中的选手 → "批量上源"
4. **切换视角**: 使用快捷键（修饰键+单字符）或点击监视器窗口
5. **监控**: 工具栏 → "监视器" 打开多画面预览

### 8.5 快捷键

- 默认修饰键: `Alt+Shift`
- 切换: 按住修饰键 + 选手快捷键（如 `Alt+Shift+1`）
- 可在系统设置中修改修饰键组合

---

## 9. 配置说明

### 9.1 config.json 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `obs_host` | `localhost` | OBS WebSocket 主机 |
| `obs_port` | `4455` | OBS WebSocket 端口 |
| `obs_password` | `""` | OBS WebSocket 密码 |
| `max_active_streams` | `6` | 最大同时推流数量 |
| `hotkey_modifiers` | `alt+shift` | 快捷键修饰键 |
| `scene_name` | `多视角切换` | 专用 OBS 场景名 |

### 9.2 选手字段说明

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识，自动递增 |
| `name` | 显示名称 |
| `hotkey` | 单字符快捷键（字母或数字） |
| `platform` | 平台: `twitch` / `bilibili` / `douyin` / `custom_web` |
| `quality` | 推流清晰度: `best` / `worst` / `720p60` / `480p` / `360p` |
| `view_label` | 视角编号，用于 OBS 源命名 |
| `stream_name` | RTMP 流名称，格式 `player{id}` |
| `obs_source_name` | OBS 源名称，格式 `{name}_{view_label}_{hotkey}` |

---

> **文档生成时间**: 2026-07-11 | **项目路径**: `c:\myobs\`