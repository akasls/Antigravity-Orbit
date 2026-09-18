"""
Antigravity Orbit - 独立桌面客户端控制中心 (Native Desktop GUI Client)
极简现代设计风格，无冗余 AI 炫光，专注高效配置与一键管理
"""

import os
import sys
import json
import time
import socket
import platform
import threading
import subprocess
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
from notifiers import TelegramNotifier, FeishuNotifier, WeComNotifier


class ModernOrbitApp(tk.Tk):
    """Antigravity Orbit 极简现代桌面控制中心"""

    def __init__(self):
        super().__init__()
        self.title("Antigravity Orbit")
        self.geometry("900x710")
        self.minsize(840, 660)

        # 窗口居中
        self._center_window(900, 710)

        # 尝试设置图标
        icon_path = RESOURCE_DIR / "resources" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.cfg = load_config()
        self._init_variables()
        self._init_theme_colors()
        self._setup_ttk_styles()
        self._build_layout()
        self._refresh_system_status()

    def _center_window(self, width, height):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, int((sw - width) / 2))
            y = max(0, int((sh - height) / 2) - 20)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _init_variables(self):
        """绑定表单数据模型"""
        custom = self.cfg.get("customization", {})

        # 页面 1: 界面外观
        self.var_language = tk.StringVar(value=custom.get("language", "zh-CN"))
        self.var_show_quota = tk.BooleanVar(value=custom.get("show_quota_badge", True))
        self.var_quota_interval = tk.IntVar(value=custom.get("quota_refresh_interval", 60))
        self.var_hide_ide = tk.BooleanVar(value=custom.get("hide_ide_buttons", True))

        # 页面 2: 性能与隐私
        self.var_gpu_accel = tk.BooleanVar(value=custom.get("enable_gpu_acceleration", True))
        self.var_unthrottle = tk.BooleanVar(value=custom.get("disable_background_throttling", True))
        self.var_v8_mem = tk.BooleanVar(value=custom.get("expand_v8_memory", True))
        self.var_telemetry = tk.BooleanVar(value=custom.get("disable_telemetry", True))

        # 页面 3: 通知通道
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

        # 页面 4: 监控常驻
        self.var_daemon_port = tk.IntVar(value=self.cfg.get("lock_port", 49222))
        self.var_daemon_interval = tk.DoubleVar(value=self.cfg.get("scan_interval", 3.0))

        # 状态显示
        self.var_status_msg = tk.StringVar(value="就绪")
        self.var_stat_install = tk.StringVar(value="检测中...")
        self.var_stat_daemon = tk.StringVar(value="检测中...")
        self.var_stat_autostart = tk.StringVar(value="检测中...")

    def _init_theme_colors(self):
        """专业现代深色调 (无炫光渐变，专注质感与清晰可读)"""
        self.C_BG = "#161618"              # 主背景 (深黑灰)
        self.C_SIDEBAR = "#1c1c1f"         # 侧边栏背景
        self.C_SIDEBAR_BORDER = "#28282d"  # 侧边栏分割线
        self.C_CARD = "#1f1f23"            # 卡片背景
        self.C_CARD_BORDER = "#2c2c32"     # 卡片描边
        self.C_ROW_HOVER = "#242429"       # 悬停色

        self.C_TEXT_MAIN = "#f4f4f5"       # 主文字
        self.C_TEXT_MUTED = "#8e8e96"      # 次要提示文字
        self.C_TEXT_DIM = "#62626a"        # 暗提示文字

        self.C_ACCENT = "#3b82f6"          # 经典靛蓝色 (主动作)
        self.C_ACCENT_HOVER = "#2563eb"    # 主动作悬停
        self.C_BTN_SEC = "#2a2a2f"         # 次级按钮背景
        self.C_BTN_SEC_HOVER = "#34343a"   # 次级按钮悬停
        self.C_BORDER_SEC = "#383840"

        self.C_GREEN = "#10b981"           # 正常/已激活
        self.C_GREEN_BG = "#132b22"
        self.C_GRAY_BG = "#242429"

        self.configure(bg=self.C_BG)

    def _setup_ttk_styles(self):
        """精细定制 ttk 原生控件以融合深色主题"""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("TFrame", background=self.C_BG)
        self.style.configure("Card.TFrame", background=self.C_CARD)

        # 检查框 Checkbutton
        self.style.configure(
            "Clean.TCheckbutton",
            background=self.C_CARD,
            foreground=self.C_TEXT_MAIN,
            font=("Segoe UI", 9),
            indicatorcolor=self.C_CARD,
            indicatormargin=4,
            padding=2
        )
        self.style.map(
            "Clean.TCheckbutton",
            background=[("active", self.C_CARD)],
            indicatorcolor=[("selected", self.C_ACCENT), ("active", "#383842")]
        )

        # 单选框 Radiobutton
        self.style.configure(
            "Clean.TRadiobutton",
            background=self.C_CARD,
            foreground=self.C_TEXT_MAIN,
            font=("Segoe UI", 9),
            indicatorcolor=self.C_CARD,
            padding=3
        )
        self.style.map(
            "Clean.TRadiobutton",
            background=[("active", self.C_CARD)],
            indicatorcolor=[("selected", self.C_ACCENT), ("active", "#383842")]
        )

        # 下拉框 Combobox
        self.style.configure(
            "Clean.TCombobox",
            fieldbackground=self.C_BG,
            background=self.C_BTN_SEC,
            foreground=self.C_TEXT_MAIN,
            arrowcolor=self.C_TEXT_MAIN,
            bordercolor=self.C_CARD_BORDER,
            padding=4
        )
        self.style.map("Clean.TCombobox", fieldbackground=[("readonly", self.C_BG)])

    def _build_layout(self):
        """构建左右侧边栏与底部主框架"""
        # 主体容器
        body_container = tk.Frame(self, bg=self.C_BG)
        body_container.pack(fill="both", expand=True, side="top")

        # 1. 左侧边栏
        self.sidebar_frame = tk.Frame(body_container, bg=self.C_SIDEBAR, width=220)
        self.sidebar_frame.pack(fill="y", side="left")
        self.sidebar_frame.pack_propagate(False)

        # 侧边栏垂直分割线
        sep_vert = tk.Frame(body_container, bg=self.C_SIDEBAR_BORDER, width=1)
        sep_vert.pack(fill="y", side="left")

        # 2. 右侧主工作区
        self.main_content = tk.Frame(body_container, bg=self.C_BG)
        self.main_content.pack(fill="both", expand=True, side="left")

        # 3. 底部操作栏
        self._build_bottom_bar()

        # 构建侧边栏内容
        self._build_sidebar()

        # 构建右侧各面板
        self._build_panels()

        # 默认选中第一个导航页
        self._switch_nav("appearance")

    # -------------------------------------------------------------
    # 侧边栏构建
    # -------------------------------------------------------------
    def _build_sidebar(self):
        # 品牌 Header
        brand_box = tk.Frame(self.sidebar_frame, bg=self.C_SIDEBAR, padx=18, pady=20)
        brand_box.pack(fill="x", side="top")

        lbl_logo = tk.Label(
            brand_box,
            text="Antigravity Orbit",
            font=("Segoe UI", 12, "bold"),
            fg=self.C_TEXT_MAIN,
            bg=self.C_SIDEBAR
        )
        lbl_logo.pack(anchor="w")

        lbl_desc = tk.Label(
            brand_box,
            text="桌面管理与控制中心",
            font=("Segoe UI", 8),
            fg=self.C_TEXT_DIM,
            bg=self.C_SIDEBAR
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 导航列表
        self.nav_buttons = {}
        nav_list_box = tk.Frame(self.sidebar_frame, bg=self.C_SIDEBAR, padx=10, pady=8)
        nav_list_box.pack(fill="x", side="top")

        nav_items = [
            ("appearance", "界面与外观"),
            ("performance", "性能与隐私"),
            ("notifications", "网络与通知"),
            ("system", "服务与自启")
        ]

        for key, label in nav_items:
            btn = tk.Frame(nav_list_box, bg=self.C_SIDEBAR, cursor="hand2", padx=12, pady=9)
            btn.pack(fill="x", pady=2)

            lbl = tk.Label(
                btn,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fg=self.C_TEXT_MUTED,
                bg=self.C_SIDEBAR,
                cursor="hand2"
            )
            lbl.pack(anchor="w")

            # 绑定点击与 Hover
            btn.bind("<Button-1>", lambda e, k=key: self._switch_nav(k))
            lbl.bind("<Button-1>", lambda e, k=key: self._switch_nav(k))
            btn.bind("<Enter>", lambda e, b=btn, l=lbl, k=key: self._nav_hover(b, l, k, True))
            btn.bind("<Leave>", lambda e, b=btn, l=lbl, k=key: self._nav_hover(b, l, k, False))

            self.nav_buttons[key] = {"frame": btn, "label": lbl}

        # 侧边栏底部精简状态报告
        bottom_status = tk.Frame(self.sidebar_frame, bg=self.C_SIDEBAR, padx=16, pady=16)
        bottom_status.pack(fill="x", side="bottom")

        tk.Label(bottom_status, text="系统检测", font=("Segoe UI", 8, "bold"), fg=self.C_TEXT_DIM, bg=self.C_SIDEBAR).pack(anchor="w", pady=(0, 6))

        r1 = tk.Frame(bottom_status, bg=self.C_SIDEBAR)
        r1.pack(fill="x", pady=2)
        tk.Label(r1, text="客户端:", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_SIDEBAR).pack(side="left")
        tk.Label(r1, textvariable=self.var_stat_install, font=("Segoe UI", 8), fg=self.C_TEXT_MAIN, bg=self.C_SIDEBAR).pack(side="left", padx=4)

        r2 = tk.Frame(bottom_status, bg=self.C_SIDEBAR)
        r2.pack(fill="x", pady=2)
        tk.Label(r2, text="监控守护:", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_SIDEBAR).pack(side="left")
        tk.Label(r2, textvariable=self.var_stat_daemon, font=("Segoe UI", 8), fg=self.C_TEXT_MAIN, bg=self.C_SIDEBAR).pack(side="left", padx=4)

    def _nav_hover(self, frame, label, key, entering):
        if getattr(self, "active_nav", None) == key:
            return
        if entering:
            frame.configure(bg="#232327")
            label.configure(bg="#232327", fg=self.C_TEXT_MAIN)
        else:
            frame.configure(bg=self.C_SIDEBAR)
            label.configure(bg=self.C_SIDEBAR, fg=self.C_TEXT_MUTED)

    def _switch_nav(self, key):
        self.active_nav = key
        for k, item in self.nav_buttons.items():
            if k == key:
                item["frame"].configure(bg="#27272b")
                item["label"].configure(bg="#27272b", fg="#ffffff")
            else:
                item["frame"].configure(bg=self.C_SIDEBAR)
                item["label"].configure(bg=self.C_SIDEBAR, fg=self.C_TEXT_MUTED)

        # 切换右侧面板
        for k, p in self.panels.items():
            if k == key:
                p.pack(fill="both", expand=True)
            else:
                p.pack_forget()

    # -------------------------------------------------------------
    # 右侧主面板构建
    # -------------------------------------------------------------
    def _build_panels(self):
        self.panels = {}

        # 1. 界面与外观
        self.panels["appearance"] = self._create_panel_appearance()
        # 2. 性能与隐私
        self.panels["performance"] = self._create_panel_performance()
        # 3. 网络与通知
        self.panels["notifications"] = self._create_panel_notifications()
        # 4. 服务与自启
        self.panels["system"] = self._create_panel_system()

    def _create_panel_appearance(self):
        p = tk.Frame(self.main_content, bg=self.C_BG, padx=28, pady=24)

        self._create_section_title(p, "界面与外观", "管理客户端语言、顶栏配额组件与多余入口清理")

        # 卡片 1: 界面语言
        c1 = self._create_card(p, "客户端语言")
        self._create_setting_row(
            c1,
            title="简体中文 (zh-CN)",
            desc="全面汉化导航、设置、模型配额与对话交互 [推荐]",
            widget=lambda parent: ttk.Radiobutton(parent, variable=self.var_language, value="zh-CN", style="Clean.TRadiobutton")
        )
        self._create_setting_row(
            c1,
            title="繁体中文 (zh-TW)",
            desc="对齐港澳台本地化用语习惯",
            widget=lambda parent: ttk.Radiobutton(parent, variable=self.var_language, value="zh-TW", style="Clean.TRadiobutton")
        )
        self._create_setting_row(
            c1,
            title="官方英文原版 (en)",
            desc="保留纯正英文界面，仅启用顶栏额度与性能加速",
            widget=lambda parent: ttk.Radiobutton(parent, variable=self.var_language, value="en", style="Clean.TRadiobutton"),
            is_last=True
        )

        # 卡片 2: 顶栏模型额度
        c2 = self._create_card(p, "顶部标题栏实时模型额度")
        self._create_setting_row(
            c2,
            title="顶栏模型配额胶囊",
            desc="在标题栏右上角实时呈现 Gemini 与 Claude/GPT 限额比例与状态指示灯",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_show_quota, style="Clean.TCheckbutton")
        )
        self._create_setting_row(
            c2,
            title="额度刷新频率",
            desc="通过 ConnectRPC 内部端点自动轮询配额的时间间隔 (秒)",
            widget=lambda parent: ttk.Combobox(parent, textvariable=self.var_quota_interval, values=[30, 60, 120, 300], width=7, state="readonly", style="Clean.TCombobox"),
            is_last=True
        )

        # 卡片 3: 界面净化
        c3 = self._create_card(p, "界面净化")
        self._create_setting_row(
            c3,
            title="移除右上角推广按钮",
            desc="彻底隐藏 'Open IDE' / 'Install IDE' 及其空白外层容器",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_hide_ide, style="Clean.TCheckbutton"),
            is_last=True
        )

        return p

    def _create_panel_performance(self):
        p = tk.Frame(self.main_content, bg=self.C_BG, padx=28, pady=24)

        self._create_section_title(p, "性能与隐私", "底层 Chromium 硬件栅格化、防降频与全栈去遥测配置")

        # 卡片 1: 性能优化
        c1 = self._create_card(p, "极限性能加速")
        self._create_setting_row(
            c1,
            title="GPU 硬件栅格化与零拷贝",
            desc="开启显卡硬件加速 (enable-gpu-rasterization & zero-copy)，降低流式输出 CPU 开销",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_gpu_accel, style="Clean.TCheckbutton")
        )
        self._create_setting_row(
            c1,
            title="解除后台调度降频 (Unthrottling)",
            desc="切到其他编辑器或被遮挡时，防止定时器被降频至 1Hz 导致长跑任务假死",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_unthrottle, style="Clean.TCheckbutton")
        )
        self._create_setting_row(
            c1,
            title="V8 垃圾回收堆扩容至 4GB",
            desc="注入 --max-old-space-size=4096，消除大工程与数十轮对话下的 GC 停顿卡顿",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_v8_mem, style="Clean.TCheckbutton"),
            is_last=True
        )

        # 卡片 2: 遥测与数据隐私
        c2 = self._create_card(p, "遥测阻断与隐私安全")
        self._create_setting_row(
            c2,
            title="全栈切断遥测数据回传",
            desc="关闭 Language Server 核心度量上报、Chromium 崩溃诊断与 DevTools Clearcut 日志",
            widget=lambda parent: ttk.Checkbutton(parent, variable=self.var_telemetry, style="Clean.TCheckbutton"),
            is_last=True
        )

        return p

    def _create_panel_notifications(self):
        p = tk.Frame(self.main_content, bg=self.C_BG, padx=28, pady=24)

        self._create_section_title(p, "网络与通知", "配置长跑任务彻底完成时的即时消息推送机器人")

        # Telegram
        c_tg = self._create_card(p, "Telegram 机器人")
        tg_header = tk.Frame(c_tg, bg=self.C_CARD)
        tg_header.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Checkbutton(tg_header, text="启用 Telegram 通道", variable=self.var_tg_enabled, style="Clean.TCheckbutton").pack(side="left")
        self._create_flat_btn(tg_header, "发送测试", self._test_telegram).pack(side="right")

        f_tg = tk.Frame(c_tg, bg=self.C_CARD, padx=16, pady=4)
        f_tg.pack(fill="x", pady=(0, 10))
        self._create_input_field(f_tg, "Bot Token:", self.var_tg_token)
        self._create_input_field(f_tg, "Chat ID:", self.var_tg_chat)
        self._create_input_field(f_tg, "网络代理 (可选):", self.var_tg_proxy, hint="如 127.0.0.1:7890，国内直连不通时填写")

        # 飞书
        c_fs = self._create_card(p, "飞书自定义机器人")
        fs_header = tk.Frame(c_fs, bg=self.C_CARD)
        fs_header.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Checkbutton(fs_header, text="启用飞书 Webhook", variable=self.var_fs_enabled, style="Clean.TCheckbutton").pack(side="left")
        self._create_flat_btn(fs_header, "发送测试", self._test_feishu).pack(side="right")

        f_fs = tk.Frame(c_fs, bg=self.C_CARD, padx=16, pady=4)
        f_fs.pack(fill="x", pady=(0, 10))
        self._create_input_field(f_fs, "Webhook URL:", self.var_fs_url)

        # 企业微信
        c_wc = self._create_card(p, "企业微信机器人")
        wc_header = tk.Frame(c_wc, bg=self.C_CARD)
        wc_header.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Checkbutton(wc_header, text="启用企业微信 Webhook", variable=self.var_wc_enabled, style="Clean.TCheckbutton").pack(side="left")
        self._create_flat_btn(wc_header, "发送测试", self._test_wecom).pack(side="right")

        f_wc = tk.Frame(c_wc, bg=self.C_CARD, padx=16, pady=4)
        f_wc.pack(fill="x", pady=(0, 10))
        self._create_input_field(f_wc, "Webhook URL:", self.var_wc_url)

        return p

    def _create_panel_system(self):
        p = tk.Frame(self.main_content, bg=self.C_BG, padx=28, pady=24)

        self._create_section_title(p, "服务与自启", "管理后台任务感知守护进程与 Windows 开机静默启动")

        # 守护控制
        c1 = self._create_card(p, "长跑任务监控常驻服务")
        row_daemon = tk.Frame(c1, bg=self.C_CARD, padx=16, pady=12)
        row_daemon.pack(fill="x")

        tk.Label(row_daemon, text="运行状态:", font=("Segoe UI", 9), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        tk.Label(row_daemon, textvariable=self.var_stat_daemon, font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left", padx=(4, 16))

        tk.Label(row_daemon, text="端口:", font=("Segoe UI", 9), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        tk.Entry(row_daemon, textvariable=self.var_daemon_port, width=6, bg="#161618", fg=self.C_TEXT_MAIN, insertbackground="#fff", relief="flat").pack(side="left", padx=(4, 16))

        self._create_flat_btn(row_daemon, "启动服务", self._start_daemon).pack(side="left", padx=4)
        self._create_flat_btn(row_daemon, "停止服务", self._stop_daemon).pack(side="left", padx=4)

        # 自启控制
        c2 = self._create_card(p, "系统开机自启动")
        row_auto = tk.Frame(c2, bg=self.C_CARD, padx=16, pady=12)
        row_auto.pack(fill="x")

        tk.Label(row_auto, textvariable=self.var_stat_autostart, font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(side="left", padx=(0, 20))
        self._create_flat_btn(row_auto, "开启开机自启", self._enable_autostart).pack(side="left", padx=4)
        self._create_flat_btn(row_auto, "关闭开机自启", self._disable_autostart).pack(side="left", padx=4)

        # 日志预览
        c3 = self._create_card(p, "运行日志预览")
        log_header = tk.Frame(c3, bg=self.C_CARD, padx=16, pady=6)
        log_header.pack(fill="x")
        self._create_flat_btn(log_header, "刷新日志", self._refresh_log_preview).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            c3,
            height=7,
            bg="#161618",
            fg="#d4d4d8",
            insertbackground="#ffffff",
            font=("Consolas", 8),
            relief="flat",
            wrap="word",
            padx=12,
            pady=8
        )
        self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._refresh_log_preview()

        return p

    # -------------------------------------------------------------
    # 辅助卡片与行布局构建
    # -------------------------------------------------------------
    def _create_section_title(self, parent, title: str, subtitle: str):
        box = tk.Frame(parent, bg=self.C_BG)
        box.pack(fill="x", pady=(0, 14))
        tk.Label(box, text=title, font=("Segoe UI", 13, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_BG).pack(anchor="w")
        tk.Label(box, text=subtitle, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_BG).pack(anchor="w", pady=(2, 0))

    def _create_card(self, parent, title: str) -> tk.Frame:
        c = tk.Frame(parent, bg=self.C_CARD, highlightthickness=1, highlightbackground=self.C_CARD_BORDER)
        c.pack(fill="x", pady=6)
        
        # 头部标题
        h = tk.Frame(c, bg=self.C_CARD, padx=16, pady=8)
        h.pack(fill="x")
        tk.Label(h, text=title, font=("Segoe UI", 9, "bold"), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        
        sep = tk.Frame(c, bg=self.C_CARD_BORDER, height=1)
        sep.pack(fill="x")
        return c

    def _create_setting_row(self, card, title: str, desc: str, widget, is_last=False):
        row = tk.Frame(card, bg=self.C_CARD, padx=16, pady=10)
        row.pack(fill="x")

        # 左侧文案
        left = tk.Frame(row, bg=self.C_CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text=title, font=("Segoe UI", 9), fg=self.C_TEXT_MAIN, bg=self.C_CARD).pack(anchor="w")
        if desc:
            tk.Label(left, text=desc, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(anchor="w", pady=(2, 0))

        # 右侧控件
        right = tk.Frame(row, bg=self.C_CARD)
        right.pack(side="right", anchor="center")
        w = widget(right)
        if w:
            w.pack(anchor="e")

        if not is_last:
            sep = tk.Frame(card, bg="#26262c", height=1)
            sep.pack(fill="x", padx=16)

    def _create_input_field(self, parent, label_text: str, var, hint=""):
        row = tk.Frame(parent, bg=self.C_CARD, pady=4)
        row.pack(fill="x")
        tk.Label(row, text=label_text, width=14, anchor="w", font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg=self.C_CARD).pack(side="left")
        e = tk.Entry(
            row,
            textvariable=var,
            bg="#161618",
            fg=self.C_TEXT_MAIN,
            insertbackground="#ffffff",
            relief="flat",
            font=("Consolas", 9),
            highlightthickness=1,
            highlightbackground=self.C_CARD_BORDER,
            highlightcolor=self.C_ACCENT
        )
        e.pack(side="left", fill="x", expand=True)
        if hint:
            tk.Label(row, text=hint, font=("Segoe UI", 8), fg=self.C_TEXT_DIM, bg=self.C_CARD).pack(side="left", padx=8)

    def _create_flat_btn(self, parent, text: str, command):
        b = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 8),
            bg=self.C_BTN_SEC,
            fg=self.C_TEXT_MAIN,
            activebackground=self.C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        return b

    # -------------------------------------------------------------
    # 底部全局操作栏
    # -------------------------------------------------------------
    def _build_bottom_bar(self):
        self.footer_frame = tk.Frame(self, bg="#18181b", padx=24, pady=12, highlightthickness=1, highlightbackground=self.C_SIDEBAR_BORDER)
        self.footer_frame.pack(fill="x", side="bottom")

        # 状态文案
        lbl_msg = tk.Label(self.footer_frame, textvariable=self.var_status_msg, font=("Segoe UI", 8), fg=self.C_TEXT_MUTED, bg="#18181b")
        lbl_msg.pack(side="left", anchor="center")

        # 按钮组
        btn_box = tk.Frame(self.footer_frame, bg="#18181b")
        btn_box.pack(side="right")

        self.btn_restore = tk.Button(
            btn_box,
            text="还原官方原版英文",
            font=("Segoe UI", 9),
            bg=self.C_BTN_SEC,
            fg=self.C_TEXT_MAIN,
            activebackground=self.C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_click_restore
        )
        self.btn_restore.pack(side="left", padx=5)

        self.btn_restart = tk.Button(
            btn_box,
            text="重启客户端",
            font=("Segoe UI", 9),
            bg=self.C_BTN_SEC,
            fg=self.C_TEXT_MAIN,
            activebackground=self.C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_click_restart_app
        )
        self.btn_restart.pack(side="left", padx=5)

        self.btn_apply = tk.Button(
            btn_box,
            text="保存并应用配置",
            font=("Segoe UI", 9, "bold"),
            bg=self.C_ACCENT,
            fg="#ffffff",
            activebackground=self.C_ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._on_click_save_and_apply
        )
        self.btn_apply.pack(side="left", padx=5)

    # -------------------------------------------------------------
    # 状态更新
    # -------------------------------------------------------------
    def _refresh_system_status(self):
        loc = LocalizationManager.get_status()
        if loc.get("installed"):
            install_dir = loc.get("install_dir", "")
            base_name = os.path.basename(install_dir)
            self.var_stat_install.set(f"已定位 ({base_name})")
        else:
            self.var_stat_install.set("未找到客户端")

        port = self.var_daemon_port.get()
        is_running, pid = self._check_daemon_running(port)
        if is_running:
            self.var_stat_daemon.set(f"运行中 (PID {pid})")
        else:
            self.var_stat_daemon.set("未运行")

        if AutostartManager.is_enabled():
            self.var_stat_autostart.set("已开启 Windows 自启")
        else:
            self.var_stat_autostart.set("未开启自启")

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
                recent = "\n".join(lines[-30:]) if lines else "暂无日志记录"
                self.txt_log.insert(tk.END, recent)
                self.txt_log.see(tk.END)
            except Exception as e:
                self.txt_log.insert(tk.END, f"读取日志异常: {e}")
        else:
            self.txt_log.insert(tk.END, "日志文件尚未生成 (启动服务后将自动记录)")

    # -------------------------------------------------------------
    # 动作：保存与应用
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
                    "enable_gpu_acceleration": self.var_gpu_accel.get(),
                    "disable_background_throttling": self.var_unthrottle.get(),
                    "expand_v8_memory": self.var_v8_mem.get(),
                    "disable_telemetry": self.var_telemetry.get(),
                    "hide_ide_buttons": self.var_hide_ide.get()
                }
                self.cfg["lock_port"] = self.var_daemon_port.get()
                self.cfg["scan_interval"] = self.var_daemon_interval.get()

                ch = self.cfg.setdefault("channels", {})
                ch["telegram"] = {
                    "enabled": self.var_tg_enabled.get(),
                    "bot_token": self.var_tg_token.get().strip(),
                    "chat_id": self.var_tg_chat.get().strip(),
                    "proxy": self.var_tg_proxy.get().strip()
                }
                ch["feishu"] = {
                    "enabled": self.var_fs_enabled.get(),
                    "webhook_url": self.var_fs_url.get().strip()
                }
                ch["wecom"] = {
                    "enabled": self.var_wc_enabled.get(),
                    "webhook_url": self.var_wc_url.get().strip()
                }

                save_config(self.cfg)

                is_tw = (lang == "zh-TW")
                is_en = (lang == "en")

                ok, msg = LocalizationManager.install(
                    tw=is_tw,
                    en=is_en,
                    no_kill=True,
                    stream_output=False
                )

                if ok:
                    self.after(0, lambda: messagebox.showinfo(
                        "应用成功",
                        "配置已成功保存并注入到 Antigravity！\n\n如 Antigravity 正在运行中，点击【重启客户端】即可即时查看效果。"
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror("应用失败", f"部署遇到错误:\n\n{msg}"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"发生异常: {e}"))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))
                self.after(0, self._refresh_system_status)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_click_restore(self):
        confirm = messagebox.askyesno(
            "确认还原",
            "确定要还原官方英文原版吗？\n此操作将无损撤销所有汉化与优化补丁，恢复官方 app.asar 原始状态。"
        )
        if not confirm:
            return

        self._set_busy(True, "正在还原官方原版...")

        def _worker():
            try:
                ok, msg = LocalizationManager.restore(no_kill=True, stream_output=False)
                if ok:
                    self.after(0, lambda: messagebox.showinfo("还原成功", "官方英文原版已成功无痕恢复！\n如需查看效果，可重启客户端。"))
                else:
                    self.after(0, lambda: messagebox.showwarning("提示", msg))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))
                self.after(0, self._refresh_system_status)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_click_restart_app(self):
        loc = LocalizationManager.get_status()
        install_dir = loc.get("install_dir")
        if not install_dir or not Path(install_dir).exists():
            messagebox.showwarning("提示", "未检测到 Antigravity 安装路径。")
            return

        self._set_busy(True, "正在重启客户端...")

        def _worker():
            try:
                if sys.platform.startswith("win"):
                    subprocess.run("taskkill /F /IM Antigravity.exe /T", shell=True, capture_output=True)
                else:
                    subprocess.run("pkill -f Antigravity", shell=True, capture_output=True)

                time.sleep(1.2)

                if sys.platform.startswith("win"):
                    exe = Path(install_dir) / "Antigravity.exe"
                    if exe.exists():
                        subprocess.Popen([str(exe)], creationflags=subprocess.DETACHED_PROCESS)
                else:
                    subprocess.Popen(["open", install_dir])

                self.after(0, lambda: self.var_status_msg.set("客户端已重新启动"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("重启失败", str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 测试通道
    # -------------------------------------------------------------
    def _test_telegram(self):
        cfg = {
            "enabled": True,
            "bot_token": self.var_tg_token.get().strip(),
            "chat_id": self.var_tg_chat.get().strip(),
            "proxy": self.var_tg_proxy.get().strip()
        }
        if not cfg["bot_token"] or not cfg["chat_id"]:
            messagebox.showwarning("提示", "请先填写 Bot Token 与 Chat ID。")
            return

        self._set_busy(True, "测试发送 Telegram 消息...")

        def _worker():
            n = TelegramNotifier(cfg)
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"发送成功: {msg}" if ok else f"发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    def _test_feishu(self):
        url = self.var_fs_url.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先填写飞书 Webhook 地址。")
            return

        self._set_busy(True, "测试发送飞书消息...")

        def _worker():
            n = FeishuNotifier({"enabled": True, "webhook_url": url})
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"发送成功: {msg}" if ok else f"发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    def _test_wecom(self):
        url = self.var_wc_url.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先填写企业微信 Webhook 地址。")
            return

        self._set_busy(True, "测试发送企业微信消息...")

        def _worker():
            n = WeComNotifier({"enabled": True, "webhook_url": url})
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"发送成功: {msg}" if ok else f"发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 守护进程与自启控制
    # -------------------------------------------------------------
    def _start_daemon(self):
        from main import cmd_start
        cmd_start(None)
        time.sleep(0.5)
        self._refresh_system_status()
        self._refresh_log_preview()

    def _stop_daemon(self):
        from main import cmd_stop
        cmd_stop(None)
        time.sleep(0.5)
        self._refresh_system_status()
        self._refresh_log_preview()

    def _enable_autostart(self):
        ok, msg = AutostartManager.enable()
        if ok:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showwarning("失败", msg)
        self._refresh_system_status()

    def _disable_autostart(self):
        ok, msg = AutostartManager.disable()
        messagebox.showinfo("提示", msg)
        self._refresh_system_status()

    def _set_busy(self, busy: bool, message: str = "就绪"):
        self.var_status_msg.set(message)
        state = "disabled" if busy else "normal"
        self.btn_apply.configure(state=state)
        self.btn_restore.configure(state=state)
        self.btn_restart.configure(state=state)
        self.config(cursor="watch" if busy else "")


def launch_gui():
    """桌面客户端主入口"""
    app = ModernOrbitApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
