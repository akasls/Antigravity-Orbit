#!/usr/bin/env node
/**
 * Antigravity 客户端自主汉化系统 CLI 执行入口
 */
const { LocalizationEngine } = require('./core/engine');

function showHelp() {
    console.log(`
Antigravity 自主汉化引擎 CLI

用法:
  node engine.js [操作] [选项]

操作:
  --status              查询 Antigravity 客户端路径及汉化状态
  --restore, --huifu    卸载汉化，一键还原官方原版英文

选项:
  --json                以 JSON 格式输出状态信息 (配合 --status)
  --tw, --traditional   安装繁体中文语言包 (默认: 简体中文)
  --install-dir <path>  手动指定 Antigravity 安装目录
  --no-kill             执行时不强制终止运行中的 Antigravity 客户端
  --help, -h            显示本帮助信息
`);
}

function parseArgs() {
    const args = process.argv.slice(2);
    const opts = {
        action: 'install',
        json: false,
        tw: false,
        installDir: null,
        noKill: false
    };

    for (let i = 0; i < args.length; i++) {
        const a = args[i];
        if (a === '--help' || a === '-h') {
            showHelp();
            process.exit(0);
        } else if (a === '--status') {
            opts.action = 'status';
        } else if (a === '--restore' || a === '--huifu') {
            opts.action = 'restore';
        } else if (a === '--json') {
            opts.json = true;
        } else if (a === '--tw' || a === '--traditional') {
            opts.tw = true;
        } else if (a === '--no-kill') {
            opts.noKill = true;
        } else if (a === '--install-dir') {
            opts.installDir = args[i + 1] || null;
            i++;
        } else if (a.startsWith('--install-dir=')) {
            opts.installDir = a.slice('--install-dir='.length);
        }
    }
    return opts;
}

function main() {
    const engine = new LocalizationEngine();
    const opts = parseArgs();

    try {
        if (opts.action === 'status') {
            const s = engine.getStatus(opts.installDir);
            if (opts.json) {
                console.log(JSON.stringify(s, null, 2));
            } else {
                console.log("=========================================");
                console.log("🌐【Antigravity 客户端汉化与运行状态】");
                console.log("=========================================");
                if (!s.installed) {
                    console.log("• 安装状态: 🔴 未检测到 Antigravity 安装目录");
                } else {
                    console.log(`• 软件路径: ${s.installDir}`);
                    const langStr = s.lang === 'zh-TW' ? '繁体中文' : (s.lang === 'zh-CN' ? '简体中文' : '官方英文');
                    const stateDesc = s.isLocalized 
                        ? `🟢 已汉化 (${langStr})` 
                        : '⚪ 官方原版英文';
                    console.log(`• 界面语言: ${stateDesc}`);
                    console.log(`• 官方备份: ${s.hasBackup ? '🟢 存在 (可随时一键还原)' : '⚪ 未创建'}`);
                }
                console.log("=========================================");
            }
            process.exit(0);
        }

        if (opts.action === 'restore') {
            console.log("====== 正在卸载中文汉化，恢复官方原版 ======");
            const ok = engine.restore(opts);
            process.exit(ok ? 0 : 1);
        }

        // 默认: install
        const langName = opts.tw ? "繁体中文" : "简体中文";
        console.log(`====== 正在安装 Antigravity ${langName}汉化 (全新架构版) ======`);
        const ok = engine.install(opts);
        process.exit(ok ? 0 : 1);

    } catch (err) {
        console.error(`[错误] ${err.message}`);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}
