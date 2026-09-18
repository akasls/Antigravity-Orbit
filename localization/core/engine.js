const fs = require('fs');
const path = require('path');
const child_process = require('child_process');
const { AsarPatcher } = require('./asar_patcher');

const LOCALIZATION_ROOT = path.resolve(__dirname, '..');

class LocalizationEngine {
    constructor() {
        this.dictDirCn = path.join(LOCALIZATION_ROOT, 'dictionaries');
        this.dictDirTw = path.join(LOCALIZATION_ROOT, 'dictionaries_tw');
        this.runtimeTemplatePath = path.join(__dirname, 'runtime_template.js');
    }

    /**
     * 跨平台自动探测 Antigravity 安装目录
     */
    detectInstallDir(manualDir = null, silent = false) {
        if (manualDir) {
            const p = path.resolve(manualDir);
            if (fs.existsSync(p)) {
                return fs.statSync(p).isFile() && p.endsWith('app.asar') ? path.dirname(path.dirname(p)) : p;
            }
            if (!silent) console.error(`[错误] 手动指定的安装目录不存在: ${manualDir}`);
            return null;
        }

        const candidates = [];
        const seen = new Set();
        const add = (candidate) => {
            if (!candidate) return;
            const norm = path.resolve(candidate);
            const key = norm.toLowerCase();
            if (!seen.has(key)) {
                candidates.push(norm);
                seen.add(key);
            }
        };

        if (process.platform === 'win32') {
            add(process.env.ANTIGRAVITY_INSTALL_DIR);
            add(process.env.ANTIGRAVITY_HOME);

            const regRoots = [
                'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall',
                'HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall',
                'HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall'
            ];
            for (const root of regRoots) {
                try {
                    const out = child_process.execSync(`reg query "${root}" /s /f Antigravity /d`, { encoding: 'utf-8', stdio: 'pipe', windowsHide: true });
                    for (const line of out.split(/\r?\n/)) {
                        const m = line.match(/^\s*(InstallLocation|DisplayIcon)\s+REG_\w+\s+(.+)$/i);
                        if (m) {
                            let val = m[2].trim().replace(/^"|"$/g, '');
                            if (/Antigravity\.exe/i.test(val)) val = path.dirname(val);
                            add(val);
                        }
                    }
                } catch (e) {}
            }

            for (const d of ['C', 'D', 'E', 'F']) {
                add(`${d}:\\Programs\\Antigravity`);
                add(`${d}:\\Antigravity`);
            }
            add('C:\\Program Files\\Antigravity');

            const localAppdata = process.env.LOCALAPPDATA;
            if (localAppdata) {
                add(path.join(localAppdata, 'Programs', 'antigravity'));
            }
        } else if (process.platform === 'darwin') {
            add('/Applications/Antigravity.app');
            add(path.join(process.env.HOME || '', 'Applications', 'Antigravity.app'));
        }

        for (const c of candidates) {
            if (fs.existsSync(c)) {
                if (fs.existsSync(path.join(c, 'resources', 'app.asar')) ||
                    fs.existsSync(path.join(c, 'Contents', 'Resources', 'app.asar')) ||
                    fs.existsSync(path.join(c, 'app.asar'))) {
                    return c;
                }
            }
        }

        return null;
    }

    /**
     * 定位 resources 目录
     */
    getResourcesDir(installDir) {
        if (!installDir) return null;
        if (fs.existsSync(path.join(installDir, 'resources'))) {
            return path.join(installDir, 'resources');
        }
        if (fs.existsSync(path.join(installDir, 'Contents', 'Resources'))) {
            return path.join(installDir, 'Contents', 'Resources');
        }
        if (fs.existsSync(path.join(installDir, 'app.asar'))) {
            return installDir;
        }
        return path.join(installDir, 'resources');
    }

    /**
     * 加载所有模块化字典并根据品牌设置与语言编译
     */
    /**
     * 加载所有模块化字典并根据语言编译
     */
    loadDictionary(isTraditional = false, isEnglish = false) {
        if (isEnglish) {
            return {};
        }
        const dictDir = isTraditional ? this.dictDirTw : this.dictDirCn;
        const total = {};

        if (fs.existsSync(dictDir)) {
            const files = fs.readdirSync(dictDir);
            for (const f of files) {
                if (f.endsWith('.json')) {
                    try {
                        const content = fs.readFileSync(path.join(dictDir, f), 'utf-8');
                        const data = JSON.parse(content);
                        for (const [k, v] of Object.entries(data)) {
                            const normK = k.replace(/\s+/g, ' ').trim();
                            if (normK) total[normK] = v;
                        }
                    } catch (e) {}
                }
            }
        }

        // 保持官方原生品牌名 Antigravity 不被替换
        delete total['Antigravity'];

        return total;
    }

    /**
     * 读取项目 config.json 中的自定义配置
     */
    loadCustomConfig(customConfigFile = null) {
        const configPath = customConfigFile ? path.resolve(customConfigFile) : path.resolve(LOCALIZATION_ROOT, '..', 'config.json');
        try {
            if (fs.existsSync(configPath)) {
                const raw = fs.readFileSync(configPath, 'utf-8');
                const cfg = JSON.parse(raw);
                if (cfg && cfg.customization) {
                    return cfg.customization;
                }
            }
        } catch (e) {}
        return {
            language: 'zh-CN',
            show_quota_badge: true,
            quota_refresh_interval: 60,
            enable_gpu_acceleration: true,
            disable_background_throttling: true,
            expand_v8_memory: true,
            disable_telemetry: true,
            hide_ide_buttons: true,
            auto_retry_on_error: true,
            max_retry_count: 3,
            notify_on_quota_exhausted: true,
            notify_on_max_retry_failed: true
        };
    }

    /**
     * 生成注入用的 runtime 脚本
     */
    generateRuntimeScript(isTraditional = false, customConfig = null, isEnglish = false, customConfigFile = null) {
        const dict = this.loadDictionary(isTraditional, isEnglish);
        // 按英文短语长度从长到短排序
        const phraseEntries = Object.entries(dict).filter(([k]) => k.length >= 15);
        phraseEntries.sort((a, b) => b[0].length - a[0].length);

        const cfg = customConfig || this.loadCustomConfig(customConfigFile);

        let template = fs.readFileSync(this.runtimeTemplatePath, 'utf-8');
        const configCode = `
    const IS_TRADITIONAL = ${isTraditional ? 'true' : 'false'};
    const TRANSLATIONS_MAP = ${JSON.stringify(dict, null, 2)};
    const PHRASE_REPLACEMENTS = ${JSON.stringify(phraseEntries)};
    const CUSTOM_CONFIG = ${JSON.stringify(cfg, null, 2)};
`;
        return template.replace('/* --- I18N_CONFIG_PLACEHOLDER --- */', configCode);
    }

    /**
     * 查询客户端与汉化状态
     */
    getStatus(manualDir = null) {
        const installDir = this.detectInstallDir(manualDir, true);
        if (!installDir) {
            return {
                installed: false,
                installDir: null,
                resourcesDir: null,
                isLocalized: false,
                lang: null,
                hasBackup: false
            };
        }

        const resDir = this.getResourcesDir(installDir);
        const asarPath = path.join(resDir, 'app.asar');
        const bakPath = path.join(resDir, 'app.asar.bak');
        const metaPath = path.join(resDir, '.localization_info.json');

        let isLocalized = false;
        let lang = null;
        let hasBackup = fs.existsSync(bakPath);

        if (fs.existsSync(metaPath)) {
            try {
                const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
                isLocalized = !!meta.localized;
                lang = meta.lang || 'zh-CN';
            } catch (e) {}
        } else if (hasBackup) {
            isLocalized = true;
            lang = 'zh-CN';
        }

        return {
            installed: true,
            installDir: installDir,
            resourcesDir: resDir,
            isV2: fs.existsSync(asarPath),
            isLocalized: isLocalized,
            lang: lang,
            hasBackup: hasBackup
        };
    }

    /**
     * 检测客户端进程是否正在运行
     */
    isClientRunning() {
        try {
            if (process.platform === 'win32') {
                const out = child_process.execSync('tasklist /fi "imagename eq Antigravity.exe" /nh', { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true });
                return out.toLowerCase().includes('antigravity.exe');
            } else if (process.platform === 'darwin') {
                const out = child_process.execSync('pgrep -f Antigravity', { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] });
                return out.trim().length > 0;
            }
        } catch (e) {}
        return false;
    }

    /**
     * 关闭运行中的客户端
     */
    closeClient() {
        console.log('[进程] 正在关闭 Antigravity 客户端以解除文件锁...');
        try {
            if (process.platform === 'win32') {
                child_process.execSync('taskkill /f /im Antigravity.exe /t >nul 2>nul', { windowsHide: true });
            } else {
                child_process.execSync('pkill -f Antigravity >/dev/null 2>&1');
            }
        } catch (e) {}
        const start = Date.now();
        while (Date.now() - start < 1200) {}
    }

    /**
     * 重新拉起客户端
     */
    launchClient(installDir) {
        console.log('\n[启动] 正在重新拉起 Antigravity 客户端...');
        try {
            if (process.platform === 'win32') {
                const exe = path.join(installDir, 'Antigravity.exe');
                if (fs.existsSync(exe)) {
                    const child = child_process.spawn(exe, [], { detached: true, stdio: 'ignore', windowsHide: true });
                    child.unref();
                    console.log('[启动] 客户端启动成功！');
                }
            } else if (process.platform === 'darwin') {
                child_process.exec(`open "${installDir}"`);
                console.log('[启动] 客户端启动成功！');
            }
        } catch (e) {
            console.warn('[警告] 客户端拉起失败:', e.message);
        }
    }

    /**
     * 执行安装调度
     */
    install(options = {}) {
        const installDir = this.detectInstallDir(options.installDir);
        if (!installDir) {
            throw new Error('未找到 Antigravity 安装目录，请使用 --install-dir 手动指定。');
        }

        const wasRunning = this.isClientRunning();
        if (!options.noKill && wasRunning) {
            this.closeClient();
        }

        const resDir = this.getResourcesDir(installDir);
        const customConfig = options.customConfig || this.loadCustomConfig(options.configFile);
        const patcher = new AsarPatcher(resDir, { ...options, customConfig });
        const isEnglish = !!options.en || (customConfig && customConfig.language === 'en');
        const isTw = !!options.tw || (customConfig && customConfig.language === 'zh-TW');
        const runtimeJs = this.generateRuntimeScript(isTw, customConfig, isEnglish, options.configFile);

        const ok = patcher.install(runtimeJs);
        if (ok && wasRunning && !options.noKill) {
            this.launchClient(installDir);
        }
        return ok;
    }

    /**
     * 执行恢复调度
     */
    restore(options = {}) {
        const installDir = this.detectInstallDir(options.installDir);
        if (!installDir) {
            throw new Error('未找到 Antigravity 安装目录。');
        }

        const wasRunning = this.isClientRunning();
        if (!options.noKill && wasRunning) {
            this.closeClient();
        }

        const resDir = this.getResourcesDir(installDir);
        const patcher = new AsarPatcher(resDir, options);
        const ok = patcher.restore();

        if (ok && wasRunning && !options.noKill) {
            this.launchClient(installDir);
        }
        return ok;
    }
}

module.exports = { LocalizationEngine };
