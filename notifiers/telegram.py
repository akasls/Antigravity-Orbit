import os
import json
import urllib.request
import urllib.error
from .base import BaseNotifier
from core.utils import Logger, format_notification

class TelegramNotifier(BaseNotifier):
    def __init__(self, config=None, chat_id: str = "", proxy: str = ""):
        if isinstance(config, dict):
            super().__init__("telegram", config)
            self.bot_token = config.get("bot_token", "").strip()
            self.chat_id = config.get("chat_id", "").strip()
            self.proxy = config.get("proxy", "").strip()
        else:
            cfg = {"bot_token": str(config or "").strip(), "chat_id": str(chat_id or "").strip(), "proxy": str(proxy or "").strip()}
            super().__init__("telegram", cfg)
            self.bot_token = cfg["bot_token"]
            self.chat_id = cfg["chat_id"]
            self.proxy = cfg["proxy"]

    def _get_proxies(self) -> list[str]:
        proxies = []
        if self.proxy:
            proxies.append(self.proxy)
        # 尝试环境常用代理
        for env_key in ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"]:
            val = os.environ.get(env_key)
            if val and val not in proxies:
                proxies.append(val)
        return proxies

    def _send_payload(self, text: str) -> tuple[bool, str]:
        if not self.bot_token or not self.chat_id:
            return False, "Telegram 配置不完整：缺少 bot_token 或 chat_id"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        body = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True
        }).encode("utf-8")

        headers = {"Content-Type": "application/json; charset=utf-8"}
        req = urllib.request.Request(url, data=body, headers=headers)

        last_error = ""

        # 1. 尝试直连
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return True, "直连发送成功"
        except Exception as e:
            last_error = f"直连失败: {e}"

        # 2. 尝试代理
        for proxy_url in self._get_proxies():
            try:
                handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                opener = urllib.request.build_opener(handler)
                with opener.open(req, timeout=10) as resp:
                    if resp.status == 200:
                        return True, f"通过代理 ({proxy_url}) 发送成功"
            except Exception as e:
                last_error = f"代理 ({proxy_url}) 发送失败: {e}"

        return False, last_error or "未知网络连接错误"

    def send(self, project_name: str, status: str, summary: str) -> bool:
        text = format_notification(project_name, status, summary)
        ok, msg = self._send_payload(text)
        if ok:
            Logger.log(f"[{self.name}] 通知发送成功: {msg}")
        else:
            Logger.log(f"[{self.name}] 通知发送失败: {msg}")
        return ok

    def test(self) -> tuple[bool, str]:
        test_text = (
            "🎉【Antigravity Notifier】配置测试成功！\n"
            "--------------------------------\n"
            "当你使用反重力执行完任何任务或长跑测试时，任务完成通知将自动在此处提醒你。"
        )
        return self._send_payload(test_text)
