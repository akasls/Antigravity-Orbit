# 🛰️ Antigravity Orbit (反重力轨道增强套件)

<p align="center">
  <a href="https://github.com/akasls/Antigravity-Orbit">
    <img src="https://img.shields.io/badge/Antigravity-Orbit-6366f1?style=for-the-badge&logo=google&logoColor=white" alt="Antigravity Orbit" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License MIT" />
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/Antigravity-2.0+-FF6F00?style=flat-square" alt="Antigravity 2.0+" />
</p>

> 🚀 **Antigravity Orbit** 是专为 **Google Antigravity** 打造的一体化生产力伴侣套件。  
> 深度整合 **【现代化客户端全界面深度汉化】** 与 **【长跑任务完工跨平台即时推送（Telegram / 飞书 / 企微）】**，让您的 AI 编程与智能体协同如在轨道运行般顺畅。

---

## 🌟 核心功能特性

### 🌐 1. 现代化客户端全界面深度汉化
- **深度适配 Antigravity 2.0+ 架构**：针对 Electron ASAR 架构与 DOM 渲染特性定制，原子级安全注入。
- **全方位模块化词库**：
  - **通用设置与浏览器子代理**：完整覆盖浏览器代理、常规设置、偏好选项与链接。
  - **驱动模型与配额用量**：精确翻译模型设置、方案详情、每周与 5 小时限额、动态剩余倒计时长句。
  - **个性化定制 / 技能 / MCP**：支持插件市场、官方推荐目录、技能库与自定义 MCP 服务器配置。
  - **AI 对话页面与工件卡片**：交付件（Walkthrough、实施计划、任务清单）、代码修改统计（`X files changed`）、深度思考时长（`已深度思考 X 秒` / `已思考 X 秒`）动态计算。
  - **右键菜单与工作区侧边栏**：会话列表操作、分栏、重命名、终端列表、上传列表、暂存区与未提交代码变更面板。
- **简繁双模一键切换**：内置严格镜像对齐的简体中文 (`zh-CN`) 与繁体中文 (`zh-TW`) 词库。
- **纯净品牌与界面优化**：
  - **100% 保持官方原生品牌**：坚决不篡改品牌名，严格保留官方英文 `Antigravity`。
  - **移除多余推广按钮**：三层阻断并彻底隐藏界面右上角冗余的“安装 IDE”按钮。
- **代码沙箱隔离保护**：内置 Monaco 编辑器、代码块、用户消息正文的高优先级隔离沙箱，**坚决不误译任何实际代码**。
- **一键无损还原**：注入前自动生成官方原始备份 (`app.asar.bak`)，随时可一键秒级还原官方原版英文。

---

### 🔔 2. 任务完工智能感知与即时通知
- **零骚扰·精准状态感知**：深入底层状态引擎，严格识别任务完整结束点，彻底过滤中间工具调用过程，仅在长跑任务彻底完成时触发提醒。
- **真实工程名称解析**：自动解析对话主题与工作区真实项目名称（如 `📁 工程: Antigravity-Orbit`），告别临时文件名乱码。
- **多通道即时推送**：
  - **Telegram Bot**（支持直连及 Clash/v2ray 本地代理网络自适应）
  - **飞书群自定义机器人 (Webhook)**
  - **企业微信群机器人 (Webhook)**
- **电脑开机全自动静默自启**：支持 Windows 注册表无窗口后台驻留 (`pythonw`)，电脑开机自启，后台守护零干扰。

---

## 📱 通知消息预览

```text
🔔【反重力任务已完成】
📁 工程: Antigravity-Orbit (任务完成与汉化系统全面重构)
⚡ 状态: 正常完成
🕒 时间: 2026-09-17 16:36:20

📝 回复摘要:
全量单元测试与压力测试已通过，所有模块验证正常。
相关更新已全量部署，并已完成版本提交！
```

---

## ⚡ 快速开始 (1 分钟上手)

### 方式一：Windows 用户（强烈推荐）

1. 下载或克隆本项目到本地：
   ```bash
   git clone https://github.com/akasls/Antigravity-Orbit.git
   cd Antigravity-Orbit
   ```
2. 双击运行根目录下的 **`install.bat`**。
3. 按照控制台向导顺序操作：
   - **【步骤 1/2】界面汉化**：自动检测客户端，选择 `1` 安装简体中文（或 `2` 繁体中文）。
   - **【步骤 2/2】通知配置**：选择配置 Telegram / 飞书 / 企业微信机器人，输入 Token/Webhook，即时发送连通性测试。
   - **开机自启**：按提示输入 `y` 即可写入开机启动项并立即后台运行。

---

### 方式二：macOS / Linux 用户

```bash
git clone https://github.com/akasls/Antigravity-Orbit.git
cd Antigravity-Orbit
bash install.sh
```

---

## 🛠️ CLI 常用管理命令

本项目提供全功能命令行工具 `main.py`：

### 🌐 1. 客户端汉化管理

```bash
# 查看 Antigravity 安装路径及当前汉化状态
python main.py localize status

# 一键安装 / 更新简体中文汉化 (推荐)
python main.py localize install

# 一键安装 / 更新繁体中文汉化
python main.py localize install --tw

# 卸载汉化，恢复官方原版英文界面
python main.py localize restore

# 呼出交互式汉化管理向导
python main.py localize
```

### 🔔 2. 监控服务与通知管理

```bash
# 查看当前监控状态、实时日志与运行健康度
python main.py status

# 手动发送一条测试通知以验证通道是否正常
python main.py test

# 重新运行交互式配置向导 (汉化 + 通知)
python main.py setup

# 启动后台常驻监控进程
python main.py start

# 停止后台常驻监控进程
python main.py stop

# 管理开机自启动
python main.py autostart status    # 查看自启状态
python main.py autostart enable    # 启用开机自启
python main.py autostart disable   # 禁用开机自启
```

---

## 🤖 如何获取 Telegram 机器人凭据？

1. **获取 Bot Token**：
   - 在 Telegram 中搜索官方机器人 [@BotFather](https://t.me/botfather)。
   - 发送 `/newbot`，根据提示给机器人命名，获取 API Token（如 `7488372875:AAH...`）。
2. **获取 Chat ID**：
   - 搜索并联系 [@userinfobot](https://t.me/userinfobot)，发送任意消息，即可看到回复的 `Id`（用户 ID 或群组 ID，群组通常以 `-100` 开头）。
3. **关键提示**：
   - 在首次接收消息前，**请务必先私聊机器人点击一次 `Start`**，或者将机器人加入接收通知的群组并给予发言权限！
   - 若在中国大陆网络环境下，可配置代理端口（如 Clash 的 `7890` 或 v2rayN 的 `10808`），本程序原生支持代理转发。

---

## ⚙️ 配置文件说明 (`config.json`)

运行 `main.py setup` 后会自动生成配置，也可以参考 `config.example.json` 手动修改：

```json
{
  "enabled": true,
  "scan_interval": 3.0,
  "lock_port": 49222,
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
      "chat_id": "-100xxxxxxxxxx",
      "proxy": "http://127.0.0.1:10808"
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
Antigravity-Orbit/
├── core/                              # 核心业务逻辑
│   ├── autostart.py                   # 跨平台开机自启管理器 (Windows 注册表/macOS plist)
│   ├── config.py                      # 配置加载、合并与持久化
│   ├── localization.py                # 客户端汉化管理器桥接模块
│   ├── monitor.py                     # Antigravity 任务状态嗅探与通知调度
│   └── utils.py                       # 进程单例锁、日志与格式化工具
├── localization/                      # 现代化客户端汉化引擎
│   ├── core/
│   │   ├── asar_patcher.js            # Electron ASAR 安全原子解包、打补丁与重新封装
│   │   ├── engine.js                  # 汉化主调度控制器
│   │   └── runtime_template.js        # 前端 DOM 注入、正则模式匹配与动态沙箱
│   ├── dictionaries/                  # 简体中文模块化专业词典 (8 大维度)
│   │   ├── chat.json                  # AI 对话、工件、徽章
│   │   ├── context_menus.json         # 右键与上下文菜单
│   │   ├── navigation.json            # 导航栏与主菜单
│   │   ├── settings_app.json          # 应用与远程控制
│   │   ├── settings_browser.json      # 浏览器子代理设置
│   │   ├── settings_customization.json# 技能、规则、MCP 插件
│   │   ├── settings_general.json      # 通用设置与权限
│   │   ├── settings_models.json       # 驱动模型与配额用量
│   │   └── common.json                # 通用基础词汇
│   └── dictionaries_tw/               # 繁体中文镜像词典 (结构完全对齐)
├── notifiers/                         # 推送通知模块
│   ├── base.py                        # 通知基类
│   ├── telegram.py                    # Telegram 通道 (含代理自适应)
│   ├── feishu.py                      # 飞书 Webhook 通道
│   └── wecom.py                       # 企业微信 Webhook 通道
├── install.bat                        # Windows 单一交互配置向导脚本
├── install.sh                         # macOS / Linux 交互配置向导脚本
├── main.py                            # 统一 CLI 命令行入口
├── config.example.json                # 配置文件示例模板
└── README.md                          # 项目说明文档
```

---

## 🔒 隐私与安全性

1. **100% 本地运算**：本工具仅在本地读取 Antigravity 客户端日志与本地会话状态，绝不上传任何用户代码、对话正文或敏感信息到第三方服务器。
2. **防凭据泄露设计**：项目仓库已配置严格的 `.gitignore`，您的 `config.json`（包含 Telegram Token、Webhook URL 等）、运行日志与备份文件绝不会被意外提交到版本库中。

---

## 📄 开源协议

本项目遵循 [MIT 许可证](LICENSE)。
欢迎提交 Issue 与 Pull Request 共同改进！
