"""
Antigravity Orbit - 独立桌面客户端管理中心 (Native Desktop GUI Client)
极简现代浅色单页设计，对齐 macOS / Fluent 视觉规范
按钮规格严格等高对齐，无多级菜单，无多余顶栏标题
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
    """Antigravity Orbit 极简现代浅色桌面管理中心"""

    def __init__(self):
        super().__init__()
        self.title("Antigravity Orbit")
        self.geometry("940x760")
        self.minsize(860, 640)

        # 1. 严格使用电脑自带原生系统字体 (无需外挂任何自定义字体)
        self._init_system_fonts()
        self._center_window(940, 760)
        self._init_theme_colors()

        # 2. 原生秒载图标 (零 PIL 依赖，启动提速)
        self._setup_app_icons()

        # 读取用户配置 (多级路径智能嗅探)
        self.cfg = load_config()
        self._init_variables()
        self._setup_ttk_styles()

        # 构建单页平铺流式布局 (无多级菜单，无多余顶栏标题)
        self._build_single_page_layout()

        # 异步非阻塞环境刷新 (零卡顿秒开)
        self.after(20, self._refresh_system_status_async)

    def _init_system_fonts(self):
        """严格使用电脑自带原生系统字体 (Windows: 微软雅黑 / macOS: 苹方 / 系统默认)，不使用自定义字体"""
        sys_font_family = ""
        try:
            import tkinter.font as tkfont
            sys_font_family = tkfont.nametofont("TkDefaultFont").cget("family")
        except Exception:
            pass

        if sys.platform.startswith("win"):
            # Windows 电脑自带系统原生界面字体: 微软雅黑 (Microsoft YaHei UI)
            self.FONT_FAMILY = sys_font_family if sys_font_family in ["Microsoft YaHei UI", "Microsoft YaHei"] else "Microsoft YaHei UI"
            self.FONT_MONO = "Consolas"
        elif sys.platform.startswith("darwin"):
            # macOS 电脑自带系统字体: 苹方 / 系统默认
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
        self.font_mono = (self.FONT_MONO, 9)
        self.font_mono_sm = (self.FONT_MONO, 8)

        # 注入 Tk 全局字体库规则
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
        self.C_CARD = "#ffffff"           # 卡片纯白底色
        self.C_BORDER = "#e2e8f0"         # 边框细线 (Slate-200)
        self.C_SEP = "#f1f5f9"            # 行内弱分隔线 (Slate-100)
        self.C_HOVER = "#f8fafc"          # 悬停轻灰

        self.C_TEXT_MAIN = "#0f172a"      # 主要文字 (深墨黑，高对比清晰度)
        self.C_TEXT_MUTED = "#475569"     # 次要描述文字 (Slate-600)
        self.C_TEXT_DIM = "#94a3b8"       # 提示弱说明文字 (Slate-400)

        self.C_ACCENT = "#2563eb"         # 系统级宝蓝 (Blue-600)
        self.C_ACCENT_HOVER = "#1d4ed8"   # 宝蓝悬停 (Blue-700)
        self.C_BTN_SEC = "#ffffff"        # 次级按钮底色
        self.C_BTN_SEC_BORDER = "#cbd5e1" # 次级按钮描边 (Slate-300)
        self.C_BTN_SEC_HOVER = "#f1f5f9"  # 次级按钮悬停

        self.C_GREEN = "#16a34a"          # 正常色 (Green-600)
        self.C_GRAY = "#94a3b8"           # 未运行/未启用色 (Slate-400)
        self.C_DANGER = "#dc2626"         # 警告红色 (Red-600)

        self.configure(bg=self.C_BG)

    def _setup_app_icons(self):
        """设置窗口与任务栏图标 (纯原生 Tkinter PhotoImage 载入，0 外部依赖，秒开启动)"""
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

        # 界面与外观
        self.var_language = tk.StringVar(value=custom.get("language", "zh-CN"))
        self.var_show_quota = tk.BooleanVar(value=custom.get("show_quota_badge", True))
        self.var_quota_interval = tk.IntVar(value=custom.get("quota_refresh_interval", 60))
        self.var_hide_ide = tk.BooleanVar(value=custom.get("hide_ide_buttons", True))

        # 性能与隐私
        self.var_gpu_accel = tk.BooleanVar(value=custom.get("enable_gpu_acceleration", True))
        self.var_unthrottle = tk.BooleanVar(value=custom.get("disable_background_throttling", True))
        self.var_v8_mem = tk.BooleanVar(value=custom.get("expand_v8_memory", True))
        self.var_telemetry = tk.BooleanVar(value=custom.get("disable_telemetry", True))

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
    # 单页平铺流式布局构建 (全部一页，无多级菜单，无多余顶栏标题)
    # -------------------------------------------------------------
    def _build_single_page_layout(self):
        # 1. 中间可滚动的主面板 (全功能平铺)
        self._build_scroll_content()

        # 2. 底部全局操作栏 (附带左下角 GitHub 跳转与严格等高对齐的操作按钮)
        self._build_bottom_bar()

    def _build_scroll_content(self):
        container = tk.Frame(self, bg=self.C_BG)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=self.C_BG, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.C_BG, padx=22, pady=16)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 依次构建各功能卡片
        self._build_card_system_status(self.scrollable_frame)
        self._build_card_localization(self.scrollable_frame)
        self._build_card_performance(self.scrollable_frame)
        self._build_card_notifications(self.scrollable_frame)
        self._build_card_logs(self.scrollable_frame)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    # -------------------------------------------------------------
    # 卡片 1: 客户端状态与服务管理 (宽敞独立行，解决遮挡问题)
    # -------------------------------------------------------------
    def _build_card_system_status(self, parent):
        c = self._create_card(parent, "客户端与后台守护服务", "检测 Antigravity 本地安装状态、管理后台常驻守护与开机自启动")

        # 行 1: 客户端本地安装与汉化状态
        r_client = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_client.pack(fill="x")

        left_c = tk.Frame(r_client, bg=self.C_CARD)
        left_c.pack(side="left", fill="x", expand=True)
        tk.Label(left_c, text="Antigravity 客户端:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left_c, textvariable=self.var_stat_install, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        self.pill_install = tk.Label(r_client, text="检测中...", font=self.font_sm_bold, fg="#1e293b", bg="#f1f5f9", padx=10, pady=4)
        self.pill_install.pack(side="right")

        self._create_row_separator(c)

        # 行 2: 后台常驻监听服务 (独立行，空间充足)
        r_daemon = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_daemon.pack(fill="x")

        left_d = tk.Frame(r_daemon, bg=self.C_CARD)
        left_d.pack(side="left", fill="x", expand=True)

        d_title_row = tk.Frame(left_d, bg=self.C_CARD)
        d_title_row.pack(anchor="w")
        tk.Label(d_title_row, text="任务完成守护监听:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left")

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

        # 行 3: 系统开机自启动 (完全独立行，确保“关闭自启”按钮 100% 完整显示，绝不遮挡)
        r_auto = tk.Frame(c, bg=self.C_CARD, padx=20, pady=12)
        r_auto.pack(fill="x")

        left_a = tk.Frame(r_auto, bg=self.C_CARD)
        left_a.pack(side="left", fill="x", expand=True)
        tk.Label(left_a, text="系统开机自动启动:", font=self.font_main_bold, fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left_a, textvariable=self.var_stat_autostart, font=self.font_sm, fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        # 右侧操作按钮组 (间距充足，绝不截断)
        right_a = tk.Frame(r_auto, bg=self.C_CARD)
        right_a.pack(side="right")
        self._create_inline_btn(right_a, "开启自启", self._enable_autostart).pack(side="left", padx=(0, 6))
        self._create_inline_btn(right_a, "关闭自启", self._disable_autostart).pack(side="left")

    # -------------------------------------------------------------
    # 卡片 2: 界面汉化与外观设置
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
            variable=self.var_hide_ide,
            is_last=True
        )

    # -------------------------------------------------------------
    # 卡片 3: 性能极限加速与顶栏额度
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

        # Checkmark
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
            title="全栈切断遥测数据回传 (Anti-Telemetry)",
            desc="关闭 Language Server 指标收集、Chromium 诊断与 DevTools 日志上报",
            variable=self.var_telemetry,
            is_last=True
        )

    # -------------------------------------------------------------
    # 卡片 4: 消息通知推送渠道
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
    # 卡片 5: 运行日志预览
    # -------------------------------------------------------------
    def _build_card_logs(self, parent):
        c = self._create_card(parent, "守护日志即时预览", "实时预览后台守护进程心跳与任务完成推送记录")

        h = tk.Frame(c, bg=self.C_CARD, padx=20, pady=8)
        h.pack(fill="x")
        self._create_inline_btn(h, "刷新日志", self._refresh_log_preview).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            c,
            height=5,
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
        # 异步非阻塞载入日志，确保主窗口零卡顿瞬时弹出
        self.after(50, self._refresh_log_preview)

    # -------------------------------------------------------------
    # 底部全局操作栏 (严格等高对齐设计，消除高低不一的问题)
    # -------------------------------------------------------------
    def _build_bottom_bar(self):
        self.footer_frame = tk.Frame(self, bg="#ffffff", height=56, padx=20, pady=10, highlightthickness=1, highlightbackground=self.C_BORDER)
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

        # 统一使用 _create_action_btn 构建，消除高低不一与粗细差异
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
        - style_type:
            - "primary": 现代宝蓝底色 + 白字
            - "secondary": 纯白底色 + 浅灰细边 + 深灰字
            - "danger": 纯白底色 + 浅红细边 + 红字
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
        """生成现代浅色高质感微圆角卡片 (无老旧深灰条纹，无粗糙线框)"""
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

    def _create_checkbox_row(self, card, title: str, desc: str, variable: tk.BooleanVar, is_last: bool = False):
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

        chk = ModernCheckmark(right, variable=variable, bg=self.C_CARD, font_family=self.FONT_FAMILY)
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
            auto_enabled = AutostartManager.is_enabled()
            self.after(0, lambda: self._apply_status_to_ui(loc, is_running, pid, auto_enabled))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_status_to_ui(self, loc, is_running, pid, auto_enabled):
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

        if auto_enabled:
            self.var_stat_autostart.set("● 已开启 (系统登录后自动在后台静默运行)")
        else:
            self.var_stat_autostart.set("○ 未开启 (关闭状态)")

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
                recent = "\n".join(lines[-25:]) if lines else "暂无日志记录"
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
                self.cfg["customization"] = {
                    "language": lang,
                    "show_quota_badge": self.var_show_quota.get(),
                    "quota_refresh_interval": self.var_quota_interval.get(),
                    "hide_ide_buttons": self.var_hide_ide.get(),
                    "enable_gpu_acceleration": self.var_gpu_accel.get(),
                    "disable_background_throttling": self.var_unthrottle.get(),
                    "expand_v8_memory": self.var_v8_mem.get(),
                    "disable_telemetry": self.var_telemetry.get(),
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


def launch_gui():
    """桌面可视化管理中心统一启动入口"""
    app = ModernOrbitApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
