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
    "close_to_tray": True,          # 默认点击关闭窗口时最小化到系统托盘
    "app_autostart": False,         # Orbit 客户端开机静默驻留托盘
    "customization": {
        "language": "zh-CN",            # "zh-CN" (简体), "zh-TW" (繁体), "en" (原版英文)
        "show_quota_badge": True,        # 是否在顶栏显示模型额度胶囊徽章
        "quota_refresh_interval": 60,    # 顶栏模型额度自动刷新间隔 (秒)
        "enable_gpu_acceleration": True, # GPU 硬件栅格化加速与零拷贝
        "disable_background_throttling": True, # 解除后台定时器降频与窗口遮挡冻结
        "expand_v8_memory": True,        # 扩充 V8 垃圾回收堆内存至 4GB
        "disable_telemetry": True,       # 全栈关闭遥测与数据回传
        "hide_ide_buttons": True,        # 彻底隐藏右上角多余推广按钮
        "proxy_enabled": False,          # Antigravity 专属网络代理 (彻底取代 Proxifier)
        "proxy_url": "http://127.0.0.1:10808", # 代理地址 (支持 http/socks5)
        "disable_auto_update": True,     # 锁定稳定版本，禁止后台静默更新导致补丁被覆盖
        "enable_smooth_scrolling": True, # 硬件级长文本平滑滚动与 60FPS 渲染
        "compact_ui_mode": False,        # 紧凑代码视野模式 (有效代码显示面积提升 35%~50%)
        "prune_guide_skills": False,     # 裁剪内置说明型 Skills，节省前置 Token 预算
        "auto_retry_on_error": True,          # 任务异常自动重试 (意外出错时自动点击重试继续工作)
        "max_retry_count": 3,                 # 最大自动重试次数 (1~10次，恢复工作后重置计数)
        "notify_on_quota_exhausted": True,    # 额度用尽告警 (发送"任务中断：额度已耗尽")
        "notify_on_max_retry_failed": True    # 重试超限告警 (达到最大重试次数发送"任务失败")
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

def get_config_search_paths() -> list:
    """返回配置文件的候选探测路径列表，按优先级排序"""
    paths = []
    # 1. 应用程序自身目录
    paths.append(get_app_dir() / "config.json")
    # 2. 当前工作目录
    paths.append(Path.cwd() / "config.json")
    # 3. 源码工程或打包上一级工程目录
    if getattr(sys, "frozen", False):
        exe_parent = Path(sys.executable).resolve().parent
        paths.append(exe_parent / "config.json")
        paths.append(exe_parent.parent / "config.json")
    else:
        paths.append(Path(__file__).resolve().parent.parent / "config.json")
    # 4. 用户家目录 ~/.antigravity-orbit/config.json
    paths.append(Path.home() / ".antigravity-orbit" / "config.json")

    unique = []
    for p in paths:
        if p not in unique:
            unique.append(p)
    return unique


def find_active_config_file() -> Path:
    """寻找实际存在且有有效自定义内容的配置文件，若无则返回默认存储路径"""
    # 优先找存在且包含自定义配置内容的文件
    for p in get_config_search_paths():
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8").strip()
                if content and content != "{}":
                    data = json.loads(content)
                    if data.get("channels") or data.get("customization"):
                        return p
            except Exception:
                pass

    # 其次寻找任意存在的 config.json
    for p in get_config_search_paths():
        if p.exists() and p.is_file():
            return p

    return get_app_dir() / "config.json"


def load_config() -> dict:
    active_file = find_active_config_file()
    if not active_file.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(active_file, "r", encoding="utf-8") as f:
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
    # 自动保障 proxy_url 格式完整
    custom = cfg.get("customization", {})
    if custom.get("proxy_host") and custom.get("proxy_port"):
        p_type = (custom.get("proxy_type") or "http").lower()
        p_host = custom.get("proxy_host")
        p_port = custom.get("proxy_port")
        custom["proxy_url"] = f"{p_type}://{p_host}:{p_port}"

    active_file = find_active_config_file()
    active_file.parent.mkdir(parents=True, exist_ok=True)
    with open(active_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    # 镜像同步到全局家目录，防止换路径丢失凭据
    try:
        global_file = Path.home() / ".antigravity-orbit" / "config.json"
        global_file.parent.mkdir(parents=True, exist_ok=True)
        with open(global_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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
