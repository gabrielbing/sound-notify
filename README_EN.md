# sound-notify (English)

🔊 Sound Notify — Universal Sound Notification Tool for AI Agents (Windows / macOS / Linux, Python, Dual Engine)

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com/gabrielbing/sound-notify)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

## 🌟 Why Sound Notify?

AI agents work silently — you never know when a task is done, when confirmation is needed, or when permission is required. **Sound Notify** adds human voice announcements to your AI workflow, so you never miss an important moment.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🔊 Human Voice** | Uses TTS to announce events — much nicer than a beep |
| **⚡ Dual Engine** | Edge TTS (online neural voices) / System TTS (offline) |
| **🌍 Multi-language** | Built-in `zh-CN` and `en-US` language packs |
| **📋 6 Event Types** | done / daily / confirm / perm / alert / thinking |
| **⚙️ Zero Config** | Pure Python + system TTS, works out of the box |
| **📝 Configurable** | Customize voice text via `config.json` — no code changes |

## 🚀 Quick Start

### 1. Install

```bash
# Download the script
curl -O https://raw.githubusercontent.com/gabrielbing/sound-notify/main/scripts/notify.py

# Install Edge TTS (recommended — better voice quality)
pip install edge-tts
```

### 2. Test

```bash
# Use Edge TTS (requires internet)
python notify.py test --edge

# Use system TTS (offline)
python notify.py test --voice
```

## 🔧 How It Works

```
AI Agent (WorkBuddy/Claude/Cursor)
    ↓ (task done / needs confirmation)
Hook triggers
    ↓
notify.py <event>
    ↓
TTS Engine (Edge TTS / System TTS)
    ↓
🔊 Voice announcement played
```

## 📦 Install to AI Agents

### WorkBuddy

Download `sound-notify.zip` and upload it in the WorkBuddy Skills page.

### Claude Code / Cursor / Any Agent

Call `notify.py` from your hook / script:

```bash
python notify.py done --edge    # task completed
python notify.py confirm --edge  # needs confirmation
python notify.py perm --edge     # permission required
```

## 🎯 Supported Events

| Event | Argument | Default Message (EN) | When to Use |
|-------|----------|---------------------|-------------|
| Task done | `done` | "Done! Task completed." | When AI finishes a task |
| Daily push | `daily` | "Your daily update is ready." | Scheduled reminders |
| Needs confirm | `confirm` | "Please confirm to proceed." | Waiting for user input |
| Permission | `perm` | "Permission required to continue." | When authorization is needed |
| Alert | `alert` | "Alert! Please check this out." | Important notifications |
| Thinking | `thinking` | "Still processing, please wait." | Long-running tasks |

## ⚙️ Configuration (No Code Changes!)

Create a `config.json` to customize voice text:

```bash
python notify.py --generate-config
# Creates: ~/.sound-notify/config.json
```

Edit the config:

```json
{
  "language": "en-US",
  "events": {
    "done":    { "voice": "✅ All done!" },
    "confirm":  { "voice": "⚠️ Please confirm!" },
    "perm":     { "voice": "🔐 Need your permission" }
  }
}
```

## 🌍 Multi-language Support

```bash
# Chinese (default)
python notify.py done --edge

# English
python notify.py done --edge --lang en-US
```

## 📖 Full Usage

```
Usage: notify.py <event> [options]

Positional arguments:
  <event>       done / daily / confirm / perm / alert / thinking / test / list

Options:
  --edge, -e              Use Edge TTS (online, recommended)
  --voice, -v             Use system TTS (offline)
  --voice-name NAME        Specify TTS voice (e.g. zh-CN-YunyangNeural)
  --lang LANG             Language: zh-CN (default) / en-US
  --rate N                 Speech rate (positive = faster, negative = slower)
  --loop N                Repeat N times
  --interval SEC           Interval between repeats (seconds)
  --list-voices           List all available voices
  --no-cache              Clear cache and force re-generation
  --config PATH            Specify JSON config file path
  --generate-config       Generate sample config file
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|-----------|
| Edge TTS error | Check internet connection, or use `--voice` for offline mode |
| No sound (SAPI) | Check Windows speech synthesis settings |
| Permission error | Run command prompt as administrator |
| Cache takes space | Use `--no-cache` to clean up |

## 📄 License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE) file for details.

---

⭐ If this project helps you, please give it a star!
