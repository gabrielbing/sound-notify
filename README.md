# 🔊 Sound Notify

> 一个零依赖的 Windows 声音提醒脚本 —— 任务完成、需要确认、权限请求时，用温柔的人声提醒你。

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <b>✨ 支持任意 AI Agent 平台</b> · WorkBuddy · Claude Code · Cursor · Windsurf · Copilot
</p>

---

## 🎯 它能做什么

当你的 AI Agent 完成任务、需要你确认、或者请求权限时，自动播放人声提醒。你再也不用盯着屏幕等结果。

| 事件 | 触发场景 | 播报内容 |
|------|---------|----------|
| `done` | 任务完成 | "搞定了，任务已完成。" |
| `confirm` | 需要确认 | "需要你确认一下。" |
| `perm` | 权限请求 | "需要你的授权才能继续。" |
| `alert` | 紧急提醒 | "请注意，一条重要的提醒。" |
| `daily` | 每日推送 | "这是您的每日推送。" |
| `thinking` | 思考超时 | "我还在思考，请稍微等一下。" |

---

## 🎤 语音引擎

| 引擎 | 音质 | 需要网络 | 需要安装 |
|------|------|---------|---------|
| **Edge TTS** ⭐ | 神经网络，自然温柔 | 首次需联网 | `pip install edge-tts` |
| **SAPI** | 系统自带 | 否 | 无（Windows 内置） |

默认使用 **Edge TTS + 云希**（温暖阳光男声），支持 8 种中文语音随时切换。

---

## 🚀 快速开始

### 1. 安装

```bash
# 安装在线语音引擎（推荐，音质更好）
pip install edge-tts

# 或者直接用离线模式（无需安装任何依赖）
```

### 2. 测试

```bash
# 在线人声测试
python scripts/notify.py test --edge

# 离线人声测试
python scripts/notify.py test --voice
```

### 3. 使用

```bash
python scripts/notify.py done --edge     # 任务完成
python scripts/notify.py confirm --edge  # 需要确认
python scripts/notify.py perm --edge     # 权限请求
```

---

## ⚙️ 自定义配置（无需改代码）

通过 JSON 配置文件，可以随意修改播报文案、默认语音、缓存目录，**完全不用改 `notify.py` 代码**。

### 生成示例配置

```bash
python scripts/notify.py --generate-config
# 生成到: ~/.sound-notify/config.json
```

### 配置文件格式

```json
{
  "default_voice": "zh-CN-YunxiNeural",
  "cache_dir": "~/.sound-notify/cache",
  "events": {
    "done":    { "voice": "✅ 任务搞定啦！" },
    "confirm":  { "voice": "⚠️ 等您确认哦～" },
    "perm":     { "voice": "🔐 需要授权才能继续" },
    "alert":    { "voice": "🚨 紧急提醒！" },
    "daily":    { "voice": "☀️ 今日推送已就绪" },
    "thinking": { "voice": "⏳ 稍等，正在处理中" }
  }
}
```

### 使用配置文件

```bash
# 使用默认路径 (~/.sound-notify/config.json)
python scripts/notify.py done --edge

# 使用指定路径
python scripts/notify.py --config /path/to/my-config.json done --edge
```

> 💡 配置文件支持 emoji！让播报更有趣 😄

### 多语言支持

通过 `--lang` 参数或配置文件中的 `"language"` 字段切换语言：

```bash
# 中文播报（默认）
python scripts/notify.py done --edge

# 英文播报
python scripts/notify.py done --edge --lang en-US
```

在 `config.json` 中设置默认语言：

```json
{
  "language": "en-US",
  "events": {
    "done": { "voice": "Job's done!" }
  }
}
```

内置语言包：
| 语言代码 | 语言 | 默认语音 |
|---------|------|---------|
| `zh-CN` | 中文 | 云希 (温柔男声) |
| `en-US` | English | Yunxi (warm male) |

---

## 📦 安装到各类 AI Agent

### WorkBuddy
直接上传 `sound-notify.zip` 到技能页面，开箱即用。

### Claude Code / Cursor / Windsurf / 任意 Agent
任何能执行 shell 命令的地方都能调用：

```bash
python /path/to/scripts/notify.py done --edge
```

在你的 Agent 配置中，绑定以下事件：

| Hook 事件 | 命令 |
|-----------|------|
| 任务完成 / Stop | `python notify.py done --edge` |
| 权限请求 | `python notify.py perm --edge` |
| 需要确认 | `python notify.py confirm --edge` |

### 作为 Python 模块

```python
from notify import play_voice, play_beep_then_voice

play_voice("done")                   # 离线人声
play_beep_then_voice("perm", engine="edge")  # 在线人声
```

---

## 🎛️ 命令行用法

```
python scripts/notify.py <事件> [选项]

事件:
  done       任务完成
  confirm    需要确认
  perm       权限请求
  alert      紧急提醒
  daily      每日推送
  thinking   处理中
  test       测试所有声音
  list       列出所有事件

选项:
  --edge, -e              使用 Edge TTS 在线人声（推荐）
  --voice, -v             使用 Windows SAPI 离线人声
  --voice-name NAME       指定 TTS 语音（如 zh-CN-YunyangNeural）
  --lang LANG            语言: zh-CN (默认) / en-US
  --rate N                语速调节（正数加快，负数减慢）
  --loop N                重复播放 N 次
  --interval SEC          重复间隔（秒）
  --list-voices           列出所有可用语音
  --no-cache              清理缓存并强制重新生成
  --config PATH           指定 JSON 配置文件路径
  --generate-config       生成示例配置文件
```

---

## 🗣️ 语音列表

### 男声

| ID | 名称 | 风格 |
|----|------|------|
| `zh-CN-YunxiNeural` ⭐ | 云希 | 温暖阳光（默认） |
| `zh-CN-YunyangNeural` | 云扬 | 专业可靠 |
| `zh-CN-YunjianNeural` | 云健 | 激情活力 |
| `zh-CN-YunxiaNeural` | 云夏 | 可爱少年 |

### 女声

| ID | 名称 | 风格 |
|----|------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 温暖知性 |
| `zh-CN-XiaoyiNeural` | 晓伊 | 活泼生动 |
| `zh-CN-XiaohanNeural` | 晓涵 | 温柔文静 |
| `zh-CN-XiaomoNeural` | 晓墨 | 知性成熟 |

切换语音：
```bash
python scripts/notify.py done --edge --voice-name zh-CN-YunyangNeural
```

---

## 🧠 工作原理

```
用户/AI 触发 → notify.py 接收事件
                     ↓
          ┌──────────┼──────────┐
          ↓          ↓          ↓
      Edge TTS    SAPI 离线   电子音
     (在线生成)  (系统自带)  (winsound)
          ↓          ↓          ↓
        MP3 缓存 → Windows MCI 播放 → 🔈 出声
```

- **Edge TTS**：首次播放在线生成音频（~1秒），之后从缓存秒播
- **SAPI**：调用 Windows 内置语音引擎，完全离线
- **缓存**：`~/.workbuddy/sound-cache/` 目录，按文本+语音 hash 存储

---

## 📋 系统要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows（使用 winsound 播报） |
| Python | 3.6+ |
| 网络 | Edge TTS 模式需要，SAPI 模式不需要 |

> 💡 macOS / Linux 用户可以用 `--voice` 离线模式，但 SAPI 仅限 Windows。欢迎提 PR 添加跨平台支持！

---

## 🔧 故障排查

| 问题 | 解决方案 |
|------|---------|
| 听不到人声 | 确认已安装 edge-tts: `pip install edge-tts` |
| 首次播放慢 | 正常现象，首次需联网生成，之后有缓存 |
| edge-tts 命令未找到 | 检查 Python Scripts 目录是否在 PATH 中 |
| 想用默认语音 | 不加 `--edge`，直接用系统 beep 或 SAPI |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果想添加新的语音、新的事件类型、或跨平台支持，请先开 Issue 讨论。

---

## 📄 许可证

[MIT License](LICENSE) — 自由使用、修改、分发。

---

## ⭐ Star History

如果这个项目对你有帮助，请点个 Star ⭐

---

<p align="center">
  Made with ❤️ for AI Agent users
</p>
