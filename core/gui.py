"""
Antigravity Orbit - 独立桌面客户端管理中心 (Native Desktop GUI Client)
极简现代浅色分类导航设计，对齐 macOS / Fluent 视觉规范
左侧 7 大功能分类导航 + 右侧独立卡片流，支持系统托盘常驻与系统提示词可视化管理
"""

import os
import sys
import json
import time
import socket
import platform
import threading
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# 开启 Windows 高 DPI 适配
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    CONFIG_FILE,
    LOG_FILE,
    BASE_DIR,
    RESOURCE_DIR,
    load_config,
    save_config,
    find_active_config_file,
)
from core.localization import LocalizationManager
from core.autostart import AutostartManager
from core.storage import StorageManager
from core.skills_optimizer import SkillsOptimizer
from core.prompt_manager import PromptManager


class ModernCheckmark(tk.Canvas):
    """
    高质感现代复选方块组件 (20x20 像素级几何绘制)：
    - 选中状态：宝蓝底色 (#2563eb) + 清晰居中纯白勾选符 ✔ (\u2714)
    - 未选状态：纯白底色 + 浅灰精致描边 (#cbd5e1)
    - 严格使用电脑自带原生字体，支持鼠标悬停高亮与整行联动点击
    """

    def __init__(self, parent, variable: tk.BooleanVar, command=None, size=20, bg="#ffffff", font_family=""):
        super().__init__(parent, width=size, height=size, bg=bg, bd=0, highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.command = command
        self.size = size
        self.bg_color = bg
        self.font_family = font_family or ("Microsoft YaHei UI" if sys.platform.startswith("win") else "TkDefaultFont")

        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))

        self.variable.trace_add("write", lambda *_: self.render())
        self.render()

    def toggle(self):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _on_hover(self, entering: bool):
        if not self.variable.get():
            outline = "#93c5fd" if entering else "#cbd5e1"
            self.itemconfig("box", outline=outline)

    def render(self):
        self.delete("all")
        is_checked = self.variable.get()
        s = self.size

        box_bg = "#2563eb" if is_checked else "#ffffff"
        box_border = "#2563eb" if is_checked else "#cbd5e1"

        # 绘制微圆角方块
        self.create_rectangle(1, 1, s - 2, s - 2, fill=box_bg, outline=box_border, width=1.5, tags="box")

        # 绘制居中高对比白勾 ✔ (使用电脑自带原生字体)
        if is_checked:
            self.create_text(s / 2, s / 2, text="✔", fill="#ffffff", font=(self.font_family, 10, "bold"))


class ModernOrbitApp(tk.Tk):
    """Antigravity Orbit 极简现代桌面管理中心 (左侧导航 + 右侧分类面板 + 系统托盘)"""

    def __init__(self, start_in_tray: bool = False):
        super().__init__()
        self.title("Antigravity Orbit")
        self.geometry("980x740")
        self.minsize(880, 640)

        self.start_in_tray = start_in_tray
        self.tray_icon = None

        # 1. 严格使用电脑自带原生系统字体 (无需外挂任何自定义字体)
        self._init_system_fonts()
        self._center_window(980, 740)
        self._init_theme_colors()

        # 2. 原生秒载图标 (零外部无谓依赖，极速秒开启动)
        self._setup_app_icons()

        # 读取用户配置 (多级路径智能嗅探)
        self.cfg = load_config()
        self._init_variables()
        self._setup_ttk_styles()

        # 3. 初始化系统托盘常驻 (后台守护线程)
        self._init_tray()

        # 4. 构建侧边分类导航与主体布局
        self._build_categorized_layout()

        # 5. 绑定窗口关闭事件 (默认托盘最小化)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # 6. 若以 --tray 启动，则默认保持隐藏
        if self.start_in_tray:
            self.withdraw()

        # 7. 异步非阻塞状态刷新 (零卡顿秒开)
        self.after(30, self._refresh_system_status_async)

    def _init_system_fonts(self):
        """严格使用电脑自带原生系统字体 (Windows: 微软雅黑 / macOS: 苹方 / 系统默认)，不使用自定义字体"""
        sys_font_family = ""
        try:
            import tkinter.font as tkfont
            sys_font_family = tkfont.nametofont("TkDefaultFont").cget("family")
        except Exception:
            pass

        if sys.platform.startswith("win"):
            self.FONT_FAMILY = sys_font_family if sys_font_family in ["Microsoft YaHei UI", "Microsoft YaHei"] else "Microsoft YaHei UI"
            self.FONT_MONO = "Consolas"
        elif sys.platform.startswith("darwin"):
            self.FONT_FAMILY = sys_font_family or "PingFang SC"
            self.FONT_MONO = "Menlo"
        else:
            self.FONT_FAMILY = sys_font_family or "TkDefaultFont"
            self.FONT_MONO = "TkFixedFont"

        self.font_main = (self.FONT_FAMILY, 9)
        self.font_main_bold = (self.FONT_FAMILY, 9, "bold")
        self.font_sm = (self.FONT_FAMILY, 8)
        self.font_sm_bold = (self.FONT_FAMILY, 8, "bold")
        self.font_title = (self.FONT_FAMILY, 10, "bold")
        self.font_header = (self.FONT_FAMILY, 11, "bold")
        self.font_mono = (self.FONT_MONO, 9)
        self.font_mono_sm = (self.FONT_MONO, 8)

        try:
            self.option_add("*Font", self.font_main)
        except Exception:
            pass

    def _center_window(self, width, height):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, int((sw - width) / 2))
            y = max(0, int((sh - height) / 2) - 25)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _init_theme_colors(self):
        """现代极简浅色调色盘 (Slate / Zinc 风格规范)"""
        self.C_BG = "#f8fafc"             # 页面极简浅灰底色 (Slate-50)
        self.C_SIDEBAR = "#f8fafc"        # 侧边栏底色
        self.C_CARD = "#ffffff"           # 卡片纯白底色
        self.C_BORDER = "#e2e8f0"         # 边框细线 (Slate-200)
        self.C_SEP = "#f1f5f9"            # 行内弱分隔线 (Slate-100)
        self.C_HOVER = "#f1f5f9"          # 悬停轻灰

        self.C_TEXT_MAIN = "#0f172a"      # 主要文字 (深墨黑，高对比清晰度)
        self.C_TEXT_MUTED = "#475569"     # 次要描述文字 (Slate-600)
        self.C_TEXT_DIM = "#94a3b8"       # 提示弱说明文字 (Slate-400)

        self.C_ACCENT = "#2563eb"         # 系统级宝蓝 (Blue-600)
        self.C_ACCENT_HOVER = "#1d4ed8"   # 宝蓝悬停 (Blue-700)
        self.C_ACCENT_BG = "#eff6ff"      # 激活状态浅蓝底色 (Blue-50)
        self.C_BTN_SEC = "#ffffff"        # 次级按钮底色
        self.C_BTN_SEC_BORDER = "#cbd5e1" # 次级按钮描边 (Slate-300)
        self.C_BTN_SEC_HOVER = "#f1f5f9"  # 次级按钮悬停

        self.C_GREEN = "#16a34a"          # 正常色 (Green-600)
        self.C_GRAY = "#94a3b8"           # 未运行/未启用色 (Slate-400)
        self.C_DANGER = "#dc2626"         # 警告红色 (Red-600)

        self.configure(bg=self.C_BG)

    def _setup_app_icons(self):
        """设置窗口与任务栏图标 (纯原生 Tkinter PhotoImage 载入，秒开启动)"""
        icon_ico = RESOURCE_DIR / "resources" / "icon.ico"
        icon_32 = RESOURCE_DIR / "resources" / "icon_32.png"
        gh_16 = RESOURCE_DIR / "resources" / "github_16.png"

        if icon_ico.exists() and sys.platform.startswith("win"):
            try:
                self.iconbitmap(str(icon_ico))
            except Exception:
                pass

        self.app_icon_img = None
        if icon_32.exists():
            try:
                self.app_icon_img = tk.PhotoImage(file=str(icon_32))
                self.iconphoto(True, self.app_icon_img)
            except Exception:
                pass
        elif (RESOURCE_DIR / "resources" / "icon.png").exists():
            try:
                self.app_icon_img = tk.PhotoImage(file=str(RESOURCE_DIR / "resources" / "icon.png")).subsample(16, 16)
                self.iconphoto(True, self.app_icon_img)
            except Exception:
                pass

        self.github_icon_img = None
        if gh_16.exists():
            try:
                self.github_icon_img = tk.PhotoImage(file=str(gh_16))
            except Exception:
                pass
        elif (RESOURCE_DIR / "resources" / "github.png").exists():
            try:
                self.github_icon_img = tk.PhotoImage(file=str(RESOURCE_DIR / "resources" / "github.png")).subsample(2, 2)
            except Exception:
                pass

    def _init_variables(self):
        """绑定表单数据模型"""
        custom = self.cfg.get("customization", {})

        # 窗口与自启设置
        self.var_close_to_tray = tk.BooleanVar(value=self.cfg.get("close_to_tray", True))
        self.var_app_autostart = tk.BooleanVar(value=AutostartManager.is_app_autostart_enabled())

        # 界面与外观
        self.var_language = tk.StringVar(value=custom.get("language", "zh-CN"))
        self.var_show_quota = tk.BooleanVar(value=custom.get("show_quota_badge", True))
        self.var_quota_interval = tk.IntVar(value=custom.get("quota_refresh_interval", 60))
        self.var_hide_ide = tk.BooleanVar(value=custom.get("hide_ide_buttons", True))
        self.var_compact_ui = tk.BooleanVar(value=custom.get("compact_ui_mode", False))

        # 性能与深度系统优化
        self.var_gpu_accel = tk.BooleanVar(value=custom.get("enable_gpu_acceleration", True))
        self.var_unthrottle = tk.BooleanVar(value=custom.get("disable_background_throttling", True))
        self.var_v8_mem = tk.BooleanVar(value=custom.get("expand_v8_memory", True))
        self.var_telemetry = tk.BooleanVar(value=custom.get("disable_telemetry", True))
        self.var_smooth_scrolling = tk.BooleanVar(value=custom.get("enable_smooth_scrolling", True))
        self.var_disable_auto_update = tk.BooleanVar(value=custom.get("disable_auto_update", True))
        self.var_prune_skills = tk.BooleanVar(value=custom.get("prune_guide_skills", False))

        # Antigravity 专属网络代理 (彻底取代 Proxifier)
        self.var_proxy_enabled = tk.BooleanVar(value=custom.get("proxy_enabled", False))
        self.var_proxy_url = tk.StringVar(value=custom.get("proxy_url", "http://127.0.0.1:10808"))

        # 任务异常自愈与额度监控
        self.var_auto_retry = tk.BooleanVar(value=custom.get("auto_retry_on_error", True))
        self.var_max_retry_count = tk.IntVar(value=custom.get("max_retry_count", 3))
        self.var_notify_quota = tk.BooleanVar(value=custom.get("notify_on_quota_exhausted", True))
        self.var_notify_max_retry = tk.BooleanVar(value=custom.get("notify_on_max_retry_failed", True))

        # 通知通道 (精准读取历史配置)
        channels = self.cfg.get("channels", {})
        tg = channels.get("telegram", {})
        self.var_tg_enabled = tk.BooleanVar(value=tg.get("enabled", False))
        self.var_tg_token = tk.StringVar(value=tg.get("bot_token", ""))
        self.var_tg_chat = tk.StringVar(value=tg.get("chat_id", ""))
        self.var_tg_proxy = tk.StringVar(value=tg.get("proxy", ""))

        fs = channels.get("feishu", {})
        self.var_fs_enabled = tk.BooleanVar(value=fs.get("enabled", False))
        self.var_fs_url = tk.StringVar(value=fs.get("webhook_url", ""))

        wc = channels.get("wecom", {})
        self.var_wc_enabled = tk.BooleanVar(value=wc.get("enabled", False))
        self.var_wc_url = tk.StringVar(value=wc.get("webhook_url", ""))

        # 守护服务
        self.var_daemon_port = tk.IntVar(value=self.cfg.get("lock_port", 49222))

        # 状态指示
        self.var_status_msg = tk.StringVar(value="就绪")
        self.var_stat_install = tk.StringVar(value="正在快速检测...")
        self.var_stat_daemon = tk.StringVar(value="正在快速检测...")
        self.var_stat_autostart = tk.StringVar(value="正在快速检测...")
        self.var_stat_app_autostart = tk.StringVar(value="正在检测客户端自启...")
        self.var_stat_storage = tk.StringVar(value="正在分析可清理存储占用...")

    def _setup_ttk_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("TFrame", background=self.C_BG)
        self.style.configure("Card.TFrame", background=self.C_CARD)

        self.style.configure(
            "Clean.TRadiobutton",
            background=self.C_CARD,
            foreground=self.C_TEXT_MAIN,
            font=self.font_main,
            padding=3
        )
        self.style.map(
            "Clean.TRadiobutton",
            background=[("active", self.C_CARD)],
            indicatorcolor=[("selected", self.C_ACCENT), ("active", "#93c5fd")]
        )

        self.style.configure(
            "Clean.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=self.C_TEXT_MAIN,
            selectbackground=self.C_ACCENT,
            selectforeground="#ffffff",
            font=self.font_main,
            padding=3
        )

    # -------------------------------------------------------------
    # 系统托盘集成 (pystray)
    # -------------------------------------------------------------
    def _init_tray(self):
        """初始化系统托盘后台守护线程"""
        try:
            import pystray
            from PIL import Image

            icon_path = RESOURCE_DIR / "resources" / "icon_32.png"
            if not icon_path.exists():
                icon_path = RESOURCE_DIR / "resources" / "icon.ico"

            img = Image.open(str(icon_path))
            menu = pystray.Menu(
                pystray.MenuItem("🖥️ 打开管理中心", self._show_window, default=True),
                pystray.MenuItem("🚀 重启 Antigravity", lambda icon, item: self.after(0, self._on_click_restart_app)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("🚪 彻底退出", self._force_quit)
            )
            self.tray_icon = pystray.Icon("Antigravity Orbit", img, "Antigravity Orbit", menu)
            self.tray_icon.run_detached()
        except Exception as e:
            self.tray_icon = None
            print(f"[Tray Warning] 系统托盘未能初始化: {e}")

    def _show_window(self, icon=None, item=None):
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        if sys.platform.startswith("win"):
            try:
                self.attributes("-topmost", True)
                self.after(100, lambda: self.attributes("-topmost", False))
            except Exception:
                pass

    def _on_window_close(self):
        """点击右上角关闭按钮拦截"""
        if self.var_close_to_tray.get() and self.tray_icon:
            self.withdraw()
        else:
            self._force_quit()

    def _force_quit(self, icon=None, item=None):
        """彻底终止进程并退出"""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        def _terminate():
            try:
                self.destroy()
            except Exception:
                pass
            sys.exit(0)
        self.after(0, _terminate)

    # -------------------------------------------------------------
    # 整体布局构建：左侧导航 + 右侧面板 + 底部操作栏
    # -------------------------------------------------------------
    def _build_categorized_layout(self):
        # 1. 顶部主体区域 (左侧导航 + 右侧分类面板)
        self.main_body = tk.Frame(self, bg=self.C_BG)
        self.main_body.pack(fill="both", expand=True, side="top")

        # 2. 底部全局常驻操作栏 (严格等高对齐)
        self._build_bottom_bar()

        # 3. 构建左侧导航栏
        self._build_sidebar(self.main_body)

        # 4. 构建右侧分类内容容器
        self.content_area = tk.Frame(self.main_body, bg=self.C_BG)
        self.content_area.pack(side="left", fill="both", expand=True)

        # 5. 定义 7 大模块分类
        self.tabs_meta = [
            ("overview", "📌 概览与服务", "客户端状态、守护监听、开机自启、深度瘦身"),
            ("ui", "🎨 界面与外观", "语言切换、移除推广按钮、紧凑代码排版"),
            ("perf", "⚡ 性能与代理", "显卡加速、防休眠降频、专属网络代理"),
            ("healing", "🛡️ 自愈与额度", "任务异常自动重试、额度耗尽熔断告警"),
            ("prompts", "📝 系统提示词", "AGENTS.md 全局提示词与角色预设模板"),
            ("notify", "🔔 消息推送", "Telegram、飞书、企业微信机器人配置"),
            ("logs", "📜 运行日志", "常驻后台心跳与长跑任务推送日志"),
        ]

        self.tab_frames = {}
        self.nav_items = {}

        # 依次构建各分类页面
        self._init_all_tabs()

        # 默认选中第一个分类
        self._switch_tab("overview")

    # -------------------------------------------------------------
    # 左侧导航栏构建 (macOS / Fluent 风格)
    # -------------------------------------------------------------
    def _build_sidebar(self, parent):
        self.sidebar_frame = tk.Frame(parent, bg=self.C_SIDEBAR, width=210, highlightthickness=1, highlightbackground=self.C_BORDER)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # 品牌头部区域
        brand_frame = tk.Frame(self.sidebar_frame, bg=self.C_SIDEBAR, padx=16, pady=18)
        brand_frame.pack(fill="x")

        b_title_row = tk.Frame(brand_frame, bg=self.C_SIDEBAR)
        b_title_row.pack(anchor="w")

        tk.Label(b_title_row, text="Orbit 管理中心", font=self.font_header, fg=self.C_TEXT_MAIN, bg=self.C_SIDEBAR).pack(side="left")
        
        # 版本小徽章
        v_pill = tk.Label(b_title_row, text="v2.7.0", font=self.font_sm_bold, fg=self.C_ACCENT, bg=self.C_ACCENT_BG, padx=6, pady=1)
        v_pill.pack(side="left", padx=(8, 0))

        tk.Label(brand_frame, text="Antigravity 增强套件", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_SIDEBAR).pack(anchor="w", pady=(2, 0))

        # 细微分割线
        tk.Frame(self.sidebar_frame, bg=self.C_BORDER, height=1).pack(fill="x", padx=12, pady=(0, 8))

        # 导航选项容器
        self.nav_container = tk.Frame(self.sidebar_frame, bg=self.C_SIDEBAR)
        self.nav_container.pack(fill="both", expand=True, padx=8)

        # 底部托盘与自启状态小卡
        tray_hint_box = tk.Frame(self.sidebar_frame, bg="#ffffff", padx=10, pady=8, highlightthickness=1, highlightbackground=self.C_BORDER)
        tray_hint_box.pack(fill="x", side="bottom", padx=10, pady=10)

        tk.Label(tray_hint_box, text="💡 托盘常驻提示", font=self.font_sm_bold, fg=self.C_TEXT_MAIN, bg="#ffffff").pack(anchor="w")
        tk.Label(tray_hint_box, text="关闭窗口后自动缩入系统托盘\n右键图标可彻底退出或重启", font=self.font_sm, fg=self.C_TEXT_MUTED, bg="#ffffff", justify="left").pack(anchor="w", pady=(2, 0))

    def _add_nav_button(self, key: str, title: str):
        item_frame = tk.Frame(self.nav_container, bg=self.C_SIDEBAR, cursor="hand2", pady=1)
        item_frame.pack(fill="x", pady=2)

        # 左侧 3px 宝蓝激活指示条
        bar = tk.Frame(item_frame, bg=self.C_SIDEBAR, width=3)
        bar.pack(side="left", fill="y", padx=(2, 6))

        lbl = tk.Label(
            item_frame,
            text=title,
            font=self.font_main,
            fg=self.C_TEXT_MAIN,
            bg=self.C_SIDEBAR,
            anchor="w",
            cursor="hand2",
            padx=4,
            pady=7
        )
        lbl.pack(side="left", fill="x", expand=True)

        # 绑定点击切换
        for w in [item_frame, bar, lbl]:
            w.bind("<Button-1>", lambda e, k=key: self._switch_tab(k))
            w.bind("<Enter>", lambda e, k=key: self._on_nav_hover(k, True))
            w.bind("<Leave>", lambda e, k=key: self._on_nav_hover(k, False))

        self.nav_items[key] = {
            "frame": item_frame,
            "bar": bar,
            "label": lbl,
        }

    def _on_nav_hover(self, key: str, entering: bool):
        if getattr(self, "active_tab", None) == key:
            return
        item = self.nav_items.get(key)
        if item:
            bg = self.C_HOVER if entering else self.C_SIDEBAR
            item["frame"].configure(bg=bg)
            item["label"].configure(bg=bg)
            item["bar"].configure(bg=bg)

    def _switch_tab(self, key: str):
        self.active_tab = key

        # 1. 刷新所有导航按钮样式
        for k, item in self.nav_items.items():
            if k == key:
                item["frame"].configure(bg=self.C_ACCENT_BG)
                item["label"].configure(bg=self.C_ACCENT_BG, fg=self.C_ACCENT, font=self.font_main_bold)
                item["bar"].configure(bg=self.C_ACCENT)
            else:
                item["frame"].configure(bg=self.C_SIDEBAR)
                item["label"].configure(bg=self.C_SIDEBAR, fg=self.C_TEXT_MAIN, font=self.font_main)
                item["bar"].configure(bg=self.C_SIDEBAR)

        # 2. 切换右侧内容面板
        for k, frame in self.tab_frames.items():
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # -------------------------------------------------------------
    # 右侧 7 大模块视图页面构建
    # -------------------------------------------------------------
    def _create_tab_scrollable_container(self, parent) -> tuple[tk.Frame, tk.Canvas]:
        """为分类页面创建精致平滑滚动容器"""
        container = tk.Frame(parent, bg=self.C_BG)

        canvas = tk.Canvas(container, bg=self.C_BG, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg=self.C_BG, padx=22, pady=16)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(canvas_window, width=e.width)
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind("<MouseWheel>", _on_wheel)
        scrollable_frame.bind("<MouseWheel>", _on_wheel)

        return container, scrollable_frame

    def _init_all_tabs(self):
        for key, title, _ in self.tabs_meta:
            self._add_nav_button(key, title)
            c_outer, c_inner = self._create_tab_scrollable_container(self.content_area)
            self.tab_frames[key] = c_outer

            if key == "overview":
                self._build_card_system_status(c_inner)
            elif key == "ui":
                self._build_card_localization(c_inner)
            elif key == "perf":
                self._build_card_performance(c_inner)
                self._build_card_proxy(c_inner)
            elif key == "healing":
                self._build_card_task_healing(c_inner)
            elif key == "prompts":
                self._build_card_prompts(c_inner)
            elif key == "notify":
                self._build_card_notifications(c_inner)
            elif key == "logs":
                self._build_card_logs(c_inner)

    # -------------------------------------------------------------
    # 模块 1: 概览与服务 (含守护、托盘行为、客户端自启与垃圾瘦身)
    # -------------------------------------------------------------
    def _build_card_system_status(self, parent):
        c = self._create_card(parent, "客户端核心与系统服务", "检测 Antigravity 本地安装状态、管理后台常驻守护、托盘行为与开机自启动")

        # 行 1: 客户端本地安装与汉化状态
        r_client = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_client.pack(fill="x")

        left_c = tk.Frame(r_client, bg=self.C_CARD)
        left_c.pack(side="left", fill="x", expand=True)
        tk.Label(left_c, text="Antigravity 客户端状态:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left_c, textvariable=self.var_stat_install, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        self.pill_install = tk.Label(r_client, text="检测中...", font=self.font_sm_bold, fg="#1e293b", bg="#f1f5f9", padx=10, pady=4)
        self.pill_install.pack(side="right")

        self._create_row_separator(c)

        # 行 2: 后台常驻监听服务
        r_daemon = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_daemon.pack(fill="x")

        left_d = tk.Frame(r_daemon, bg=self.C_CARD)
        left_d.pack(side="left", fill="x", expand=True)

        d_title_row = tk.Frame(left_d, bg=self.C_CARD)
        d_title_row.pack(anchor="w")
        tk.Label(d_title_row, text="任务完成守护监听服务:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left")

        # 端口输入框
        tk.Label(d_title_row, text="端口", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(12, 4))
        e_port = tk.Entry(d_title_row, textvariable=self.var_daemon_port, width=6, bg="#f9fafb", fg=self.C_TEXT_MAIN, relief="solid", bd=1, font=self.font_mono)
        e_port.pack(side="left")

        tk.Label(left_d, textvariable=self.var_stat_daemon, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        # 右侧操作按钮组
        right_d = tk.Frame(r_daemon, bg=self.C_CARD)
        right_d.pack(side="right")
        self._create_inline_btn(right_d, "启动守护", self._start_daemon).pack(side="left", padx=(0, 6))
        self._create_inline_btn(right_d, "停止守护", self._stop_daemon).pack(side="left")

        self._create_row_separator(c)

        # 行 3: 后台守护服务系统开机自启
        r_auto = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_auto.pack(fill="x")

        left_a = tk.Frame(r_auto, bg=self.C_CARD)
        left_a.pack(side="left", fill="x", expand=True)
        tk.Label(left_a, text="后台守护服务开机自启:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left_a, textvariable=self.var_stat_autostart, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right_a = tk.Frame(r_auto, bg=self.C_CARD)
        right_a.pack(side="right")
        self._create_inline_btn(right_a, "开启守护自启", self._enable_autostart).pack(side="left", padx=(0, 6))
        self._create_inline_btn(right_a, "关闭守护自启", self._disable_autostart).pack(side="left")

        self._create_row_separator(c)

        # 行 4: Orbit 管理中心客户端开机自启 (驻留托盘)
        self._create_checkbox_row(
            c,
            title="Orbit 管理中心客户端随开机自启动",
            desc="开机自动以静默方式启动 Orbit 并驻留系统托盘，无需手动点开",
            variable=self.var_app_autostart,
            command=self._on_toggle_app_autostart
        )

        # 行 5: 默认关闭窗口时最小化到系统托盘
        self._create_checkbox_row(
            c,
            title="关闭窗口时最小化到系统托盘 (Close to Tray)",
            desc="点击窗口右上角关闭按钮时自动隐藏常驻至托盘图标，右键托盘可彻底退出",
            variable=self.var_close_to_tray
        )

        # 行 6: 本地存储与深度垃圾瘦身
        r_store = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_store.pack(fill="x")

        left_s = tk.Frame(r_store, bg=self.C_CARD)
        left_s.pack(side="left", fill="x", expand=True)
        tk.Label(left_s, text="本地存储与深度垃圾瘦身:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left_s, textvariable=self.var_stat_storage, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right_s = tk.Frame(r_store, bg=self.C_CARD)
        right_s.pack(side="right")
        self._create_inline_btn(right_s, "一键深度瘦身", self._on_clean_storage).pack(side="left")

    def _on_toggle_app_autostart(self):
        """联动系统注册表开机启动"""
        if self.var_app_autostart.get():
            ok, msg = AutostartManager.enable_app_autostart()
            if ok:
                self.var_status_msg.set("Orbit 客户端开机自启已开启")
            else:
                self.var_app_autostart.set(False)
                messagebox.showerror("设置失败", msg)
        else:
            ok, msg = AutostartManager.disable_app_autostart()
            self.var_status_msg.set("Orbit 客户端开机自启已关闭")

    # -------------------------------------------------------------
    # 模块 2: 界面汉化与外观设置
    # -------------------------------------------------------------
    def _build_card_localization(self, parent):
        c = self._create_card(parent, "界面语言与外观净化", "全面汉化 Antigravity 界面菜单与对话交互，移除右上角多余推广按钮")

        # 语言单选组
        r_lang = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_lang.pack(fill="x")

        tk.Label(r_lang, text="客户端界面语言:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w", pady=(0, 8))

        rb_box = tk.Frame(r_lang, bg=self.C_CARD)
        rb_box.pack(fill="x")

        ttk.Radiobutton(
            rb_box,
            text="简体中文 (zh-CN) [默认推荐]",
            variable=self.var_language,
            value="zh-CN",
            style="Clean.TRadiobutton"
        ).pack(side="left", padx=(0, 24))

        ttk.Radiobutton(
            rb_box,
            text="繁体中文 (zh-TW)",
            variable=self.var_language,
            value="zh-TW",
            style="Clean.TRadiobutton"
        ).pack(side="left", padx=(0, 24))

        ttk.Radiobutton(
            rb_box,
            text="官方英文原版 (en)",
            variable=self.var_language,
            value="en",
            style="Clean.TRadiobutton"
        ).pack(side="left")

        self._create_row_separator(c)

        # 界面净化勾选行
        self._create_checkbox_row(
            c,
            title="移除右上角推广按钮 (Open IDE / Install IDE)",
            desc="彻底隐藏右上角多余的推广按钮及其占位空白容器，恢复干净的顶栏",
            variable=self.var_hide_ide
        )

        self._create_checkbox_row(
            c,
            title="紧凑代码排版模式 (Compact UI Mode)",
            desc="缩减对话气泡与工具卡片上下空白边距，有效代码展示视野提升 35%~50%",
            variable=self.var_compact_ui,
            is_last=True
        )

    # -------------------------------------------------------------
    # 模块 3: 性能加速与专属网络代理
    # -------------------------------------------------------------
    def _build_card_performance(self, parent):
        c = self._create_card(parent, "性能加速与实时配额胶囊", "Chromium 显卡硬件加速、防后台休眠降频与顶栏模型配额")

        # 顶栏额度胶囊行
        r_quota = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_quota.pack(fill="x")

        left = tk.Frame(r_quota, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="顶栏模型额度实时胶囊", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left, text="在 Antigravity 标题栏右上角常驻显示 Gemini 与 Claude/GPT 限额比例与健康指示灯", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(r_quota, bg=self.C_CARD)
        right.pack(side="right", anchor="center")

        tk.Label(right, text="轮询频率:", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 4))
        cb_interval = ttk.Combobox(right, textvariable=self.var_quota_interval, values=[30, 60, 120, 300], width=5, state="readonly", style="Clean.TCombobox")
        cb_interval.pack(side="left", padx=(0, 10))
        tk.Label(right, text="秒", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 16))

        f_chk = tk.Frame(right, bg=self.C_CARD, cursor="hand2")
        f_chk.pack(side="left")
        chk = ModernCheckmark(f_chk, variable=self.var_show_quota, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk.pack(side="left", padx=(0, 6))
        lbl_txt = tk.Label(f_chk, text="启用显示", font=self.font_main, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_txt.pack(side="left")
        lbl_txt.bind("<Button-1>", lambda e: chk.toggle())
        f_chk.bind("<Button-1>", lambda e: chk.toggle())

        self._create_row_separator(c)

        # 性能加速勾选列表
        self._create_checkbox_row(
            c,
            title="GPU 显卡硬件栅格化与零拷贝 (Zero-Copy Rasterization)",
            desc="降低复杂项目与大量代码流式输出时的 CPU 渲染负载，交互更流畅",
            variable=self.var_gpu_accel
        )

        self._create_checkbox_row(
            c,
            title="长文本平滑滚动与 60FPS 顺滑渲染 (Smooth Scrolling)",
            desc="消除长篇代码流式输出与深度推理过程中的滚动顿挫撕裂感",
            variable=self.var_smooth_scrolling
        )

        self._create_checkbox_row(
            c,
            title="解除后台调度降频 (Disable Background Throttling)",
            desc="切换其他窗口时防止定时器被降频至 1Hz，保障智能体任务后台全速执行",
            variable=self.var_unthrottle
        )

        self._create_checkbox_row(
            c,
            title="V8 引擎堆内存扩容至 4GB (--max-old-space-size=4096)",
            desc="消除深度推理分析与数十轮长对话下的垃圾回收停顿与内存溢出崩溃",
            variable=self.var_v8_mem
        )

        self._create_checkbox_row(
            c,
            title="锁定稳定版本 (Disable Auto-Update)",
            desc="阻断后台自动静默检测与下载更新，防止官方静默升级覆盖汉化与各项补丁",
            variable=self.var_disable_auto_update
        )

        self._create_checkbox_row(
            c,
            title="裁剪内置说明型 Skills 提示词 (Prune Builtin Skills)",
            desc="安全屏蔽 antigravity_guide 等庞大教程技能，每次请求节省约 14,700 Token 预算",
            variable=self.var_prune_skills
        )

        self._create_checkbox_row(
            c,
            title="全栈切断遥测数据回传 (Anti-Telemetry)",
            desc="关闭 Language Server 指标收集、Chromium 诊断与 DevTools 日志上报",
            variable=self.var_telemetry,
            is_last=True
        )

    def _build_card_proxy(self, parent):
        c = self._create_card(parent, "Antigravity 专属网络代理 (彻底取代 Proxifier)", "为 Electron 界面与 Go 核心引擎 (language_server) 原生注入代理，无需开启 Proxifier 或系统全局 TUN 模式")

        # 勾选行
        r_chk = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_chk.pack(fill="x")

        left = tk.Frame(r_chk, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="启用 Antigravity 专属网络代理", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left, text="开启后 Chromium 界面、Go 语言服务器及 git.exe/ssh.exe 均自动走此代理", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(r_chk, bg=self.C_CARD)
        right.pack(side="right", anchor="center")

        f_chk = tk.Frame(right, bg=self.C_CARD, cursor="hand2")
        f_chk.pack(side="left")
        chk = ModernCheckmark(f_chk, variable=self.var_proxy_enabled, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk.pack(side="left", padx=(0, 6))
        lbl_txt = tk.Label(f_chk, text="启用代理", font=self.font_main, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_txt.pack(side="left")
        lbl_txt.bind("<Button-1>", lambda e: chk.toggle())
        f_chk.bind("<Button-1>", lambda e: chk.toggle())

        self._create_row_separator(c)

        # 代理地址输入框
        f_in = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        f_in.pack(fill="x")
        self._create_compact_input(f_in, "代理地址:", self.var_proxy_url, "支持 HTTP/SOCKS5，例如: http://127.0.0.1:10808")

        # 底部说明文案
        f_tip = tk.Frame(c, bg="#f8fafc", padx=16, pady=10, highlightthickness=1, highlightbackground=self.C_BORDER)
        f_tip.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(
            f_tip,
            text="💡 原理解析：此前您使用 Proxifier 代理 language_server_windows_x64.exe、Antigravity.exe、git.exe 等进程；本功能通过在 Chromium 命令行中直接注入 --proxy-server，并在 Language Server 启动时直接为其子进程注入 HTTP_PROXY / HTTPS_PROXY 环境变量，原生无死角接管所有 Google API 与网络请求，保存生效后您可以彻底退出并卸载 Proxifier！",
            font=self.font_sm,
            fg="#475569",
            bg="#f8fafc",
            wraplength=640,
            justify="left"
        ).pack(anchor="w")

    # -------------------------------------------------------------
    # 模块 4: 任务自愈与额度监控
    # -------------------------------------------------------------
    def _build_card_task_healing(self, parent):
        c = self._create_card(parent, "任务异常自愈与额度监控告警", "智能体任务意外报错自动重试，恢复工作自动重置计数；额度耗尽或超限即时通知")

        # 行 1: 任务异常自动重试与最大重试次数
        r_retry = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_retry.pack(fill="x")

        left = tk.Frame(r_retry, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="任务异常自动重试 (Auto-Retry on Error)", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left, text="智能体运行遭遇网络抖动或偶发报错时自动重试，重试后恢复工作将自动重置重试计数为 0", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(r_retry, bg=self.C_CARD)
        right.pack(side="right", anchor="center")

        tk.Label(right, text="最大重试:", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 4))
        cb_retries = ttk.Combobox(right, textvariable=self.var_max_retry_count, values=[1, 2, 3, 4, 5, 8, 10], width=4, state="readonly", style="Clean.TCombobox")
        cb_retries.pack(side="left", padx=(0, 4))
        tk.Label(right, text="次", font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 16))

        f_chk = tk.Frame(right, bg=self.C_CARD, cursor="hand2")
        f_chk.pack(side="left")
        chk = ModernCheckmark(f_chk, variable=self.var_auto_retry, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk.pack(side="left", padx=(0, 6))
        lbl_txt = tk.Label(f_chk, text="已启用", font=self.font_main, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_txt.pack(side="left")
        lbl_txt.bind("<Button-1>", lambda e: chk.toggle())
        f_chk.bind("<Button-1>", lambda e: chk.toggle())

        self._create_row_separator(c)

        # 行 2: 额度耗尽专门告警
        self._create_checkbox_row(
            c,
            title="模型额度耗尽立即发送中断通知 (Notify on Quota Exhausted)",
            desc="检测到 429、Rate Limit 或模型额度用尽时立即停止重试，向各渠道发送【任务中断：额度已耗尽】告警",
            variable=self.var_notify_quota
        )

        # 行 3: 重试次数超限失败告警
        self._create_checkbox_row(
            c,
            title="重试次数超限发送任务失败通知 (Notify on Max Retries Failed)",
            desc="连续自动重试达到设定上限仍无法恢复工作时，向各渠道发送【任务执行失败】告警",
            variable=self.var_notify_max_retry,
            is_last=True
        )

    # -------------------------------------------------------------
    # 模块 5: 系统提示词管理器 (System Prompt Manager)
    # -------------------------------------------------------------
    def _build_card_prompts(self, parent):
        c = self._create_card(
            parent,
            "Antigravity 全局系统提示词与规则管理",
            "直接编辑 ~/.gemini/config/AGENTS.md，实时约束智能体底层角色、代码逻辑与回复准则"
        )

        # 顶部预设选择与操作栏
        top_bar = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        top_bar.pack(fill="x")

        left_tpl = tk.Frame(top_bar, bg=self.C_CARD)
        left_tpl.pack(side="left", fill="x", expand=True)

        tk.Label(left_tpl, text="预设角色模板:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left", padx=(0, 8))

        self.tpl_keys = list(PromptManager.TEMPLATES.keys())
        self.tpl_names = [PromptManager.TEMPLATES[k]["name"] for k in self.tpl_keys]
        self.var_active_tpl = tk.StringVar(value=self.tpl_names[0] if self.tpl_names else "")

        cb_tpl = ttk.Combobox(
            left_tpl,
            textvariable=self.var_active_tpl,
            values=self.tpl_names,
            width=32,
            state="readonly",
            style="Clean.TCombobox"
        )
        cb_tpl.pack(side="left", padx=(0, 10))

        self._create_inline_btn(left_tpl, "套用此模板", self._apply_selected_template).pack(side="left")

        # 右侧操作按钮组
        right_actions = tk.Frame(top_bar, bg=self.C_CARD)
        right_actions.pack(side="right")

        self._create_inline_btn(right_actions, "重新读取", self._reload_system_prompt).pack(side="left", padx=(0, 6))
        self._create_inline_btn(right_actions, "恢复上次备份", self._restore_prompt_backup).pack(side="left", padx=(0, 6))
        
        # 专属独立保存按钮 (高亮浅蓝)
        btn_save_p = tk.Button(
            right_actions,
            text="保存系统提示词",
            command=self._save_system_prompt,
            font=self.font_sm_bold,
            bg=self.C_ACCENT,
            fg="#ffffff",
            activebackground=self.C_ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="solid",
            bd=1,
            padx=12,
            pady=3,
            cursor="hand2"
        )
        btn_save_p.pack(side="left")

        self._create_row_separator(c)

        # 文本编辑器区域
        f_editor = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        f_editor.pack(fill="both", expand=True)

        self.txt_prompt = scrolledtext.ScrolledText(
            f_editor,
            height=14,
            bg="#ffffff",
            fg=self.C_TEXT_MAIN,
            insertbackground="#0f172a",
            font=self.font_mono,
            relief="solid",
            bd=1,
            wrap="word",
            padx=12,
            pady=10,
            undo=True
        )
        self.txt_prompt.pack(fill="both", expand=True)

        # 异步非阻塞载入当前系统提示词
        self.after(50, self._reload_system_prompt)

        # 底部原理与生效提示框
        f_tip = tk.Frame(c, bg="#f8fafc", padx=16, pady=10, highlightthickness=1, highlightbackground=self.C_BORDER)
        f_tip.pack(fill="x", padx=20, pady=(0, 14))
        tk.Label(
            f_tip,
            text="💡 原理提示：Antigravity 启动会话时会自动读取 ~/.gemini/config/AGENTS.md 并注入为全局 <RULE[user_global]>。在此修改并保存后，无需重启 Antigravity，下一个新任务或对话轮次将直接生效！保存时会自动在同级目录生成 AGENTS.md.bak 备份。",
            font=self.font_sm,
            fg="#475569",
            bg="#f8fafc",
            wraplength=640,
            justify="left"
        ).pack(anchor="w")

    def _reload_system_prompt(self):
        """重新从磁盘读取系统提示词"""
        content = PromptManager.read_system_prompt()
        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert(tk.END, content)
        self.var_status_msg.set(f"已载入当前系统提示词 ({len(content)} 字符)")

    def _apply_selected_template(self):
        """将选中的预设模板填入编辑区"""
        chosen_name = self.var_active_tpl.get()
        target_tpl = None
        for k, v in PromptManager.TEMPLATES.items():
            if v["name"] == chosen_name:
                target_tpl = v
                break
        if not target_tpl:
            messagebox.showwarning("提示", "未找到对应的预设模板！")
            return

        if not messagebox.askyesno("套用模板确认", f"确定要将编辑区内容替换为【{chosen_name}】模板吗？\n\n您可以在替换后自由编辑，点击右上方'保存系统提示词'才会正式写入生效。"):
            return

        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert(tk.END, target_tpl["content"])
        self.var_status_msg.set(f"已套用模板: {target_tpl['desc']}")

    def _save_system_prompt(self):
        """保存当前编辑器中的提示词到 AGENTS.md"""
        content = self.txt_prompt.get("1.0", tk.END).strip()
        ok, msg = PromptManager.save_system_prompt(content)
        if ok:
            self.var_status_msg.set(msg)
            messagebox.showinfo("保存成功", f"{msg}\n\nAntigravity 在接下来的对话与任务中将自动采纳新规则。")
        else:
            messagebox.showerror("保存失败", msg)

    def _restore_prompt_backup(self):
        """从 .bak 备份还原系统提示词"""
        if not messagebox.askyesno("备份恢复确认", "确定要从上一次的历史备份 AGENTS.md.bak 恢复系统提示词吗？"):
            return
        ok, msg = PromptManager.restore_backup()
        if ok:
            self._reload_system_prompt()
            messagebox.showinfo("恢复成功", msg)
        else:
            messagebox.showerror("恢复失败", msg)

    # -------------------------------------------------------------
    # 模块 6: 消息通知推送渠道
    # -------------------------------------------------------------
    def _build_card_notifications(self, parent):
        c = self._create_card(parent, "任务完工即时通知渠道", "长跑任务、构建或复杂对话完成时自动向手机或电脑发送通知")

        # 1. Telegram
        f_tg = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        f_tg.pack(fill="x")

        head_tg = tk.Frame(f_tg, bg=self.C_CARD)
        head_tg.pack(fill="x", pady=(0, 8))

        tg_check_box = tk.Frame(head_tg, bg=self.C_CARD, cursor="hand2")
        tg_check_box.pack(side="left")
        chk_tg = ModernCheckmark(tg_check_box, variable=self.var_tg_enabled, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk_tg.pack(side="left", padx=(0, 6))
        lbl_tg = tk.Label(tg_check_box, text="启用 Telegram Bot 消息推送", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_tg.pack(side="left")
        lbl_tg.bind("<Button-1>", lambda e: chk_tg.toggle())
        tg_check_box.bind("<Button-1>", lambda e: chk_tg.toggle())

        self._create_inline_btn(head_tg, "测试 Telegram", self._test_telegram).pack(side="right")

        self._create_compact_input(f_tg, "Bot Token:", self.var_tg_token, "已自动同步您的历史 Token")
        self._create_compact_input(f_tg, "Chat ID:", self.var_tg_chat, "例如: -1003820990608")
        self._create_compact_input(f_tg, "代理配置:", self.var_tg_proxy, "可选, 例如: 10808 或 http://127.0.0.1:10808")

        self._create_row_separator(c)

        # 2. 飞书
        f_fs = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        f_fs.pack(fill="x")

        head_fs = tk.Frame(f_fs, bg=self.C_CARD)
        head_fs.pack(fill="x", pady=(0, 8))

        fs_check_box = tk.Frame(head_fs, bg=self.C_CARD, cursor="hand2")
        fs_check_box.pack(side="left")
        chk_fs = ModernCheckmark(fs_check_box, variable=self.var_fs_enabled, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk_fs.pack(side="left", padx=(0, 6))
        lbl_fs = tk.Label(fs_check_box, text="启用飞书自定义机器人 (Feishu)", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_fs.pack(side="left")
        lbl_fs.bind("<Button-1>", lambda e: chk_fs.toggle())
        fs_check_box.bind("<Button-1>", lambda e: chk_fs.toggle())

        self._create_inline_btn(head_fs, "测试飞书", self._test_feishu).pack(side="right")

        self._create_compact_input(f_fs, "Webhook URL:", self.var_fs_url, "例如: https://open.feishu.cn/open-apis/bot/v2/hook/xxxx")

        self._create_row_separator(c)

        # 3. 企业微信
        f_wc = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        f_wc.pack(fill="x")

        head_wc = tk.Frame(f_wc, bg=self.C_CARD)
        head_wc.pack(fill="x", pady=(0, 8))

        wc_check_box = tk.Frame(head_wc, bg=self.C_CARD, cursor="hand2")
        wc_check_box.pack(side="left")
        chk_wc = ModernCheckmark(wc_check_box, variable=self.var_wc_enabled, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk_wc.pack(side="left", padx=(0, 6))
        lbl_wc = tk.Label(wc_check_box, text="启用企业微信群机器人 (WeCom)", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_wc.pack(side="left")
        lbl_wc.bind("<Button-1>", lambda e: chk_wc.toggle())
        wc_check_box.bind("<Button-1>", lambda e: chk_wc.toggle())

        self._create_inline_btn(head_wc, "测试企微", self._test_wecom).pack(side="right")

        self._create_compact_input(f_wc, "Webhook URL:", self.var_wc_url, "例如: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx")

    # -------------------------------------------------------------
    # 模块 7: 守护运行日志预览
    # -------------------------------------------------------------
    def _build_card_logs(self, parent):
        c = self._create_card(parent, "守护日志即时预览", "实时预览后台守护进程心跳与任务完成推送记录")

        h = tk.Frame(c, bg=self.C_CARD, padx=20, pady=8)
        h.pack(fill="x")

        self._create_inline_btn(h, "清空日志", self._clear_log).pack(side="right", padx=(6, 0))
        self._create_inline_btn(h, "刷新日志", self._refresh_log_preview).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            c,
            height=14,
            bg="#f9fafb",
            fg="#1e293b",
            insertbackground="#0f172a",
            font=self.font_mono_sm,
            relief="solid",
            bd=1,
            wrap="word",
            padx=10,
            pady=6
        )
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.txt_log.insert(tk.END, "正在载入运行日志...")
        self.after(50, self._refresh_log_preview)

    def _clear_log(self):
        """清空日志文件"""
        if messagebox.askyesno("清空日志确认", "确定要清空后台守护服务的历史运行日志吗？"):
            try:
                if LOG_FILE.exists():
                    LOG_FILE.write_text("", encoding="utf-8")
                self._refresh_log_preview()
                self.var_status_msg.set("运行日志已清空")
            except Exception as e:
                messagebox.showerror("清空失败", str(e))

    # -------------------------------------------------------------
    # 底部全局操作栏 (严格等高对齐设计，消除高低不一的问题)
    # -------------------------------------------------------------
    def _build_bottom_bar(self):
        self.footer_frame = tk.Frame(self, bg="#ffffff", height=54, padx=20, pady=9, highlightthickness=1, highlightbackground=self.C_BORDER)
        self.footer_frame.pack(fill="x", side="bottom")

        # 左侧：GitHub 专属图标与项目链接
        f_left = tk.Frame(self.footer_frame, bg="#ffffff", cursor="hand2")
        f_left.pack(side="left", anchor="center")

        if self.github_icon_img:
            lbl_gh_ico = tk.Label(f_left, image=self.github_icon_img, bg="#ffffff", cursor="hand2")
            lbl_gh_ico.pack(side="left", padx=(0, 6))
            lbl_gh_ico.bind("<Button-1>", lambda e: self._open_github())

        self.lbl_github = tk.Label(
            f_left,
            text="GitHub: akasls/Antigravity-Orbit",
            font=self.font_main,
            fg="#2563eb",
            bg="#ffffff",
            cursor="hand2"
        )
        self.lbl_github.pack(side="left")
        self.lbl_github.bind("<Button-1>", lambda e: self._open_github())
        self.lbl_github.bind("<Enter>", lambda e: self.lbl_github.configure(font=(self.FONT_FAMILY, 9, "underline")))
        self.lbl_github.bind("<Leave>", lambda e: self.lbl_github.configure(font=self.font_main))

        # 中间：操作状态提示文案
        self.lbl_msg = tk.Label(self.footer_frame, textvariable=self.var_status_msg, font=self.font_sm, fg=self.C_TEXT_MUTED, bg="#ffffff")
        self.lbl_msg.pack(side="left", padx=16, anchor="center")

        # 右侧：核心动作按钮组 (高度、字体、内边距严格等高统一)
        btn_box = tk.Frame(self.footer_frame, bg="#ffffff")
        btn_box.pack(side="right")

        self.btn_restore = self._create_action_btn(btn_box, "还原官方英文原版", self._on_click_restore, style_type="danger")
        self.btn_restore.pack(side="left", padx=4)

        self.btn_restart = self._create_action_btn(btn_box, "重启 Antigravity", self._on_click_restart_app, style_type="secondary")
        self.btn_restart.pack(side="left", padx=4)

        self.btn_apply = self._create_action_btn(btn_box, "保存并一键生效", self._on_click_save_and_apply, style_type="primary")
        self.btn_apply.pack(side="left", padx=(4, 0))

    def _open_github(self):
        """打开 GitHub 项目主页"""
        try:
            webbrowser.open("https://github.com/akasls/Antigravity-Orbit")
        except Exception as e:
            messagebox.showinfo("GitHub 地址", f"项目主页: https://github.com/akasls/Antigravity-Orbit\n\n({e})")

    # -------------------------------------------------------------
    # 统一按钮与卡片工厂组件 (保证高度、内边距、圆角与层次 100% 对齐)
    # -------------------------------------------------------------
    def _create_action_btn(self, parent, text: str, command, style_type="secondary"):
        """
        统一构建右下角核心操作按钮：
        - 保证高度、字体大小、文字基线与内外边距完全相同，消除尺寸不一致
        """
        font_spec = self.font_main
        pad_x = 16
        pad_y = 6

        if style_type == "primary":
            bg = self.C_ACCENT
            fg = "#ffffff"
            hover_bg = self.C_ACCENT_HOVER
            hover_fg = "#ffffff"
            border_col = self.C_ACCENT
        elif style_type == "danger":
            bg = "#ffffff"
            fg = self.C_DANGER
            hover_bg = "#fee2e2"
            hover_fg = "#991b1b"
            border_col = "#fca5a5"
        else: # secondary
            bg = "#ffffff"
            fg = "#334155"
            hover_bg = "#f1f5f9"
            hover_fg = "#0f172a"
            border_col = self.C_BTN_SEC_BORDER

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=font_spec,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=hover_fg,
            relief="solid",
            bd=1,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        return btn

    def _create_inline_btn(self, parent, text: str, command):
        """卡片内部行操作小按钮 (启动/停止/自启/测试)"""
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=self.font_sm,
            bg=self.C_BTN_SEC,
            fg=self.C_TEXT_MAIN,
            activebackground=self.C_BTN_SEC_HOVER,
            activeforeground=self.C_TEXT_MAIN,
            relief="solid",
            bd=1,
            padx=12,
            pady=3,
            cursor="hand2"
        )

    def _create_card(self, parent, title: str, subtitle: str = "") -> tk.Frame:
        """生成现代浅色高质感微圆角卡片"""
        c = tk.Frame(parent, bg=self.C_CARD, highlightthickness=1, highlightbackground=self.C_BORDER)
        c.pack(fill="x", pady=8)

        # 头部标题区
        h = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        h.pack(fill="x")

        tk.Label(h, text=title, font=self.font_title, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        if subtitle:
            tk.Label(h, text=subtitle, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        sep = tk.Frame(c, bg=self.C_BORDER, height=1)
        sep.pack(fill="x")
        return c

    def _create_row_separator(self, parent):
        sep = tk.Frame(parent, bg=self.C_SEP, height=1)
        sep.pack(fill="x", padx=20)

    def _create_checkbox_row(self, card, title: str, desc: str, variable: tk.BooleanVar, is_last: bool = False, command=None):
        """生成整行带 ModernCheckmark (✔) 联动响应的现代行"""
        row = tk.Frame(card, bg=self.C_CARD, padx=20, pady=11, cursor="hand2")
        row.pack(fill="x")

        left = tk.Frame(row, bg=self.C_CARD, cursor="hand2")
        left.pack(side="left", fill="both", expand=True)

        lbl_t = tk.Label(left, text=title, font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_t.pack(anchor="w")
        if desc:
            lbl_d = tk.Label(left, text=desc, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD, cursor="hand2")
            lbl_d.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(row, bg=self.C_CARD, cursor="hand2")
        right.pack(side="right", anchor="center")

        chk = ModernCheckmark(right, variable=variable, command=command, bg=self.C_CARD, font_family=self.FONT_FAMILY)
        chk.pack(side="left", padx=(0, 6))

        lbl_state = tk.Label(right, text="已启用", font=self.font_main, fg=self.C_TEXT_MAIN, bg=self.C_CARD, cursor="hand2")
        lbl_state.pack(side="left")

        # 绑定整行点击切换
        for w in [row, left, lbl_t, right, lbl_state]:
            w.bind("<Button-1>", lambda e: chk.toggle())
        if desc:
            lbl_d.bind("<Button-1>", lambda e: chk.toggle())

        if not is_last:
            self._create_row_separator(card)

    def _create_compact_input(self, parent, label_text: str, var, hint=""):
        row = tk.Frame(parent, bg=self.C_CARD, pady=4)
        row.pack(fill="x")

        tk.Label(row, text=label_text, width=13, anchor="w", font=self.font_sm_bold, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        e = tk.Entry(
            row,
            textvariable=var,
            bg="#f9fafb",
            fg=self.C_TEXT_MAIN,
            insertbackground="#0f172a",
            relief="solid",
            bd=1,
            font=self.font_mono
        )
        e.pack(side="left", fill="x", expand=True)
        if hint:
            tk.Label(row, text=hint, font=self.font_sm, fg=self.C_TEXT_DIM, bg=self.C_CARD).pack(side="left", padx=8)

    # -------------------------------------------------------------
    # 极速异步状态更新
    # -------------------------------------------------------------
    def _refresh_system_status_async(self):
        def _worker():
            loc = LocalizationManager.get_status(fast=True)
            port = self.var_daemon_port.get()
            is_running, pid = self._check_daemon_running(port)
            daemon_auto = AutostartManager.is_enabled()
            app_auto = AutostartManager.is_app_autostart_enabled()
            storage_info = None
            try:
                storage_info = StorageManager.get_storage_breakdown()
            except Exception:
                pass
            self.after(0, lambda: self._apply_status_to_ui(loc, is_running, pid, daemon_auto, app_auto, storage_info))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_status_to_ui(self, loc, is_running, pid, daemon_auto, app_auto, storage_info=None):
        if loc.get("installed"):
            install_dir = loc.get("install_dir", "")
            lang_label = "已汉化 (zh-CN)" if loc.get("is_localized") else "官方原版英文"
            self.var_stat_install.set(f"{lang_label} · 路径: {install_dir}")
            self.pill_install.configure(text=f"● {lang_label}", fg=self.C_GREEN, bg="#ecfdf5")
        else:
            self.var_stat_install.set("未自动检测到 Antigravity 安装目录")
            self.pill_install.configure(text="○ 未找到客户端", fg=self.C_DANGER, bg="#fef2f2")

        if is_running:
            self.var_stat_daemon.set(f"● 运行中 (监听端口: {self.var_daemon_port.get()}, PID: {pid})")
        else:
            self.var_stat_daemon.set("○ 未运行 (点击右侧启动守护可在任务完成后自动发送通知)")

        if daemon_auto:
            self.var_stat_autostart.set("● 已开启 (系统登录后自动在后台静默监听)")
        else:
            self.var_stat_autostart.set("○ 未开启 (关闭状态)")

        self.var_app_autostart.set(app_auto)
        self.var_stat_app_autostart.set("● 已开启" if app_auto else "○ 未开启")

        if storage_info:
            clean_mb = storage_info.get("cleanable_mb", 0)
            sess_cnt = storage_info.get("session_count", 0)
            if clean_mb >= 1024:
                size_str = f"{storage_info.get('cleanable_gb', 0):.2f} GB"
            else:
                size_str = f"{clean_mb:.1f} MB"
            self.var_stat_storage.set(f"可深度瘦身: {size_str} (含 Chromium 缓存与 {sess_cnt} 个会话的中间流日志)")

    def _on_clean_storage(self):
        """一键深度清理垃圾缓存与整理碎片"""
        if not messagebox.askyesno("深度瘦身确认", "即将清理 Chromium 静态渲染缓存、历史会话临时流日志并压缩整理数据库。\n\n此操作完全安全，不会删除您的任何对话记录、代码或配置。是否继续？"):
            return

        self._set_busy(True, "正在进行安全深度瘦身与缓存清理...")

        def _worker():
            try:
                freed, details = StorageManager.clean_storage(clean_cache=True, clean_temp_logs=True, vacuum_db=True)
                freed_mb = freed / (1024 * 1024)
                if freed_mb >= 1024:
                    size_str = f"{freed / (1024 * 1024 * 1024):.2f} GB"
                else:
                    size_str = f"{freed_mb:.1f} MB"
                msg = f"深度瘦身已完成！共成功释放磁盘空间 {size_str}。"

                def _done():
                    self._set_busy(False, msg)
                    self._refresh_system_status_async()
                    messagebox.showinfo("瘦身成功", msg)

                self.after(0, _done)
            except Exception as e:
                def _err():
                    self._set_busy(False, f"瘦身异常: {e}")
                    messagebox.showerror("瘦身失败", f"清理过程中发生异常:\n{e}")
                self.after(0, _err)

        threading.Thread(target=_worker, daemon=True).start()

    def _check_daemon_running(self, port: int):
        pid_file = BASE_DIR / ".daemon.pid"
        pid = None
        if pid_file.exists():
            try:
                pid = pid_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return False, None
        except socket.error:
            return True, pid or "活跃"

    def _refresh_log_preview(self):
        self.txt_log.delete("1.0", tk.END)
        if LOG_FILE.exists():
            try:
                lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                recent = "\n".join(lines[-35:]) if lines else "暂无日志记录"
                self.txt_log.insert(tk.END, recent)
                self.txt_log.see(tk.END)
            except Exception as e:
                self.txt_log.insert(tk.END, f"读取日志异常: {e}")
        else:
            self.txt_log.insert(tk.END, "日志文件尚未生成 (启动服务后将自动记录)")

    # -------------------------------------------------------------
    # 动作：保存与一键生效
    # -------------------------------------------------------------
    def _on_click_save_and_apply(self):
        self._set_busy(True, "正在保存配置并应用补丁...")

        def _worker():
            try:
                lang = self.var_language.get()
                self.cfg["close_to_tray"] = self.var_close_to_tray.get()
                self.cfg["app_autostart"] = self.var_app_autostart.get()

                self.cfg["customization"] = {
                    "language": lang,
                    "show_quota_badge": self.var_show_quota.get(),
                    "quota_refresh_interval": self.var_quota_interval.get(),
                    "hide_ide_buttons": self.var_hide_ide.get(),
                    "enable_gpu_acceleration": self.var_gpu_accel.get(),
                    "disable_background_throttling": self.var_unthrottle.get(),
                    "expand_v8_memory": self.var_v8_mem.get(),
                    "disable_telemetry": self.var_telemetry.get(),
                    "proxy_enabled": self.var_proxy_enabled.get(),
                    "proxy_url": self.var_proxy_url.get().strip(),
                    "disable_auto_update": self.var_disable_auto_update.get(),
                    "enable_smooth_scrolling": self.var_smooth_scrolling.get(),
                    "compact_ui_mode": self.var_compact_ui.get(),
                    "prune_guide_skills": self.var_prune_skills.get(),
                    "auto_retry_on_error": self.var_auto_retry.get(),
                    "max_retry_count": self.var_max_retry_count.get(),
                    "notify_on_quota_exhausted": self.var_notify_quota.get(),
                    "notify_on_max_retry_failed": self.var_notify_max_retry.get(),
                }

                if "channels" not in self.cfg:
                    self.cfg["channels"] = {}

                self.cfg["channels"]["telegram"] = {
                    "enabled": self.var_tg_enabled.get(),
                    "bot_token": self.var_tg_token.get().strip(),
                    "chat_id": self.var_tg_chat.get().strip(),
                    "proxy": self.var_tg_proxy.get().strip(),
                }

                self.cfg["channels"]["feishu"] = {
                    "enabled": self.var_fs_enabled.get(),
                    "webhook_url": self.var_fs_url.get().strip(),
                }

                self.cfg["channels"]["wecom"] = {
                    "enabled": self.var_wc_enabled.get(),
                    "webhook_url": self.var_wc_url.get().strip(),
                }

                self.cfg["lock_port"] = self.var_daemon_port.get()
                save_config(self.cfg)

                # 设置 Skills 裁剪状态
                try:
                    SkillsOptimizer.set_pruned(self.var_prune_skills.get())
                except Exception:
                    pass

                # 调用 LocalizationManager 部署补丁
                is_tw = (lang == "zh-TW")
                is_en = (lang == "en")
                ok, msg = LocalizationManager.install(tw=is_tw, en=is_en, stream_output=False)

                def _done():
                    self._set_busy(False, "配置与优化已成功生效！" if ok else "部分操作失败")
                    self._refresh_system_status_async()
                    if ok:
                        messagebox.showinfo("部署完成", "所有配置与优化补丁已成功部署生效！\n若 Antigravity 客户端未自动重启，请点击底部'重启客户端'。")
                    else:
                        messagebox.showerror("部署失败", f"部署遇到错误:\n{msg}")

                self.after(0, _done)

            except Exception as e:
                def _err():
                    self._set_busy(False, f"保存异常: {e}")
                    messagebox.showerror("错误", f"处理配置异常: {e}")
                self.after(0, _err)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 动作：还原官方原版英文
    # -------------------------------------------------------------
    def _on_click_restore(self):
        if not messagebox.askyesno("确认还原", "确定要还原 Antigravity 官方原版英文界面并卸载汉化补丁吗？"):
            return

        self._set_busy(True, "正在还原官方原版英文...")

        def _worker():
            ok, msg = LocalizationManager.restore(stream_output=False)
            def _done():
                self._set_busy(False, "官方英文原版已还原" if ok else "还原失败")
                self._refresh_system_status_async()
                if ok:
                    messagebox.showinfo("还原成功", "Antigravity 已恢复官方纯净原版备份！")
                else:
                    messagebox.showerror("还原失败", f"未能还原备份: {msg}")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 动作：重启客户端
    # -------------------------------------------------------------
    def _on_click_restart_app(self):
        self._set_busy(True, "正在重启 Antigravity 客户端...")

        def _worker():
            LocalizationManager.kill_running_antigravity()
            time.sleep(0.8)
            ok, msg = LocalizationManager.launch_antigravity()
            def _done():
                self._set_busy(False, "客户端已重新拉起" if ok else "未能拉起客户端")
                if not ok:
                    messagebox.showwarning("启动提醒", f"未能自动拉起客户端: {msg}\n请手动点击桌面图标启动 Antigravity。")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 守护服务管理
    # -------------------------------------------------------------
    def _start_daemon(self):
        port = self.var_daemon_port.get()
        is_running, _ = self._check_daemon_running(port)
        if is_running:
            messagebox.showinfo("提示", f"监控守护服务已在运行中 (端口 {port})。")
            return

        system = platform.system().lower()
        if system == "windows":
            main_py = PROJECT_ROOT / "main.py"
            py_exe = sys.executable
            if getattr(sys, "frozen", False):
                cmd = [str(sys.executable), "run"]
            else:
                pyw = Path(py_exe).parent / "pythonw.exe"
                launcher = str(pyw) if pyw.exists() else py_exe
                cmd = [launcher, str(main_py), "run"]

            try:
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
                time.sleep(0.5)
                self.var_status_msg.set("监控守护服务已启动")
                self._refresh_system_status_async()
            except Exception as e:
                messagebox.showerror("启动失败", f"无法启动常驻服务: {e}")
        else:
            messagebox.showinfo("提示", "Unix/macOS 请使用后台命令: python3 main.py start")

    def _stop_daemon(self):
        pid_file = BASE_DIR / ".daemon.pid"
        stopped = False
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
                if platform.system().lower() == "windows":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, 15)
                stopped = True
            except Exception:
                pass
            try:
                pid_file.unlink()
            except Exception:
                pass

        time.sleep(0.3)
        self.var_status_msg.set("监控守护服务已停止" if stopped else "守护服务未运行")
        self._refresh_system_status_async()

    # -------------------------------------------------------------
    # 自启动管理
    # -------------------------------------------------------------
    def _enable_autostart(self):
        ok, msg = AutostartManager.enable()
        if ok:
            messagebox.showinfo("成功", "已启用 Windows 开机自启动。")
        else:
            messagebox.showerror("失败", f"设置自启动失败: {msg}")
        self._refresh_system_status_async()

    def _disable_autostart(self):
        ok, msg = AutostartManager.disable()
        if ok:
            messagebox.showinfo("成功", "已关闭开机自启动。")
        else:
            messagebox.showerror("失败", f"取消自启动失败: {msg}")
        self._refresh_system_status_async()

    # -------------------------------------------------------------
    # 通道测试
    # -------------------------------------------------------------
    def _test_telegram(self):
        from notifiers import TelegramNotifier
        token = self.var_tg_token.get().strip()
        chat_id = self.var_tg_chat.get().strip()
        proxy = self.var_tg_proxy.get().strip()
        if not token or not chat_id:
            messagebox.showwarning("缺少参数", "请先填写 Telegram Bot Token 与 Chat ID！")
            return

        self._set_busy(True, "正在发送 Telegram 测试消息...")
        def _worker():
            n = TelegramNotifier(token, chat_id, proxy=proxy or None)
            ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的 Telegram 测试通知！")
            def _done():
                self._set_busy(False, "Telegram 测试成功！" if ok else f"发送失败: {err}")
                if ok:
                    messagebox.showinfo("测试成功", "Telegram 消息发送成功！请检查手机或客户端。")
                else:
                    messagebox.showerror("测试失败", f"Telegram 发送失败:\n{err}")
            self.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def _test_feishu(self):
        from notifiers import FeishuNotifier
        url = self.var_fs_url.get().strip()
        if not url:
            messagebox.showwarning("缺少参数", "请先填写飞书 Webhook 地址！")
            return

        self._set_busy(True, "正在发送飞书测试消息...")
        def _worker():
            n = FeishuNotifier(url)
            ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的飞书机器人测试通知！")
            def _done():
                self._set_busy(False, "飞书测试成功！" if ok else f"发送失败: {err}")
                if ok:
                    messagebox.showinfo("测试成功", "飞书消息发送成功！请查看对应飞书群。")
                else:
                    messagebox.showerror("测试失败", f"飞书发送失败:\n{err}")
            self.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def _test_wecom(self):
        from notifiers import WeComNotifier
        url = self.var_wc_url.get().strip()
        if not url:
            messagebox.showwarning("缺少参数", "请先填写企业微信 Webhook 地址！")
            return

        self._set_busy(True, "正在发送企业微信测试消息...")
        def _worker():
            n = WeComNotifier(url)
            ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的企业微信机器人测试通知！")
            def _done():
                self._set_busy(False, "企微测试成功！" if ok else f"发送失败: {err}")
                if ok:
                    messagebox.showinfo("测试成功", "企业微信消息发送成功！请查看对应群聊。")
                else:
                    messagebox.showerror("测试失败", f"企业微信发送失败:\n{err}")
            self.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def _set_busy(self, busy: bool, msg: str = ""):
        if msg:
            self.var_status_msg.set(msg)
        state = "disabled" if busy else "normal"
        self.btn_apply.configure(state=state)
        self.btn_restore.configure(state=state)
        self.btn_restart.configure(state=state)


def launch_gui(start_in_tray: bool = False):
    """桌面可视化管理中心统一启动入口"""
    app = ModernOrbitApp(start_in_tray=start_in_tray)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
