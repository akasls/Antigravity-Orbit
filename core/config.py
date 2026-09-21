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
        elif platform.system().lower() == "windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                user_dir = Path(appdata) / "Antigravity-Orbit"
            else:
                user_dir = Path.home() / ".antigravity-orbit"
        else:
            user_dir = Path.home() / ".antigravity-orbit"

        user_dir.mkdir(parents=True, exist_ok=True)

        # 首次从旧版安装目录或当前目录自动平滑迁移已有配置文件与状态
        target_cfg = user_dir / "config.json"
        if not target_cfg.exists():
            legacy_candidates = [
                Path(sys.executable).resolve().parent / "config.json",
                Path.cwd() / "config.json",
                Path.home() / ".antigravity-orbit" / "config.json",
            ]
            for cand in legacy_candidates:
                if cand.exists() and cand != target_cfg:
                    try:
                        import shutil
                        shutil.copy2(cand, target_cfg)
                        break
                    except Exception:
                        pass
        return user_dir
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
    "close_to_tray": False,          # 默认点击关闭窗口时彻底退出，由用户自主开启托盘常驻
    "app_autostart": False,         # Orbit 客户端开机静默驻留托盘
    "customization": {
        "language": "zh-CN",            # "zh-CN" (简体), "zh-TW" (繁体), "en" (原版英文)
        "show_quota_badge": False,       # 是否在顶栏显示模型额度胶囊徽章
        "quota_refresh_interval": 60,    # 顶栏模型额度自动刷新间隔 (秒，保持兼容)
        "quota_refresh_active_interval": 60,    # 使用中活跃账号额度刷新间隔 (秒，默认 1 分钟)
        "quota_refresh_idle_interval": 900,     # 未使用闲置账号刷新间隔 (秒，默认 15 分钟)
        "enable_gpu_acceleration": False,# GPU 硬件栅格化加速与零拷贝
        "disable_background_throttling": False, # 解除后台定时器降频与窗口遮挡冻结
        "expand_v8_memory": False,       # 扩充 V8 垃圾回收堆内存至 4GB/8GB
        "disable_telemetry": False,      # 全栈关闭遥测与数据回传
        "hide_ide_buttons": False,       # 彻底隐藏右上角多余推广按钮
        "clean_ui": False,              # 净化界面多余横幅
        "opt_gpu": False,
        "opt_max_heap": False,
        "opt_nosleep": False,
        "opt_telemetry": False,
        "proxy_enabled": False,         # Antigravity 专属网络代理 (彻底取代 Proxifier)
        "proxy_host": "127.0.0.1",
        "proxy_port": 10808,
        "proxy_type": "socks5",
        "proxy_url": "",                # 代理地址 (支持 http/socks5)
        "proxy_bypass": "<local>;localhost;127.0.0.1;::1;127.0.0.0/8;*.local",
        "disable_auto_update": False,    # 锁定稳定版本，禁止后台静默更新导致补丁被覆盖
        "enable_smooth_scrolling": False,# 硬件级长文本平滑滚动与 60FPS 渲染
        "compact_ui_mode": False,       # 紧凑代码视野模式 (有效代码显示面积提升 35%~50%)
        "prune_guide_skills": False,    # 裁剪内置说明型 Skills，节省前置 Token 预算
        "auto_retry_on_error": False,        # 任务异常自动重试 (意外出错时自动点击重试继续工作)
        "notify_on_quota_exhausted": False,  # 额度用尽告警 (发送"任务中断：额度已耗尽")
        "notify_on_max_retry_failed": False, # 重试超限告警 (达到最大重试次数发送"任务失败")
        "start_maximized": False             # 启动时自动最大化反重力客户端窗口
    },
    "channels": {
        "telegram": {
            "enabled": False,
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
    # 1. 应用程序自身目录及 dist 目录
    app_dir = get_app_dir()
    paths.append(app_dir / "config.json")
    paths.append(app_dir / "dist" / "config.json")

    # 2. 当前工作目录
    paths.append(Path.cwd() / "config.json")
    paths.append(Path.cwd() / "dist" / "config.json")

    # 3. 源码工程或打包上一级工程目录
    if getattr(sys, "frozen", False):
        exe_parent = Path(sys.executable).resolve().parent
        paths.append(exe_parent / "config.json")
        paths.append(exe_parent.parent / "config.json")
    else:
        root_dir = Path(__file__).resolve().parent.parent
        paths.append(root_dir / "config.json")
        paths.append(root_dir / "dist" / "config.json")

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


def is_placeholder(val: any) -> bool:
    if not val:
        return True
    s = str(val).strip()
    return s in ("", "YOUR_TELEGRAM_BOT_TOKEN", "YOUR_CHAT_ID", "xxxxxxxx")


def load_config() -> dict:
    active_file = find_active_config_file()
    merged = DEFAULT_CONFIG.copy()
    user_config = {}

    if active_file.exists():
        try:
            with open(active_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
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
                    if "quota_refresh_active_interval" not in user_config["customization"]:
                        merged["customization"]["quota_refresh_active_interval"] = user_config["customization"].get("quota_refresh_interval", 60)
                    if "quota_refresh_idle_interval" not in user_config["customization"]:
                        merged["customization"]["quota_refresh_idle_interval"] = 900
        except Exception:
            merged = DEFAULT_CONFIG.copy()

    # 自动探测与迁移：如果当前生效配置中缺少有效的 Telegram 或其它推送凭据，自动从历史候选路径中合并提取
    migrated = False
    current_tg = merged.get("channels", {}).get("telegram", {})
    tg_bot = current_tg.get("bot_token", "")
    tg_chat = current_tg.get("chat_id", "")
    if is_placeholder(tg_bot) or is_placeholder(tg_chat):
        for cand_path in get_config_search_paths():
            if cand_path != active_file and cand_path.exists() and cand_path.is_file():
                try:
                    c_data = json.loads(cand_path.read_text(encoding="utf-8"))
                    c_channels = c_data.get("channels", {})
                    c_tg = c_channels.get("telegram", {})
                    c_bot = str(c_tg.get("bot_token", "")).strip()
                    c_chat = str(c_tg.get("chat_id", "")).strip()
                    if not is_placeholder(c_bot) and not is_placeholder(c_chat):
                        if "channels" not in merged:
                            merged["channels"] = {}
                        if "telegram" not in merged["channels"]:
                            merged["channels"]["telegram"] = DEFAULT_CONFIG["channels"]["telegram"].copy()
                        merged["channels"]["telegram"].update(c_tg)
                        migrated = True
                        break
                except Exception:
                    pass

    # 清除任何残留的占位符文本，避免在界面上显示 YOUR_TELEGRAM_BOT_TOKEN 等
    tg_conf = merged.get("channels", {}).get("telegram", {})
    if is_placeholder(tg_conf.get("bot_token")):
        tg_conf["bot_token"] = ""
    if is_placeholder(tg_conf.get("chat_id")):
        tg_conf["chat_id"] = ""

    # 规范化 Telegram 代理：若仅填写了端口如 "10808"，自动转为 "http://127.0.0.1:10808"
    tg_proxy = str(tg_conf.get("proxy", "")).strip()
    if tg_proxy and tg_proxy.isdigit():
        tg_conf["proxy"] = f"http://127.0.0.1:{tg_proxy}"
        migrated = True

    # 若发生了自动继承或规范化，写回生效文件以长久保持
    if migrated:
        try:
            save_config(merged)
        except Exception:
            pass

    return merged


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
