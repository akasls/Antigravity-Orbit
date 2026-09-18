import os
import socket
import sys
import json
import threading
import http.server
from datetime import datetime
from .config import LOG_FILE

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class SingleInstanceLock:
    def __init__(self, port: int = 49222, notify_callback=None):
        self.port = port
        self.notify_callback = notify_callback
        self.sock = None
        self.httpd = None
        self.server_thread = None

    def acquire(self) -> bool:
        if self.notify_callback:
            try:
                callback = self.notify_callback
                class _NotifyHandler(http.server.BaseHTTPRequestHandler):
                    def do_OPTIONS(self):
                        self.send_response(204)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-codeium-csrf-token")
                        self.end_headers()

                    def do_GET(self):
                        if self.path == "/ping":
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "ok", "pid": os.getpid()}).encode("utf-8"))
                        else:
                            self.send_response(404)
                            self.end_headers()

                    def do_POST(self):
                        if self.path == "/notify":
                            try:
                                length = int(self.headers.get("Content-Length", 0))
                                body = self.rfile.read(length).decode("utf-8")
                                data = json.loads(body)
                                proj = data.get("project_name", "默认工程")
                                status = data.get("status", "正常完成")
                                summary = data.get("summary", "")
                                callback(proj, status, summary)

                                self.send_response(200)
                                self.send_header("Content-Type", "application/json")
                                self.send_header("Access-Control-Allow-Origin", "*")
                                self.end_headers()
                                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
                            except Exception as err:
                                self.send_response(500)
                                self.send_header("Access-Control-Allow-Origin", "*")
                                self.end_headers()
                                self.wfile.write(str(err).encode("utf-8"))
                        else:
                            self.send_response(404)
                            self.end_headers()

                    def log_message(self, format, *args):
                        pass

                self.httpd = http.server.HTTPServer(("127.0.0.1", self.port), _NotifyHandler)
                self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                self.server_thread.start()
                return True
            except Exception:
                return False
        else:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind(("127.0.0.1", self.port))
                self.sock.listen(1)
                return True
            except socket.error:
                return False

    def release(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

class Logger:
    @staticmethod
    def log(msg: str, echo: bool = True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        if echo:
            print(formatted)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

def format_notification(project_name: str, status: str, summary: str) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(summary) > 800:
        summary = summary[:800] + "\n\n... (回复内容较长，已自动截断)"
    
    # 动态匹配标题图标与状态
    if "额度" in status or "耗尽" in status:
        icon = "⚠️"
        title = "【反重力任务中断：额度已耗尽】"
    elif "失败" in status or "超限" in status or "异常" in status:
        icon = "❌"
        title = "【反重力任务执行失败】"
    elif "重试" in status:
        icon = "🔄"
        title = "【反重力任务自动重试中】"
    else:
        icon = "🔔"
        title = "【反重力任务已完成】"

    lines = [
        f"{icon}{title}",
        f"📁 工程: {project_name}",
        f"⚡ 状态: {status}",
        f"🕒 时间: {now_str}",
        "",
        "📝 回复摘要 / 详情:",
        summary
    ]
    return "\n".join(lines)
