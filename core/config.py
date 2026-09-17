import os
import json
from pathlib import Path

# Antigravity 核心系统路径 (跨平台动态解析用户家目录)
GEMINI_DIR = Path.home() / ".gemini" / "antigravity"
BRAIN_DIR = GEMINI_DIR / "brain"
DB_PATH = GEMINI_DIR / "conversation_summaries.db"

# 本地数据存储路径
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "watch_state.json"
LOG_FILE = BASE_DIR / "watch_log.txt"

DEFAULT_CONFIG = {
    "enabled": True,
    "scan_interval": 3.0,
    "lock_port": 49222,
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
            # channels 也要合并
            if "channels" in user_config:
                for k, v in user_config["channels"].items():
                    if k in merged["channels"]:
                        merged["channels"][k].update(v)
                    else:
                        merged["channels"][k] = v
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
