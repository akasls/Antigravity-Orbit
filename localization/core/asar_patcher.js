const fs = require('fs');
const path = require('path');
const child_process = require('child_process');

const SIGNATURE_START = "/* === ANTIGRAVITY_LOCALIZATION_START === */";
const SIGNATURE_END = "/* === ANTIGRAVITY_LOCALIZATION_END === */";

class AsarPatcher {
    constructor(resourcesDir, options = {}) {
        this.resourcesDir = path.resolve(resourcesDir);
        this.asarPath = path.join(this.resourcesDir, 'app.asar');
        this.bakPath = path.join(this.resourcesDir, 'app.asar.bak');
        this.metaPath = path.join(this.resourcesDir, '.localization_info.json');
        this.isTraditional = !!options.tw;
        this.options = options;
        this.customConfig = options.customConfig || {};
        this.tempDir = path.join(this.resourcesDir, '_temp_asar_build');
    }

    /**
     * 执行命令封装
     */
    static runCmd(cmd) {
        try {
            const out = child_process.execSync(cmd, { encoding: 'utf-8', stdio: 'pipe', windowsHide: true });
            return { success: true, stdout: out, stderr: '' };
        } catch (e) {
            return { success: false, stdout: e.stdout || '', stderr: e.stderr || e.message };
        }
    }

    /**
     * macOS Ad-hoc 深度重签名
     */
    resignMacApp() {
        if (process.platform !== 'darwin') return;
        let current = this.resourcesDir;
        let appPath = null;
        for (let i = 0; i < 8; i++) {
            if (current.endsWith('.app')) {
                appPath = current;
                break;
            }
            const parent = path.dirname(current);
            if (parent === current) break;
            current = parent;
        }

        if (appPath && fs.existsSync(appPath)) {
            console.log(`[签名] 正在对 macOS 应用包进行本地重签名: ${appPath} ...`);
            const res = AsarPatcher.runCmd(`codesign --force --deep --sign - "${appPath}"`);
            if (res.success) {
                console.log('[签名] 重新签名完成！');
            } else {
                console.warn('[警告] 重签名提示:', res.stderr || res.stdout);
            }
        }
    }

    /**
     * 安装并注入汉化
     */
    install(runtimeJs) {
        if (!fs.existsSync(this.asarPath)) {
            throw new Error(`未在目标目录找到 app.asar: ${this.resourcesDir}`);
        }

        // 1. 安全备份
        if (!fs.existsSync(this.bakPath)) {
            console.log('[备份] 正在创建官方原始包备份: app.asar.bak ...');
            fs.copyFileSync(this.asarPath, this.bakPath);
            console.log('[备份] 官方备份完成！');
        } else {
            // 用纯净备份重置当前 asar，以保证每次都是全新干净的注入
            try {
                fs.copyFileSync(this.bakPath, this.asarPath);
                console.log('[还原] 已重置为官方纯净备份，准备注入新版汉化...');
            } catch (e) {
                console.log('[提示] app.asar 处于占用中，将进行增量升级注入。');
            }
        }

        // 2. 清理并解包
        if (fs.existsSync(this.tempDir)) {
            fs.rmSync(this.tempDir, { recursive: true, force: true });
        }

        console.log('[解包] 正在提取 app.asar 资源文件...');
        const extractCmd = `npx -y @electron/asar extract "${this.asarPath}" "${this.tempDir}"`;
        const extractRes = AsarPatcher.runCmd(extractCmd);
        if (!extractRes.success || !fs.existsSync(this.tempDir)) {
            throw new Error(`解包失败: ${extractRes.stderr}\n${extractRes.stdout}`);
        }

        // 3. 补丁注入
        try {
            this._patchPreload(runtimeJs);
            this._patchIdeInstalled();
            this._patchMenu();
            this._patchTray();
            this._patchLoadingOverlay();
            this._patchUpdater();
            this._patchPerformanceAndTelemetry();
            this._handleAppUpdateYml();
        } catch (e) {
            fs.rmSync(this.tempDir, { recursive: true, force: true });
            throw e;
        }

        // 4. 打包重装
        console.log('[打包] 正在将修改后的资源重新封装回 app.asar...');
        const packCmd = `npx -y @electron/asar pack "${this.tempDir}" "${this.asarPath}"`;
        const packRes = AsarPatcher.runCmd(packCmd);

        // 清理临时工作目录
        fs.rmSync(this.tempDir, { recursive: true, force: true });

        if (!packRes.success) {
            throw new Error(`打包失败: ${packRes.stderr}\n${packRes.stdout}`);
        }

        // 5. 记录元数据并重签名
        try {
            fs.writeFileSync(this.metaPath, JSON.stringify({
                localized: true,
                lang: this.isTraditional ? 'zh-TW' : 'zh-CN',
                version: '2.14.0',
                engine: 'Antigravity-Custom-Localization',
                updated_at: new Date().toISOString()
            }, null, 2), 'utf-8');
        } catch (e) {}

        this.resignMacApp();
        console.log('[√] Antigravity 中文汉化部署成功！');
        return true;
    }

    /**
     * 还原官方英文原版
     */
    restore() {
        if (!fs.existsSync(this.bakPath)) {
            console.log('[!] 未检测到备份文件 app.asar.bak，可能当前已是官方原版。');
            return false;
        }

        console.log('[还原] 正在从官方备份文件恢复原版 app.asar ...');
        fs.copyFileSync(this.bakPath, this.asarPath);
        fs.unlinkSync(this.bakPath);

        if (fs.existsSync(this.metaPath)) {
            try { fs.unlinkSync(this.metaPath); } catch (e) {}
        }

        const disabledYml = path.join(this.resourcesDir, 'app-update.yml.disabled');
        const origYml = path.join(this.resourcesDir, 'app-update.yml');
        if (fs.existsSync(disabledYml)) {
            try { fs.renameSync(disabledYml, origYml); } catch (e) {}
        }

        this.resignMacApp();
        console.log('[√] 官方英文原版已成功无痕恢复！');
        return true;
    }

    _handleAppUpdateYml() {
        const cfg = this.customConfig || {};
        const origYml = path.join(this.resourcesDir, 'app-update.yml');
        const disabledYml = path.join(this.resourcesDir, 'app-update.yml.disabled');

        if (cfg.disable_auto_update !== false) {
            if (fs.existsSync(origYml)) {
                try {
                    fs.renameSync(origYml, disabledYml);
                    console.log('[锁定] app-update.yml 已重命名为 .disabled，阻断后台静默更新。');
                } catch (e) {}
            }
        } else {
            if (fs.existsSync(disabledYml)) {
                try {
                    fs.renameSync(disabledYml, origYml);
                    console.log('[恢复] app-update.yml 已恢复。');
                } catch (e) {}
            }
        }
    }

    // --- 内部补丁实现 ---

    _patchPreload(runtimeJs) {
        const preloadPath = path.join(this.tempDir, 'dist', 'preload.js');
        if (!fs.existsSync(preloadPath)) {
            throw new Error(`未能在解包文件中找到 preload.js: ${preloadPath}`);
        }

        console.log('[注入] 正在向 preload.js 注入 DOM 翻译引擎...');
        let content = fs.readFileSync(preloadPath, 'utf-8');

        // 清除任何已有注入签名块
        const regexOld = /\/\* === ANTIGRAVITY_LOCALIZATION_START === \*\/[\s\S]*?\/\* === ANTIGRAVITY_LOCALIZATION_END === \*\//g;
        content = content.replace(regexOld, '');

        const injected = `${content}\n\n${SIGNATURE_START}\n${runtimeJs}\n${SIGNATURE_END}\n`;
        fs.writeFileSync(preloadPath, injected, 'utf-8');
        console.log('[注入] preload.js 注入完成。');
    }

    _patchIdeInstalled() {
        if (this.customConfig && this.customConfig.hide_ide_buttons === false) {
            console.log('[跳过] 用户配置保留 IDE 推广按钮，跳过相关补丁。');
            return;
        }

        // 1. 拦截 preload.js 中的 ideAPI.isInstalled，直接返回 true 已安装
        const preloadPath = path.join(this.tempDir, 'dist', 'preload.js');
        if (fs.existsSync(preloadPath)) {
            let pContent = fs.readFileSync(preloadPath, 'utf-8');
            const targetIde = "isInstalled: () => electron_1.ipcRenderer.invoke('ide:is-installed')";
            if (pContent.includes(targetIde)) {
                pContent = pContent.replace(targetIde, "isInstalled: () => Promise.resolve(true)");
                fs.writeFileSync(preloadPath, pContent, 'utf-8');
                console.log('[补丁] preload.js 已设置 IDE 安装状态为已就绪。');
            }
        }

        // 2. 拦截 ipcHandlers.js 中的 ide:is-installed 处理器，确保返回 true
        const ipcPath = path.join(this.tempDir, 'dist', 'ipcHandlers.js');
        if (fs.existsSync(ipcPath)) {
            let ipcContent = fs.readFileSync(ipcPath, 'utf-8');
            const targetHandle = "electron_1.ipcMain.handle('ide:is-installed', async () => {";
            if (ipcContent.includes(targetHandle)) {
                ipcContent = ipcContent.replace(targetHandle, "electron_1.ipcMain.handle('ide:is-installed', async () => { return true;");
                fs.writeFileSync(ipcPath, ipcContent, 'utf-8');
                console.log('[补丁] ipcHandlers.js 已设置 ide:is-installed 恒为 true (隐藏右上角安装 IDE 按钮)。');
            }
        }
    }

    _patchMenu() {
        const menuPath = path.join(this.tempDir, 'dist', 'menu.js');
        if (!fs.existsSync(menuPath)) return;

        console.log('[注入] 正在向 menu.js 注入系统原生菜单汉化...');
        let content = fs.readFileSync(menuPath, 'utf-8');

        // 简繁菜单映射表
        const menuTranslations = this.isTraditional ? {
            'File': '檔案', 'Edit': '編輯', 'View': '檢視', 'Window': '視窗', 'Help': '說明',
            'New Window': '開新視窗', 'Create Project': '建立專案', 'Command Palette': '命令面板',
            'Docs': '說明文件', 'Check for Updates': '檢查更新', 'Toggle Developer Tools': '切換開發者工具',
            'Undo': '復原', 'Redo': '重做', 'Cut': '剪下', 'Copy': '複製', 'Paste': '貼上',
            'Select All': '全選', 'Minimize': '最小化', 'Maximize': '最大化', 'Close': '關閉',
            'Zoom': '縮放', 'Reset Zoom': '重設縮放', 'Zoom In': '放大', 'Zoom Out': '縮小',
            'Toggle Full Screen': '切換全螢幕', 'Version': '版本'
        } : {
            'File': '文件', 'Edit': '编辑', 'View': '视图', 'Window': '窗口', 'Help': '帮助',
            'New Window': '新建窗口', 'Create Project': '创建项目', 'Command Palette': '命令面板',
            'Docs': '文档', 'Check for Updates': '检查更新', 'Toggle Developer Tools': '切换开发者工具',
            'Undo': '撤销', 'Redo': '重做', 'Cut': '剪切', 'Copy': '复制', 'Paste': '粘贴',
            'Select All': '全选', 'Minimize': '最小化', 'Maximize': '最大化', 'Close': '关闭',
            'Zoom': '缩放', 'Reset Zoom': '重置缩放', 'Zoom In': '放大', 'Zoom Out': '缩小',
            'Toggle Full Screen': '切换全屏', 'Version': '版本'
        };

        const patchCode = `
    /* === NATIVE_MENU_I18N === */
    const _menuTrans = ${JSON.stringify(menuTranslations, null, 2)};
    function _translateNativeMenu(items) {
        if (!items || !Array.isArray(items)) return;
        for (const item of items) {
            let label = item.label || '';
            let m = label.match(/&([a-zA-Z])/);
            let mnemonic = m ? " (&" + m[1] + ")" : "";
            let clean = label.replace('&', '');
            if (_menuTrans[clean]) {
                item.label = _menuTrans[clean] + mnemonic;
            } else if (_menuTrans[label]) {
                item.label = _menuTrans[label];
            } else if (/^Version\\s*([\\d.]*)$/i.test(clean)) {
                item.label = clean.replace(/^Version\\s*([\\d.]*)$/i, (_, v) => v ? "版本 " + v : "版本");
            }
            if (item.submenu && item.submenu.items) {
                _translateNativeMenu(item.submenu.items);
            }
        }
    }
    _translateNativeMenu(menu.items);
    `;

        const target = "electron_1.Menu.setApplicationMenu(menu);";
        if (content.includes(target) && !content.includes('/* === NATIVE_MENU_I18N === */')) {
            content = content.replace(target, patchCode + "\n    " + target);
            fs.writeFileSync(menuPath, content, 'utf-8');
            console.log('[注入] menu.js 系统菜单注入成功。');
        }
    }

    _patchTray() {
        const trayPath = path.join(this.tempDir, 'dist', 'tray.js');
        if (!fs.existsSync(trayPath)) return;

        console.log('[注入] 正在向 tray.js 注入系统托盘菜单汉化...');
        let content = fs.readFileSync(trayPath, 'utf-8');

        const trayTrans = this.isTraditional ? {
            'No agents running': '無執行中的智能體',
            'Open Antigravity': '開啟 Antigravity',
            'Quit': '結束'
        } : {
            'No agents running': '无运行中的智能体',
            'Open Antigravity': '打开 Antigravity',
            'Quit': '退出'
        };

        const targetCreate = "function createTray(actions) {";
        const replacementCreate = `function createTray(actions) {
    /* === TRAY_I18N === */
    const _trayTrans = ${JSON.stringify(trayTrans)};
    for (const item of actions) {
        if (_trayTrans[item.label]) item.label = _trayTrans[item.label];
    }`;

        if (content.includes(targetCreate) && !content.includes('/* === TRAY_I18N === */')) {
            content = content.replace(targetCreate, replacementCreate);
        }

        const countRegex = /countItem\.label\s*=\s*\([\s\S]*?' running';/g;
        const replacementCount = this.isTraditional
            ? "countItem.label = count > 0 ? `${count} 個智能體執行中` : '無執行中的智能體';"
            : "countItem.label = count > 0 ? `${count} 个智能体运行中` : '无运行中的智能体';";
        content = content.replace(countRegex, replacementCount);

        fs.writeFileSync(trayPath, content, 'utf-8');
        console.log('[注入] tray.js 托盘菜单注入成功。');
    }

    _patchLoadingOverlay() {
        const loadingPath = path.join(this.tempDir, 'dist', 'loadingOverlay.js');
        if (!fs.existsSync(loadingPath)) return;

        let content = fs.readFileSync(loadingPath, 'utf-8');
        const target = '<div class="text">Loading Antigravity</div>';
        const replacement = this.isTraditional
            ? '<div class="text">正在啟動 Antigravity...</div>'
            : '<div class="text">正在启动 Antigravity...</div>';

        if (content.includes(target)) {
            content = content.replace(target, replacement);
            fs.writeFileSync(loadingPath, content, 'utf-8');
            console.log('[注入] loadingOverlay.js 启动页文字注入成功。');
        }
    }

    _patchUpdater() {
        const cfg = this.customConfig || {};
        const updaterPath = path.join(this.tempDir, 'dist', 'updater.js');
        if (!fs.existsSync(updaterPath)) return;

        let content = fs.readFileSync(updaterPath, 'utf-8');
        const target = `title: 'Check for Updates',
                message: 'No updates available',
                buttons: ['OK'],`;
        const replacement = this.isTraditional
            ? `title: '檢查更新',
                message: '目前已是最新版本，暫無可用更新。',
                buttons: ['確定'],`
            : `title: '检查更新',
                message: '当前已是最新版本，暂无可用更新。',
                buttons: ['确定'],`;

        if (content.includes(target)) {
            content = content.replace(target, replacement);
        }

        // 锁定版本，禁止后台自动检测与下载更新
        if (cfg.disable_auto_update !== false) {
            const initTarget = "function initAutoUpdater(isHeadless, settingsService) {";
            if (content.includes(initTarget) && !content.includes('/* === AUTO_UPDATE_DISABLED === */')) {
                content = content.replace(initTarget, `${initTarget}\n    /* === AUTO_UPDATE_DISABLED === */\n    console.log('[AutoUpdater] 后台自动更新已被安全锁定。');\n    return;`);
            }
            const checkTarget = "function startAutoUpdateChecks() {";
            if (content.includes(checkTarget) && !content.includes('/* === AUTO_CHECK_DISABLED === */')) {
                content = content.replace(checkTarget, `${checkTarget}\n    /* === AUTO_CHECK_DISABLED === */\n    return;`);
            }
        }

        fs.writeFileSync(updaterPath, content, 'utf-8');
        console.log('[注入] updater.js 更新机制与文案注入成功。');
    }

    _patchPerformanceAndTelemetry() {
        const cfg = this.customConfig || {};
        console.log('[优化] 正在注入性能加速、网络代理与遥测配置补丁...');

        // 1. 注入 Electron / Chromium 启动参数 (main.js)
        const mainPath = path.join(this.tempDir, 'dist', 'main.js');
        if (fs.existsSync(mainPath)) {
            let mContent = fs.readFileSync(mainPath, 'utf-8');
            const targetLock = "const gotTheLock = electron_1.app.requestSingleInstanceLock();";
            
            let switchLines = [];

            if (cfg.disable_telemetry !== false) {
                switchLines.push(
                    "// 1. 全面阻断 Chromium/Electron 遥测、指标采集、崩溃与可靠性回传",
                    "electron_1.app.commandLine.appendSwitch('disable-metrics');",
                    "electron_1.app.commandLine.appendSwitch('disable-telemetry');",
                    "electron_1.app.commandLine.appendSwitch('disable-breakpad');",
                    "electron_1.app.commandLine.appendSwitch('disable-component-update');",
                    "electron_1.app.commandLine.appendSwitch('no-report-upload');",
                    "electron_1.app.commandLine.appendSwitch('disable-domain-reliability');"
                );
            }

            if (cfg.enable_gpu_acceleration !== false) {
                switchLines.push(
                    "// 2. 启用 GPU 硬件加速与零拷贝 (大幅降低界面与流式代码渲染 CPU 开销)",
                    "electron_1.app.commandLine.appendSwitch('enable-gpu-rasterization');",
                    "electron_1.app.commandLine.appendSwitch('enable-zero-copy');",
                    "electron_1.app.commandLine.appendSwitch('ignore-gpu-blocklist');",
                    "electron_1.app.commandLine.appendSwitch('enable-native-gpu-memory-buffers');"
                );
            }

            if (cfg.enable_smooth_scrolling !== false) {
                switchLines.push(
                    "// 3. 启用硬件级长文本平滑滚动与 60FPS 顺滑渲染",
                    "electron_1.app.commandLine.appendSwitch('enable-smooth-scrolling');",
                    "electron_1.app.commandLine.appendSwitch('enable-accelerated-2d-canvas');"
                );
            }

            if (cfg.disable_background_throttling !== false) {
                switchLines.push(
                    "// 4. 解除后台降频与冻结 (保证后台多任务切换及代码流式打印满速执行)",
                    "electron_1.app.commandLine.appendSwitch('disable-background-timer-throttling');",
                    "electron_1.app.commandLine.appendSwitch('disable-backgrounding-occluded-windows');",
                    "electron_1.app.commandLine.appendSwitch('disable-renderer-backgrounding');"
                );
            }

            if (cfg.expand_v8_memory !== false) {
                switchLines.push(
                    "// 5. 扩充 V8 垃圾回收堆内存至 4GB (杜绝大工程索引与长上下文频繁卡顿)",
                    "electron_1.app.commandLine.appendSwitch('js-flags', '--max-old-space-size=4096');"
                );
            }

            if (cfg.proxy_enabled && cfg.proxy_url) {
                const proxyUrl = cfg.proxy_url.trim();
                switchLines.push(
                    "// 6. Antigravity 专属网络代理 (彻底取代 Proxifier)",
                    `electron_1.app.commandLine.appendSwitch('proxy-server', ${JSON.stringify(proxyUrl)});`,
                    `electron_1.app.commandLine.appendSwitch('proxy-bypass-list', '<-loopback>;127.0.0.1;localhost');`,
                    `process.env['HTTP_PROXY'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['HTTPS_PROXY'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['ALL_PROXY'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['http_proxy'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['https_proxy'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['all_proxy'] = ${JSON.stringify(proxyUrl)};`,
                    `process.env['NO_PROXY'] = 'localhost,127.0.0.1';`,
                    `process.env['no_proxy'] = 'localhost,127.0.0.1';`
                );
            }

            if (switchLines.length > 0) {
                const optSwitches = "\n/* === ANTIGRAVITY_OPTIMIZATION_START === */\n" +
                    switchLines.join("\n") +
                    "\n/* === ANTIGRAVITY_OPTIMIZATION_END === */\n";

                if (mContent.includes(targetLock) && !mContent.includes('/* === ANTIGRAVITY_OPTIMIZATION_START === */')) {
                    mContent = mContent.replace(targetLock, optSwitches + "\n" + targetLock);
                    fs.writeFileSync(mainPath, mContent, 'utf-8');
                    console.log('[优化] main.js 已按需注入硬件渲染加速、平滑滚动、专属代理与全套防降频、去遥测参数。');
                }
            }
        }

        // 2. 注入 Go 后端核心 Language Server 遥测禁用与专属代理环境变量 (languageServer.js)
        const lsPath = path.join(this.tempDir, 'dist', 'languageServer.js');
        if (fs.existsSync(lsPath)) {
            let lsContent = fs.readFileSync(lsPath, 'utf-8');
            if (cfg.disable_telemetry !== false) {
                const targetRegex = /'--override_user_agent_name',\s*'antigravity',/;
                if (targetRegex.test(lsContent) && !lsContent.includes("'--disable_telemetry=true'")) {
                    lsContent = lsContent.replace(targetRegex, "'--override_user_agent_name',\n            'antigravity',\n            '--disable_telemetry=true',");
                    console.log('[优化] languageServer.js 已注入 --disable_telemetry=true 彻底切断后端核心遥测。');
                }
            }

            if (cfg.proxy_enabled && cfg.proxy_url) {
                const proxyUrl = cfg.proxy_url.trim();
                const targetEnv = "const env = { ...process.env, ...(0, shell_env_1.shellEnvSync)() };";
                if (lsContent.includes(targetEnv) && !lsContent.includes('/* === ANTIGRAVITY_PROXY_INJECT === */')) {
                    const proxyEnvCode = `${targetEnv}\n        /* === ANTIGRAVITY_PROXY_INJECT === */\n` +
                        `        env['HTTP_PROXY'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['HTTPS_PROXY'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['ALL_PROXY'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['http_proxy'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['https_proxy'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['all_proxy'] = ${JSON.stringify(proxyUrl)};\n` +
                        `        env['NO_PROXY'] = 'localhost,127.0.0.1';\n` +
                        `        env['no_proxy'] = 'localhost,127.0.0.1';\n`;
                    lsContent = lsContent.replace(targetEnv, proxyEnvCode);
                    console.log(`[代理] languageServer.js 已为 Language Server 注入专属代理环境: ${proxyUrl}。`);
                }
            }

            fs.writeFileSync(lsPath, lsContent, 'utf-8');
        }

        if (cfg.disable_telemetry !== false) {
            // 3. 中和 Chrome DevTools MCP 中的 Clearcut 遥测外发
            const clearcutPath = path.join(this.tempDir, 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'telemetry', 'ClearcutLogger.js');
            if (fs.existsSync(clearcutPath)) {
                let cContent = fs.readFileSync(clearcutPath, 'utf-8');
                if (!cContent.includes('/* === CLEARCUT_TELEMETRY_DISABLED === */')) {
                    cContent = cContent.replace('async logToolInvocation(args) {', 'async logToolInvocation(args) { return; /* clearcut disabled */');
                    cContent = cContent.replace('async logServerStart(flagUsage) {', 'async logServerStart(flagUsage) { return; /* clearcut disabled */');
                    cContent = cContent.replace('async logDailyActiveIfNeeded() {', 'async logDailyActiveIfNeeded() { return; /* clearcut disabled */');
                    cContent = cContent.replace('async logServerError(args) {', 'async logServerError(args) { return; /* clearcut disabled */');
                    cContent = "/* === CLEARCUT_TELEMETRY_DISABLED === */\n" + cContent;
                    fs.writeFileSync(clearcutPath, cContent, 'utf-8');
                    console.log('[优化] ClearcutLogger.js 已中和 Google Clearcut 数据回传。');
                }
            }

            const watchdogPath = path.join(this.tempDir, 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'telemetry', 'WatchdogClient.js');
            if (fs.existsSync(watchdogPath)) {
                let wContent = fs.readFileSync(watchdogPath, 'utf-8');
                if (!wContent.includes('/* === WATCHDOG_DISABLED === */')) {
                    wContent = wContent.replace('send(message) {', 'send(message) { return; /* watchdog disabled */');
                    wContent = "/* === WATCHDOG_DISABLED === */\n" + wContent;
                    fs.writeFileSync(watchdogPath, wContent, 'utf-8');
                    console.log('[优化] WatchdogClient.js 已彻底阻断看门狗进程遥测网络外发。');
                }
            }
        }
    }
}

module.exports = { AsarPatcher };
