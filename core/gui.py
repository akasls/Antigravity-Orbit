"""
Antigravity Orbit - 独立桌面客户端管理中心 (Native Desktop GUI Client)
极简现代浅色设计风格 (Light Modern Theme)，无多级菜单，单页平铺流式布局
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
)
from core.localization import LocalizationManager
from core.autostart import AutostartManager


class CheckmarkBox(tk.Frame):
    """
    自绘现代复选框组件：
    - 选中状态：醒目高对比蓝底白字 ✔ (Unicode \u2714)
    - 未选状态：清爽浅灰边框白色空框
    彻底解决 ttk 原生主题在不同操作系统下无勾选或仅显示方块的问题
    """

    def __init__(self, parent, variable: tk.BooleanVar, text: str = "", command=None, bg="#ffffff", fg="#0f172a"):
        super().__init__(parent, bg=bg, cursor="hand2")
        self.variable = variable
        self.command = command
        self.bg_color = bg

        # 边框方块指示器
        self.box = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9, "bold"),
            width=2,
            height=1,
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        self.box.pack(side="left", padx=(0, 6))

        # 文本标签
        if text:
            self.lbl = tk.Label(
                self,
                text=text,
                font=("Segoe UI", 9),
                fg=fg,
                bg=bg,
                cursor="hand2"
            )
            self.lbl.pack(side="left")
            self.lbl.bind("<Button-1>", lambda e: self.toggle())

        self.box.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Button-1>", lambda e: self.toggle())

        # 追踪变量变化
        self.variable.trace_add("write", lambda *_: self._update_view())
        self._update_view()

    def toggle(self):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _update_view(self):
        is_checked = self.variable.get()
        if is_checked:
            self.box.configure(
                text="✔",
                bg="#2563eb",
                fg="#ffffff",
                highlightthickness=1,
                highlightbackground="#1d4ed8",
                highlightcolor="#1d4ed8"
            )
        else:
            self.box.configure(
                text=" ",
                bg="#ffffff",
                fg="#2563eb",
                highlightthickness=1,
                highlightbackground="#cbd5e1",
                highlightcolor="#94a3b8"
            )


class ModernOrbitApp(tk.Tk):
    """Antigravity Orbit 极简现代浅色桌面管理中心"""

    def __init__(self):
        super().__init__()
        self.title("Antigravity Orbit - 管理中心")
        self.geometry("960x780")
        self.minsize(880, 680)

        self._center_window(960, 780)
        self._init_theme_colors()

        # 加载应用图标
        self._setup_app_icons()

        self.cfg = load_config()
        self._init_variables()
        self._setup_ttk_styles()

        # 构建单页平铺流式布局
        self._build_single_page_layout()

        # 极速秒级异步状态刷新 (窗口先行渲染，后台线程零阻塞刷新)
        self.after(30, self._refresh_system_status_async)

    def _center_window(self, width, height):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, int((sw - width) / 2))
            y = max(0, int((sh - height) / 2) - 30)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _init_theme_colors(self):
        """现代浅色主题调色盘 (Slate / Zinc 风格规范)"""
        self.C_BG = "#f8fafc"             # 页面浅灰底色
        self.C_CARD = "#ffffff"           # 卡片纯白底色
        self.C_CARD_BORDER = "#e2e8f0"    # 卡片边框浅灰
        self.C_SEP = "#f1f5f9"            # 内部行分割线
        self.C_HOVER = "#f1f5f9"          # 悬停轻灰

        self.C_TEXT_MAIN = "#0f172a"      # 主要文字 (深墨黑，高对比清晰度)
        self.C_TEXT_MUTED = "#475569"     # 次要描述文字
        self.C_TEXT_DIM = "#94a3b8"       # 浅灰弱化说明

        self.C_ACCENT = "#2563eb"         # 现代高雅宝蓝 (主按钮/主动作)
        self.C_ACCENT_HOVER = "#1d4ed8"   # 宝蓝悬停加深
        self.C_BTN_SEC = "#ffffff"        # 次级按钮纯白背景
        self.C_BTN_SEC_BORDER = "#cbd5e1" # 次级按钮边框
        self.C_BTN_SEC_HOVER = "#f8fafc"  # 次级按钮悬停

        self.C_GREEN = "#16a34a"          # 运行中正常色 (Green-600)
        self.C_GRAY = "#94a3b8"           # 离线或停止色 (Slate-400)
        self.C_DANGER = "#dc2626"         # 警告/还原红色

        self.configure(bg=self.C_BG)

    def _setup_app_icons(self):
        """设置窗口与任务栏图标"""
        icon_ico = RESOURCE_DIR / "resources" / "icon.ico"
        icon_png = RESOURCE_DIR / "resources" / "icon.png"

        if icon_ico.exists():
            try:
                self.iconbitmap(str(icon_ico))
            except Exception:
                pass

        self.app_icon_img = None
        if icon_png.exists():
            try:
                from PIL import Image, ImageTk
                im = Image.open(icon_png).resize((32, 32), Image.Resampling.LANCZOS)
                self.app_icon_img = ImageTk.PhotoImage(im)
                self.iconphoto(True, self.app_icon_img)
            except Exception:
                pass

        self.github_icon_img = None
        gh_png = RESOURCE_DIR / "resources" / "github.png"
        if gh_png.exists():
            try:
                from PIL import Image, ImageTk
                im_gh = Image.open(gh_png).resize((16, 16), Image.Resampling.LANCZOS)
                self.github_icon_img = ImageTk.PhotoImage(im_gh)
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

        # 通知通道
        tg = self.cfg.get("channels", {}).get("telegram", {})
        self.var_tg_enabled = tk.BooleanVar(value=tg.get("enabled", False))
        self.var_tg_token = tk.StringVar(value=tg.get("bot_token", ""))
        self.var_tg_chat = tk.StringVar(value=tg.get("chat_id", ""))
        self.var_tg_proxy = tk.StringVar(value=tg.get("proxy", ""))

        fs = self.cfg.get("channels", {}).get("feishu", {})
        self.var_fs_enabled = tk.BooleanVar(value=fs.get("enabled", False))
        self.var_fs_url = tk.StringVar(value=fs.get("webhook_url", ""))

        wc = self.cfg.get("channels", {}).get("wecom", {})
        self.var_wc_enabled = tk.BooleanVar(value=wc.get("enabled", False))
        self.var_wc_url = tk.StringVar(value=wc.get("webhook_url", ""))

        # 监控常驻
        self.var_daemon_port = tk.IntVar(value=self.cfg.get("lock_port", 49222))

        # 状态显示
        self.var_status_msg = tk.StringVar(value="就绪")
        self.var_stat_install = tk.StringVar(value="正在快速检测...")
        self.var_stat_daemon = tk.StringVar(value="正在快速检测...")
        self.var_stat_autostart = tk.StringVar(value="正在快速检测...")

    def _setup_ttk_styles(self):
        """定制 ttk 控件以适应浅色主题"""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("TFrame", background=self.C_BG)
        self.style.configure("Card.TFrame", background=self.C_CARD)

        # 单选框
        self.style.configure(
            "Clean.TRadiobutton",
            background=self.C_CARD,
            foreground=self.C_TEXT_MAIN,
            font=("Segoe UI", 9),
            padding=2
        )
        self.style.map(
            "Clean.TRadiobutton",
            background=[("active", self.C_CARD)],
            indicatorcolor=[("selected", self.C_ACCENT), ("active", "#93c5fd")]
        )

        # 下拉框
        self.style.configure(
            "Clean.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=self.C_TEXT_MAIN,
            selectbackground=self.C_ACCENT,
            selectforeground="#ffffff",
            padding=3
        )

    # -------------------------------------------------------------
    # 单页平铺流式布局构建 (全部一页，无多级菜单)
    # -------------------------------------------------------------
    def _build_single_page_layout(self):
        # 1. 顶部 Header
        self._build_top_header()

        # 2. 中间可滚动区域 (包含全部配置卡片)
        self._build_scroll_content()

        # 3. 底部吸底全局状态栏
        self._build_bottom_bar()

    def _build_top_header(self):
        header = tk.Frame(self, bg="#ffffff", height=60, padx=24, pady=12, highlightthickness=1, highlightbackground=self.C_CARD_BORDER)
        header.pack(fill="x", side="top")

        # 左侧应用 Logo 与标题
        left = tk.Frame(header, bg="#ffffff")
        left.pack(side="left", anchor="center")

        if self.app_icon_img:
            lbl_ico = tk.Label(left, image=self.app_icon_img, bg="#ffffff")
            lbl_ico.pack(side="left", padx=(0, 10))

        title_box = tk.Frame(left, bg="#ffffff")
        title_box.pack(side="left")

        title_row = tk.Frame(title_box, bg="#ffffff")
        title_row.pack(anchor="w")
        tk.Label(title_row, text="Antigravity Orbit", font=("Segoe UI", 13, "bold"), fg=self.C_TEXT_MAIN, bg="#ffffff").pack(side="left")
        
        # 标签 Pill
        pill = tk.Label(title_row, text="v2.3", font=("Segoe UI", 8, "bold"), fg=self.C_ACCENT, bg="#eff6ff", padx=6, pady=1)
        pill.pack(side="left", padx=8)

        tk.Label(title_box, text="一站式客户端汉化、性能优化、顶栏额度与长任务通知管理中心", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg="#ffffff").pack(anchor="w", pady=(1, 0))

        # 右侧快速状态指示
        right = tk.Frame(header, bg="#ffffff")
        right.pack(side="right", anchor="center")

        # 客户端状态 Pill
        self.pill_install = tk.Label(right, textvariable=self.var_stat_install, font=("Segoe UI", 8), fg="#1e293b", bg="#f1f5f9", padx=10, pady=4)
        self.pill_install.pack(side="left", padx=4)

        # 监控状态 Pill
        self.pill_daemon = tk.Label(right, textvariable=self.var_stat_daemon, font=("Segoe UI", 8), fg="#1e293b", bg="#f1f5f9", padx=10, pady=4)
        self.pill_daemon.pack(side="left", padx=4)

    def _build_scroll_content(self):
        """中间垂直滚动的单页内容流"""
        container = tk.Frame(self, bg=self.C_BG)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=self.C_BG, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.C_BG, padx=24, pady=16)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)

        # 保持窗口宽度自适应
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # 绑定鼠标滚轮
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 依次加载平铺卡片（全部在一页内呈现）
        self._build_card_overview(self.scrollable_frame)
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
    # 卡片 1: 运行状态与服务管理
    # -------------------------------------------------------------
    def _build_card_overview(self, parent):
        c = self._create_card(parent, "核心运行状态与服务管理", "实时监视 Antigravity 客户端及后台守护进程状态")

        row = tk.Frame(c, bg=self.C_CARD, padx=16, pady=12)
        row.pack(fill="x")

        # 守护服务操作
        f_daemon = tk.Frame(row, bg=self.C_CARD)
        f_daemon.pack(side="left", fill="x", expand=True)

        tk.Label(f_daemon, text="后台常驻监听服务:", font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left")
        tk.Label(f_daemon, textvariable=self.var_stat_daemon, font=("Segoe UI", 9), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(6, 16))

        tk.Label(f_daemon, text="端口:", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        e_port = tk.Entry(f_daemon, textvariable=self.var_daemon_port, width=6, bg="#ffffff", fg=self.C_TEXT_MAIN, relief="solid", bd=1)
        e_port.pack(side="left", padx=(4, 12))

        self._create_outline_btn(f_daemon, "启动守护", self._start_daemon).pack(side="left", padx=3)
        self._create_outline_btn(f_daemon, "停止守护", self._stop_daemon).pack(side="left", padx=3)

        # 自启操作
        f_auto = tk.Frame(row, bg=self.C_CARD)
        f_auto.pack(side="right")

        tk.Label(f_auto, text="开机自启:", font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left")
        tk.Label(f_auto, textvariable=self.var_stat_autostart, font=("Segoe UI", 9), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(6, 12))
        self._create_outline_btn(f_auto, "开启", self._enable_autostart).pack(side="left", padx=3)
        self._create_outline_btn(f_auto, "关闭", self._disable_autostart).pack(side="left", padx=3)

    # -------------------------------------------------------------
    # 卡片 2: 界面汉化与外观设置
    # -------------------------------------------------------------
    def _build_card_localization(self, parent):
        c = self._create_card(parent, "界面汉化与外观净化", "全量汉化菜单、对话列表与设置项，并净化多余按钮")

        # 语言单选组
        r_lang = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        r_lang.pack(fill="x")

        tk.Label(r_lang, text="客户端语言选择:", font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w", pady=(0, 6))

        rb_box = tk.Frame(r_lang, bg=self.C_CARD)
        rb_box.pack(fill="x")

        ttk.Radiobutton(
            rb_box,
            text="简体中文 (zh-CN) [推荐]",
            variable=self.var_language,
            value="zh-CN",
            style="Clean.TRadiobutton"
        ).pack(side="left", padx=(0, 20))

        ttk.Radiobutton(
            rb_box,
            text="繁体中文 (zh-TW)",
            variable=self.var_language,
            value="zh-TW",
            style="Clean.TRadiobutton"
        ).pack(side="left", padx=(0, 20))

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
            desc="彻底隐藏右上角多余的 'Open IDE' 与 'Install IDE' 及其容器，使顶栏界面干净紧凑",
            variable=self.var_hide_ide,
            is_last=True
        )

    # -------------------------------------------------------------
    # 卡片 3: 极限性能加速与顶栏额度
    # -------------------------------------------------------------
    def _build_card_performance(self, parent):
        c = self._create_card(parent, "性能加速与实时额度胶囊", "底层 Chromium 硬件栅格化、后台防休眠降频与顶栏模型配额")

        # 顶栏额度胶囊
        r_quota = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        r_quota.pack(fill="x")

        left = tk.Frame(r_quota, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="顶栏模型配额胶囊", font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        tk.Label(left, text="在 Antigravity 标题栏右上角常驻呈现 5小时 / 每周 模型限额百分比与健康指示灯", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(r_quota, bg=self.C_CARD)
        right.pack(side="right", anchor="center")

        tk.Label(right, text="刷新间隔:", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 4))
        cb_interval = ttk.Combobox(right, textvariable=self.var_quota_interval, values=[30, 60, 120, 300], width=5, state="readonly", style="Clean.TCombobox")
        cb_interval.pack(side="left", padx=(0, 12))
        tk.Label(right, text="秒", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left", padx=(0, 16))

        CheckmarkBox(right, variable=self.var_show_quota, text="启用显示", bg=self.C_CARD, fg=self.C_TEXT_MAIN).pack(side="left")

        self._create_row_separator(c)

        # 性能加速勾选项
        self._create_checkbox_row(
            c,
            title="GPU 显卡硬件栅格化与零拷贝渲染 (Zero-Copy Rasterization)",
            desc="大幅降低 AI 流式输出时的 CPU 占用与界面渲染开销，输入输出更加丝滑",
            variable=self.var_gpu_accel
        )

        self._create_checkbox_row(
            c,
            title="解除后台调度降频 (Disable Background Throttling)",
            desc="切换至其他窗口时防止 Electron 定时器降频至 1Hz，保障长对话任务后台满速执行",
            variable=self.var_unthrottle
        )

        self._create_checkbox_row(
            c,
            title="V8 引擎内存扩容至 4GB (--max-old-space-size=4096)",
            desc="消除超大工程分析与上百轮长对话下的 V8 垃圾回收卡顿与内存溢出崩溃",
            variable=self.var_v8_mem
        )

        self._create_checkbox_row(
            c,
            title="全栈切断遥测数据回传 (Anti-Telemetry)",
            desc="阻断 Language Server 性能指标上报、Chromium 崩溃诊断与 DevTools 日志收集",
            variable=self.var_telemetry,
            is_last=True
        )

    # -------------------------------------------------------------
    # 卡片 4: 即时通知渠道配置
    # -------------------------------------------------------------
    def _build_card_notifications(self, parent):
        c = self._create_card(parent, "消息通知推送渠道", "长跑任务、构建或对话完成时自动推送即时通知到手机或电脑")

        # 1. Telegram
        f_tg = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        f_tg.pack(fill="x")

        head_tg = tk.Frame(f_tg, bg=self.C_CARD)
        head_tg.pack(fill="x", pady=(0, 6))
        CheckmarkBox(head_tg, variable=self.var_tg_enabled, text="启用 Telegram Bot 通知", bg=self.C_CARD, fg=self.C_TEXT_MAIN).pack(side="left")
        self._create_outline_btn(head_tg, "测试 Telegram", self._test_telegram).pack(side="right")

        self._create_compact_input(f_tg, "Bot Token:", self.var_tg_token, "例如: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        self._create_compact_input(f_tg, "Chat ID:", self.var_tg_chat, "例如: 123456789")
        self._create_compact_input(f_tg, "代理地址:", self.var_tg_proxy, "可选, 例如: http://127.0.0.1:7890 (国内网络建议配置)")

        self._create_row_separator(c)

        # 2. 飞书
        f_fs = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        f_fs.pack(fill="x")

        head_fs = tk.Frame(f_fs, bg=self.C_CARD)
        head_fs.pack(fill="x", pady=(0, 6))
        CheckmarkBox(head_fs, variable=self.var_fs_enabled, text="启用飞书自定义机器人 (Feishu)", bg=self.C_CARD, fg=self.C_TEXT_MAIN).pack(side="left")
        self._create_outline_btn(head_fs, "测试飞书", self._test_feishu).pack(side="right")

        self._create_compact_input(f_fs, "Webhook URL:", self.var_fs_url, "例如: https://open.feishu.cn/open-apis/bot/v2/hook/xxxx")

        self._create_row_separator(c)

        # 3. 企业微信
        f_wc = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        f_wc.pack(fill="x")

        head_wc = tk.Frame(f_wc, bg=self.C_CARD)
        head_wc.pack(fill="x", pady=(0, 6))
        CheckmarkBox(head_wc, variable=self.var_wc_enabled, text="启用企业微信群机器人 (WeCom)", bg=self.C_CARD, fg=self.C_TEXT_MAIN).pack(side="left")
        self._create_outline_btn(head_wc, "测试企微", self._test_wecom).pack(side="right")

        self._create_compact_input(f_wc, "Webhook URL:", self.var_wc_url, "例如: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx")

    # -------------------------------------------------------------
    # 卡片 5: 运行日志预览
    # -------------------------------------------------------------
    def _build_card_logs(self, parent):
        c = self._create_card(parent, "监控日志预览", "实时预览后台守护服务的心跳与任务推送记录")

        h = tk.Frame(c, bg=self.C_CARD, padx=16, pady=6)
        h.pack(fill="x")
        self._create_outline_btn(h, "刷新日志", self._refresh_log_preview).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            c,
            height=5,
            bg="#f8fafc",
            fg="#1e293b",
            insertbackground="#0f172a",
            font=("Consolas", 8),
            relief="solid",
            bd=1,
            wrap="word",
            padx=10,
            pady=6
        )
        self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._refresh_log_preview()

    # -------------------------------------------------------------
    # 底部全局操作栏 (包含左下角 GitHub 跳转与主要动作按钮)
    # -------------------------------------------------------------
    def _build_bottom_bar(self):
        self.footer_frame = tk.Frame(self, bg="#ffffff", height=54, padx=24, pady=10, highlightthickness=1, highlightbackground=self.C_CARD_BORDER)
        self.footer_frame.pack(fill="x", side="bottom")

        # 左侧：GitHub 图标与项目链接 (可点击直接跳转)
        f_left = tk.Frame(self.footer_frame, bg="#ffffff", cursor="hand2")
        f_left.pack(side="left", anchor="center")

        if self.github_icon_img:
            lbl_gh_ico = tk.Label(f_left, image=self.github_icon_img, bg="#ffffff", cursor="hand2")
            lbl_gh_ico.pack(side="left", padx=(0, 6))
            lbl_gh_ico.bind("<Button-1>", lambda e: self._open_github())

        self.lbl_github = tk.Label(
            f_left,
            text="GitHub: akasls/Antigravity-Orbit",
            font=("Segoe UI", 9),
            fg="#2563eb",
            bg="#ffffff",
            cursor="hand2"
        )
        self.lbl_github.pack(side="left")
        self.lbl_github.bind("<Button-1>", lambda e: self._open_github())
        self.lbl_github.bind("<Enter>", lambda e: self.lbl_github.configure(font=("Segoe UI", 9, "underline")))
        self.lbl_github.bind("<Leave>", lambda e: self.lbl_github.configure(font=("Segoe UI", 9)))

        # 中间：操作状态简述
        self.lbl_msg = tk.Label(self.footer_frame, textvariable=self.var_status_msg, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg="#ffffff")
        self.lbl_msg.pack(side="left", padx=20, anchor="center")

        # 右侧：动作按钮组
        btn_box = tk.Frame(self.footer_frame, bg="#ffffff")
        btn_box.pack(side="right")

        self.btn_restore = self._create_outline_btn(btn_box, "还原官方英文原版", self._on_click_restore, danger=True)
        self.btn_restore.pack(side="left", padx=5)

        self.btn_restart = self._create_outline_btn(btn_box, "重启 Antigravity", self._on_click_restart_app)
        self.btn_restart.pack(side="left", padx=5)

        self.btn_apply = tk.Button(
            btn_box,
            text="保存并一键生效",
            font=("Segoe UI", 9, "bold"),
            bg=self.C_ACCENT,
            fg="#ffffff",
            activebackground=self.C_ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
            command=self._on_click_save_and_apply
        )
        self.btn_apply.pack(side="left", padx=(5, 0))

    def _open_github(self):
        """跳转到 GitHub 项目地址"""
        try:
            webbrowser.open("https://github.com/akasls/Antigravity-Orbit")
        except Exception as e:
            messagebox.showinfo("GitHub 地址", f"项目地址: https://github.com/akasls/Antigravity-Orbit\n\n({e})")

    # -------------------------------------------------------------
    # 辅助卡片与行布局组件
    # -------------------------------------------------------------
    def _create_card(self, parent, title: str, subtitle: str = "") -> tk.Frame:
        """生成现代浅色微圆角卡片"""
        c = tk.Frame(parent, bg=self.C_CARD, highlightthickness=1, highlightbackground=self.C_CARD_BORDER)
        c.pack(fill="x", pady=8)

        h = tk.Frame(c, bg=self.C_CARD, padx=16, pady=10)
        h.pack(fill="x")

        tk.Label(h, text=title, font=("Segoe UI", 10, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        if subtitle:
            tk.Label(h, text=subtitle, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        sep = tk.Frame(c, bg=self.C_CARD_BORDER, height=1)
        sep.pack(fill="x")
        return c

    def _create_row_separator(self, parent):
        sep = tk.Frame(parent, bg=self.C_SEP, height=1)
        sep.pack(fill="x", padx=16)

    def _create_checkbox_row(self, card, title: str, desc: str, variable: tk.BooleanVar, is_last: bool = False):
        """生成带显眼 ✔ 勾选指示的设置行"""
        row = tk.Frame(card, bg=self.C_CARD, padx=16, pady=10)
        row.pack(fill="x")

        left = tk.Frame(row, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text=title, font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        if desc:
            tk.Label(left, text=desc, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(row, bg=self.C_CARD)
        right.pack(side="right", anchor="center")

        chk = CheckmarkBox(right, variable=variable, text="已启用", bg=self.C_CARD, fg=self.C_TEXT_MAIN)
        chk.pack(anchor="e")

        if not is_last:
            self._create_row_separator(card)

    def _create_compact_input(self, parent, label_text: str, var, hint=""):
        row = tk.Frame(parent, bg=self.C_CARD, pady=3)
        row.pack(fill="x")

        tk.Label(row, text=label_text, width=13, anchor="w", font=("Segoe UI", 8, "bold"), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        e = tk.Entry(
            row,
            textvariable=var,
            bg="#ffffff",
            fg=self.C_TEXT_MAIN,
            insertbackground="#0f172a",
            relief="solid",
            bd=1,
            font=("Consolas", 9)
        )
        e.pack(side="left", fill="x", expand=True)
        if hint:
            tk.Label(row, text=hint, font=("Segoe UI", 8), fg=self.C_TEXT_DIM, bg=self.C_CARD).pack(side="left", padx=8)

    def _create_outline_btn(self, parent, text: str, command, danger: bool = False):
        border_col = "#fca5a5" if danger else self.C_BTN_SEC_BORDER
        fg_col = self.C_DANGER if danger else self.C_TEXT_MAIN
        b = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 8),
            bg=self.C_BTN_SEC,
            fg=fg_col,
            activebackground=self.C_BTN_SEC_HOVER,
            activeforeground=fg_col,
            relief="solid",
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        return b

    # -------------------------------------------------------------
    # 极速异步状态更新 (零卡顿后台检测)
    # -------------------------------------------------------------
    def _refresh_system_status_async(self):
        """在后台线程异步检测环境，不阻塞前台 UI 渲染"""
        def _worker():
            # 1. 快速检查汉化与客户端目录
            loc = LocalizationManager.get_status(fast=True)

            # 2. 检查守护端口与 PID
            port = self.var_daemon_port.get()
            is_running, pid = self._check_daemon_running(port)

            # 3. 检查开机自启
            auto_enabled = AutostartManager.is_enabled()

            # 回调至主线程更新 UI 变量与指示 Pill
            self.after(0, lambda: self._apply_status_to_ui(loc, is_running, pid, auto_enabled))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_status_to_ui(self, loc, is_running, pid, auto_enabled):
        if loc.get("installed"):
            install_dir = loc.get("install_dir", "")
            base_name = os.path.basename(install_dir)
            lang_label = "已汉化 (zh-CN)" if loc.get("is_localized") else "官方原版英文"
            self.var_stat_install.set(f"● 客户端: {lang_label} ({base_name})")
            self.pill_install.configure(fg=self.C_GREEN, bg="#dcfce7")
        else:
            self.var_stat_install.set("○ 未检测到 Antigravity 安装")
            self.pill_install.configure(fg=self.C_DANGER, bg="#fee2e2")

        if is_running:
            self.var_stat_daemon.set(f"● 守护服务: 运行中 (PID {pid})")
            self.pill_daemon.configure(fg=self.C_GREEN, bg="#dcfce7")
        else:
            self.var_stat_daemon.set("○ 守护服务: 未启动")
            self.pill_daemon.configure(fg=self.C_GRAY, bg="#f1f5f9")

        if auto_enabled:
            self.var_stat_autostart.set("已开启")
        else:
            self.var_stat_autostart.set("未开启")

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
