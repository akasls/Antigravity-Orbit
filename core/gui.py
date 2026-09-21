"""
Antigravity Orbit - 现代桌面客户端管理中心 (Native Edge WebView2 Desktop Client)
基于微软原生 Edge WebView2 与现代化 Fluent / macOS 设计系统
实现极致现代化界面质感、零卡顿 60FPS 响应速度与秒级冷启动
"""

import os
import sys
import time
import platform
import threading
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 提前注册 Windows 任务栏应用专属 ID，避免归类为通用 python 或空白应用
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AntigravityTeam.AntigravityOrbit.Desktop.App")
    except Exception:
        pass

import webview
from core.config import (
    RESOURCE_DIR,
    BASE_DIR,
    load_config,
)
from core.api_bridge import OrbitApi
from core.monitor import AntigravityMonitor
from core.localization import LocalizationManager


class OrbitWindowManager:
    """管理 WebView2 视窗与系统托盘常驻生命周期"""

    def __init__(self, start_in_tray: bool = False):
        self.start_in_tray = start_in_tray
        self.window = None
        self.tray_icon = None
        self.is_force_quitting = False
        self.api = OrbitApi(window_holder=self)
        self.monitor = AntigravityMonitor()
        self.monitor_thread = None

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

    def get_icon_path(self) -> Optional[Path]:
        """全路径候选搜索应用图标 (支持打包与源码模式)"""
        candidates = [
            RESOURCE_DIR / "resources" / "icon.ico",
            BASE_DIR / "resources" / "icon.ico",
            BASE_DIR / "_internal" / "resources" / "icon.ico",
            PROJECT_ROOT / "resources" / "icon.ico",
            Path(sys.executable).parent / "resources" / "icon.ico",
            Path(sys.executable).parent / "_internal" / "resources" / "icon.ico",
        ]
        for p in candidates:
            if p.exists():
                return p.resolve()
        return None

    def get_tray_icon_path(self) -> Optional[Path]:
        """获取托盘图标路径"""
        candidates = [
            RESOURCE_DIR / "resources" / "icon_32.png",
            BASE_DIR / "resources" / "icon_32.png",
            BASE_DIR / "_internal" / "resources" / "icon_32.png",
            PROJECT_ROOT / "resources" / "icon_32.png",
            RESOURCE_DIR / "resources" / "icon.ico",
            PROJECT_ROOT / "resources" / "icon.ico",
        ]
        for p in candidates:
            if p.exists():
                return p.resolve()
        return None

    def _apply_windows_icon(self):
        """通过 Win32 API 为窗口句柄精准赋予高清图标、居中还原坐标并默认最大化展示"""
        if sys.platform != "win32":
            return
        icon_p = self.get_icon_path()
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32

            hwnd = user32.FindWindowW(None, "Antigravity Orbit")
            if not hwnd:
                return

            # 1. 注入大/小图标
            if icon_p and icon_p.exists():
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040
                h_big = user32.LoadImageW(0, str(icon_p), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                h_sm = user32.LoadImageW(0, str(icon_p), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if h_big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
                if h_sm:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_sm)

            # 2. 精确计算工作区居中坐标 (扣除 Windows 任务栏并适配高 DPI 屏幕)
            class RECT(ctypes.Structure):
                _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]
            class POINT(ctypes.Structure):
                _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]
            class WINDOWPLACEMENT(ctypes.Structure):
                _fields_ = [
                    ('length', wintypes.UINT),
                    ('flags', wintypes.UINT),
                    ('showCmd', wintypes.UINT),
                    ('ptMinPosition', POINT),
                    ('ptMaxPosition', POINT),
                    ('rcNormalPosition', RECT)
                ]

            work_rect = RECT()
            # 0x0030 = SPI_GETWORKAREA
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_rect), 0)
            work_w = work_rect.right - work_rect.left
            work_h = work_rect.bottom - work_rect.top
            win_w = 980
            win_h = 740
            cx = work_rect.left + max(0, (work_w - win_w) // 2)
            cy = work_rect.top + max(0, (work_h - win_h) // 2)

            is_maximized = bool(user32.IsZoomed(hwnd))

            # 3. 配置还原态与默认最大化状态
            wp = WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(WINDOWPLACEMENT)
            if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
                # 无论当前是否最大化，将还原状态 (rcNormalPosition) 精确锚定在屏幕正中央
                wp.rcNormalPosition.left = cx
                wp.rcNormalPosition.top = cy
                wp.rcNormalPosition.right = cx + win_w
                wp.rcNormalPosition.bottom = cy + win_h

                if not self.start_in_tray:
                    # 默认打开时全屏最大化
                    wp.showCmd = 3  # SW_MAXIMIZE = 3
                    user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
                    user32.ShowWindow(hwnd, 3)
                    try:
                        if self.window:
                            self.window.maximize()
                    except Exception:
                        pass
                else:
                    wp.showCmd = 0  # SW_HIDE = 0
                    user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
                    user32.ShowWindow(hwnd, 0)

            # 4. 若为托盘静默启动模式，强制维持隐藏状态
            if self.start_in_tray:
                user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    def _on_gui_ready(self):
        """WebView2 GUI 线程就绪回调"""
        if self.start_in_tray:
            try:
                if self.window:
                    self.window.hide()
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    hwnd = user32.FindWindowW(None, "Antigravity Orbit")
                    if hwnd:
                        user32.ShowWindow(hwnd, 0)
                except Exception:
                    pass
        else:
            time.sleep(0.15)
            try:
                if self.window:
                    self.window.maximize()
            except Exception:
                pass
        self._apply_windows_icon()

    def _get_antigravity_menu_text(self, item=None) -> str:
        """根据当前反重力客户端运行状态动态返回菜单文案 (纯文本，无任何图标)"""
        return "重启反重力" if LocalizationManager.is_running() else "开启反重力"

    def _on_antigravity_tray_action(self, icon=None, item=None):
        """动态托盘操作：反重力运行中则重启并更新补丁，未运行则直接拉起客户端"""
        try:
            if LocalizationManager.is_running():
                self.api.restart_antigravity()
            else:
                cfg = load_config()
                custom = cfg.get("customization", {})
                lang = custom.get("language", "zh-CN")
                is_tw = (lang == "zh-TW")
                is_en = (lang == "en")
                try:
                    LocalizationManager.install(tw=is_tw, en=is_en, no_kill=True, stream_output=False)
                except Exception:
                    pass
                LocalizationManager.launch_antigravity()
        except Exception as e:
            print(f"[Tray Action Error] 开启/重启反重力失败: {e}")
        if self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def init_tray(self):
        """初始化系统托盘后台守护"""
        try:
            import pystray
            from PIL import Image

            icon_p = self.get_tray_icon_path()
            if not icon_p:
                return

            img = Image.open(str(icon_p))
            menu = pystray.Menu(
                pystray.MenuItem("打开管理中心", self.show_window, default=True),
                pystray.MenuItem(self._get_antigravity_menu_text, self._on_antigravity_tray_action),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.force_quit)
            )
            self.tray_icon = pystray.Icon("Antigravity Orbit", img, "Antigravity Orbit", menu)

            # Windows 平台右键弹出菜单前拦截 WM_RBUTTONUP 动态刷新文案状态
            orig_on_notify = getattr(self.tray_icon, "_on_notify", None)
            if orig_on_notify:
                def wrapped_on_notify(wparam, lparam):
                    if lparam == 0x0205:  # WM_RBUTTONUP
                        try:
                            self.tray_icon.update_menu()
                        except Exception:
                            pass
                    return orig_on_notify(wparam, lparam)
                self.tray_icon._on_notify = wrapped_on_notify

            self.tray_icon.run_detached()
        except Exception as e:
            print(f"[Tray Warning] 托盘初始化失败: {e}")
            self.tray_icon = None

    def show_window(self, icon=None, item=None):
        """从托盘恢复显示窗口并以最大化全屏展示"""
        self.start_in_tray = False
        if self.window:
            try:
                self.window.show()
                self.window.maximize()
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, "Antigravity Orbit")
                if hwnd:
                    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = 3
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        threading.Timer(0.1, self._apply_windows_icon).start()

    def on_closing(self):
        """拦截窗口关闭按钮"""
        if self.is_force_quitting:
            return True

        cfg = load_config()
        close_to_tray = cfg.get("close_to_tray", False)
        if close_to_tray and self.tray_icon:
            if self.window:
                try:
                    self.window.hide()
                except Exception:
                    pass
            return False  # 返回 False 阻断窗口销毁，仅隐藏驻留托盘保持后台监控

        # 若未开启托盘常驻，则彻底退出
        self.force_quit()
        return True

    def force_quit(self, icon=None, item=None):
        """彻底终止进程并退出应用 (干净停止所有后台守护和监控)"""
        self.is_force_quitting = True

        # 1. 停止内置后台监控引擎
        if self.monitor:
            try:
                self.monitor.stop()
            except Exception:
                pass

        # 2. 停止托盘
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        # 3. 销毁窗口
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass

        # 4. 强制终结进程
        threading.Timer(0.2, lambda: os._exit(0)).start()

    def run(self):
        """启动应用与 WebView2 视窗"""
        html_path = self.get_web_entry_path()
        icon_p = self.get_icon_path()

        # 1. 启动内置后台守护监控引擎 (工具启动即随主程序在后台守护，退出时自动终止)
        try:
            self.monitor_thread = threading.Thread(target=self.monitor.run_loop, daemon=True)
            self.monitor_thread.start()
        except Exception as e:
            print(f"[Monitor Warning] 内置后台监控启动失败: {e}")

        # 2. 异步非阻塞启动系统托盘
        threading.Thread(target=self.init_tray, daemon=True).start()

        # 3. 创建现代 Edge WebView2 窗口 (屏幕居中显示)
        win_w = 980
        win_h = 740
        win_x = None
        win_y = None
        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
                if sw > win_w and sh > win_h:
                    win_x = int((sw - win_w) / 2)
                    win_y = int((sh - win_h) / 2)
            except Exception:
                pass

        self.window = webview.create_window(
            title="Antigravity Orbit",
            url=str(html_path),
            js_api=self.api,
            width=win_w,
            height=win_h,
            x=win_x,
            y=win_y,
            min_size=(880, 640),
            hidden=self.start_in_tray,
            background_color="#f8fafc",
            easy_drag=True,
            text_select=True,
            maximized=not self.start_in_tray,
        )

        # 4. 挂载关闭拦截事件
        self.window.events.closing += self.on_closing

        # 5. 延迟注入 Win32 原生大/小图标到窗口句柄 (强化任务栏显示)
        threading.Timer(0.5, self._apply_windows_icon).start()
        threading.Timer(1.5, self._apply_windows_icon).start()

        # 6. 启动主循环
        cache_storage = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Antigravity-Orbit" / "webview_cache"
        start_kwargs = {
            "private_mode": False,
            "storage_path": str(cache_storage),
        }
        if icon_p and icon_p.exists():
            start_kwargs["icon"] = str(icon_p)

        webview.start(self._on_gui_ready, **start_kwargs)


def launch_gui(start_in_tray: bool = False):
    """桌面可视化管理中心统一启动入口 (支持多实例防重激活与最大化聚焦)"""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "Antigravity Orbit")
            if hwnd:
                if not start_in_tray:
                    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = 3
                    user32.SetForegroundWindow(hwnd)
                return
        except Exception:
            pass

    app = OrbitWindowManager(start_in_tray=start_in_tray)
    app.run()


if __name__ == "__main__":
    launch_gui()
