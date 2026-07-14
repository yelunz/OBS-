# 统一 Streamlink 架构设计

**日期**: 2026-07-15
**状态**: 已确认，待实现
**作者**: brainstorming 流程

## 背景与动机

### 当前问题

软件当前混合使用三种直播流获取方式，导致多个相互矛盾的问题：

1. **Twitch**: streamlink + ffmpeg → RTMP → OBS VLC源 + 监视器VLC嵌入
2. **B站/抖音/自定义网页**: OBS 浏览器源 + 监视器截图轮询

这套混合架构产生三个无法在OBS框架内解决的矛盾：

- **OBS干净 vs 监视器可用**: 浏览器源必须 `enabled=true` 才能渲染供截图，但 `enabled=true` 的源必然出现在音频混合器中。OBS框架内无法同时做到"源隐藏（OBS+音频干净）"和"源渲染（截图可用）"。
- **视角开关直观性**: 用户喜欢的"只显示当前视角，其他全部隐藏"老逻辑无法与浏览器源截图共存。
- **监视器帧率**: OBS截图轮询限制在10-15fps，用户反馈"有点卡"。

### 调研结论

经过网络调研确认：

1. **Streamlink 原生支持三平台**:
   - Twitch: 原生支持
   - B站 (`live.bilibili.com`): 有完整的 v1/v2 API + 页面解析插件
   - 抖音 (`live.douyin.com`): 用 `webcast/room/reflow/info` 接口解析，带画质权重（`full_hd1` > `hd1` > `sd2` > `sd1`），直接拿到 FLV 流

2. **B站二压是平台行为，与获取方式无关**:
   - "真原画"（1080P 60帧 8Mbps）只在开播瞬间存在，B站会在主播热度达阈值后隐藏，改提供二压流（1080P 60帧 ~3Mbps）
   - **浏览器源和 streamlink 拿到的是同一个二压流**，画质完全相同
   - 结论：切换到 streamlink 不会让B站画质变差

3. **抖音流有token时效**（约30分钟），streamlink douyin 插件内部处理token获取，流断开后重启streamlink会自动重新解析获取新token

## 设计目标

1. **OBS显示 + 监视器显示**: 同一个RTMP流同时供OBS VLC源和监视器VLC嵌入使用，两者都要正常显示画面
2. **OBS干净**: 恢复"只显示当前视角"的传统开关逻辑，音频面板只显示当前视角
3. **监视器流畅**: VLC原生播放，帧率远高于截图
4. **修复刷新问题**: 自动生成的VLC源添加到OBS后不点刷新不显示的bug
5. **三平台统一**: 统一代码路径，简化维护

## 架构设计

### 整体架构

```
Twitch频道 ─┐
            │
B站直播间 ──┼──→ Streamlink解析 ──→ ffmpeg ──→ MediaMTX(RTMP) ──┬──→ OBS VLC源(显示用)
            │   (最高画质)         (转封装flv)                    └──→ 监视器VLC嵌入(预览用)
抖音直播间 ─┘
```

三个平台全部用 Streamlink 统一解析 → RTMP 流 → OBS VLC源(显示) + 监视器VLC嵌入(预览)。**完全移除 OBS 浏览器源和截图轮询**。

### 组件划分

#### 组件1: 推流管线 (Streamlink + ffmpeg)

**职责**: 从平台解析直播流并转封装为RTMP推送到MediaMTX

**接口**:
- 输入: 选手URL (网页链接), stream_name (RTMP路径名)
- 输出: RTMP流 `rtmp://localhost:1935/live/{stream_name}`
- 副作用: 启动两个子进程 (streamlink + ffmpeg), 记录 `stream_pid`

**实现细节**:

统一命令（所有平台相同）:
- 步骤1: `streamlink {url} best -O --retry-max 5 --retry-streams 5` → 输出流数据到stdout
- 步骤2: `ffmpeg -re -i pipe:0 -c copy -f flv {rtmp_url}` → 转封装为RTMP推流
- 两步通过 pipe 连接

**平台差异处理**:
- Twitch: URL 直接是 `twitch.tv/频道名`
- B站: URL 是 `live.bilibili.com/房间号`
- 抖音: URL 是 `live.douyin.com/房间号`

**统一配置字段**: 所有平台只保留一个 `url` 字段（网页链接），废弃 `douyin_url`/`browser_url`/`channel` 等多字段。需提供数据迁移逻辑，启动时将旧字段值合并到 `url`。

**依赖**: streamlink (已安装), ffmpeg (已安装), MediaMTX (已运行)

#### 组件2: OBS源管理 (含刷新修复)

**职责**: 创建/删除/显隐 OBS VLC源，确保源正确播放

**关键修复 — 主动触发播放**:

当前 `create_vlc` 依赖 `playback_behavior: always_play`，但该设置有时不生效，导致源不显示画面。修复方案：

1. `CreateInput` 创建VLC源（enabled=false，静音）
2. **新增**: 主动调用 `TriggerMediaInputAction(action=play)` 触发播放
3. 延迟500ms后通过 `GetMediaInputStatus` 检查 `mediaState` 是否为 `playing`，未播放则再次调用 `trigger_media_play` 重试一次

**新增 OBSController 方法**:
```python
def trigger_media_play(self, name):
    """主动触发VLC源播放，解决always_play不生效问题"""
    try:
        self.ws.call(requests.TriggerMediaInputAction(
            inputName=name,
            mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY"
        ))
    except Exception as e:
        log("系统", f"[OBS-触发播放失败] {name}: {e}")

def trigger_media_restart(self, name):
    """重启VLC源播放"""
    try:
        self.ws.call(requests.TriggerMediaInputAction(
            inputName=name,
            mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
        ))
    except Exception as e:
        log("系统", f"[OBS-重启播放失败] {name}: {e}")
```

**切换视角** (`switch_to` 恢复老逻辑):
- 隐藏并静音所有其他源（**包括B站/抖音**，因为不再依赖截图）
- 显示并取消静音当前源
- **新增**: 显示后主动调用 `trigger_media_play` 确保播放

**刷新功能** (`refresh_player` 修复，支持所有平台):
- 不再 deactivate→activate 重建进程
- 改为: 重启推流管线 + `trigger_media_restart` 重启OBS源播放
- 三平台通用
- 监视器VLC实例同步: `mp.stop()` → `mp.play()` 重连

#### 组件3: 监视器预览 (统一VLC嵌入)

**职责**: 在监视器网格中嵌入VLC播放RTMP流

**实现**:
- 所有平台: `mp.set_hwnd(canvas.winfo_id())` 嵌入同一RTMP流
- pynput全局钩子处理点击跳转（已实现，保持不变）
- `_check_vlc_health` 每3秒检查，未播放则重连

**移除内容**:
- `_start_screenshot_monitor` 及相关截图线程、锁、帧缓存
- `_switch_thread` 中的"不隐藏浏览器源"逻辑（改为全部隐藏）
- `set_source_index` 层级覆盖逻辑（不再需要）

#### 组件4: 进程监控与自动重试

**职责**: 监控推流进程，异常退出时自动重启

**抖音token时效处理**:
- Streamlink douyin 插件内部已处理token获取
- 但流地址本身有30分钟时效，超时后流会断开
- **处理方式**: `_stream_process_monitor` 检测到进程退出后自动重启，重启时streamlink会重新解析获取新token
- **重试上限**: 从3次改为**无限次**（抖音token时效是正常现象，不应限制重试）

**Twitch/B站**: 保持现有3次重试上限（异常退出才重试，正常情况不会触发）

#### 组件5: sync_player 统一

**职责**: 确保OBS中存在对应选手的VLC源

**变更**: 
- 移除B站/抖音/自定义网页的浏览器源创建分支
- 所有平台统一调用 `create_vlc` 创建VLC源
- URL 来自选手的 `url` 字段（统一字段）

## 数据流

### 推流启动流程

```
选手加入活跃池
  → activate_player
    → sync_player (创建OBS VLC源)
    → start_stream
      → streamlink {url} best -O | ffmpeg -re -i pipe:0 -c copy -f flv {rtmp}
      → _stream_process_monitor (启动进程监控)
    → switch_to (显示当前源, 触发播放)
    → 监视器 refresh → _show_grid → _start_vlc (嵌入VLC预览)
```

### 切换视角流程

```
用户点击监视器网格 (pynput全局钩子)
  → after(0, switch_to, player)
    → 隐藏并静音所有其他VLC源
    → 显示并取消静音目标VLC源
    → trigger_media_play (确保播放)
```

### 刷新流程

```
用户右键选手 → 刷新源
  → refresh_player
    → stop_stream (停止推流管线)
    → start_stream (重启推流管线)
    → trigger_media_restart (重启OBS VLC源)
    → 监视器VLC: mp.stop() → mp.play() (重连)
```

## 错误处理

1. **Streamlink解析失败** (直播间未开播/链接无效):
   - 日志记录 `[推流-失败] streamlink解析失败`
   - 不启动ffmpeg，`start_stream` 返回 False
   - UI提示"推流失败，请检查直播间链接"

2. **ffmpeg推流失败**:
   - 进程监控检测到退出，自动重启（抖音无限次，其他3次）
   - 连续失败超限后停止监控，UI标记为"已断开"

3. **OBS VLC源不显示画面**:
   - `create_vlc` 后主动 `trigger_media_play`
   - 500ms后检查未播放则重试一次
   - 仍失败则日志告警，用户可手动"刷新源"

4. **MediaMTX未运行**:
   - `wait_for_mediamtx` 等待10秒
   - 超时则启动 MediaMTX 进程

5. **OBS断连**:
   - 现有 `ensure_obs_connected` 重连机制保持不变

## 测试计划

### 功能测试

1. **Twitch推流**: 添加Twitch选手，推流后OBS和监视器都显示画面
2. **B站推流**: 添加B站选手，推流后OBS和监视器都显示画面，画质与浏览器源方案相同
3. **抖音推流**: 添加抖音选手，推流后OBS和监视器都显示画面
4. **三平台混合**: 同时推流Twitch+B站+抖音，OBS和监视器都正常
5. **切换视角**: 快速点击不同视角，OBS只显示当前视角，音频面板干净
6. **刷新源**: 右键刷新Twitch/B站/抖音源，画面重启正常
7. **抖音token超时**: 抖音推流30分钟后，流断开自动重连

### 回归测试

8. **OBS快捷键**: switcher.py 切换视角正常工作
9. **监视器点击跳转**: pynput全局钩子点击跳转正常
10. **主题切换**: 明暗主题切换不破坏监视器
11. **进程退出恢复**: 强杀推流进程，自动重启

### 性能验证

12. **多视角资源占用**: 8个活跃选手的内存/CPU占用
13. **监视器帧率**: VLC嵌入帧率（预期30fps+，远高于截图的10fps）

## 配置迁移

启动时检测旧配置并迁移:
- `douyin_url` → `url` (抖音选手)
- `browser_url` → `url` (B站/自定义网页选手)
- `channel` → `url` (Twitch选手，转换为 `https://twitch.tv/{channel}`)
- 保留 `obs_source_name` (switcher.py 依赖)
- 移除 `douyin_url`/`browser_url`/`channel` 旧字段

## 范围边界

**本次包含**:
- 三平台统一 Streamlink 推流管线
- OBS VLC源主动触发播放修复
- 监视器统一VLC嵌入（移除截图）
- 抖音token自动重试
- 配置字段统一迁移

**本次不包含**:
- switcher.py 快捷键逻辑（保持不变）
- web_remote.py 遥控功能（保持不变）
- UI布局/主题（保持不变）
- 自定义网页(custom_web)平台支持（如果URL是网页而非直播流，streamlink可能无法解析，暂不支持，后续按需扩展）
