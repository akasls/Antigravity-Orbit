from .base import BaseNotifier
from .telegram import TelegramNotifier
from .feishu import FeishuNotifier
from .wecom import WeComNotifier

def get_active_notifiers(config: dict) -> list[BaseNotifier]:
    active = []
    channels = config.get("channels", {})
    
    tg_cfg = channels.get("telegram", {})
    if tg_cfg.get("enabled"):
        active.append(TelegramNotifier(tg_cfg))

    fs_cfg = channels.get("feishu", {})
    if fs_cfg.get("enabled"):
        active.append(FeishuNotifier(fs_cfg))

    wc_cfg = channels.get("wecom", {})
    if wc_cfg.get("enabled"):
        active.append(WeComNotifier(wc_cfg))

    return active
