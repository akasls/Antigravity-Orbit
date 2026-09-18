"""
Antigravity Orbit 独立桌面客户端管理工具 (Native Desktop GUI Client)
提供直观可视化的界面汉化、顶栏模型额度、极限性能加速、遥测阻断、通知推送与常驻监控配置
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

# 开启 Windows 高 DPI 适配，确保文字与组件清晰不发糊
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
    load_config,
    save_config,
)
from core.localization import LocalizationManager
from core.autostart import AutostartManager
from notifiers import TelegramNotifier, FeishuNotifier, WeComNotifier, get_active_notifiers


class OrbitGui(tk.Tk):
    """Antigravity Orbit 桌面控制中心主窗口"""

    def __init__(self):
        super().__init__()
        self.title("🌌 Antigravity Orbit - 控制中心")
        self.geometry("860x730")
        self.minsize(800, 680)

        # 尝试设置窗口图标 (如果有)
        icon_path = PROJECT_ROOT / "resources" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.cfg = load_config()
        self._init_variables()
        self._init_styles()
        self._build_ui()
        self._refresh_all_statuses()

    def _init_variables(self):
        """初始化表单数据绑定变量"""
        custom = self.cfg.get("customization", {})

        # 选项卡 1: 外观与汉化
        self.var_language = tk.StringVar(value=custom.get("language", "zh-CN"))
        self.var_show_quota = tk.BooleanVar(value=custom.get("show_quota_badge", True))
        self.var_quota_interval = tk.IntVar(value=custom.get("quota_refresh_interval", 60))
        self.var_hide_ide = tk.BooleanVar(value=custom.get("hide_ide_buttons", True))

        # 选项卡 2: 性能与去遥测
        self.var_gpu_accel = tk.BooleanVar(value=custom.get("enable_gpu_acceleration", True))
        self.var_unthrottle = tk.BooleanVar(value=custom.get("disable_background_throttling", True))
        self.var_v8_mem = tk.BooleanVar(value=custom.get("expand_v8_memory", True))
        self.var_telemetry = tk.BooleanVar(value=custom.get("disable_telemetry", True))

        # 选项卡 3: 通知渠道
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

        # 选项卡 4: 监控服务
        self.var_daemon_port = tk.IntVar(value=self.cfg.get("lock_port", 49222))
        self.var_daemon_interval = tk.DoubleVar(value=self.cfg.get("scan_interval", 3.0))

        # 状态文本
        self.var_status_msg = tk.StringVar(value="就绪")
        self.var_stat_install = tk.StringVar(value="检测中...")
        self.var_stat_lang = tk.StringVar(value="检测中...")
        self.var_stat_daemon = tk.StringVar(value="检测中...")
        self.var_stat_autostart = tk.StringVar(value="检测中...")

    def _init_styles(self):
        """配置现代深色视觉样式"""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # 色板配置
        self.BG_DARK = "#18181b"
        self.CARD_BG = "#27272a"
        self.CARD_BORDER = "#3f3f46"
        self.TEXT_MAIN = "#f4f4f5"
        self.TEXT_MUTED = "#a1a1aa"
        self.ACCENT_BLUE = "#3b82f6"
        self.ACCENT_HOVER = "#2563eb"
        self.SUCCESS_GREEN = "#10b981"
        self.DANGER_RED = "#ef4444"

        self.configure(bg=self.BG_DARK)

        # 全局 Frame 与 Label
        self.style.configure("TFrame", background=self.BG_DARK)
        self.style.configure("Card.TFrame", background=self.CARD_BG, relief="flat")
        self.style.configure("TLabel", background=self.BG_DARK, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=self.CARD_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("CardMuted.TLabel", background=self.CARD_BG, foreground=self.TEXT_MUTED, font=("Segoe UI", 9))
        self.style.configure("CardBold.TLabel", background=self.CARD_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 10, "bold"))

        # Notebook (选项卡)
        self.style.configure("TNotebook", background=self.BG_DARK, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background="#202023",
            foreground=self.TEXT_MUTED,
            padding=[18, 9],
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.CARD_BG), ("active", "#2e2e33")],
            foreground=[("selected", "#60a5fa"), ("active", "#ffffff")]
        )

        # Checkbutton / Radiobutton
        self.style.configure(
            "Card.TCheckbutton",
            background=self.CARD_BG,
            foreground=self.TEXT_MAIN,
            font=("Segoe UI", 10)
        )
        self.style.map("Card.TCheckbutton", background=[("active", self.CARD_BG)])

        self.style.configure(
            "Card.TRadiobutton",
            background=self.CARD_BG,
            foreground=self.TEXT_MAIN,
            font=("Segoe UI", 10)
        )
        self.style.map("Card.TRadiobutton", background=[("active", self.CARD_BG)])

        # 按钮样式
        self.style.configure(
            "Primary.TButton",
            background=self.ACCENT_BLUE,
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=[16, 7]
        )
        self.style.map("Primary.TButton", background=[("active", self.ACCENT_HOVER), ("disabled", "#475569")])

        self.style.configure(
            "Secondary.TButton",
            background="#3f3f46",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padding=[12, 5]
        )
        self.style.map("Secondary.TButton", background=[("active", "#52525b")])

        self.style.configure(
            "Danger.TButton",
            background="#dc2626",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padding=[12, 5]
        )
        self.style.map("Danger.TButton", background=[("active", "#b91c1c")])

        # Entry 边框
        self.style.configure(
            "Dark.TEntry",
            fieldbackground="#18181b",
            foreground="#f4f4f5",
            insertcolor="#ffffff",
            padding=5
        )

    def _build_ui(self):
        """构建整个可视化窗口界面"""
        # 1. 顶部 Header 状态栏
        header_frame = tk.Frame(self, bg="#202023", padx=20, pady=14)
        header_frame.pack(fill="x", side="top")

        # 标题与副标题
        title_box = tk.Frame(header_frame, bg="#202023")
        title_box.pack(side="left", fill="y")
        lbl_title = tk.Label(
            title_box,
            text="🌌 Antigravity Orbit 控制中心",
            font=("Segoe UI", 16, "bold"),
            fg="#60a5fa",
            bg="#202023"
        )
        lbl_title.pack(anchor="w")
        lbl_sub = tk.Label(
            title_box,
            text="Google Antigravity 界面汉化 · 顶栏实时额度 · 极限加速 · 去遥测 · 任务完成监控",
            font=("Segoe UI", 9),
            fg=self.TEXT_MUTED,
            bg="#202023"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. 状态指示卡片面板 (4个胶囊)
        status_bar = tk.Frame(self, bg=self.BG_DARK, padx=20, pady=12)
        status_bar.pack(fill="x")

        cards = [
            ("💻 客户端路径", self.var_stat_install),
            ("🌐 界面语言", self.var_stat_lang),
            ("🚀 任务监控服务", self.var_stat_daemon),
            ("⚡ 开机自启动", self.var_stat_autostart),
        ]
        for title, var in cards:
            c = tk.Frame(status_bar, bg=self.CARD_BG, padx=12, pady=8, highlightthickness=1, highlightbackground=self.CARD_BORDER)
            c.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(c, text=title, font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg=self.CARD_BG).pack(anchor="w")
            tk.Label(c, textvariable=var, font=("Segoe UI", 9, "bold"), fg=self.TEXT_MAIN, bg=self.CARD_BG).pack(anchor="w", pady=(2, 0))

        # 3. 核心选项卡 Notebook
        tab_container = tk.Frame(self, bg=self.BG_DARK, padx=20, pady=6)
        tab_container.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(tab_container)
        self.notebook.pack(fill="both", expand=True)

        self.tab_appearance = ttk.Frame(self.notebook, style="Card.TFrame", padding=16)
        self.tab_performance = ttk.Frame(self.notebook, style="Card.TFrame", padding=16)
        self.tab_notify = ttk.Frame(self.notebook, style="Card.TFrame", padding=16)
        self.tab_daemon = ttk.Frame(self.notebook, style="Card.TFrame", padding=16)

        self.notebook.add(self.tab_appearance, text="  🌐 界面汉化与外观  ")
        self.notebook.add(self.tab_performance, text="  ⚡ 性能加速与去遥测  ")
        self.notebook.add(self.tab_notify, text="  🔔 任务完成通知  ")
        self.notebook.add(self.tab_daemon, text="  🚀 监控常驻与自启  ")

        self._build_tab_appearance()
        self._build_tab_performance()
        self._build_tab_notify()
        self._build_tab_daemon()

        # 4. 底部固定全局操作栏
        footer_frame = tk.Frame(self, bg="#202023", padx=20, pady=12)
        footer_frame.pack(fill="x", side="bottom")

        # 状态指示
        lbl_status = tk.Label(footer_frame, textvariable=self.var_status_msg, font=("Segoe UI", 9), fg="#93c5fd", bg="#202023")
        lbl_status.pack(side="left", anchor="center")

        # 底部按钮组
        btn_box = tk.Frame(footer_frame, bg="#202023")
        btn_box.pack(side="right")

        self.btn_restore = ttk.Button(
            btn_box,
            text="🔄 还原官方原版英文",
            style="Secondary.TButton",
            command=self._on_click_restore
        )
        self.btn_restore.pack(side="left", padx=6)

        self.btn_restart_app = ttk.Button(
            btn_box,
            text="🚀 重启 Antigravity",
            style="Secondary.TButton",
            command=self._on_click_restart_app
        )
        self.btn_restart_app.pack(side="left", padx=6)

        self.btn_apply = ttk.Button(
            btn_box,
            text="⚡ 保存并应用配置到 Antigravity",
            style="Primary.TButton",
            command=self._on_click_save_and_apply
        )
        self.btn_apply.pack(side="left", padx=6)

    # -------------------------------------------------------------
    # 选项卡 1: 界面汉化与外观
    # -------------------------------------------------------------
    def _build_tab_appearance(self):
        f = self.tab_appearance

        # 分组 1: 语言包
        g1 = self._create_group_box(f, "🌐 客户端界面语言包")
        ttk.Radiobutton(
            g1, text="简体中文 (zh-CN) - 全面汉化导航、设置、模型管理与对话控件 [推荐]",
            variable=self.var_language, value="zh-CN", style="Card.TRadiobutton"
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            g1, text="繁体中文 (zh-TW) - 港澳台词汇习惯本地化语言包",
            variable=self.var_language, value="zh-TW", style="Card.TRadiobutton"
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            g1, text="官方原版英文 (en) - 保持纯正英文界面，仅启用顶栏额度与性能加速",
            variable=self.var_language, value="en", style="Card.TRadiobutton"
        ).pack(anchor="w", pady=4)

        # 分组 2: 顶栏模型额度徽章
        g2 = self._create_group_box(f, "📊 顶部标题栏实时模型额度显示 (Top-Right Quota Badge)")
        ttk.Checkbutton(
            g2,
            text="在客户端顶栏右上角实时显示模型额度胶囊 (Gemini / Claude / GPT)",
            variable=self.var_show_quota,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=(2, 6))

        interval_row = tk.Frame(g2, bg=self.CARD_BG)
        interval_row.pack(fill="x", pady=2)
        ttk.Label(interval_row, text="额度自动轮询刷新频率:", style="Card.TLabel").pack(side="left")
        
        cbo_interval = ttk.Combobox(
            interval_row,
            textvariable=self.var_quota_interval,
            values=[30, 60, 120, 300],
            width=6,
            state="readonly"
        )
        cbo_interval.pack(side="left", padx=8)
        ttk.Label(interval_row, text="秒 (切换至窗口时也会自动极速刷新)", style="CardMuted.TLabel").pack(side="left")

        tip_quota = (
            "💡 说明: 通过 ConnectRPC 内部端点直接获取实时限额数据（完全免鉴权），"
            "点击顶栏胶囊可展开浮动面板，查看 5小时限制 与 周限制 的精确百分比与刷新倒计时。"
        )
        ttk.Label(g2, text=tip_quota, style="CardMuted.TLabel", wraplength=760).pack(anchor="w", pady=(8, 0))

        # 分组 3: 界面精简
        g3 = self._create_group_box(f, "🧹 界面精简与多余元素净化")
        ttk.Checkbutton(
            g3,
            text="彻底隐藏右上角多余推广按钮 ('Open IDE' / 'Install IDE')",
            variable=self.var_hide_ide,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            g3,
            text="💡 拦截 preload.js 与 ipcHandlers 并注入强力 DOM 样式，消除无用的推广安装按钮与空白占位。",
            style="CardMuted.TLabel",
            wraplength=760
        ).pack(anchor="w", pady=(4, 0))

    # -------------------------------------------------------------
    # 选项卡 2: 性能加速与去遥测
    # -------------------------------------------------------------
    def _build_tab_performance(self):
        f = self.tab_performance

        # 分组 1: 硬件加速与渲染
        g1 = self._create_group_box(f, "⚡ Chromium 硬件渲染加速与零拷贝")
        ttk.Checkbutton(
            g1,
            text="启用 GPU 硬件栅格化与零拷贝内存缓冲区 (GPU Rasterization & Zero-Copy)",
            variable=self.var_gpu_accel,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            g1,
            text="大幅降低流式代码打字输出、长对话滚动与语法高亮时的 CPU 占用与功耗，避免界面掉帧卡顿。",
            style="CardMuted.TLabel",
            wraplength=760
        ).pack(anchor="w", pady=(2, 0))

        # 分组 2: 后台调度优化
        g2 = self._create_group_box(f, "🕒 后台调度优化与防降频 (Background Unthrottling)")
        ttk.Checkbutton(
            g2,
            text="解除后台定时器降频与窗口遮挡冻结 (Disable Background Throttling)",
            variable=self.var_unthrottle,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            g2,
            text="当 Antigravity 被切换到后台或被 VSCode/浏览器完全遮挡时，防止定时器被降频至 1Hz 导致长跑任务假死变慢。",
            style="CardMuted.TLabel",
            wraplength=760
        ).pack(anchor="w", pady=(2, 0))

        # 分组 3: 内存与堆扩展
        g3 = self._create_group_box(f, "🧠 内存与垃圾回收堆扩展")
        ttk.Checkbutton(
            g3,
            text="扩充 V8 垃圾回收堆内存上限至 4GB (--max-old-space-size=4096)",
            variable=self.var_v8_mem,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            g3,
            text="针对超大工程代码库索引以及持续几十轮长上下文对话，杜绝频繁 Full GC 引起的瞬间卡顿或内存溢出崩溃。",
            style="CardMuted.TLabel",
            wraplength=760
        ).pack(anchor="w", pady=(2, 0))

        # 分组 4: 全栈去遥测与隐私保护
        g4 = self._create_group_box(f, "🛡️ 全栈遥测阻断与隐私安全 (Zero-Telemetry)")
        ttk.Checkbutton(
            g4,
            text="全面切断所有遥测数据回传 (核心 Language Server + Chromium + DevTools MCP)",
            variable=self.var_telemetry,
            style="Card.TCheckbutton"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            g4,
            text="注入 --disable_telemetry=true 彻底切断 Go 后端度量上报；禁用指标收集与崩溃回传；中和 Google Clearcut 日志。",
            style="CardMuted.TLabel",
            wraplength=760
        ).pack(anchor="w", pady=(2, 0))

    # -------------------------------------------------------------
    # 选项卡 3: 任务完成通知推送
    # -------------------------------------------------------------
    def _build_tab_notify(self):
        f = self.tab_notify

        # Telegram
        g_tg = self._create_group_box(f, "🤖 Telegram 机器人推送 (支持国内外直连与本地代理)")
        tg_header = tk.Frame(g_tg, bg=self.CARD_BG)
        tg_header.pack(fill="x", pady=2)
        ttk.Checkbutton(tg_header, text="启用 Telegram 通道", variable=self.var_tg_enabled, style="Card.TCheckbutton").pack(side="left")
        ttk.Button(tg_header, text="📡 发送 Telegram 测试", style="Secondary.TButton", command=self._test_telegram).pack(side="right")

        row1 = tk.Frame(g_tg, bg=self.CARD_BG)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Bot Token:", width=11, style="Card.TLabel").pack(side="left")
        ttk.Entry(row1, textvariable=self.var_tg_token, font=("Consolas", 9)).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(row1, text="Chat ID:", width=8, style="Card.TLabel").pack(side="left")
        ttk.Entry(row1, textvariable=self.var_tg_chat, font=("Consolas", 9), width=18).pack(side="left")

        row2 = tk.Frame(g_tg, bg=self.CARD_BG)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="网络代理:", width=11, style="Card.TLabel").pack(side="left")
        ttk.Entry(row2, textvariable=self.var_tg_proxy, font=("Consolas", 9)).pack(side="left", fill="x", expand=True)
        ttk.Label(row2, text="(如 127.0.0.1:7890 或 10808，国内直连不通时填写)", style="CardMuted.TLabel").pack(side="left", padx=8)

        # 飞书
        g_fs = self._create_group_box(f, "🕊️ 飞书群自定义机器人 (Webhook)")
        fs_header = tk.Frame(g_fs, bg=self.CARD_BG)
        fs_header.pack(fill="x", pady=2)
        ttk.Checkbutton(fs_header, text="启用飞书推送", variable=self.var_fs_enabled, style="Card.TCheckbutton").pack(side="left")
        ttk.Button(fs_header, text="📡 发送飞书测试", style="Secondary.TButton", command=self._test_feishu).pack(side="right")

        row_fs = tk.Frame(g_fs, bg=self.CARD_BG)
        row_fs.pack(fill="x", pady=4)
        ttk.Label(row_fs, text="Webhook 地址:", width=13, style="Card.TLabel").pack(side="left")
        ttk.Entry(row_fs, textvariable=self.var_fs_url, font=("Consolas", 9)).pack(side="left", fill="x", expand=True)

        # 企业微信
        g_wc = self._create_group_box(f, "💬 企业微信群机器人 (Webhook)")
        wc_header = tk.Frame(g_wc, bg=self.CARD_BG)
        wc_header.pack(fill="x", pady=2)
        ttk.Checkbutton(wc_header, text="启用企业微信推送", variable=self.var_wc_enabled, style="Card.TCheckbutton").pack(side="left")
        ttk.Button(wc_header, text="📡 发送企微测试", style="Secondary.TButton", command=self._test_wecom).pack(side="right")

        row_wc = tk.Frame(g_wc, bg=self.CARD_BG)
        row_wc.pack(fill="x", pady=4)
        ttk.Label(row_wc, text="Webhook 地址:", width=13, style="Card.TLabel").pack(side="left")
        ttk.Entry(row_wc, textvariable=self.var_wc_url, font=("Consolas", 9)).pack(side="left", fill="x", expand=True)

    # -------------------------------------------------------------
    # 选项卡 4: 监控常驻与自启
    # -------------------------------------------------------------
    def _build_tab_daemon(self):
        f = self.tab_daemon

        # 后台服务控制
        g1 = self._create_group_box(f, "🚀 后台长跑任务监控常驻服务")
        ctrl_row = tk.Frame(g1, bg=self.CARD_BG)
        ctrl_row.pack(fill="x", pady=4)

        ttk.Label(ctrl_row, text="服务端口:", style="Card.TLabel").pack(side="left")
        ttk.Entry(ctrl_row, textvariable=self.var_daemon_port, width=8).pack(side="left", padx=(4, 14))

        ttk.Label(ctrl_row, text="扫描间隔(秒):", style="Card.TLabel").pack(side="left")
        ttk.Entry(ctrl_row, textvariable=self.var_daemon_interval, width=6).pack(side="left", padx=(4, 16))

        ttk.Button(ctrl_row, text="▶️ 启动后台监控", style="Secondary.TButton", command=self._start_daemon).pack(side="left", padx=4)
        ttk.Button(ctrl_row, text="⏹️ 停止后台监控", style="Secondary.TButton", command=self._stop_daemon).pack(side="left", padx=4)

        # 自启控制
        g2 = self._create_group_box(f, "⚡ 系统开机静默自启动")
        auto_row = tk.Frame(g2, bg=self.CARD_BG)
        auto_row.pack(fill="x", pady=4)

        ttk.Label(auto_row, textvariable=self.var_stat_autostart, style="CardBold.TLabel").pack(side="left", padx=(0, 20))
        ttk.Button(auto_row, text="✅ 开启开机自启", style="Secondary.TButton", command=self._enable_autostart).pack(side="left", padx=4)
        ttk.Button(auto_row, text="❌ 关闭开机自启", style="Secondary.TButton", command=self._disable_autostart).pack(side="left", padx=4)

        # 实时日志预览
        g3 = self._create_group_box(f, "📜 监控运行日志预览 (最近记录)")
        log_ctrl = tk.Frame(g3, bg=self.CARD_BG)
        log_ctrl.pack(fill="x", pady=(0, 4))
        ttk.Button(log_ctrl, text="🔄 刷新日志", style="Secondary.TButton", command=self._refresh_log_preview).pack(side="right")

        self.txt_log = scrolledtext.ScrolledText(
            g3,
            height=8,
            bg="#18181b",
            fg="#e4e4e7",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            wrap="word"
        )
        self.txt_log.pack(fill="both", expand=True)
        self._refresh_log_preview()

    # -------------------------------------------------------------
    # 辅助与卡片构建器
    # -------------------------------------------------------------
    def _create_group_box(self, parent, title: str) -> tk.Frame:
        """创建带边框与标题的独立卡片组件"""
        box = tk.Frame(
            parent,
            bg=self.CARD_BG,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=self.CARD_BORDER
        )
        box.pack(fill="x", pady=6)
        lbl = tk.Label(
            box,
            text=title,
            font=("Segoe UI", 10, "bold"),
            fg="#93c5fd",
            bg=self.CARD_BG
        )
        lbl.pack(anchor="w", pady=(0, 8))
        return box

    # -------------------------------------------------------------
    # 状态刷新与网络检测
    # -------------------------------------------------------------
    def _refresh_all_statuses(self):
        """刷新所有系统状态"""
        # 1. 客户端安装与汉化状态
        loc = LocalizationManager.get_status()
        if loc.get("installed"):
            install_dir = loc.get("install_dir", "")
            short_dir = os.path.basename(install_dir)
            self.var_stat_install.set(f"🟢 已检测 ({short_dir})")
            if loc.get("is_localized"):
                lang = loc.get("lang")
                lang_str = "繁体中文" if lang == "zh-TW" else "简体中文"
                self.var_stat_lang.set(f"🟢 已汉化 ({lang_str})")
            else:
                self.var_stat_lang.set("⚪ 官方原版英文")
        else:
            self.var_stat_install.set("🔴 未检测到路径")
            self.var_stat_lang.set("⚪ 未知")

        # 2. 监控常驻状态
        port = self.var_daemon_port.get()
        is_running, pid = self._check_daemon_running(port)
        if is_running:
            self.var_stat_daemon.set(f"🟢 运行中 (PID: {pid})")
        else:
            self.var_stat_daemon.set("🔴 未运行")

        # 3. 开机自启状态
        if AutostartManager.is_enabled():
            self.var_stat_autostart.set("🟢 已开启自启")
        else:
            self.var_stat_autostart.set("⚪ 未开启自启")

    def _check_daemon_running(self, port: int):
        """通过端口与 pid 判定监控是否在运行"""
        pid_file = PROJECT_ROOT / ".daemon.pid"
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
        """读取最近日志"""
        self.txt_log.delete("1.0", tk.END)
        if LOG_FILE.exists():
            try:
                lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                recent = "\n".join(lines[-40:]) if lines else "暂无日志记录"
                self.txt_log.insert(tk.END, recent)
                self.txt_log.see(tk.END)
            except Exception as e:
                self.txt_log.insert(tk.END, f"读取日志异常: {e}")
        else:
            self.txt_log.insert(tk.END, "日志文件尚未生成 (启动监控后将自动记录)")

    # -------------------------------------------------------------
    # 底部核心动作：保存配置并应用到 Antigravity
    # -------------------------------------------------------------
    def _on_click_save_and_apply(self):
        """保存当前所有配置并调用引擎注入 asar 补丁"""
        self._set_busy(True, "⏳ 正在保存配置并应用补丁到 Antigravity...")

        def _worker():
            try:
                # 1. 收集表单数据
                lang = self.var_language.get()
                custom_cfg = {
                    "language": lang,
                    "show_quota_badge": self.var_show_quota.get(),
                    "quota_refresh_interval": self.var_quota_interval.get(),
                    "enable_gpu_acceleration": self.var_gpu_accel.get(),
                    "disable_background_throttling": self.var_unthrottle.get(),
                    "expand_v8_memory": self.var_v8_mem.get(),
                    "disable_telemetry": self.var_telemetry.get(),
                    "hide_ide_buttons": self.var_hide_ide.get()
                }

                self.cfg["customization"] = custom_cfg
                self.cfg["lock_port"] = self.var_daemon_port.get()
                self.cfg["scan_interval"] = self.var_daemon_interval.get()

                # channels
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

                # 2. 执行补丁注入
                is_tw = (lang == "zh-TW")
                is_en = (lang == "en")

                ok, msg = LocalizationManager.install(
                    tw=is_tw,
                    en=is_en,
                    no_kill=True,
                    stream_output=False
                )

                if ok:
                    self.after(0, lambda: self._show_apply_success(lang))
                else:
                    self.after(0, lambda: self._show_apply_error(msg))

            except Exception as e:
                self.after(0, lambda: self._show_apply_error(str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))
                self.after(0, self._refresh_all_statuses)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_apply_success(self, lang):
        lang_str = "繁体中文" if lang == "zh-TW" else ("官方原版英文" if lang == "en" else "简体中文")
        msg = f"🎉 配置已成功保存并注入到 Antigravity！\n\n• 当前语言: {lang_str}\n• 顶栏额度显示: {'已开启' if self.var_show_quota.get() else '已关闭'}\n• 极限性能加速: 已注入\n• 全栈遥测阻断: 已生效\n\n若 Antigravity 正在运行中，点击【重启 Antigravity】即可立刻查看崭新效果！"
        messagebox.showinfo("应用成功", msg)

    def _show_apply_error(self, err_msg):
        messagebox.showerror("应用失败", f"部署补丁时遇到错误:\n\n{err_msg}")

    # -------------------------------------------------------------
    # 底部核心动作：还原官方原版英文
    # -------------------------------------------------------------
    def _on_click_restore(self):
        confirm = messagebox.askyesno(
            "确认还原官方原版",
            "确定要还原官方英文原版吗？\n此操作将无损撤销汉化、顶栏额度与注入的优化补丁，恢复官方 app.asar 原始状态。"
        )
        if not confirm:
            return

        self._set_busy(True, "⏳ 正在从官方备份文件恢复原版 app.asar ...")

        def _worker():
            try:
                ok, msg = LocalizationManager.restore(no_kill=True, stream_output=False)
                if ok:
                    self.after(0, lambda: messagebox.showinfo("还原成功", "官方英文原版已成功无痕恢复！\n如需查看效果，可重启 Antigravity 客户端。"))
                else:
                    self.after(0, lambda: messagebox.showwarning("提示", f"还原提示: {msg}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"还原异常: {e}"))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))
                self.after(0, self._refresh_all_statuses)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 底部核心动作：重启客户端
    # -------------------------------------------------------------
    def _on_click_restart_app(self):
        loc = LocalizationManager.get_status()
        install_dir = loc.get("install_dir")
        if not install_dir or not Path(install_dir).exists():
            messagebox.showwarning("警告", "未检测到 Antigravity 安装目录，请先确保已安装该应用。")
            return

        self._set_busy(True, "⏳ 正在重启 Antigravity 客户端...")

        def _worker():
            try:
                # 杀死进程
                if sys.platform.startswith("win"):
                    subprocess.run("taskkill /F /IM Antigravity.exe /T", shell=True, capture_output=True)
                else:
                    subprocess.run("pkill -f Antigravity", shell=True, capture_output=True)

                time.sleep(1.2)

                # 重新拉起
                if sys.platform.startswith("win"):
                    exe = Path(install_dir) / "Antigravity.exe"
                    if exe.exists():
                        subprocess.Popen([str(exe)], creationflags=subprocess.DETACHED_PROCESS)
                else:
                    subprocess.Popen(["open", install_dir])

                self.after(0, lambda: self.var_status_msg.set("Antigravity 客户端重启成功！"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("重启失败", f"无法重新拉起客户端: {e}"))
            finally:
                self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 通知测试动作
    # -------------------------------------------------------------
    def _test_telegram(self):
        cfg = {
            "enabled": True,
            "bot_token": self.var_tg_token.get().strip(),
            "chat_id": self.var_tg_chat.get().strip(),
            "proxy": self.var_tg_proxy.get().strip()
        }
        if not cfg["bot_token"] or not cfg["chat_id"]:
            messagebox.showwarning("缺少参数", "请先输入 Telegram Bot Token 和 Chat ID。")
            return

        self._set_busy(True, "正在测试 Telegram 消息发送...")

        def _worker():
            n = TelegramNotifier(cfg)
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"✅ 发送成功: {msg}" if ok else f"❌ 发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    def _test_feishu(self):
        url = self.var_fs_url.get().strip()
        if not url:
            messagebox.showwarning("缺少参数", "请先输入飞书 Webhook 地址。")
            return

        self._set_busy(True, "正在测试飞书消息发送...")

        def _worker():
            n = FeishuNotifier({"enabled": True, "webhook_url": url})
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"✅ 发送成功: {msg}" if ok else f"❌ 发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    def _test_wecom(self):
        url = self.var_wc_url.get().strip()
        if not url:
            messagebox.showwarning("缺少参数", "请先输入企业微信 Webhook 地址。")
            return

        self._set_busy(True, "正在测试企业微信消息发送...")

        def _worker():
            n = WeComNotifier({"enabled": True, "webhook_url": url})
            ok, msg = n.test()
            self.after(0, lambda: messagebox.showinfo("测试结果", f"✅ 发送成功: {msg}" if ok else f"❌ 发送失败: {msg}"))
            self.after(0, lambda: self._set_busy(False, "就绪"))

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 守护进程与自启控制
    # -------------------------------------------------------------
    def _start_daemon(self):
        """后台启动常驻监控"""
        from main import cmd_start
        cmd_start(None)
        time.sleep(0.5)
        self._refresh_all_statuses()
        self._refresh_log_preview()

    def _stop_daemon(self):
        """停止常驻监控"""
        from main import cmd_stop
        cmd_stop(None)
        time.sleep(0.5)
        self._refresh_all_statuses()
        self._refresh_log_preview()

    def _enable_autostart(self):
        ok, msg = AutostartManager.enable()
        if ok:
            messagebox.showinfo("成功", f"开机自启动设置成功:\n{msg}")
        else:
            messagebox.showwarning("警告", f"开机自启动设置失败:\n{msg}")
        self._refresh_all_statuses()

    def _disable_autostart(self):
        ok, msg = AutostartManager.disable()
        messagebox.showinfo("提示", msg)
        self._refresh_all_statuses()

    def _set_busy(self, busy: bool, message: str = "就绪"):
        """设置界面忙碌状态，防止重复点击"""
        self.var_status_msg.set(message)
        state = "disabled" if busy else "normal"
        self.btn_apply.configure(state=state)
        self.btn_restore.configure(state=state)
        self.btn_restart_app.configure(state=state)
        self.config(cursor="watch" if busy else "")


def launch_gui():
    """启动桌面 GUI 客户端"""
    app = OrbitGui()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
