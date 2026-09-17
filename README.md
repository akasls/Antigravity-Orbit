# 🔔 Antigravity Toolkit & Notifier (反重力任务通知与中文汉化综合工具箱)

> 🚀 为 Google Antigravity (反重力 AI 编程助手) 量身打造的一体化生产力工具。集 **【客户端全界面中文汉化】** 与 **【长跑任务完成多渠道即时推送】** 于一体！

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![License MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

---

## 🌟 核心功能特性

### 🌐 1. Antigravity 客户端全界面中文汉化
- 深度适配 **Antigravity 2.0+** (ASAR 包注入) 与 **1.0** (HTML 架构)。
- **全方位本地化**：覆盖软件主界面、顶部系统菜单、任务栏托盘菜单、加载页动画、设置面板、MCP 知识库管理面板等。
- **简繁双模支持**：支持标准简体中文（zh-CN）与繁体中文（zh-TW）。
- **终极 DOM 隔离引擎**：内置 WeakMap 缓存与 DOM 树回溯隔离，智能识别代码编辑器 (`monaco-editor`) 与聊天历史容器，**坚决杜绝 AI 聊天气泡被误译**，确保指令原文纯净。
- **极速一键还原**：注入前全自动创建官方原始包备份 (`app.asar.bak`)，随时可一键无损还原官方原版英文。
- **纯净品牌与界面优化**：严格保留官方英文 `Antigravity` 品牌标识，专注界面汉化，并自动移除右上角多余的“安装 IDE”推广按钮。


### 🔔 2. 任务完工智能感知与即时推送
- 🧠 **零多余骚扰（精准状态感知）**：深入反重力底层引擎与 SQLite 状态库，严格识别 `CASCADE_RUN_STATUS_IDLE` 与后台子任务完成状态，**彻底过滤中间进度过程**，仅在整轮任务彻底完工时触发通知。
- 📁 **精准工程名称解析**：自动解析 Antigravity 真实工作区目录与对话主题（如 `📁 工程: pikpak (PikPak Cloud System)`），绝不误将 `walkthrough.md` 等临时文件名当作工程名。
- 🌐 **双通道自适应网络**：内置智能连接探测，国内环境自动尝试直连与本地代理（Clash / v2rayN 等），无缝收发 Telegram 消息。
- 🔀 **多渠道支持**：支持 **Telegram Bot**、**飞书群机器人 (Webhook)**、**企业微信机器人 (Webhook)**，随时随地接收消息。
- 🔄 **开机全自动静默自启**：支持 Windows 注册表无窗口后台驻留 (`pythonw`)、macOS LaunchAgent、Linux systemd 用户服务，电脑重启依然常驻守护。

---

## 📱 通知消息预览

```text
🔔【反重力任务已完成】
📁 工程: pikpak (PikPak Multi-Account Cloud System)
⚡ 状态: 正常完成
🕒 时间: 2026-09-17 11:05:20

📝 回复摘要:
全量单元测试与压力测试已通过，16 个核心功能模块验证正常。
相关优化代码已全量提交至 main 分支，并已完成镜像自动构建！
```

---

## ⚡ 快速开始 (1 分钟上手)

### 方式一：Windows 用户（推荐）
直接双击运行 **`install.bat`**，控制台向导将依次引导：
1. **第一步：客户端界面汉化**（检测当前状态，一键安装简体/繁体中文汉化包，或还原官方原版英文）。
2. **第二步：长跑任务完成通知**（询问是否配置 Telegram / 飞书 / 企业微信推送机器人，提供即时连通测试与开机自启设置）。

### 方式二：macOS / Linux 用户
```bash
git clone https://github.com/your-username/antigravity-notifier.git
cd antigravity-notifier
bash install.sh
```

---

## 🛠️ CLI 常用管理命令

### 🌐 1. 客户端汉化管理命令 (`localize` 或 `hanhua`)

```bash
# 查看 Antigravity 安装路径及当前汉化状态
python main.py localize status

# 进入交互式汉化向导
python main.py localize

# 一键安装 / 更新简体中文汉化 (推荐方式: 保留 Antigravity 品牌名)
python main.py localize install

# 一键安装繁体中文汉化
python main.py localize install --tw

# 卸载汉化，恢复官方原版英文
python main.py localize restore

# 手动指定 Antigravity 安装目录安装
python main.py localize install --dir "C:\Custom\Antigravity"
```

### 🔔 2. 监控服务与通知管理命令

```bash
# 查看当前监控状态、日志与客户端汉化状态
python main.py status

# 发送一条测试通知以验证通道是否正常
python main.py test

# 重新运行通知渠道配置向导
python main.py setup

# 启动后台常驻监控进程
python main.py start

# 停止后台监控进程
python main.py stop

# 管理开机自启动
python main.py autostart status    # 查看自启状态
python main.py autostart enable    # 启用开机自启
python main.py autostart disable   # 禁用开机自启
```

---

## 🤖 如何获取 Telegram 凭据？

1. **Bot Token**：
   - 打开 Telegram，搜索并联系官方 [@BotFather](https://t.me/botfather)。
   - 发送 `/newbot`，按照提示输入机器人名称与用户名。
   - 创建成功后，会获得一段 HTTP API Token（格式如 `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`）。
2. **Chat ID**：
   - 在 Telegram 搜索并联系 [@userinfobot](https://t.me/userinfobot)，向其发送任意消息。
   - 机器人会立即回复你的专属 `Id`（一串纯数字，如 `987654321`）。
3. **重要提示**：在收到通知前，**请先在 Telegram 中找到你创建的机器人并点击一次 `Start`**，否则机器人无法主动向你推送消息！

---

## ⚙️ 高级配置说明 (`config.json`)

配置文件会在首次运行 `setup` 后自动生成，也可以参考 `config.example.json` 手动创建：

```json
{
  "enabled": true,
  "scan_interval": 3.0,
  "lock_port": 49222,
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID",
      "proxy": "http://127.0.0.1:7890"
    },
    "feishu": {
      "enabled": false,
      "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
    },
    "wecom": {
      "enabled": false,
      "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx"
    }
  }
}
```

---

## 📂 项目文件结构

```text
反重力通知/
├── core/
│   ├── autostart.py           # 跨平台开机自启管理器
│   ├── config.py              # 配置加载与管理
│   ├── localization.py        # 汉化管理器核心
│   ├── monitor.py             # 反重力任务状态嗅探与通知调度
│   └── utils.py               # 单例锁与消息格式化
├── localization/
│   ├── dicts/                 # 简体中文翻译词典 (6 大模块)
│   ├── dicts_tw/              # 繁体中文翻译词典
│   └── engine.js              # ASAR 注入与解包底层引擎
├── notifiers/                 # Telegram / 飞书 / 企业微信通道
├── install.bat                # Windows 综合向导脚本
├── install.sh                 # macOS / Linux 综合向导脚本
├── 一键安装中文汉化.bat        # Windows 独立汉化双击入口
├── 一键还原官方英文.bat        # Windows 独立还原双击入口
├── main.py                    # 统一 CLI 管理入口
└── README.md
```

---

## 🔒 隐私与安全性

- **全本地解析**：本工具仅在本地读取反重力日志与本地包，绝不上传任何代码或对话到任何第三方服务器。
- **开源防泄密**：仓库自带严格的 `.gitignore`，即使执行 `git commit`，也不会将个人凭据或备份文件上传。

---

## 📄 开源许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
