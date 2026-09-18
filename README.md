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

> 🚀 **Antigravity Orbit** 是专为 **Google Antigravity** 打造的一体化独立桌面管理与生产力伴侣套件。  
> 拥有 **【左侧分类导航独立桌面客户端 (Native GUI)】**、**【系统托盘后台静默驻留】**、**【全局系统提示词/角色规则可视化管理】**、**【顶栏实时模型额度胶囊 (Gemini / Claude / GPT)】**、**【全界面深度汉化】**、**【专属网络代理接管 (彻底取代 Proxifier)】**、**【任务异常自动重试与自愈】** 与 **【长跑任务完工跨平台推送（Telegram / 飞书 / 企微）】**，让您的 AI 编程与智能体协同如在轨道运行般顺畅。

---

## 🌟 核心功能特性

### 🖥️ 1. 独立桌面可视化管理客户端 (Native Edge WebView2 GUI v3.0.0)
- **全新微前端现代架构**：基于 Windows 原生 **Edge WebView2** 渲染引擎与现代 Fluent / Tailwind 本地设计系统，实现 0.15s 秒级冷启动与 60~120 FPS 显卡硬件直推！
- **现代 Fluent / macOS 分类导航架构**：全新重塑为左侧 7 大模块分类导航 + 右侧独立卡片流，彻底告别超长滚动与老旧拼凑感：
  - 📌 **概览与服务**：检测 Antigravity 本地状态、常驻守护、托盘行为、客户端自启动与一键深度瘦身。
  - 🎨 **界面与外观**：多语言切换（简中/繁中/英文）、移除右上角推广按钮、紧凑代码排版模式。
  - ⚡ **性能与代理**：顶栏额度胶囊、GPU 硬件加速、防休眠降频、4GB V8 堆内存、专属网络代理。
  - 🛡️ **自愈与额度**：任务异常报错自动重试（恢复工作重置计数）、额度耗尽熔断通知、重试超限失败通知。
  - 📝 **系统提示词**：实时查看/修改/备份全局 `AGENTS.md`，内置 5 大预设角色模板一键套用。
  - 🔔 **消息推送**：Telegram / 飞书 / 企业微信推送凭据配置与在线即时测试。
  - 📜 **运行日志**：守护进程心跳与任务推送记录即时滚动预览与清空。
- **现代化视觉组件系统**：iOS/Fluent 风格丝滑滑动开关、纯本地 SVG 矢量图标、优雅悬浮非阻塞 Toast 提示、代码级等宽系统提示词编辑器，任何缩放比例下**绝对零截断、零错位**。
- **系统托盘后台静默常驻 (System Tray Integration)**：
  - 点击窗口关闭按钮默认平滑缩入托盘图标，右键支持“打开管理中心”、“重启客户端”与“彻底退出”。
  - 支持随 Windows 开机静默启动直接驻留托盘（`--tray`），无需手动开启。
- **一键热应用与一键无损还原**：一键保存并注入生效，也可一键随时无痕撤销所有补丁恢复官方原版。

---

### 📝 2. 全局系统提示词与规则可视化管理器 (System Prompt Manager)
- **底层精准映射**：直接读写 Antigravity 核心注入的全局规则文件 `~/.gemini/config/AGENTS.md`（对应智能体底层 `<RULE[user_global]>`）。
- **即时生效无需重启**：修改保存后无需重启 Antigravity，下一个新会话或新任务直接生效！
- **内置 5 大精选角色模板**：
  1. 🛡️ **网络安全与底层系统工程**：专注于底层协议、API Hooking、免杀逆向分析与安全仿真；
  2. 💻 **资深全栈工程师与架构专家**：注重设计模式、高可用架构、边界防护与类型安全；
  3. ⚡ **极简极速代码助手**：杜绝废话和长篇客套，直接输出高精度代码与改动；
  4. 🧪 **代码审计与自动化测试专家**：深挖边界用例、OWASP 漏洞与内存泄漏；
  5. 🔄 **官方纯净空白规则**：恢复原版空提示词状态。
- **安全自动备份**：每次保存均自动在同目录生成 `AGENTS.md.bak`，支持一键恢复上一次历史备份。

---

### 📊 3. 顶部标题栏实时模型额度显示 (Top-Right Quota Badge)
- **免鉴权内部直连**：逆向重构 ConnectRPC 内部端点 `/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`，直接获取各模型限额。
- **原生融入顶部标题栏**：无缝挂载于右上角安全区，微磨砂圆角半透明胶囊，不影响窗口拖拽与系统控制按钮。
- **双模型状态指示灯**：
  - `🟢 Gemini XX% · 🟣 Claude XX%`（正常时采用官方模型主色，低于 50% 自动变橙黄，低于 20% 自动变红告警）。
- **交互式浮动详情面板**：
  - 点击胶囊展开半透明详情卡片，显示 Gemini 与 Claude & GPT 的 **5 小时限额进度条** 与 **周限额进度条**。
  - 倒计时精确计算（`距离刷新还有 X 天 X 小时` / `距离刷新还有 X 小时 X 分钟`）。
  - 内置“🔄 立即刷新”按钮，支持自定义定时轮询及窗口聚焦自动极速刷新。

---

### 🌐 4. 现代化客户端全界面深度汉化
- **深度适配 Antigravity 2.0+ 架构**：针对 Electron ASAR 架构与 DOM 渲染特性定制，原子级安全注入。
- **全方位模块化词库**：
  - **通用设置与浏览器子代理**：完整覆盖浏览器代理、常规设置、偏好选项与链接。
  - **驱动模型与配额用量**：精确翻译模型设置、方案详情、每周与 5 小时限额、动态剩余倒计时长句。
  - **个性化定制 / 技能 / MCP**：支持插件市场、官方推荐目录、技能库与自定义 MCP 服务器配置。
  - **AI 对话页面与工件卡片**：交付件（Walkthrough、实施计划、任务清单）、代码修改统计（`X files changed`）、深度思考时长（`已深度思考 X 秒` / `已思考 X 秒`）动态计算。
  - **右键菜单与工作区侧边栏**：会话列表操作、分栏、重命名、终端列表、上传列表、暂存区与未提交代码变更面板。
- **简繁双模一键切换**：内置严格镜像对齐的简体中文 (`zh-CN`) 与繁体中文 (`zh-TW`) 词库。
- **纯净品牌与界面净化**：
  - **100% 保持官方原生品牌**：坚决不篡改品牌名，严格保留官方英文 `Antigravity`。
  - **彻底移除多余推广按钮**：无论处于 `Open IDE` 还是 `Install IDE` 状态，均全方位阻断并自动消除其外层容器，右上角彻底整洁无残留。
- **代码沙箱隔离保护**：内置 Monaco 编辑器、代码块、用户消息正文的高优先级隔离沙箱，**坚决不误译任何实际代码**。
- **一键无损还原**：注入前自动生成官方原始备份 (`app.asar.bak`)，随时可一键秒级还原官方原版英文。

---

### ⚡ 5. 极致性能加速与专属网络代理 (Performance Boost & Dedicated Proxy)
- **Antigravity 专属网络代理 (彻底取代 Proxifier)**：
  - 原生支持 HTTP / SOCKS5 代理。直接在 Chromium 与 Go 核心 Language Server 层面注入代理与环境变量，全面接管 Google API、git.exe、ssh.exe 与模型推理网络请求，无需运行 Proxifier。
- **GPU 硬件加速与零拷贝渲染**：强制开启 2D 页面与 Canvas 的 GPU 栅格化加速（`enable-gpu-rasterization` / `enable-zero-copy`），显卡硬件直推，流式打字与超长文档滚动丝滑流畅，CPU 占用骤降。
- **解除后台防降频与防冻结**：
  - 默认情况下，Electron 会在窗口置于后台或被其他窗口遮挡时将定时器降频至 1Hz。
  - 本套件注入 `disable-background-timer-throttling` 与 `disable-backgrounding-occluded-windows`，彻底解决**切到其他 IDE 窗口编码时 Antigravity 生成变慢、后台任务被挂起**的痛点。
- **V8 引擎 4GB 堆内存扩容**：注入 `--js-flags="--max-old-space-size=4096"`，大幅扩充 JavaScript 垃圾回收堆内存空间，彻底告别超大项目索引与几十轮超长会话下的频繁 GC 卡顿。

---

### 🛡️ 6. 全栈关闭遥测与数据隐私保护 (Anti-Telemetry)
- **Go 核心服务级阻断**：利用官方 Language Server 原生未公开参数 `--disable_telemetry=true`，从后端进程根源掐断遥测采集。
- **Chromium / Electron 客户端级屏蔽**：注入 `--disable-metrics`、`--disable-telemetry`、`--disable-breakpad`、`--no-report-upload` 与 `--disable-domain-reliability`，阻断匿名行为打点、系统诊断与崩溃转储上报。
- **DevTools MCP 收集器中和**：全面中和内置 `chrome-devtools-mcp` 插件中的 Google Clearcut 遥测回传与 Watchdog 进程网络外发。

---

### 🛡️ 7. 任务异常自动重试与额度耗尽熔断告警
- **异常自动重试 (Auto-Retry on Error)**：智能体任务执行过程中若遭遇网络抖动或偶发服务异常，客户端自动点击重试（可配置 1~10 次，默认 3 次）。
- **智能工作态复位**：重试后智能体一旦恢复正常工作（流式输出/深度思考），**自动将重试计数清零重置为 0**，满足长时间持续任务的自愈需求。
- **额度用尽熔断保护**：一旦检测到 429、Rate Limit 或模型额度降至 0%，立即阻断重试，向各通知渠道发送【⚠️ 任务中断：额度已耗尽】告警。
- **重试超限告警通知**：连续重试达到最大次数仍无法恢复工作时，向各通知渠道发送【❌ 任务执行失败】告警。

---

### 🔔 8. 任务完工智能感知与即时通知
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
📁 工程: Antigravity-Orbit
⚡ 状态: 正常完成
🕒 时间: 2026-09-18 16:30:00

📝 回复摘要 / 详情:
已成功完成全量代码重构与功能验证！
```

```text
⚠️【反重力任务中断：额度已耗尽】
📁 工程: Antigravity-Orbit
⚡ 状态: 任务中断：额度已耗尽
🕒 时间: 2026-09-18 16:35:00

📝 回复摘要 / 详情:
Gemini 额度耗尽 (5h限制剩余: 0%, 周限制剩余: 12%)，任务已自动暂停保护，请等待限额刷新或切换模型。
```

```text
❌【反重力任务执行失败】
📁 工程: Antigravity-Orbit
⚡ 状态: 任务失败：重试次数超限
🕒 时间: 2026-09-18 16:40:00

📝 回复摘要 / 详情:
任务在执行过程中发生异常，已连续自动重试 3 次仍未恢复。
```

---

## ⚡ 快速开始 (1 分钟上手)

### 方式零：直接下载免安装预编译客户端（最省心，无需 Python / Git）

前往 [GitHub Releases 发布页](https://github.com/akasls/Antigravity-Orbit/releases) 下载官方自动打包好的开箱即用版本：
- **Windows 用户**：下载 `Antigravity-Orbit-Windows-x64.zip`，解压后直接双击 **`Antigravity-Orbit.exe`** 即可打开！
- **macOS 用户**：下载 `Antigravity-Orbit-macOS.zip`，解压后运行 **`Antigravity-Orbit.app`** 即可！

---

### 方式一：克隆源码并运行独立桌面客户端

1. 下载或克隆本项目到本地：
   ```bash
   git clone https://github.com/akasls/Antigravity-Orbit.git
   cd Antigravity-Orbit
   ```
2. 双击运行根目录下的 **`gui.bat`**（或命令行运行 `python main.py gui`）。
3. 在极简桌面控制中心中：
   - 切换界面语言（简体中文 / 繁体中文 / 官方英文）。
   - 自由开关【顶栏实时模型额度胶囊】与自定义刷新频率。
   - 一键启用【GPU 硬件加速】、【后台防降频】与【全栈遥测阻断】。
   - 配置 Telegram / 飞书 / 企业微信机器人并在线测试。
4. 点击右下角 **【保存并应用配置】**，即刻完成一键热部署！
5. 点击 **【重启客户端】** 实时查看崭新效果！

---

### 方式二：命令行交互式向导

1. 双击运行根目录下的 **`install.bat`**，选择 `[2]` 运行控制台向导。
2. 按照交互向导逐步完成汉化与通知设置。

---

### 方式三：macOS / Linux 源码运行

```bash
git clone https://github.com/akasls/Antigravity-Orbit.git
cd Antigravity-Orbit
bash install.sh
```

---

## 🛠️ CLI 常用管理命令

本项目提供全功能命令行工具 `main.py`：

### 🖥️ 1. 桌面可视化管理客户端

```bash
# 启动独立桌面可视化管理客户端
python main.py gui
# 或者直接双击运行 gui.bat
```

### 🌐 2. 客户端汉化管理

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

### ⚡ 3. 性能加速与去遥测独立部署

```bash
# 一键部署 GPU 硬件加速、后台防降频与全栈去遥测补丁
python main.py optimize
```

### 🔔 4. 监控服务与通知管理

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

### 📦 5. 跨平台独立打包构建

```bash
# 自动编译生成 Windows 单文件 (.exe) 或 macOS 应用包 (.app / .zip)
python scripts/build.py
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

在桌面客户端或命令行配置后会自动生成，也可参考 `config.example.json` 手动修改：

```json
{
  "enabled": true,
  "scan_interval": 3.0,
  "lock_port": 49222,
  "customization": {
    "language": "zh-CN",
    "show_quota_badge": true,
    "quota_refresh_interval": 60,
    "enable_gpu_acceleration": true,
    "disable_background_throttling": true,
    "expand_v8_memory": true,
    "disable_telemetry": true,
    "hide_ide_buttons": true
  },
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
│   ├── gui.py                         # 独立桌面可视化管理客户端 (Native Tkinter/ttk)
│   ├── localization.py                # 客户端汉化管理器桥接模块
│   ├── monitor.py                     # Antigravity 任务状态嗅探与通知调度
│   └── utils.py                       # 进程单例锁、日志与格式化工具
├── localization/                      # 现代化客户端汉化引擎
│   ├── core/
│   │   ├── asar_patcher.js            # Electron ASAR 安全原子解包、打补丁与重新封装
│   │   ├── engine.js                  # 汉化主调度控制器
│   │   └── runtime_template.js        # 前端 DOM 注入、顶栏额度胶囊与动态沙箱
│   ├── dictionaries/                  # 简体中文模块化专业词典 (8 大维度)
│   └── dictionaries_tw/               # 繁体中文镜像词典 (结构完全对齐)
├── notifiers/                         # 推送通知模块
│   ├── base.py                        # 通知基类
│   ├── telegram.py                    # Telegram 通道 (含代理自适应)
│   ├── feishu.py                      # 飞书 Webhook 通道
│   └── wecom.py                       # 企业微信 Webhook 通道
├── gui.bat                            # Windows 一键拉起桌面可视化客户端
├── install.bat                        # Windows 综合配置入口 (GUI / CLI)
├── install.sh                         # macOS / Linux 交互配置向导脚本
├── main.py                            # 统一 CLI / GUI 命令行入口
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
