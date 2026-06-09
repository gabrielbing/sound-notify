#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sound Notify — 通用声音提醒工具 (离线/在线双引擎)
支持通过 JSON 配置文件自定义播报文案、语音、缓存目录。
用法:
    python notify.py done --edge
    python notify.py --config my-config.json done --edge

配置文件 (sound-notify.json / config.json):
{
  "default_voice": "zh-CN-YunxiNeural",
  "cache_dir": "~/.sound-notify/cache",
  "events": {
    "done":    { "voice": "搞定了，任务已完成。" },
    "confirm":  { "voice": "需要你确认一下。" },
    "perm":     { "voice": "需要你的授权才能继续。" },
    "alert":    { "voice": "请注意，一条重要的提醒。" },
    "daily":    { "voice": "这是您的每日推送。" },
    "thinking": { "voice": "正在处理中，请稍候。" }
  }
}
"""

import sys
import time
import winsound
import argparse
import json
import subprocess
import ctypes
import os
import tempfile
import hashlib
from pathlib import Path

# ── 多语言文案包 ──────────────────────────────────────
# 通过 --lang 切换，或通过 config.json 的 "language" 字段设置
LANG_PACK = {
    "zh-CN": {
        "done":     "搞定了，任务已完成。",
        "confirm":   "需要你确认一下。",
        "perm":      "需要你的授权才能继续。",
        "alert":     "请注意，一条重要的提醒。",
        "daily":     "今日推送已就绪，来看看吧。",
        "thinking":  "正在处理中，请稍候。",
    },
    "en-US": {
        "done":     "Done! Task completed.",
        "confirm":   "Please confirm to proceed.",
        "perm":      "Permission required to continue.",
        "alert":     "Alert! Please check this out.",
        "daily":     "Your daily update is ready.",
        "thinking":  "Still processing, please wait.",
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
        "label": "任务完成",
        "description": "愉悦的上升旋律",
        "voice": "搞定了，任务已完成。",
        "notes": [(523, 150), (659, 150), (784, 150), (1047, 400)],
        "pauses": [80, 80, 80],
    },
    "daily": {
        "label": "每日推送",
        "description": "晨间风格的温暖旋律",
        "voice": "今日推送已就绪，来看看吧。",
        "notes": [(523, 200), (659, 200), (784, 200), (659, 200), (784, 300)],
        "pauses": [100, 100, 100, 100],
    },
    "confirm": {
        "label": "待确认",
        "description": "温和的双音提示",
        "voice": "需要你确认一下。",
        "notes": [(659, 200), (784, 300)],
        "pauses": [150],
    },
    "perm": {
        "label": "权限请求",
        "description": "三段式提醒",
        "voice": "需要你的授权才能继续。",
        "notes": [(784, 120), (784, 120), (988, 300)],
        "pauses": [80, 80],
    },
    "alert": {
        "label": "紧急提醒",
        "description": "急促的警告音",
        "voice": "注意，有紧急提醒！",
        "notes": [(880, 100), (880, 100), (880, 100), (1047, 400)],
        "pauses": [60, 60, 60],
    },
    "thinking": {
        "label": "思考中",
        "description": "轻柔提示",
        "voice": "正在处理中，请稍候。",
        "notes": [(440, 100), (523, 100)],
        "pauses": [300],
    },
}

SYSTEM_SOUNDS = {
    "done_sys":    winsound.MB_ICONASTERISK,
    "confirm_sys": winsound.MB_ICONEXCLAMATION,
    "perm_sys":    winsound.MB_ICONHAND,
}

# ── Edge TTS 语音配置 ─────────────────────────────────────
EDGE_VOICE       = "zh-CN-YunxiNeural"         # 默认：云希，温柔阳光
EDGE_VOICE_FALLBACK = "zh-CN-YunyangNeural"    # 备选：云扬

# 音频缓存目录（可通过配置文件覆盖）
CACHE_DIR = Path.home() / ".sound-notify" / "cache"

# edge-tts 可执行文件路径
_EDGE_TTS_EXE = None

# 配置文件搜索路径（按优先级）
DEFAULT_CONFIG_DIR  = Path.home() / ".sound-notify"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


def load_config(config_path=None):
    """
    加载 JSON 配置文件，覆盖 SOUND_PATTERNS / EDGE_VOICE / CACHE_DIR。
    搜索顺序：
      1. --config 命令行参数指定的路径
      2. 脚本所在目录的 sound-notify.json
      3. ~/.sound-notify/config.json
    返回加载到的配置 dict（未找到返回 {}）
    """
    candidates = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    # 脚本所在目录（scripts/ 的上级）
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

    # 0. 设置语言
    if lang:
        DEFAULT_LANG = lang
    elif "language" in cfg:
        DEFAULT_LANG = cfg["language"]

    # 1. 覆盖各事件的播报文案（按当前语言）
    events = cfg.get("events", {})
    for key, val in events.items():
        if key in SOUND_PATTERNS and isinstance(val, dict) and "voice" in val:
            SOUND_PATTERNS[key]["voice"] = val["voice"]
        # 也更新语言包（如果有指定语言）
        lang_key = DEFAULT_LANG
        if lang_key in LANG_PACK and key in LANG_PACK[lang_key]:
            LANG_PACK[lang_key][key] = val["voice"]

    # 2. 覆盖默认语音
    if "default_voice" in cfg:
        EDGE_VOICE = cfg["default_voice"]

    # 3. 覆盖缓存目录
    if "cache_dir" in cfg:
        CACHE_DIR = Path(cfg["cache_dir"]).expanduser()


def _get_edge_tts():
    """查找 edge-tts 可执行文件"""
    global _EDGE_TTS_EXE
    if _EDGE_TTS_EXE:
        return _EDGE_TTS_EXE

    candidates = [
        Path.home() / ".workbuddy" / "binaries" / "python" / "versions" / "3.13.12" / "Scripts" / "edge-tts.exe",
    ]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d) / "edge-tts.exe"
        if p.exists():
            candidates.append(p)

    for p in candidates:
        if p.exists():
            _EDGE_TTS_EXE = str(p)
            return _EDGE_TTS_EXE
    return None


# ── 音频播放 (ctypes MCI, 零依赖) ──────────────────────────
def _play_mp3_mci(filepath):
    """用 Windows MCI 播放 MP3，不弹窗、不阻塞"""
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


# ── 电子音 ────────────────────────────────────────────────
def play_pattern(pattern_key):
    config = SOUND_PATTERNS.get(pattern_key)
    if not config:
        return False
    notes   = config["notes"]
    pauses  = config.get("pauses", [])
    for i, (freq, dur) in enumerate(notes):
        try:
            winsound.Beep(freq, dur)
        except Exception:
            winsound.MessageBeep(winsound.MB_OK)
            return True
        if i < len(pauses):
            time.sleep(pauses[i] / 1000.0)
    return True


def play_system(pattern_key):
    sys_key = f"{pattern_key}_sys"
    st = SYSTEM_SOUNDS.get(sys_key)
    if st:
        winsound.MessageBeep(st)
        return True
    return False


# ── 离线 TTS (Windows SAPI) ───────────────────────────────
def _speak_sapi(text, voice_name=None, rate=0):
    """Windows 内置 TTS"""
    safe = text.replace('"', "'").replace("$", " ").replace("`", "'")
    vs   = f'$s.SelectVoice("{voice_name}")' if voice_name else ""
    ps    = f'''
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
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return True
    except Exception:
        return False


# ── 在线 TTS (Edge TTS) ──────────────────────────────────
def _speak_edge(text, voice=None, rate="+0%"):
    """Microsoft Edge TTS — 神经网络语音"""
    exe = _get_edge_tts()
    if not exe:
        return False

    voice = voice or EDGE_VOICE

    # 缓存 key: voice + text 的 hash
    cache_key  = hashlib.md5(f"{voice}:{text}:{rate}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.mp3"

    if cache_file.exists():
        return _play_mp3_mci(str(cache_file))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_DIR / f"_tmp_{cache_key}.mp3"

    try:
        result = subprocess.run(
            [exe, "--voice", voice, "--rate", rate,
             "--text", text, "--write-media", str(tmp)],
            capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode != 0:
            if voice == EDGE_VOICE and EDGE_VOICE_FALLBACK:
                return _speak_edge(text, voice=EDGE_VOICE_FALLBACK, rate=rate)
            return False

        if tmp.exists() and tmp.stat().st_size > 0:
            tmp.rename(cache_file)
            return _play_mp3_mci(str(cache_file))
        return False

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


# ── 综合播放 ──────────────────────────────────────────────
def play_voice(pattern_key, engine="edge", voice_name=None, rate=0, lang=None):
    """播放人声（支持多语言）"""
    config = SOUND_PATTERNS.get(pattern_key)
    if not config:
        return False
    # 优先使用多语言文案，其次使用 config 中的 voice 字段
    text = get_voice_text(pattern_key, lang=lang)
    if text == pattern_key:  # 没找到，降级用 config 里的
        text = config.get("voice", config["label"])

    if engine == "edge":
        rate_str = f"{rate:+d}%" if isinstance(rate, int) else rate
        return _speak_edge(text, voice=voice_name, rate=rate_str)

    voice = voice_name or _detect_sapi_voice()
    return _speak_sapi(text, voice_name=voice, rate=rate)


def play_beep_then_voice(pattern_key, engine="edge", voice_name=None, rate=0, lang=None):
    """播放人声（无提示音，支持多语言）"""
    return play_voice(pattern_key, engine=engine, voice_name=voice_name, rate=rate, lang=lang)


# ── 辅助功能 ──────────────────────────────────────────────
def _detect_sapi_voice():
    """检测可用的中文 SAPI 语音"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Add-Type -AssemblyName System.Speech; "
             "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
             "$s.GetInstalledVoices() | % { $_.VoiceInfo.Name }"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.strip().split("\n"):
            name = line.strip()
            if name and ("chinese" in name.lower() or "huihui" in name.lower()):
                return name
    except Exception:
        pass
    return None


def list_edge_voices():
    """列出 Edge TTS 中文语音"""
    voices = [
        ("zh-CN-YunxiNeural",    "云希 ★",   "Male, Lively, Sunshine — 温柔阳光男声"),
        ("zh-CN-YunyangNeural",  "云扬",      "Male, Professional — 专业可靠男声"),
        ("zh-CN-YunjianNeural",  "云健",      "Male, Passion — 激情活力男声"),
        ("zh-CN-YunxiaNeural",   "云夏",      "Male, Cute — 可爱少年音"),
        ("zh-CN-XiaoxiaoNeural", "晓晓",      "Female, Gentle — 温暖知性女声"),
        ("zh-CN-XiaoyiNeural",   "晓伊",      "Female, Lively — 活泼生动女声"),
        ("zh-CN-XiaohanNeural",  "晓涵",      "Female, Soft — 温柔文静女声"),
        ("zh-CN-XiaomoNeural",   "晓墨",      "Female, Mature — 知性成熟女声"),
    ]
    print("\n可用语音 (Edge TTS):\n")
    for vid, name, desc in voices:
        mark = " ← 默认" if vid == EDGE_VOICE else ""
        print(f"  {vid:<32} {name:<8} {desc}{mark}")
    print()


def list_sapi_voices():
    """列出 SAPI 离线语音"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Add-Type -AssemblyName System.Speech; "
             "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
             "$s.GetInstalledVoices() | % { "
             "'{0}|{1}|{2}' -f $_.VoiceInfo.Name, $_.VoiceInfo.Culture, $_.VoiceInfo.Gender }"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print("\nSAPI 离线语音:\n")
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 3:
                print(f"  {parts[0]:<35} {parts[1]:<12} {parts[2]}")
    except Exception:
        print("无法获取离线语音列表")


def test_all(engine="edge"):
    """测试所有模式"""
    mode = {"edge": "Edge TTS (在线神经网络)", "sapi": "SAPI (离线)", "beep": "电子音"}.get(engine, engine)
    print("=" * 55)
    print(f"  Sound Notify — 全模式测试")
    print(f"  引擎: {mode}")
    print("=" * 55)

    for key, config in SOUND_PATTERNS.items():
        print(f"\n>>> {config['label']} ({key})")
        print(f"    播报: {config['voice']}")
        if engine == "beep":
            play_pattern(key)
        else:
            play_beep_then_voice(key, engine=engine)
        time.sleep(0.5)

    print(f"\n{'=' * 55}")
    print("  测试完成！")
    print("=" * 55)


def generate_sample_config(out_path=None):
    """生成示例配置文件"""
    sample = {
        "default_voice": "zh-CN-YunxiNeural",
        "cache_dir": "~/.sound-notify/cache",
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


# ── CLI ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Sound Notify — 通用声音提醒工具 (离线/在线双引擎)",
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
    parser.add_argument("--voice",   "-v",  action="store_true", help="离线 SAPI TTS 人声")
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

    args = parser.parse_args()

    # 生成示例配置
    if args.generate_config:
        generate_sample_config(args.config)
        return

    # 列出语音
    if args.list_voices:
        list_edge_voices()
        list_sapi_voices()
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
        engine = "edge" if args.edge else ("sapi" if (args.voice) else "beep")
        test_all(engine)
        return

    # ── 加载配置文件 ────────────────────────────────────────
    cfg = load_config(args.config)
    if cfg:
        apply_config(cfg, lang=args.lang)
    elif args.lang:
        # 没有配置文件，但有 --lang 参数
        apply_config({}, lang=args.lang)

    # 清理缓存
    if args.no_cache:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        print("缓存已清理")

    # 播放
    use_edge = args.edge
    use_sapi = args.voice

    for i in range(args.loop):
        if i > 0:
            time.sleep(args.interval)

        if use_edge:
            ok = play_beep_then_voice(args.event, engine="edge", voice_name=args.voice_name, rate=args.rate, lang=args.lang)
        elif use_sapi:
            ok = play_beep_then_voice(args.event, engine="sapi", voice_name=args.voice_name, rate=args.rate, lang=args.lang)
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
            result["voice"]     = config["voice"]
            result["engine"]    = "edge-tts"
            result["voice_id"] = args.voice_name or EDGE_VOICE
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
