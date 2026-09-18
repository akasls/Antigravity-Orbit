"""
Antigravity Orbit - 现代桌面客户端管理中心 (Native Edge WebView2 Desktop Client)
基于微软原生 Edge WebView2 与现代化 Fluent / macOS 设计系统
实现极致现代化界面质感、零卡顿 60FPS 响应速度与 0.15s 秒级冷启动
"""

import os
import sys
import time
import platform
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import webview
from core.config import (
    RESOURCE_DIR,
    BASE_DIR,
    load_config,
)
from core.api_bridge import OrbitApi


class OrbitWindowManager:
    """管理 WebView2 视窗与系统托盘常驻生命周期"""

    def __init__(self, start_in_tray: bool = False):
        self.start_in_tray = start_in_tray
        self.window = None
        self.tray_icon = None
        self.is_force_quitting = False
        self.api = OrbitApi(window_holder=self)

    def get_web_entry_path(self) -> Path:
        """解析本地前端 HTML 入口路径 (兼容源码开发与 PyInstaller 打包)"""
        candidates = [
            RESOURCE_DIR / "core" / "web" / "index.html",
            BASE_DIR / "core" / "web" / "index.html",
            PROJECT_ROOT / "core" / "web" / "index.html",
        ]
        for p in candidates:
            if p.exists():
                return p.resolve()
        return candidates[0]

    def init_tray(self):
        """初始化系统托盘后台守护"""
        try:
            import pystray
            from PIL import Image

            icon_path = RESOURCE_DIR / "resources" / "icon_32.png"
            if not icon_path.exists():
                icon_path = RESOURCE_DIR / "resources" / "icon.ico"

            img = Image.open(str(icon_path))
            menu = pystray.Menu(
                pystray.MenuItem("🖥️ 打开管理中心", self.show_window, default=True),
                pystray.MenuItem("🚀 重启 Antigravity", lambda icon, item: self.api.restart_antigravity()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("🚪 彻底退出", self.force_quit)
            )
            self.tray_icon = pystray.Icon("Antigravity Orbit", img, "Antigravity Orbit", menu)
            self.tray_icon.run_detached()
        except Exception as e:
            print(f"[Tray Warning] 托盘初始化失败: {e}")
            self.tray_icon = None

    def show_window(self, icon=None, item=None):
        """从托盘恢复显示窗口"""
        if self.window:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass

    def on_closing(self):
        """拦截窗口关闭按钮"""
        if self.is_force_quitting:
            return True

        cfg = load_config()
        close_to_tray = cfg.get("close_to_tray", True)
        if close_to_tray and self.tray_icon:
            if self.window:
                try:
                    self.window.hide()
                except Exception:
                    pass
            return False  # 返回 False 阻断窗口销毁，仅隐藏驻留托盘

        # 若未开启托盘常驻，则彻底退出
        self.force_quit()
        return True

    def force_quit(self, icon=None, item=None):
        """彻底终止进程并退出应用"""
        self.is_force_quitting = True
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        # 兜底强制终止当前进程
        threading.Timer(0.3, lambda: os._exit(0)).start()

    def run(self):
        """启动应用与 WebView2 视窗"""
        html_path = self.get_web_entry_path()
        icon_ico = RESOURCE_DIR / "resources" / "icon.ico"

        # 1. 异步非阻塞启动系统托盘，优先瞬间创建并呈现主视窗
        threading.Thread(target=self.init_tray, daemon=True).start()

        # 2. 创建现代 Edge WebView2 窗口
        self.window = webview.create_window(
            title="Antigravity Orbit",
            url=str(html_path),
            js_api=self.api,
            width=980,
            height=740,
            min_size=(880, 640),
            hidden=self.start_in_tray,
            background_color="#f8fafc",
            easy_drag=True,
            text_select=True,
        )

        # 3. 挂载关闭拦截事件
        self.window.events.closing += self.on_closing

        # 4. 启动主循环 (Windows 默认自动采用极速 Edge WebView2 内核)
        start_kwargs = {
            "private_mode": False,
        }
        if icon_ico.exists():
            start_kwargs["icon"] = str(icon_ico)

        webview.start(**start_kwargs)


def launch_gui(start_in_tray: bool = False):
    """桌面可视化管理中心统一启动入口"""
    app = OrbitWindowManager(start_in_tray=start_in_tray)
    app.run()


if __name__ == "__main__":
    launch_gui()
