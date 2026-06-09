---
name: sound-notify
description: Play audio notifications for WorkBuddy task events with both electronic beeps and human voice (offline SAPI + online Edge TTS neural voices). Defaults to warm male voice 云希 (zh-CN-YunxiNeural). Supports 8 Chinese voices (4 male + 4 female). Triggers on "声音提醒", "人声提醒", "sound notify", "/sound-notify". Use this when the user wants audible alerts for task completion, pending confirmation, permission requests, daily digests, or emergency alerts.
agent_created: true
---

# Sound Notify — WorkBuddy 声音提醒技能

为 WorkBuddy 提供声音提醒能力。在任务完成、待确认、权限请求、每日推送等关键时刻，
通过「电子提示音 + 中文人声播报」让你不用盯着屏幕也能知道发生了什么。

## 前置条件

- **操作系统**: Windows（使用了 winsound 和 Windows SAPI/MCI）
- **Python**: 3.8+（WorkBuddy 管理版自动可用）
- **edge-tts**（在线人声, 推荐）:
  ```bash
  pip install edge-tts
  ```
  安装后首次使用会自动缓存音频, 之后秒播。离线 SAPI 模式不需要额外依赖。

## 快速开始

安装技能后，直接说:

```
/sound-notify test --edge
```

会依次测试所有 6 种事件的提示音 + 云希人声播报。

## 6 种事件类型

| 事件 | 场景 | 播报内容 |
|------|------|----------|
| `done` | 任务完成 | "搞定了，任务已完成。" |
| `daily` | 每日推送 | "今日推送已就绪，来看看吧。" |
| `confirm` | 待确认 | "需要你确认一下。" |
| `perm` | 权限请求 | "需要你的授权才能继续。" |
| `alert` | 紧急提醒 | "注意，有紧急提醒！" |
| `thinking` | 处理中 | "正在处理中，请稍候。" |

## 三种播放引擎

| 参数 | 引擎 | 音质 | 需要联网 |
|------|------|------|----------|
| `--edge` ★ | Edge TTS 在线 | 神经网络，自然温柔 | 首次需联网 |
| `--voice` | Windows SAPI 离线 | 系统自带 | 否 |
| (默认) | 电子音 Beep | 钢琴旋律 | 否 |

推荐使用 `--edge` 模式，音质最佳。离线时自动回退到 SAPI 或电子音。

## 8 种中文语音（Edge TTS）

### 男声组

| ID | 名称 | 风格 | 适合场景 |
|----|------|------|----------|
| `zh-CN-YunxiNeural` ★ | 云希 | 温柔阳光 | 日常提醒（默认） |
| `zh-CN-YunyangNeural` | 云扬 | 专业可靠 | 正式汇报风格 |
| `zh-CN-YunjianNeural` | 云健 | 激情活力 | 重要通知 |
| `zh-CN-YunxiaNeural` | 云夏 | 可爱少年 | 轻松俏皮 |

### 女声组

| ID | 名称 | 风格 | 适合场景 |
|----|------|------|----------|
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 温暖知性 | 温柔提醒 |
| `zh-CN-XiaoyiNeural` | 晓伊 | 活泼生动 | 元气满满 |
| `zh-CN-liaoning-XiaobeiNeural` | 晓蓓 | 东北口音 | 幽默风趣 |
| `zh-CN-shaanxi-XiaoniNeural` | 晓妮 | 陕西口音 | 清脆明亮 |

切换语音:
```
/sound-notify done --edge --voice-name zh-CN-YunyangNeural
```

## WorkBuddy 自动触发

开启声音提醒后，WorkBuddy 在以下时刻自动调用脚本:

```
python scripts/notify.py done --edge       # 任务完成
python scripts/notify.py confirm --edge    # 待用户确认
python scripts/notify.py perm --edge       # 请求权限
python scripts/notify.py daily --edge      # 每日推送/日报
python scripts/notify.py alert --edge      # 紧急提醒
python scripts/notify.py thinking --edge   # 正在处理中
```

## 完整参数说明

| 参数 | 说明 |
|------|------|
| `event` | 事件类型: done / daily / confirm / perm / alert / thinking / test / list |
| `--edge, -e` | 使用 Edge TTS 在线神经网络语音（推荐） |
| `--voice, -v` | 使用 Windows SAPI 离线 TTS |
| `--beep-voice, -bv` | 提示音 + 离线人声（先叮一声再说话） |
| `--voice-name NAME` | 指定语音, 如 `zh-CN-YunyangNeural` 或 `zh-CN-XiaoxiaoNeural` |
| `--rate N, -r N` | 语速调节（在线: -50% ~ +50%, 离线: -10 ~ 10） |
| `--loop N` | 重复播放 N 次 |
| `--interval SEC` | 重复播放间隔（秒） |
| `--list-voices` | 列出所有可用语音 |
| `--no-cache` | 跳过/清理音频缓存, 强制重新生成 |
| `--json` | JSON 格式输出结果 |

## 音频缓存

Edge TTS 生成的音频自动缓存在 `~/.workbuddy/sound-cache/` 目录。
首次播放在线生成（约 1-2 秒），之后从缓存秒播。
使用 `--no-cache` 可清理缓存并强制重新生成。

## 工作原理

1. **电子音**: Python `winsound.Beep()` 生成不同频率/时长的钢琴音
2. **离线人声**: PowerShell 调用 Windows `System.Speech` SAPI 引擎
3. **在线人声**: `edge-tts` 调用微软 Edge TTS API, 生成 MP3 后通过 Windows MCI 播放

三种引擎互为备选，确保在任何网络状态下都能发出提醒。

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 听不到人声 | 确认已安装 edge-tts: `pip install edge-tts` |
| 中文乱码/无声 | 回退到电子音: `notify.py done` (不加 --edge) |
| 首次播放慢 | 正常现象, 首次需联网生成音频, 之后有缓存 |
| edge-tts 命令未找到 | 检查 Python Scripts 目录是否在 PATH 中 |
| 非 Windows 系统 | 电子音模式可用, SAPI/Edge 模式需要 Windows |
