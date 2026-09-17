import socket
import sys
from datetime import datetime
from .config import LOG_FILE

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class SingleInstanceLock:
    def __init__(self, port: int = 49222):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def acquire(self) -> bool:
        try:
            self.sock.bind(("127.0.0.1", self.port))
            self.sock.listen(1)
            return True
        except socket.error:
            return False

    def release(self):
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
    
    lines = [
        "🔔【反重力任务已完成】",
        f"📁 工程: {project_name}",
        f"⚡ 状态: {status}",
        f"🕒 时间: {now_str}",
        "",
        "📝 回复摘要:",
        summary
    ]
    return "\n".join(lines)
