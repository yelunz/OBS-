# 音频控制面板设计

> **背景**：OBS WebSocket v5 没有提供重排混音器的 API，混音器排序按源创建顺序固定。当前切换逻辑已通过 `SetInputAudioMonitorType` 实现了"当前视角监听并输出、非当前视角不监听不输出"，但用户希望在程序内直接控制音量，不依赖 OBS 混音器。

## 设计目标

1. **仪表盘**：活跃池卡片中每个选手名字旁添加音量滑条，直观显示当前音量
2. **监视器/弹出窗口**：格子改为卡片式 UI，底部添加 `−` `百分比` `+` 控制栏
3. **当前视角高亮**：当前视角的卡片/格子边框使用 ACCENT 色高亮
4. **实时同步**：调节音量时通过 OBS WebSocket API 实时设置，500ms 定时刷新同步显示

## 架构

### 数据流

```
用户操作 (滑条/加减按钮)
    ↓
AudioController.set_volume(player_name, volume)
    ↓
OBSController.set_volume(source_name, volume_db)
    ↓
obs-websocket SetInputVolume(inputName, inputVolumeDb)
    ↓
OBS 源音量改变
```

```
定时刷新 (500ms)
    ↓
OBSController.get_volume(source_name) → GetInputVolume
    ↓
AudioController.update_ui(player_name, volume)
    ↓
滑条/百分比标签更新
```

### 组件

#### 1. OBSController 扩展

新增方法：
- `get_volume(source_name)` → `GetInputVolume`，返回音量百分比（0-100）
- `set_volume(source_name, volume_percent)` → `SetInputVolume`，设置音量（百分比转 dB）

OBS WebSocket v5 的 `GetInputVolume` 返回两个字段：
- `inputVolumeMul`：音量乘数（0.0-1.0）
- `inputVolumeDb`：音量分贝（-100 到 0）

本设计使用 `inputVolumeMul` 转换为百分比（0-100），便于 UI 显示。

#### 2. 仪表盘活跃池卡片

修改 `_refresh_pool_cards` 方法：

卡片布局（横向）：
```
┌──────────────────────────────────┐
│ [选手名]  [━━━●━━] 75%  [活跃]  │
└──────────────────────────────────┘
```

- 选手名：FONT_BODY_BOLD
- 滑条：CTkSlider，width=80px，range=0-100
- 百分比标签：FONT_SMALL，宽度 32px
- 活跃指示：圆点（绿色=活跃，灰色=非活跃）

滑条事件：`command` 回调实时调用 `set_volume`。

#### 3. 监视器/弹出窗口格子 UI

修改 `_show_grid` 方法，改为卡片式设计：

```
┌─────────────────────────────┐
│  [选手名]      [平台图标]    │  ← 顶部栏（ELEVATED_BG）
├─────────────────────────────┤
│                             │
│        视频画面区域          │  ← Canvas（PAGE_BG）
│                             │
├─────────────────────────────┤
│  [−]  75%  [+]  [🔇]       │  ← 底部控制栏（ELEVATED_BG）
└─────────────────────────────┘
```

- 卡片：8px 圆角，1px 边框
- 顶部栏：24px 高，显示选手名 + 平台标识
- 视频区域：Canvas，VLC 嵌入或截图轮询
- 底部控制栏：28px 高，`−` 按钮 + 百分比标签 + `+` 按钮 + 静音按钮
- 当前视角：边框使用 ACCENT 色 + 2px 宽度
- 非当前视角：边框使用 BORDER 色 + 1px 宽度

按钮行为：
- `−` 按钮：点击减 5%，长按连续减少
- `+` 按钮：点击加 5%，长按连续增加
- 静音按钮：切换静音状态，静音时图标变色

#### 4. 音量同步

- **定时刷新**：500ms 间隔，通过 `GetInputVolume` 获取所有活跃选手的音量，更新 UI
- **防抖**：用户拖动滑条时，暂停定时刷新 1 秒，避免 UI 抖动
- **静音同步**：切换视角时，非当前视角自动静音（已有逻辑），UI 同步显示静音状态

## 错误处理

- `GetInputVolume` 失败（源不存在/连接断开）：保持上次显示的音量，不报错
- `SetInputVolume` 失败：日志记录，UI 不回滚（用户可重试）
- 滑条操作时 OBS 未连接：禁用滑条（grayed out）

## 范围边界

- 不修改 OBS 混音器本身的排序（API 不支持）
- 不替换 OBS 原生音频控制，只是提供程序内的便捷控制
- 不支持音频滤镜/效果（仅音量+静音）
- 不修改现有切换逻辑（`SetInputAudioMonitorType` 保持不变）

## 测试计划

1. 仪表盘滑条：拖动滑条，确认 OBS 源音量实时改变
2. 监视器加减按钮：点击 ±5%，确认音量正确变化
3. 长按连续调节：长按 `+`/`−`，确认音量连续变化
4. 静音按钮：点击静音，确认 OBS 源静音 + 图标变化
5. 定时同步：在 OBS 中手动调节音量，确认程序 UI 同步更新
6. 当前视角高亮：切换视角，确认对应卡片边框高亮
7. 卡片 UI 视觉：确认圆角、边框、配色符合主题
8. 多视角：8 个视角同时显示，确认布局自适应
