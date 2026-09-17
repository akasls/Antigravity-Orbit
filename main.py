import os
import sys
from pathlib import Path

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 适配 Windows 控制台编码，防止 GBK 终端下打印 Emoji 导致 UnicodeEncodeError 崩溃
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import socket
import argparse
import platform
import subprocess

from core.config import (
    CONFIG_FILE,
    LOG_FILE,
    STATE_FILE,
    load_config,
    save_config,
)
from core.utils import Logger
from core.monitor import AntigravityMonitor
from core.autostart import AutostartManager
from core.localization import LocalizationManager
from notifiers import get_active_notifiers, TelegramNotifier, FeishuNotifier, WeComNotifier

def cmd_run(args):
    """前台运行监控服务"""
    monitor = AntigravityMonitor()
    monitor.run_loop()

def cmd_start(args):
    """启动后台常驻服务"""
    cfg = load_config()
    port = cfg.get("lock_port", 49222)

    # 检查是否已经在运行
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.close()
    except socket.error:
        print(f"⚠️ 监控服务已经在运行中 (端口 {port} 已被占用)。")
        return

    main_py = Path(__file__).resolve()
    system = platform.system().lower()

    if system == "windows":
        # 在 Windows 上使用 pythonw 无窗口启动，通过 WMI 或 Start-Process 完全脱离控制台
        python_exe = Path(sys.executable)
        pythonw_exe = python_exe.parent / "pythonw.exe"
        runner = str(pythonw_exe) if pythonw_exe.exists() else str(python_exe)
        cmd = f'"{runner}" "{main_py}" run'

        try:
            # 优先使用 PowerShell WMI 创建，脱离当前命令行会话生命周期
            ps_cmd = f'Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine = \'{cmd}\'}}'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
            if res.returncode == 0 and "ProcessId" in res.stdout:
                print("🚀 Antigravity 监控服务已在后台静默启动！")
                print("💡 使用 'python main.py status' 可查看运行状态与日志。")
                return
        except Exception:
            pass

        # 回退为标准 Popen
        subprocess.Popen([runner, str(main_py), "run"], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
        print("🚀 Antigravity 监控服务已在后台启动！")

    else:
        # macOS / Linux
        log_f = open(LOG_FILE, "a")
        subprocess.Popen([sys.executable, str(main_py), "run"], stdout=log_f, stderr=log_f, start_new_session=True)
        print("🚀 Antigravity 监控服务已在后台启动！")
        print("💡 使用 'python main.py status' 可查看运行状态与日志。")

def cmd_stop(args):
    """停止后台监控服务"""
    cfg = load_config()
    port = cfg.get("lock_port", 49222)
    system = platform.system().lower()
    pid_file = PROJECT_ROOT / ".daemon.pid"

    stopped = False

    # 1. 优先根据 .daemon.pid 停止
    if pid_file.exists():
        try:
            pid = pid_file.read_text(encoding="utf-8").strip()
            if pid:
                if system == "windows":
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                else:
                    subprocess.run(f"kill -9 {pid}", shell=True, capture_output=True)
                print(f"🛑 已成功终止监控进程 (PID: {pid})。")
                stopped = True
            try:
                pid_file.unlink()
            except Exception:
                pass
        except Exception:
            pass

    # 2. 根据端口查找 PID 并终止
    if system == "windows":
        try:
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1]:
                    pid = parts[-1]
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                    print(f"🛑 已成功终止监控进程 (PID: {pid})。")
                    stopped = True
                    break
        except Exception:
            pass
    else:
        try:
            output = subprocess.check_output(f"lsof -ti :{port}", shell=True, text=True)
            for pid in output.strip().splitlines():
                subprocess.run(f"kill -9 {pid}", shell=True)
                print(f"🛑 已成功终止监控进程 (PID: {pid})。")
                stopped = True
        except Exception:
            pass

    if not stopped:
        print(f"ℹ️ 未发现正在运行的监控实例 (端口 {port} 未被占用)。")

def cmd_status(args):
    """查看监控服务运行状态"""
    cfg = load_config()
    port = cfg.get("lock_port", 49222)
    
    # 检查运行状态
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_running = False
    try:
        s.bind(("127.0.0.1", port))
        s.close()
    except socket.error:
        is_running = True

    print("=" * 45)
    print("📊【Antigravity Notifier 运行状态】")
    print("=" * 45)
    print(f"• 进程状态: {'🟢 正在运行中 (IDLE/Task 监听中)' if is_running else '🔴 未运行'}")
    print(f"• 监听端口: {port}")
    print(f"• 开机自启: {'🟢 已启用' if AutostartManager.is_enabled() else '⚪ 未启用'}")

    active = get_active_notifiers(cfg)
    names = [n.name for n in active] if active else ["无任何激活通道"]
    print(f"• 活跃通道: {', '.join(names)}")
    print(f"• 配置文件: {CONFIG_FILE}")

    # 客户端汉化状态
    loc_s = LocalizationManager.get_status()
    if loc_s.get("installed"):
        if loc_s.get("is_localized"):
            lang_str = "繁体中文" if loc_s.get("lang") == "zh-TW" else "简体中文"
            loc_desc = f"🟢 已汉化 ({lang_str})"
        else:
            loc_desc = "⚪ 官方原版英文"
    else:
        loc_desc = "⚪ 未检测到客户端"
    print(f"• 界面汉化: {loc_desc}")

    print("\n📜 最近 5 条运行日志:")
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-5:]
                for l in lines:
                    print("  " + l.strip())
        except Exception:
            print("  (暂无日志或读取失败)")
    else:
        print("  (暂无日志记录)")
    print("=" * 45)

def cmd_test(args):
    """测试所有已启用的通知渠道"""
    cfg = load_config()
    notifiers = get_active_notifiers(cfg)
    if not notifiers:
        print("❌ 未发现任何已启用的通知渠道，请先运行 'python main.py setup' 进行配置。")
        return

    print(f"🔍 正在向 {len(notifiers)} 个渠道发送测试消息...")
    for n in notifiers:
        print(f"\n📡 测试通道: [{n.name}]...")
        ok, msg = n.test()
        if ok:
            print(f"✅ [{n.name}] 测试成功: {msg}")
        else:
            print(f"❌ [{n.name}] 测试失败: {msg}")

def cmd_setup(args):
    """交互式综合配置向导 (汉化 + 通知)"""
    print("=" * 60)
    print("✨ 欢迎使用 Antigravity 综合配置向导 ✨")
    print("=" * 60)

    # -------------------------------------------------------------
    # 步骤 1/2: 询问用户是否汉化
    # -------------------------------------------------------------
    print("\n【步骤 1/2: Antigravity 客户端界面汉化】")
    loc_status = LocalizationManager.get_status()
    if loc_status.get("installed"):
        is_loc = loc_status.get("is_localized")
        lang_name = "繁体中文" if loc_status.get("lang") == "zh-TW" else "简体中文"
        stat_label = f"🟢 已安装汉化 ({lang_name})" if is_loc else "⚪ 官方原版英文"
        print(f"• 检测到客户端路径: {loc_status.get('install_dir')}")
        print(f"• 当前界面语言状态: {stat_label}")
    else:
        print("• 客户端状态: ⚪ 未自动检测到默认安装路径")

    print("\n请选择是否进行客户端界面汉化:")
    print("1. 安装 / 更新【简体中文】汉化 (默认推荐)")
    print("2. 安装 / 更新【繁体中文】汉化")
    print("3. 还原官方原版英文界面")
    print("4. 跳过汉化设置 (不进行修改)")

    loc_choice = input("请输入选项 [1/2/3/4, 默认 1]: ").strip()
    if loc_choice in ["", "1", "y", "yes"]:
        print("\n🚀 正在执行简体中文汉化...")
        LocalizationManager.install(tw=False)
    elif loc_choice in ["2", "tw", "t"]:
        print("\n🚀 正在执行繁体中文汉化...")
        LocalizationManager.install(tw=True)
    elif loc_choice in ["3", "r", "restore"]:
        print("\n🔄 正在还原官方原版英文...")
        LocalizationManager.restore()
    else:
        print("⏩ 已跳过客户端汉化设置。")

    # -------------------------------------------------------------
    # 步骤 2/2: 询问用户是否需要配置任务完成通知
    # -------------------------------------------------------------
    print("\n" + "-" * 60)
    print("【步骤 2/2: 长跑任务完成通知推送配置】")
    print("-" * 60)

    cfg = load_config()
    active_notifiers = get_active_notifiers(cfg)
    curr_channels = [n.name for n in active_notifiers] if active_notifiers else ["无"]
    print(f"• 当前已激活通知渠道: {', '.join(curr_channels)}")

    notify_choice = input("是否需要配置任务完成通知机器人? [Y/n]: ").strip().lower()
    if notify_choice in ["", "y", "yes"]:
        tg_cfg = cfg["channels"].setdefault("telegram", {})
        fs_cfg = cfg["channels"].setdefault("feishu", {})
        wc_cfg = cfg["channels"].setdefault("wecom", {})

        print("\n[请选择通知推送通道]")
        print("1. Telegram Bot (支持国内外直连与代理)")
        print("2. 飞书自定义机器人 (Webhook)")
        print("3. 企业微信机器人 (Webhook)")
        ch_choice = input("请选择要配置的通道 [1/2/3, 默认 1]: ").strip() or "1"

        if ch_choice == "1":
            tg_cfg["enabled"] = True
            print("\n--- 🤖 Telegram 配置 ---")
            curr_token = tg_cfg.get("bot_token", "")
            prompt_token = f"请输入 Telegram Bot Token [{curr_token[:6]}...]: " if curr_token else "请输入 Telegram Bot Token: "
            token_input = input(prompt_token).strip()
            if token_input:
                tg_cfg["bot_token"] = token_input

            curr_chat = tg_cfg.get("chat_id", "")
            prompt_chat = f"请输入 Chat ID [{curr_chat}]: " if curr_chat else "请输入 Chat ID: "
            chat_input = input(prompt_chat).strip()
            if chat_input:
                tg_cfg["chat_id"] = chat_input

            curr_proxy = tg_cfg.get("proxy", "")
            print("\n🌐 代理设置（如无法直连 Telegram，可填写 Clash 7890 或 v2ray 10808 等代理地址）：")
            prompt_proxy = f"代理地址 (直接回车保持 [{curr_proxy or '不设代理'}], 输入 'none' 清除): "
            proxy_input = input(prompt_proxy).strip()
            if proxy_input.lower() == "none":
                tg_cfg["proxy"] = ""
            elif proxy_input:
                tg_cfg["proxy"] = proxy_input

            save_config(cfg)
            print("\n正在测试 Telegram 连通性...")
            t = TelegramNotifier(tg_cfg)
            ok, msg = t.test()
            if ok:
                print(f"✅ Telegram 连接测试成功: {msg}！")
            else:
                print(f"⚠️ Telegram 连接测试失败: {msg}")
                print("提示: 你可以稍后在 config.json 中修改代理或 Token。")

        elif ch_choice == "2":
            fs_cfg["enabled"] = True
            print("\n--- 🕊️ 飞书 Webhook 配置 ---")
            curr_url = fs_cfg.get("webhook_url", "")
            prompt_url = f"请输入飞书 Webhook 地址 [{curr_url}]: " if curr_url else "请输入飞书 Webhook 地址: "
            url_in = input(prompt_url).strip()
            if url_in:
                fs_cfg["webhook_url"] = url_in
            save_config(cfg)
            f = FeishuNotifier(fs_cfg)
            ok, msg = f.test()
            if ok:
                print("✅ 飞书测试消息已成功送达！")
            else:
                print(f"⚠️ 飞书发送失败: {msg}")

        elif ch_choice == "3":
            wc_cfg["enabled"] = True
            print("\n--- 💬 企业微信 Webhook 配置 ---")
            curr_url = wc_cfg.get("webhook_url", "")
            prompt_url = f"请输入企业微信 Webhook 地址 [{curr_url}]: " if curr_url else "请输入企业微信 Webhook 地址: "
            url_in = input(prompt_url).strip()
            if url_in:
                wc_cfg["webhook_url"] = url_in
            save_config(cfg)
            w = WeComNotifier(wc_cfg)
            ok, msg = w.test()
            if ok:
                print("✅ 企业微信测试消息已成功送达！")
            else:
                print(f"⚠️ 企业微信发送失败: {msg}")

        # 开机自启配置
        print("\n--- 🚀 开机自启动设置 ---")
        is_auto = AutostartManager.is_enabled()
        auto_prompt = f"是否设置开机自动启动后台监控? ({'当前: 已开启' if is_auto else '当前: 未开启'}) [Y/n]: "
        auto_choice = input(auto_prompt).strip().lower()
        if auto_choice in ["", "y", "yes"]:
            ok, msg = AutostartManager.enable()
            if ok:
                print(f"✅ {msg}")
            else:
                print(f"⚠️ {msg}")
        elif auto_choice in ["n", "no"]:
            ok, msg = AutostartManager.disable()
            print(f"ℹ️ {msg}")

        # 是否立即启动后台监控
        start_choice = input("\n是否立即启动后台监控进程? [Y/n]: ").strip().lower()
        if start_choice in ["", "y", "yes"]:
            cmd_start(args)

    else:
        print("⏩ 已跳过任务通知机器人配置。")

    print("\n" + "=" * 60)
    print("🎉 配置向导执行完毕！")
    print("💡 常用提示:")
    print("   • 双击运行 'install.bat' 可随时重新配置或管理汉化。")
    print("   • 运行 'python main.py status' 可查看监控服务与汉化状态。")
    print("   • 运行 'python main.py stop' 可停止后台监控服务。")
    print("=" * 60)

def cmd_autostart(args):
    action = args.action
    if action == "enable":
        ok, msg = AutostartManager.enable()
        print(("✅ " if ok else "❌ ") + msg)
    elif action == "disable":
        ok, msg = AutostartManager.disable()
        print(("✅ " if ok else "❌ ") + msg)
    elif action == "status":
        enabled = AutostartManager.is_enabled()
        print(f"开机自启动状态: {'🟢 已启用' if enabled else '🔴 未启用'}")

def cmd_localize(args):
    """管理 Antigravity 客户端汉化"""
    action = getattr(args, "action", None)
    install_dir = getattr(args, "dir", None)
    no_kill = getattr(args, "no_kill", False)

    if action == "status":
        status = LocalizationManager.get_status(install_dir)
        print(LocalizationManager.format_status(status))
        return

    if action == "install":
        tw = getattr(args, "tw", False)
        ok, msg = LocalizationManager.install(tw=tw, install_dir=install_dir, no_kill=no_kill)
        if not ok:
            print(f"❌ {msg}")
        return

    if action == "restore":
        ok, msg = LocalizationManager.restore(install_dir=install_dir, no_kill=no_kill)
        if not ok:
            print(f"❌ {msg}")
        return

    # 无参数交互式菜单
    print("=" * 55)
    print("🌐 欢迎使用 Antigravity 客户端汉化管理向导")
    print("=" * 55)

    status = LocalizationManager.get_status(install_dir)
    if not status.get("installed"):
        print("⚠️ 未自动探测到 Antigravity 安装目录。")
        user_dir = input("请输入 Antigravity 安装目录路径 (回车跳过): ").strip()
        if user_dir:
            install_dir = user_dir
            status = LocalizationManager.get_status(install_dir)

    is_loc = status.get("is_localized")
    lang = "繁体中文" if status.get("lang") == "zh-TW" else "简体中文"
    status_text = f"🟢 已汉化 ({lang})" if is_loc else "⚪ 官方英文原版"
    print(f"\n当前客户端状态: {status_text}")
    print(f"软件安装路径: {status.get('install_dir') or '未检测到'}")

    print("\n[请选择操作]")
    print("1. 安装 / 更新【简体中文】汉化 (默认推荐)")
    print("2. 安装 / 更新【繁体中文】汉化")
    print("3. 一键卸载汉化，恢复官方原版英文")
    print("4. 查看汉化与客户端详细检测状态")
    print("0. 退出")

    choice = input("\n请输入选项编号 [1/2/3/4/0, 默认 1]: ").strip() or "1"

    if choice == "1":
        LocalizationManager.install(tw=False, install_dir=install_dir)
    elif choice == "2":
        LocalizationManager.install(tw=True, install_dir=install_dir)
    elif choice == "3":
        LocalizationManager.restore(install_dir=install_dir)
    elif choice == "4":
        print(LocalizationManager.format_status(LocalizationManager.get_status(install_dir)))
    else:
        print("已取消操作。")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Task Completion Notifier & Localization CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # setup
    subparsers.add_parser("setup", help="运行交互式安装与配置向导")
    # run
    subparsers.add_parser("run", help="前台运行监控循环 (守护模式)")
    # start
    subparsers.add_parser("start", help="启动后台驻留进程")
    # stop
    subparsers.add_parser("stop", help="停止后台驻留进程")
    # status
    subparsers.add_parser("status", help="查看监控服务状态与最新日志")
    # test
    subparsers.add_parser("test", help="发送一条测试通知")

    # autostart
    p_auto = subparsers.add_parser("autostart", help="管理开机自启动")
    p_auto.add_argument("action", choices=["enable", "disable", "status"], help="启用/禁用/查看自启状态")

    # localize / hanhua
    for sub_name in ["localize", "hanhua"]:
        p_loc = subparsers.add_parser(sub_name, help="安装、更新或还原 Antigravity 界面中文汉化")
        p_loc.add_argument("action", nargs="?", choices=["status", "install", "restore"], help="操作: status (查看状态), install (安装汉化), restore (恢复英文)")
        p_loc.add_argument("--tw", "--traditional", action="store_true", dest="tw", help="安装繁体中文语言包")
        p_loc.add_argument("--dir", default=None, help="手动指定 Antigravity 安装目录")
        p_loc.add_argument("--no-kill", action="store_true", help="不自动终止运行中的 Antigravity 进程")

    args = parser.parse_args()

    if not args.subcommand:
        # 无参数默认进入 setup 向导
        cmd_setup(args)
    elif args.subcommand == "setup":
        cmd_setup(args)
    elif args.subcommand == "run":
        cmd_run(args)
    elif args.subcommand == "start":
        cmd_start(args)
    elif args.subcommand == "stop":
        cmd_stop(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "test":
        cmd_test(args)
    elif args.subcommand == "autostart":
        cmd_autostart(args)
    elif args.subcommand in ["localize", "hanhua"]:
        cmd_localize(args)

if __name__ == "__main__":
    main()
