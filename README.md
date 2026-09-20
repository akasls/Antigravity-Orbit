# 🛰️ Antigravity Orbit (反重力轨道增强套件)

<p align="center">
  <a href="https://github.com/akasls/Antigravity-Orbit">
    <img src="https://img.shields.io/badge/Antigravity-Orbit-6366f1?style=for-the-badge&logo=google&logoColor=white" alt="Antigravity Orbit" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows 10/11 x64" />
  <img src="https://img.shields.io/badge/Release-v3.3.4-10B981?style=flat-square&logo=github&logoColor=white" alt="Release v3.3.4" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node.js 18+" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License MIT" />
  <img src="https://img.shields.io/badge/Antigravity-2.0+-FF6F00?style=flat-square" alt="Antigravity 2.0+" />
</p>

> 🚀 **Antigravity Orbit** 是专为 **Google Antigravity** 官方客户端打造的 Windows 原生独立桌面伴侣与生产力中枢。  
> 集成 **【👥 智能多账号池与毫秒级热切号】**、**【📊 实时双周期模型配额看板 (Claude & Gemini)】**、**【⚡ 极限渲染加速与专属网络代理】**、**【🌐 深度汉化与界面外观纯净化】**、**【📝 专家提示词库与 Skills 冗余裁剪 (省 10,000+ Token)】**、**【🛡️ 任务长跑自愈与多渠道即时推送】** 与 **【🧹 磁盘深度垃圾清理与彻底初始化】**，助您在轨道上释放反重力智能体的极致潜能。

---

## 📑 目录

- [一、项目介绍 (Project Overview)](#一项目介绍-project-overview)
  - [1. 智能账号池与极速无感切号](#1-智能账号池与极速无感切号)
  - [2. 顶部标题栏实时模型额度胶囊](#2-顶部标题栏实时模型额度胶囊)
  - [3. 极致性能调优与专属网络代理](#3-极致性能调优与专属网络代理)
  - [4. 全局提示词库与 Skills 冗余裁剪](#4-全局提示词库与-skills-冗余裁剪)
  - [5. 深度界面汉化与外观净化](#5-深度界面汉化与外观净化)
  - [6. 长跑任务自愈与多通道即时推送](#6-长跑任务自愈与多通道即时推送)
  - [7. 磁盘深度瘦身与安全初始化](#7-磁盘深度瘦身与安全初始化)
- [二、项目安装 (Installation Guide)](#二项目安装-installation-guide)
  - [版本选择与下载](#版本选择与下载)
  - [方式一：Windows 原生安装包 (强烈推荐)](#方式一windows-原生安装包-强烈推荐)
  - [方式二：Windows 单文件便携版 (即点即用)](#方式二windows-单文件便携版-即点即用)
  - [方式三：Windows 免解压极速版 (目录解压)](#方式三windows-免解压极速版-目录解压)
  - [方式四：开发者源码部署](#方式四开发者源码部署)
- [三、项目使用 (Usage Guide)](#三项目使用-usage-guide)
  - [1. 账号池管理与批量导入导出](#1-账号池管理与批量导入导出)
  - [2. 客户端汉化与性能优化热部署](#2-客户端汉化与性能优化热部署)
  - [3. 规则管理与自定义提示词应用](#3-规则管理与自定义提示词应用)
  - [4. 专属网络代理配置](#4-专属网络代理配置)
  - [5. 任务自愈与通知配置 (Telegram / 飞书 / 企微)](#5-任务自愈与通知配置-telegram--飞书--企微)
  - [6. 系统维护、托盘守护与彻底初始化](#6-系统维护托盘守护与彻底初始化)
  - [7. CLI 常用管理命令速查](#7-cli-常用管理命令速查)
- [四、隐私与安全性声明](#四隐私与安全性声明)
- [五、开源协议](#五开源协议)

---

## 一、项目介绍 (Project Overview)

### 1. 智能账号池与极速无感切号
- **原生对接 Windows Credential Manager**：通过 Windows 底层原生 API 读写系统登录凭据（`gemini:antigravity`），与官方客户端完全无缝咬合。
- **一键读取当前登录账号**：无需手动输入任何 Key 或 Token，点击即可一键将客户端正在登录的账号同步至本地账号池。
- **多途径账号导入**：
  - **Google 网页一键授权登录**：自动唤起系统默认浏览器完成 Google OAuth 2.0 授权，全自动拉取。
  - **Cockpit Tools 批量格式兼容导入**：原生兼容 `[{"email": "...", "refresh_token": "..."}]` 数组格式批量导入。
  - **单行 / 多行 Refresh Token 批量导入**：支持一行一条粘贴导入，自动并发刷新换取有效凭据并探测账户信息。
- **多格式导出备份**：支持一键导出为 **Cockpit Tools 兼容格式** 或 **Orbit 完整备份格式**，支持下载 JSON 或复制剪贴板。
- **双周期额度自动并发轮询**：全量集成 Google Cloud Code 原生配额端点，定时刷新所有账号的计划等级（Pro / Ultra / Free）、5小时滚动配额 (`5h Limit`)、周度配额 (`Weekly Limit`) 与刷新倒计时。
- **毫秒级无感热切号**：在账号卡片点击“一键切号”，毫秒级替换系统凭据，重启客户端后直接以新身份工作，彻底告别频繁登出登录。

### 2. 顶部标题栏实时模型额度胶囊
- **免鉴权内部直连**：逆向重构 ConnectRPC 端点 `/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`，直接获取实时额度。
- **原生融入顶部标题栏**：无缝挂载于右上角安全区，微磨砂圆角半透明胶囊，不影响窗口拖拽与系统控制按钮。
- **双模型状态指示灯**：
  - `🟢 Gemini XX% · 🟣 Claude XX%`（正常时采用官方模型主色，低于 50% 自动变橙黄，低于 20% 自动变红告警）。
- **交互式浮动详情面板**：
  - 点击胶囊展开半透明详情卡片，显示 Gemini 与 Claude 的 **5 小时限额进度条** 与 **周限额进度条**。
  - 倒计时精确计算（`距离刷新还有 X 天 X 小时` / `距离刷新还有 X 小时 X 分钟`）。
  - 内置“🔄 立即刷新”按钮，支持活跃使用中（默认 1 分钟）与闲置（默认 15 分钟）双轨自动轮询。

### 3. 极致性能调优与专属网络代理
- **Antigravity 专属网络代理 (彻底取代 Proxifier)**：
  - 原生支持 HTTP / SOCKS5 代理。直接在 Chromium 渲染层与 Go 核心 Language Server 层面注入代理与环境变量，全面接管 Google API、git.exe、ssh.exe 与模型推理网络请求。
  - 内置**本地代理一键智能探测**（自动检测 7890、10808 等本地代理端口并测速）。
- **GPU 硬件加速与零拷贝渲染**：强制开启 2D 页面与 Canvas 的 GPU 栅格化加速（`enable-gpu-rasterization` / `enable-zero-copy`），显卡硬件直推，流式打字与超长文档滚动丝滑流畅，CPU 占用骤降。
- **解除后台防降频与防冻结**：
  - 解决 Electron 在窗口置于后台或被其他窗口遮挡时将定时器降频至 1Hz 的通病。
  - 注入 `disable-background-timer-throttling` 与 `disable-backgrounding-occluded-windows`，彻底解决**切到其他 IDE 窗口编码时 Antigravity 生成变慢、后台任务被挂起**的痛点。
- **V8 引擎 4GB 堆内存扩容**：注入 `--js-flags="--max-old-space-size=4096"`，大幅扩充 JavaScript 垃圾回收堆内存空间，彻底告别超大项目索引与几十轮超长会话下的频繁 GC 卡顿。
- **紧凑代码视野模式**：压缩编辑器与对话界面多余空白边距，有效代码显示面积提升 35%~50%。

### 4. 全局提示词库与 Skills 冗余裁剪
- **全局系统提示词库管理**：
  - 直接读写 Antigravity 核心注入的全局规则文件 `~/.gemini/config/AGENTS.md`（对应智能体底层 `<RULE[user_global]>`）。
  - 支持新增、编辑、删除自定义提示词规则，内置语法高亮编辑器。
  - 内置 5 大精选角色模板：底层系统与逆向安全专家、资深全栈工程师与架构专家、极简极速代码助手、代码审计与自动化测试专家、官方纯净空白规则。
- **Skills 冗余说明裁剪 (节约 10,000+ Token)**：
  - 安全裁剪官方重复冗余内置操作手册（`antigravity_guide`, `migrate-workflows`, `agy-customizations`）。
  - 每次与智能体对话立省 10,000+ 前置 Prompt Token 预算，大幅降低上下文消耗并提升首字响应速度。

### 5. 深度界面汉化与外观净化
- **深度适配 Antigravity 2.0+ 架构**：针对 Electron ASAR 架构与 DOM 渲染特性定制，原子级安全注入。
- **全方位模块化词库**：完整覆盖通用设置、模型用量、插件市场、对话页面、工件卡片、右键菜单与终端面板。
- **简繁双模一键切换**：内置严格镜像对齐的简体中文 (`zh-CN`) 与繁体中文 (`zh-TW`) 词库。
- **界面外观净化**：
  - 100% 保持官方原生品牌，不篡改英文品牌名。
  - 彻底移除右上角多余推广按钮（`Open IDE` / `Install IDE`）。
  - 内置代码沙箱隔离保护，坚决不误译任何实际代码。

### 6. 长跑任务自愈与多通道即时推送
- **异常自动重试 (Auto-Retry on Error)**：任务执行过程中若遭遇网络抖动或偶发服务异常，客户端自动点击重试（可配置 1~10 次，默认 3 次）。
- **智能工作态复位**：重试后智能体一旦恢复正常工作（流式输出/深度思考），**自动将重试计数清零重置为 0**。
- **额度用尽熔断保护**：检测到 429、Rate Limit 或额度归零立即阻断重试，发送【⚠️ 任务中断：额度已耗尽】告警。
- **多通道即时推送**：支持 Telegram Bot（含国内代理自适应）、飞书群 Webhook 机器人、企业微信群 Webhook 机器人。

### 7. 磁盘深度瘦身与安全初始化
- **深度垃圾瘦身**：一键安全清理 Chromium 渲染死缓存目录与历史临时任务流日志，并对 SQLite 会话数据库执行 `VACUUM` 碎片整理，通常可释放 1GB+ 磁盘空间。
- **彻底初始化 (危险操作强确认)**：提供强警告确认模态弹窗，一键强制安全终止进程、撤销所有补丁完整还原官方原生英文原版、深度清理死缓存并重置所有设置。

---

## 二、项目安装 (Installation Guide)

### 版本选择与下载

前往 [GitHub Releases 发布页](https://github.com/akasls/Antigravity-Orbit/releases) 下载最新版本：

| 版本形态 | 文件名 | 适用场景 | 启动速度 | 安装体验 |
| :--- | :--- | :--- | :--- | :--- |
| **Windows 原生安装包** (推荐) | `Antigravity-Orbit-Setup.exe` | 个人主力机、日常首选 | ⚡ **0.017 秒** | 向导式安装，自动创建桌面与开始菜单快捷方式，支持系统控制面板标准卸载 |
| **Windows 单文件便携版** | `Antigravity-Orbit-Portable-x64.exe` | U 盘随身携带、无安装权限电脑 | 🚀 **1.2 秒** | 单个独立 exe 文件，无需安装解压，即点即用 |
| **Windows 免解压极速版** | `Antigravity-Orbit-Windows-x64.zip` | 喜欢解压即用、追求秒开的极客 | ⚡ **0.15 秒** | 解压至任意目录，双击 `Antigravity-Orbit.exe` 或 `gui.bat` 运行 |

---

### 方式一：Windows 原生安装包 (强烈推荐)

1. 从 Release 页面下载 **`Antigravity-Orbit-Setup.exe`**。
2. 双击运行安装向导，可自定义安装目录（默认安装至 `%LOCALAPPDATA%\Programs\Antigravity-Orbit`，无需管理员 UAC 弹窗干扰）。
3. 安装完成后自动在桌面和开始菜单生成快捷方式，勾选“运行 Antigravity Orbit”即可秒开体验！

---

### 方式二：Windows 单文件便携版 (即点即用)

1. 下载 **`Antigravity-Orbit-Portable-x64.exe`**。
2. 放置在任意个人目录（如桌面、D盘工具箱或 U 盘）。
3. 双击直接启动，配置数据自动保存在本地目录中。

---

### 方式三：Windows 免解压极速版 (目录解压)

1. 下载 **`Antigravity-Orbit-Windows-x64.zip`**。
2. 解压至自定义目录（例如 `D:\Tools\Antigravity-Orbit`）。
3. 双击运行目录下的 **`Antigravity-Orbit.exe`** 或 **`gui.bat`**。

---

### 方式四：开发者源码部署

适合需要二次开发或自定义词库的开发者：

1. 克隆代码仓库：
   ```powershell
   git clone https://github.com/akasls/Antigravity-Orbit.git
   cd Antigravity-Orbit
   ```
2. 安装 Python 依赖：
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 确保系统安装有 **Node.js 18+**（若需执行 ASAR 打包与汉化编译）。
4. 运行桌面客户端：
   ```powershell
   python main.py gui
   # 或直接执行根目录下的
   .\gui.bat
   ```

---

## 三、项目使用 (Usage Guide)

### 1. 账号池管理与批量导入导出

1. **导入当前已登录账号**：打开【👥 账号池】工作区，点击左上角【📥 导入当前客户端账号】，自动将当前正在使用的 Antigravity 登录身份收录到池中。
2. **通过 Google 浏览器授权新增账号**：点击【🌐 Google 登录】，客户端自动在本地监听临时回调并唤起浏览器，登录完成后自动保存新账号并拉取配额。
3. **批量导入 (Cockpit Tools / 多行 Token)**：
   - 点击【➕ 手动添加】，在文本框中粘贴：
     - 单条 `refresh_token`
     - 多行 `refresh_token`（一行一条）
     - 或直接粘贴 Cockpit Tools 导出的凭据 JSON 数组：
       ```json
       [
         {"email": "user1@gmail.com", "refresh_token": "1//06V..."},
         {"email": "user2@gmail.com", "refresh_token": "1//06B..."}
       ]
       ```
   - 点击【开始导入】，进度条实时反馈每个账号的校验进度与结果。
4. **一键导出备份**：点击【📤 导出】，可自由切换【Cockpit 兼容格式】与【完整备份格式】，一键复制或下载为 JSON 文件。
5. **秒级切号**：在目标账号卡片上点击【⚡ 一键切号】，弹窗确认后系统凭据即刻切换，重启 Antigravity 后即生效。

---

### 2. 客户端汉化与性能优化热部署

1. 进入【🌐 汉化与性能】工作区：
   - **界面语言选择**：简体中文 (`zh-CN`) / 繁体中文 (`zh-TW`) / 官方原生英文 (`en`)。
   - **标题栏实时额度胶囊**：开启/关闭顶栏胶囊，配置刷新频率。
   - **极速性能与网络**：勾选开启【GPU 硬件栅格化加速】、【解除后台防降频与防冻结】、【扩充 V8 堆内存至 4GB】、【全栈关闭遥测】与【紧凑代码视野模式】。
2. 点击右上角 **【💾 保存并应用配置】**，系统将自动热更新配置并为 Antigravity 客户端重新注入补丁。
3. 点击 **【🚀 重启 Antigravity】** 即可体验极速响应与全中文界面！

---

### 3. 规则管理与自定义提示词应用

1. 进入【📝 规则与提示词】工作区：
2. **切换内置专家角色**：点击模板列表中的角色（如“网络安全与底层系统工程”、“资深架构专家”等），右侧编辑器即时加载规则，点击【💾 应用到系统提示词】即刻生效。
3. **新增 / 编辑自定义提示词**：
   - 点击【➕ 新增提示词】，输入标题与规则内容，保存至专属提示词库。
   - 对自定义提示词随时进行二次编辑或删除。
4. **裁剪说明型 Skills**：在上方开启【裁剪说明型 Skills 节省 Token】，自动裁剪官方冗余操作手册，大幅降低前置 Token 开销。

---

### 4. 专属网络代理配置

1. 进入【🌐 专属代理】工作区：
2. 开启【启用 Antigravity 专属代理】。
3. 可点击【🔍 自动探测本地代理】自动查找正在运行的 Clash (7890) 或 v2rayN (10808) 等本地代理。
4. 也可手动填写代理类型（HTTP / SOCKS5）、主机地址与端口，点击【测试连通性】验证。
5. 保存后，Antigravity 进程全部网络流量均走该代理出口，免去启动 Proxifier 规则配置。

---

### 5. 任务自愈与通知配置 (Telegram / 飞书 / 企微)

1. 进入【🛡️ 自愈与告警】工作区：
2. **异常自愈**：开启【任务异常自动重试】，配置最大重试次数（1~10 次），开启【额度耗尽熔断保护】与【重试超限告警通知】。
3. **通知通道配置**：
   - **Telegram**：填写 `Bot Token`、`Chat ID` 与代理地址（大陆地区可配置 `http://127.0.0.1:10808`），点击【测试】接收测试推送。
   - **飞书 / 企业微信**：粘贴机器人的 `Webhook URL`，点击【测试】确认即时送达。
4. 保存后，长跑任务结束或遇到异常时将即刻向各通道推送富文本卡片通知。

---

### 6. 系统维护、托盘守护与彻底初始化

1. 进入【⚙️ 设置与维护】工作区：
2. **后台托盘常驻**：勾选【关闭窗口时最小化到系统托盘】，点击关闭按钮即隐入系统托盘右下角小图标，右键托盘图标可快速唤起或重启客户端。
3. **开机自启动**：一键开启【Orbit 客户端开机静默启动】。
4. **深度磁盘瘦身**：点击【🧹 一键深度瘦身】，清理死缓存与数据库碎片。
5. **彻底初始化**：若遇到客户端损坏或想彻底恢复原生状态，点击【⚠️ 彻底初始化】，弹出强安全确认弹窗，确认后将彻底杀掉所有残留进程、还原原生纯净英文、清理死缓存并重置所有优化项。

---

### 7. CLI 常用管理命令速查

`main.py` 提供全功能命令行管理接口：

```powershell
# 1. 桌面可视化管理中心
python main.py gui                  # 启动可视化客户端
python main.py gui --tray           # 启动并直接静默最小化至托盘

# 2. 客户端汉化与性能加速
python main.py localize status      # 查看客户端安装路径及当前汉化状态
python main.py localize install     # 安装/更新简体中文汉化及性能加速补丁
python main.py localize install --tw# 安装繁体中文汉化
python main.py localize restore     # 一键卸载汉化，恢复官方原版英文
python main.py optimize             # 仅应用性能加速与全栈去遥测补丁

# 3. 任务监控与通知服务
python main.py start                # 启动后台守护进程
python main.py status               # 查看当前后台守护运行状态与日志
python main.py stop                 # 停止后台守护进程
python main.py test                 # 向所有已激活通道发送测试通知

# 4. 深度磁盘瘦身
python main.py clean --dry-run      # 预检分析可清理的磁盘空间
python main.py clean                # 执行深度瘦身清理

# 5. 开机自启动管理
python main.py autostart status     # 查看开机自启状态
python main.py autostart enable     # 开启开机自启动
python main.py autostart disable    # 关闭开机自启动
```

---

## 四、隐私与安全性声明

1. **100% 本地运算**：本工具绝无任何中央数据收集服务器，所有账号凭据、配置数据与日志均仅保存在用户本地电脑。
2. **严格脱敏与零上传**：
   - 项目仓库通过严格的 `.gitignore` 过滤机制，彻底排除 `config.json`、`*.log`、`watch_state.json`、`*.db` 与打包临时文件夹。
   - 所有凭据均存储在 Windows 操作系统原生凭据管理器或本地可控配置文件中，绝不上传任何用户代码或私人密钥。

---

## 五、开源协议

本项目遵循 [MIT 许可证](LICENSE)。  
欢迎提交 Issue 与 Pull Request 共同改进！

