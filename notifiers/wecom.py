import json
import urllib.request
from .base import BaseNotifier
from core.utils import Logger, format_notification

class WeComNotifier(BaseNotifier):
    def __init__(self, config: dict):
        super().__init__("wecom", config)
        self.webhook_url = config.get("webhook_url", "").strip()

    def _send_payload(self, text: str) -> tuple[bool, str]:
        if not self.webhook_url:
            return False, "企业微信配置不完整：缺少 webhook_url"

        url = self.webhook_url
        body = json.dumps({
            "msgtype": "text",
            "text": {
                "content": text
            }
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("errcode") == 0:
                    return True, "企业微信消息发送成功"
                return False, f"企业微信返回错误: {data.get('errmsg')}"
        except Exception as e:
            return False, f"企业微信网络请求失败: {e}"

    def send(self, project_name: str, status: str, summary: str) -> bool:
        text = format_notification(project_name, status, summary)
        ok, msg = self._send_payload(text)
        if ok:
            Logger.log(f"[{self.name}] 通知发送成功")
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
