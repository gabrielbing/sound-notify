#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sound Notify — 通用声音提醒工具 (跨平台: Windows / macOS / Linux)
支持通过 JSON 配置文件自定义播报文案、语音、缓存目录。
用法:
    python notify.py done --edge
    python notify.py --config my-config.json done --edge
"""

import sys
import time
import argparse
import json
import subprocess
import ctypes
import os
import tempfile
import hashlib
from pathlib import Path

# ── 平台检测 ─────────────────────────────────────
PLATFORM  = sys.platform  # "win32" / "darwin" / "linux"
IS_WINDOWS = PLATFORM == "win32"
IS_MAC     = PLATFORM == "darwin"
IS_LINUX   = PLATFORM == "linux"

# ── 条件导入 Windows 专用模块 ─────────────────────
winsound = None
if IS_WINDOWS:
    import winsound


# ── 多语言文案包 ─────────────────────────────────────
LANG_PACK = {
    "zh-CN": {
        "done":       "搞定了，任务已完成。",
        "confirm":     "需要你确认一下。",
        "perm":        "需要你的授权才能继续。",
        "alert":       "请注意，一条重要的提醒。",
        "daily":       "今日推送已就绪，来看看吧。",
        "thinking":    "正在处理中，请稍候。",
    },
    "en-US": {
        "done":       "Done! Task completed.",
        "confirm":     "Please confirm to proceed.",
        "perm":        "Permission required to continue.",
        "alert":       "Alert! Please check this out.",
        "daily":       "Your daily update is ready.",
        "thinking":    "Still processing, please wait.",
    },
}
DEFAULT_LANG = "zh-CN"


def get_voice_text(event_key, lang=None):
    """获取指定事件的播报文案（支持多语言）"""
    l = lang or DEFAULT_LANG
    return LANG_PACK.get(l, LANG_PACK["zh-CN"]).get(event_key, event_key)


# ── 事件配置（可通过 JSON 配置文件覆盖）───────────────────────────────
SOUND_PATTERNS = {
    "done": {
        "label":       "任务完成",
        "description": "愉悦的上升旋律",
        "voice":       "搞定了，任务已完成。",
        "notes":       [(523, 150), (659, 150), (784, 150), (1047, 400)],
        "pauses":      [80, 80, 80],
    },
    "daily": {
        "label":       "每日推送",
        "description": "晨间风格的温暖旋律",
        "voice":       "今日推送已就绪，来看看吧。",
        "notes":       [(523, 200), (659, 200), (784, 200), (659, 200), (784, 300)],
        "pauses":      [100, 100, 100, 100],
    },
    "confirm": {
        "label":       "待确认",
        "description": "温和的双音提示",
        "voice":       "需要你确认一下。",
        "notes":       [(659, 200), (784, 300)],
        "pauses":      [150],
    },
    "perm": {
        "label":       "权限请求",
        "description": "三段式提醒",
        "voice":       "需要你的授权才能继续。",
        "notes":       [(784, 120), (784, 120), (988, 300)],
        "pauses":      [80, 80],
    },
    "alert": {
        "label":       "紧急提醒",
        "description": "急促的警告音",
        "voice":       "注意，有紧急提醒！",
        "notes":       [(880, 100), (880, 100), (880, 100), (1047, 400)],
        "pauses":      [60, 60, 60],
    },
    "thinking": {
        "label":       "思考中",
        "description": "轻柔提示",
        "voice":       "正在处理中，请稍候。",
        "notes":       [(440, 100), (523, 100)],
        "pauses":      [300],
    },
}


# ── Edge TTS 语音配置 ─────────────────────────────────────
EDGE_VOICE        = "zh-CN-YunxiNeural"    # 默认：云希
EDGE_VOICE_FALLBACK = "zh-CN-YunyangNeural" # 备选

# 音频缓存目录（可通过配置文件覆盖）
CACHE_DIR = Path.home() / ".sound-notify" / "cache"

# edge-tts 可执行文件路径
_EDGE_TTS_EXE = None

# 配置文件搜索路径
DEFAULT_CONFIG_DIR  = Path.home() / ".sound-notify"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


def load_config(config_path=None):
    """加载 JSON 配置文件"""
    candidates = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    try:
        script_dir = Path(__file__).parent.parent
        candidates.append(script_dir / "sound-notify.json")
    except NameError:
        pass
    candidates.append(DEFAULT_CONFIG_FILE)

    for cand in candidates:
        if cand.exists():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                print(f"[config] 已加载: {cand}")
                return cfg
            except Exception as e:
                print(f"[config] 读取失败 {cand}: {e}", file=sys.stderr)
    return {}


def apply_config(cfg, lang=None):
    """将 cfg 中的配置应用到全局变量"""
    global EDGE_VOICE, CACHE_DIR, DEFAULT_LANG

    if lang:
        DEFAULT_LANG = lang
    elif "language" in cfg:
        DEFAULT_LANG = cfg["language"]

    events = cfg.get("events", {})
    for key, val in events.items():
        if key in SOUND_PATTERNS and isinstance(val, dict) and "voice" in val:
            SOUND_PATTERNS[key]["voice"] = val["voice"]
        lang_key = DEFAULT_LANG
        if lang_key in LANG_PACK and key in LANG_PACK[lang_key]:
            LANG_PACK[lang_key][key] = val["voice"]

    if "default_voice" in cfg:
        EDGE_VOICE = cfg["default_voice"]

    if "cache_dir" in cfg:
        CACHE_DIR = Path(cfg["cache_dir"]).expanduser()


def _get_edge_tts():
    """查找 edge-tts 可执行文件"""
    global _EDGE_TTS_EXE
    if _EDGE_TTS_EXE:
        return _EDGE_TTS_EXE

    exe_name = "edge-tts.exe" if IS_WINDOWS else "edge-tts"
    candidates = []

    if IS_WINDOWS:
        candidates.append(
            Path.home() / ".workbuddy" / "binaries" / "python" /
            "versions" / "3.13.12" / "Scripts" / "edge-tts.exe"
        )

    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d) / exe_name
        if p.exists():
            candidates.append(p)

    for p in candidates:
        if p.exists():
            _EDGE_TTS_EXE = str(p)
            return _EDGE_TTS_EXE
    return None


# ── 跨平台音频播放 ─────────────────────────────────────

def _play_mp3(filepath):
    """跨平台播放 MP3"""
    f = str(filepath)
    try:
        if IS_WINDOWS:
            return _play_mp3_mci(f)
        elif IS_MAC:
            subprocess.run(["afplay", f],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=30)
            return True
        elif IS_LINUX:
            for player in ["paplay", "aplay", "mpg123", "mpg321"]:
                r = subprocess.run(["which", player], capture_output=True)
                if r.returncode == 0:
                    subprocess.run([player, f],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=30)
                    return True
            return False
        else:
            return _play_mp3_mci(f)  # fallback
    except Exception:
        return False


def _play_mp3_mci(filepath):
    """Windows MCI 播放 MP3（仅 Windows）"""
    if not IS_WINDOWS:
        return False
    try:
        buf = ctypes.create_unicode_buffer(256)
        cmd_open = f'open "{filepath}" type mpegvideo alias sndfy'
        r = ctypes.windll.winmm.mciSendStringW(cmd_open, None, 0, None)
        if r != 0:
            ctypes.windll.winmm.mciGetErrorStringW(r, buf, 256)
            return False
        ctypes.windll.winmm.mciSendStringW("play sndfy wait", None, 0, None)
        ctypes.windll.winmm.mciSendStringW("close sndfy", None, 0, None)
        return True
    except Exception:
        return False


def _play_beep(freq, dur_ms):
    """跨平台蜂鸣"""
    try:
        if IS_WINDOWS and winsound:
            winsound.Beep(freq, dur_ms)
            return True
        elif IS_MAC:
            # macOS: 用 sox 生成 beep（如已安装）
            r = subprocess.run(["which", "sox"], capture_output=True)
            if r.returncode == 0:
                dur_s = f"{dur_ms/1000:.2f}"
                subprocess.run(
                    ["sox", "-n", "-d", "synth", dur_s, "sine", str(freq)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=10)
                return True
            return True  # 无 sox 则跳过
        elif IS_LINUX:
            r = subprocess.run(["which", "speaker-test"], capture_output=True)
            if r.returncode == 0:
                timeout_s = max(int(dur_ms / 1000), 2)
                subprocess.run(
                    ["speaker-test", "-t", "sine", "-f", str(freq), "-l", "1"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=timeout_s, preexec_fn=os.setsid)
                return True
            return True  # 跳过
        return True
    except Exception:
        return True  # 蜂鸣失败不阻塞


def _play_system_sound(sound_name):
    """跨平台系统提示音"""
    try:
        if IS_WINDOWS and winsound:
            mapping = {
                "asterisk":   winsound.MB_ICONASTERISK,
                "exclamation": winsound.MB_ICONEXCLAMATION,
                "hand":        winsound.MB_ICONHAND,
            }
            winsound.MessageBeep(mapping.get(sound_name, winsound.MB_OK))
            return True
        elif IS_MAC:
            sound_map = {
                "asterisk":   "/System/Library/Sounds/Ping.aiff",
                "exclamation": "/System/Library/Sounds/Pop.aiff",
                "hand":        "/System/Library/Sounds/Funk.aiff",
            }
            f = sound_map.get(sound_name, "/System/Library/Sounds/Ping.aiff")
            if os.path.exists(f):
                subprocess.run(["afplay", f],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=5)
            return True
        elif IS_LINUX:
            return True  # Linux 无标准系统提示音，跳过
        return True
    except Exception:
        return True


# ── 电子音 ─────────────────────────────────────────────
def play_pattern(pattern_key):
    config = SOUND_PATTERNS.get(pattern_key)
    if not config:
        return False
    notes  = config["notes"]
    pauses = config.get("pauses", [])
    for i, (freq, dur) in enumerate(notes):
        _play_beep(freq, dur)
        if i < len(pauses):
            time.sleep(pauses[i] / 1000.0)
    return True


def play_system(pattern_key):
    sys_key = f"{pattern_key}_sys"
    # 仅 Windows 使用系统音
    if IS_WINDOWS:
        _play_system_sound(pattern_key)
        return True
    return play_pattern(pattern_key)  # 非 Windows 降级为电子音


# ── 离线 TTS ─────────────────────────────────────────────
def _speak_offline(text, voice_name=None, rate=0):
    """跨平台离线 TTS"""
    safe = text.replace('"', "'").replace("$", " ").replace("`", "'")

    if IS_WINDOWS:
        # Windows: PowerShell SAPI
        vs = f'$s.SelectVoice("{voice_name}")' if voice_name else ""
        ps = f'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
{vs}
$s.Rate = {rate}
$s.Speak("{safe}")
'''
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
            )
            return True
        except Exception:
            return False

    elif IS_MAC:
        # macOS: say 命令
        rate_arg = str(200 + rate * 20) if isinstance(rate, int) else "200"
        voice_arg = voice_name if voice_name else "Alex"
        try:
            subprocess.run(
                ["say", "-v", voice_arg, "-r", rate_arg, safe],
                timeout=30,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    elif IS_LINUX:
        # Linux: espeak 或 spd-say
        for tts_cmd in ["espeak", "spd-say"]:
            r = subprocess.run(["which", tts_cmd], capture_output=True)
            if r.returncode == 0:
                try:
                    subprocess.run(
                        [tts_cmd, "-v", "zh" if "zh" in DEFAULT_LANG else "en",
                         safe],
                        timeout=30,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    continue
        return False

    return False


# ── 在线 TTS (Edge TTS) ──────────────────────────────
def _speak_edge(text, voice=None, rate="+0%"):
    """Microsoft Edge TTS — 神经网络语音（跨平台）"""
    exe = _get_edge_tts()
    if not exe:
        return False

    voice = voice or EDGE_VOICE
    cache_key   = hashlib.md5(f"{voice}:{text}:{rate}".encode()).hexdigest()
    cache_file  = CACHE_DIR / f"{cache_key}.mp3"

    if cache_file.exists():
        return _play_mp3(str(cache_file))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_DIR / f"_tmp_{cache_key}.mp3"

    try:
        result = subprocess.run(
            [exe, "--voice", voice, "--rate", rate,
             "--text", text, "--write-media", str(tmp)],
            capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        if result.returncode != 0:
            if voice == EDGE_VOICE and EDGE_VOICE_FALLBACK:
                return _speak_edge(text, voice=EDGE_VOICE_FALLBACK, rate=rate)
            return False

        if tmp.exists() and tmp.stat().st_size > 0:
            tmp.rename(cache_file)
            return _play_mp3(str(cache_file))
        return False

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


# ── 综合播放 ─────────────────────────────────────────────
def play_voice(pattern_key, engine="edge", voice_name=None, rate=0, lang=None):
    """播放人声（支持多语言）"""
    config = SOUND_PATTERNS.get(pattern_key)
    if not config:
        return False
    text = get_voice_text(pattern_key, lang=lang)
    if text == pattern_key:
        text = config.get("voice", config["label"])

    if engine == "edge":
        rate_str = f"{rate:+d}%" if isinstance(rate, int) else rate
        return _speak_edge(text, voice=voice_name, rate=rate_str)

    return _speak_offline(text, voice_name=voice_name, rate=rate)


def play_beep_then_voice(pattern_key, engine="edge", voice_name=None, rate=0, lang=None):
    """播放人声（无提示音，支持多语言）"""
    return play_voice(pattern_key, engine=engine, voice_name=voice_name, rate=rate, lang=lang)


# ── 辅助功能 ─────────────────────────────────────────────
def _detect_voice():
    """检测可用的离线语音"""
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Speech; "
                 "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 "$s.GetInstalledVoices() | % { $_.VoiceInfo.Name }"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW)
            for line in result.stdout.strip().split("\n"):
                name = line.strip()
                if name and ("Chinese" in name or "huihui" in name.lower()):
                    return name
        except Exception:
            pass
    elif IS_MAC:
        return "Alex"  # macOS 默认语音
    elif IS_LINUX:
        r = subprocess.run(["which", "espeak"], capture_output=True)
        if r.returncode == 0:
            return "espeak"
    return None


def list_voices():
    """列出可用语音（跨平台）"""
    print("\n可用语音 (Edge TTS):\n")
    voices = [
        ("zh-CN-YunxiNeural",    "云希 ★",   "Male, Lively — 温柔阳光男声"),
        ("zh-CN-YunyangNeural",  "云扬",      "Male, Professional — 专业可靠男声"),
        ("zh-CN-YunjianNeural",  "云健",      "Male, Passion — 激情活力男声"),
        ("zh-CN-XiaoxiaoNeural", "晓晓",      "Female, Gentle — 温暖知性女声"),
        ("zh-CN-XiaoyiNeural",   "晓伊",      "Female, Lively — 活泼生动女声"),
    ]
    for vid, name, desc in voices:
        mark = " ← 默认" if vid == EDGE_VOICE else ""
        print(f"  {vid:<32} {name:<8} {desc}{mark}")

    if IS_MAC:
        print("\n[macOS 离线 TTS: 使用 `say` 命令]")
    elif IS_LINUX:
        print("\n[Linux 离线 TTS: 需要安装 espeak 或 spd-say]")


def test_all(engine="edge"):
    """测试所有模式"""
    mode = {"edge": "Edge TTS (在线神经网络)", "offline": "离线 TTS", "beep": "电子音"}.get(engine, engine)
    print("=" * 55)
    print(f"  Sound Notify — 全模式测试")
    print(f"  引擎: {mode}")
    print("=" * 55)

    for key, config in SOUND_PATTERNS.items():
        print(f"\n>>> {config['label']} ({key})")
        print(f"    播报: {config['voice']}")
        if engine == "beep":
            play_pattern(key)
        elif engine == "offline":
            play_beep_then_voice(key, engine="offline")
        else:
            play_beep_then_voice(key, engine="edge")
        time.sleep(0.5)

    print(f"\n{'=' * 55}")
    print("  测试完成！")
    print("=" * 55)


def generate_sample_config(out_path=None):
    """生成示例配置文件"""
    sample = {
        "default_voice": "zh-CN-YunxiNeural",
        "cache_dir": "~/.sound-notify/cache",
        "language": "zh-CN",
        "events": {
            k: {"voice": v["voice"]}
            for k, v in SOUND_PATTERNS.items()
        }
    }
    path = Path(out_path) if out_path else DEFAULT_CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print(f"[config] 示例配置已写入: {path}")
    return str(path)


# ── CLI ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Sound Notify — 通用声音提醒工具 (跨平台支持)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python notify.py done --edge                任务完成，云希男声
  python notify.py confirm --edge             需要确认
  python notify.py --config my.json done      使用自定义配置
  python notify.py test --edge                测试所有声音
  python notify.py --list-voices              列出所有可用语音
  python notify.py --generate-config          生成示例配置文件
        """
    )
    parser.add_argument("event", nargs="?", choices=list(SOUND_PATTERNS.keys()) + ["test", "list"])
    parser.add_argument("--edge",    "-e",  action="store_true", help="Edge TTS 在线神经网络语音 (推荐)")
    parser.add_argument("--voice",   "-v",  action="store_true", help="离线 TTS 人声")
    parser.add_argument("--system",  "-s",  action="store_true", help="系统电子音")
    parser.add_argument("--rate",    "-r",  type=int, default=0, metavar="SPEED", help="语速 (离线: -10~10, 在线: -50~+50)")
    parser.add_argument("--voice-name",       type=str, default=None, metavar="NAME", help="指定 TTS 语音 ID")
    parser.add_argument("--list-voices",      action="store_true", help="列出所有可用语音")
    parser.add_argument("--no-cache",        action="store_true", help="跳过音频缓存，强制重新生成")
    parser.add_argument("--loop",    "-l",  type=int, default=1, metavar="N")
    parser.add_argument("--interval",        type=float, default=1.0, metavar="SEC")
    parser.add_argument("--json",           action="store_true")
    parser.add_argument("--config",          type=str, default=None, metavar="PATH", help="指定 JSON 配置文件路径")
    parser.add_argument("--generate-config", action="store_true",                     help="生成示例配置文件")
    parser.add_argument("--lang",            type=str, default=None, metavar="LANG", help="语言: zh-CN (默认) / en-US")
    parser.add_argument("--platform-info",    action="store_true",                     help="显示平台信息")

    args = parser.parse_args()

    # 显示平台信息
    if args.platform_info:
        print(f"Platform: {PLATFORM}")
        print(f"IS_WINDOWS: {IS_WINDOWS}")
        print(f"IS_MAC:     {IS_MAC}")
        print(f"IS_LINUX:   {IS_LINUX}")
        return

    # 生成示例配置
    if args.generate_config:
        generate_sample_config(args.config)
        return

    # 列出语音
    if args.list_voices:
        list_voices()
        return

    # 列出模式
    if not args.event or args.event == "list":
        use_voice = args.edge or args.voice
        result = []
        for key, config in SOUND_PATTERNS.items():
            item = {"event": key, "label": config["label"], "description": config["description"]}
            if use_voice:
                item["voice"] = config["voice"]
            result.append(item)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("可用提醒模式:\n")
            for item in result:
                print(f"  {item['event']:<12} {item['label']:<8} {item['description']}")
                if "voice" in item:
                    print(f"          voice: \"{item['voice']}\"")
            print(f"\n默认引擎: Edge TTS ({EDGE_VOICE})")
            print(f"提示: 用 --config 指定自定义配置文件")
        return

    # 测试
    if args.event == "test":
        if args.voice:
            engine = "offline"
        elif args.edge:
            engine = "edge"
        else:
            engine = "beep"
        test_all(engine)
        return

    # ── 加载配置文件 ────────────────────────────────────────
    cfg = load_config(args.config)
    if cfg:
        apply_config(cfg, lang=args.lang)
    elif args.lang:
        apply_config({}, lang=args.lang)

    # 清理缓存
    if args.no_cache:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        print("缓存已清理")

    # 播放
    use_edge    = args.edge
    use_offline = args.voice

    for i in range(args.loop):
        if i > 0:
            time.sleep(args.interval)

        if use_edge:
            ok = play_beep_then_voice(args.event, engine="edge",
                                      voice_name=args.voice_name, rate=args.rate, lang=args.lang)
        elif use_offline:
            ok = play_beep_then_voice(args.event, engine="offline",
                                      voice_name=args.voice_name, rate=args.rate, lang=args.lang)
        elif args.system:
            ok = play_system(args.event)
        else:
            ok = play_pattern(args.event)

        if not ok:
            sys.exit(1)

    if args.json:
        config = SOUND_PATTERNS[args.event]
        result = {"status": "ok", "event": args.event, "label": config["label"], "times": args.loop}
        if use_edge:
            result["voice"]    = config["voice"]
            result["engine"]   = "edge-tts"
            result["voice_id"] = args.voice_name or EDGE_VOICE
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
