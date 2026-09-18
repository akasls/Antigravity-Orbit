import os
import json
from pathlib import Path

import sys
import platform

# Antigravity 核心系统路径 (跨平台动态解析用户家目录)
GEMINI_DIR = Path.home() / ".gemini" / "antigravity"
BRAIN_DIR = GEMINI_DIR / "brain"
DB_PATH = GEMINI_DIR / "conversation_summaries.db"

def get_app_dir() -> Path:
    """获取用户数据与可写配置存储目录 (支持源码运行与 PyInstaller 打包)"""
    if getattr(sys, "frozen", False):
        if platform.system().lower() == "darwin":
            user_dir = Path.home() / ".antigravity-orbit"
            user_dir.mkdir(parents=True, exist_ok=True)
            return user_dir
        else:
            return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

def get_resource_dir() -> Path:
    """获取静态资源根目录 (只读资源如字典、脚本)"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

# 本地数据存储路径
BASE_DIR = get_app_dir()
RESOURCE_DIR = get_resource_dir()
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "watch_state.json"
LOG_FILE = BASE_DIR / "watch_log.txt"

DEFAULT_CONFIG = {
    "enabled": True,
    "scan_interval": 3.0,
    "lock_port": 49222,
    "customization": {
        "language": "zh-CN",            # "zh-CN" (简体), "zh-TW" (繁体), "en" (原版英文)
        "show_quota_badge": True,        # 是否在顶栏显示模型额度胶囊徽章
        "quota_refresh_interval": 60,    # 顶栏模型额度自动刷新间隔 (秒)
        "enable_gpu_acceleration": True, # GPU 硬件栅格化加速与零拷贝
        "disable_background_throttling": True, # 解除后台定时器降频与窗口遮挡冻结
        "expand_v8_memory": True,        # 扩充 V8 垃圾回收堆内存至 4GB
        "disable_telemetry": True,       # 全栈关闭遥测与数据回传
        "hide_ide_buttons": True         # 彻底隐藏右上角多余推广按钮
    },
    "channels": {
        "telegram": {
            "enabled": True,
            "bot_token": "",
            "chat_id": "",
            "proxy": ""  # e.g. "http://127.0.0.1:7890"
        },
        "feishu": {
            "enabled": False,
            "webhook_url": ""
        },
        "wecom": {
            "enabled": False,
            "webhook_url": ""
        }
    }
}

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(user_config)
            # 合并 channels
            if "channels" in user_config:
                for k, v in user_config["channels"].items():
                    if k in merged["channels"]:
                        merged["channels"][k].update(v)
                    else:
                        merged["channels"][k] = v
            # 合并 customization
            if "customization" in user_config:
                merged["customization"] = DEFAULT_CONFIG["customization"].copy()
                merged["customization"].update(user_config["customization"])
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_seen_steps": {}}

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
