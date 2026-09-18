/**
 * Antigravity 客户端现代化 DOM 实时汉化注入引擎 (Client Runtime)
 * 采用智能上下文语义识别、精确白名单优先与代码/聊天正文沙箱隔离机制
 */
(() => {
    'use strict';

    /* --- I18N_CONFIG_PLACEHOLDER --- */

    const exactMap = new Map(Object.entries(TRANSLATIONS_MAP));
    const lowerMap = new Map();
    for (const [k, v] of exactMap.entries()) {
        lowerMap.set(k.toLowerCase(), v);
    }

    const phrases = PHRASE_REPLACEMENTS; // Array of [english, chinese] sorted by length DESC
    const visitedNodes = new WeakSet();

    // 标签白名单与黑名单定义
    const BLOCKED_TAGS = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'INPUT', 'TEXTAREA', 'SVG', 'CANVAS', 'SYMBOL', 'PATH']);
    const ALWAYS_TRANSLATE_ROLES = new Set(['menu', 'menuitem', 'menubar', 'dialog', 'tooltip', 'tab', 'button', 'status', 'alert']);

    // 真实代码与聊天正文禁区类名
    const BLOCKED_LEAF_CLASSES = [
        'view-lines', 'view-line', 'monaco-editor', 'xterm-screen', 'terminal',
        'markdown-body', 'prose', 'agent-response-content', 'user-query-content'
    ];

    /**
     * 文本规范化：处理空格与特殊标点
     */
    function normalize(str) {
        if (!str) return '';
        return str.replace(/\s+/g, ' ')
                  .replace(/[‘’]/g, "'")
                  .replace(/[“”]/g, '"')
                  .replace(/…/g, '...')
                  .trim();
    }

    /**
     * 判断当前节点是否属于菜单、弹出框、对话框等必须 100% 汉化的 UI 控件
     */
    function isUiControl(node) {
        let el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
        let depth = 0;
        while (el && depth < 8) {
            if (el.nodeType === Node.ELEMENT_NODE) {
                const role = el.getAttribute('role');
                if (role && ALWAYS_TRANSLATE_ROLES.has(role.toLowerCase())) return true;

                const cls = el.className;
                if (typeof cls === 'string' && cls) {
                    const cl = cls.toLowerCase();
                    if (cl.includes('menu') || cl.includes('dropdown') || cl.includes('popover') ||
                        cl.includes('tooltip') || cl.includes('dialog') || cl.includes('modal') ||
                        cl.includes('context-menu') || cl.includes('select-item') || cl.includes('btn') ||
                        cl.includes('button') || cl.includes('header') || cl.includes('title') ||
                        cl.includes('artifact') || cl.includes('card') || cl.includes('badge') ||
                        cl.includes('stat') || cl.includes('diff') || cl.includes('summary') ||
                        cl.includes('tool-') || cl.includes('action') || cl.includes('thinking') ||
                        cl.includes('tag') || cl.includes('footer') || cl.includes('bar')) {
                        return true;
                    }
                }

                if (el.hasAttribute('data-radix-popper-content-wrapper') ||
                    el.hasAttribute('data-floating-ui-portal') ||
                    el.hasAttribute('data-radix-dropdown-menu-content')) {
                    return true;
                }
            }
            el = el.parentElement || (el.parentNode && el.parentNode.host);
            depth++;
        }
        return false;
    }

    /**
     * 智能判定是否位于需要保护的“代码/聊天正文禁区”
     * 核心规则：如果是菜单、弹层或按钮控件，绝不阻断！只有真正的代码编辑器与消息正文内部才阻断。
     */
    function isInsideBlockedZone(node) {
        let curr = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
        if (!curr) return false;

        // 1. 代码块、富文本编辑器绝对不能汉化，优先级最高
        let checkEl = curr;
        let d = 0;
        while (checkEl && d < 6) {
            if (checkEl.nodeType === Node.ELEMENT_NODE) {
                const tag = checkEl.tagName;
                if (BLOCKED_TAGS.has(tag)) return true;
                if (checkEl.getAttribute('contenteditable') === 'true') return true;
                const cls = checkEl.className;
                if (typeof cls === 'string' && (cls.includes('monaco-editor') || cls.includes('view-lines') || cls.includes('xterm'))) {
                    return true;
                }
            }
            checkEl = checkEl.parentElement;
            d++;
        }

        // 2. 如果是 UI 控件、按钮、卡片头尾、工具调用栏、气泡工具条，允许汉化
        if (isUiControl(node)) {
            return false;
        }

        // 3. 用户消息正文、智能体普通文字正文禁区
        let depth = 0;
        while (curr && depth < 10) {
            if (curr.nodeType === Node.ELEMENT_NODE) {
                const cls = curr.className;
                if (typeof cls === 'string' && cls) {
                    for (const blocked of BLOCKED_LEAF_CLASSES) {
                        if (cls.includes(blocked)) return true;
                    }
                }

                // 阻断明确标记了用户文本正文的角色
                const dataRole = curr.getAttribute('data-role');
                if (dataRole && /^(message-body|user-text|code-content)$/i.test(dataRole)) return true;
            }
            curr = curr.parentElement || (curr.parentNode && curr.parentNode.host);
            depth++;
        }
        return false;
    }

    /**
     * 规范化时间时长显示，例如 "6 days, 23 hours" -> "6 天 23 小时", "1m" -> "1 分钟", "5s" -> "5 秒"
     */
    function formatDuration(dur) {
        if (!dur) return '';
        let s = dur.trim();
        s = s.replace(/(\d+)\s*(?:days?|d)\b/gi, '$1 天')
             .replace(/(\d+)\s*(?:hours?|hrs?|h)\b/gi, IS_TRADITIONAL ? '$1 小時' : '$1 小时')
             .replace(/(\d+)\s*(?:minutes?|mins?|m)\b/gi, IS_TRADITIONAL ? '$1 分鐘' : '$1 分钟')
             .replace(/(\d+)\s*(?:seconds?|secs?|s)\b/gi, '$1 秒')
             .replace(/,\s*/g, ' ')
             .replace(/\s+/g, ' ')
             .trim();
        return s;
    }

    /**
     * 处理快捷键组合文本，例如 "Copy (Ctrl+C)"
     */
    function translateShortcut(text) {
        if (!text) return null;
        const match = text.match(/^(.+?)\s*\((Ctrl|Cmd|Alt|Shift|⌘|⌥|⇧|⌃)\+?([^)]*)\)$/i);
        if (match) {
            const prefix = normalize(match[1]);
            const trans = exactMap.get(prefix) || lowerMap.get(prefix.toLowerCase());
            if (trans) {
                return `${trans} (${match[2]}${match[3] ? '+' + match[3] : ''})`;
            }
        }
        return null;
    }

    /**
     * 核心翻译算法：精确匹配 -> 规则匹配 -> 长句滑动替换
     */
    function translateString(raw) {
        if (!raw || raw.length < 1) return null;
        const norm = normalize(raw);
        if (!norm) return null;

        // 1. 快捷键检测
        const shortcut = translateShortcut(norm);
        if (shortcut) return shortcut;

        // 2. 精确字典匹配
        if (exactMap.has(norm)) return exactMap.get(norm);
        const lower = norm.toLowerCase();
        if (lowerMap.has(lower)) return lowerMap.get(lower);

        // 3. 动态模式规则匹配 (Pattern Matching)
        // 3.1 "Learn more about ..." 支持单字或带 ⓘ 图标及参数
        if (/^Learn more about$/i.test(norm)) {
            return IS_TRADITIONAL ? '瞭解更多關於' : '了解更多关于';
        }
        if (/^Learn more about\s+(.+)$/i.test(norm)) {
            return norm.replace(/^Learn more about\s+(.+)$/i, (match, param) => {
                let p = param.trim();
                let icon = '';
                if (p.endsWith('ⓘ') || p.endsWith('(i)')) {
                    icon = ' ⓘ';
                    p = p.replace(/(ⓘ|\(i\))$/, '').trim();
                }
                const transParam = exactMap.get(p) || lowerMap.get(p.toLowerCase()) || p;
                return (IS_TRADITIONAL ? `瞭解更多關於 ${transParam} 的詳細資訊` : `了解更多关于 ${transParam} 的详细信息`) + icon;
            });
        }

        // 3.2 刷新限制倒计时匹配
        if (/^Refreshes in (\d+)\s*(days?|hours?|minutes?),?\s*(\d+)?\s*(hours?|minutes?)?\.?$/i.test(norm)) {
            return norm.replace(/(\d+)\s*days?/gi, '$1 天')
                       .replace(/(\d+)\s*hours?/gi, IS_TRADITIONAL ? '$1 小時' : '$1 小时')
                       .replace(/(\d+)\s*minutes?/gi, IS_TRADITIONAL ? '$1 分鐘' : '$1 分钟')
                       .replace(/Refreshes in/gi, IS_TRADITIONAL ? '將於' : '将在')
                       .replace(/$/gi, IS_TRADITIONAL ? '後更新' : '后刷新');
        }

        // 3.3 限额完全刷新语句匹配 (e.g. "You have used some of your weekly limit, it will fully refresh in 6 days, 23 hours.")
        if (/^You have (used some of|used all of|reached)\s+(?:your\s+)?(.+?),\s*it will fully refresh in\s+(.+?)\.?$/i.test(norm)) {
            const m = norm.match(/^You have (used some of|used all of|reached)\s+(?:your\s+)?(.+?),\s*it will fully refresh in\s+(.+?)\.?$/i);
            const action = m[1].toLowerCase();
            const quotaType = m[2].trim();
            const rawTime = m[3].trim();
            const formattedTime = formatDuration(rawTime);

            const quotaMap = {
                'weekly limit': IS_TRADITIONAL ? '每週限額' : '每周限额',
                '5-hour limit': IS_TRADITIONAL ? '五小時限額' : '五小时限额',
                '5-hour limit remaining': IS_TRADITIONAL ? '五小時剩餘限額' : '五小时剩余限额',
                'model quota': IS_TRADITIONAL ? '模型配額' : '模型配额'
            };
            const transQuota = quotaMap[quotaType.toLowerCase()] || exactMap.get(quotaType) || lowerMap.get(quotaType.toLowerCase()) || quotaType;

            if (action === 'used some of') {
                return IS_TRADITIONAL ? `您已使用部分 ${transQuota}，將於 ${formattedTime} 後完全重新整理。` : `您已使用部分 ${transQuota}，将于 ${formattedTime} 后完全刷新。`;
            } else {
                return IS_TRADITIONAL ? `您的 ${transQuota} 已達上限，將於 ${formattedTime} 後完全重新整理。` : `您的 ${transQuota} 已达上限，将于 ${formattedTime} 后完全刷新。`;
            }
        }

        // 3.4 "... Remaining" 模式匹配 (e.g. "Weekly Limit Remaining", "五小时限制 Remaining")
        if (/^(.+?)\s+Remaining$/i.test(norm)) {
            const prefix = norm.replace(/\s+Remaining$/i, '').trim();
            const transPrefix = exactMap.get(prefix) || lowerMap.get(prefix.toLowerCase()) || prefix;
            return IS_TRADITIONAL ? `${transPrefix} 剩餘` : `${transPrefix} 剩余`;
        }

        // 3.5 版本号匹配
        if (/^Version\s+([\d.]+)$/i.test(norm)) {
            return norm.replace(/^Version\s+([\d.]+)$/i, '版本 $1');
        }

        // 3.6 相对时间格式 "5m", "2h", "3d"
        if (/^(\d+)(s|m|h|d|w|mo|yr)$/i.test(norm)) {
            const units = {
                s: '秒前', m: IS_TRADITIONAL ? '分鐘前' : '分钟前',
                h: IS_TRADITIONAL ? '小時前' : '小时前', d: '天前',
                w: IS_TRADITIONAL ? '週前' : '周前', mo: IS_TRADITIONAL ? '個月前' : '个月前', yr: '年前'
            };
            return norm.replace(/^(\d+)(s|m|h|d|w|mo|yr)$/i, (_, num, u) => num + (units[u.toLowerCase()] || u));
        }

        // 3.7 工作时长 "Worked for 1m", "Worked for 45s"
        if (/^Worked for\s+(.+)$/i.test(norm)) {
            const dur = norm.replace(/^Worked for\s+/i, '').trim();
            return `已工作 ${formatDuration(dur)}`;
        }

        // 3.8 思考时长 "Thinking for 5s", "Thought for 12s", "Thought for X seconds"
        if (/^(?:Thinking|Thought) for\s+(.+)$/i.test(norm)) {
            const dur = norm.replace(/^(?:Thinking|Thought) for\s+/i, '').trim();
            return `已思考 ${formatDuration(dur)}`;
        }

        // 3.9 文件浏览统计 "Explored 2 files", "Explored 1 file"
        if (/^Explored\s+(\d+)\s+files?$/i.test(norm)) {
            const m = norm.match(/^Explored\s+(\d+)\s+files?$/i);
            return IS_TRADITIONAL ? `已瀏覽 ${m[1]} 個檔案` : `已浏览 ${m[1]} 个文件`;
        }
        if (/^Explored\s+(.+)$/i.test(norm)) {
            const target = norm.replace(/^Explored\s+/i, '').trim();
            const transTarget = exactMap.get(target) || lowerMap.get(target.toLowerCase()) || target;
            return IS_TRADITIONAL ? `已瀏覽 ${transTarget}` : `已浏览 ${transTarget}`;
        }

        // 3.10 分支与版本差异 "Branch main", "All changes since origin/main"
        if (/^Branch\s+([a-zA-Z0-9_\-./]+)$/i.test(norm)) {
            const b = norm.match(/^Branch\s+([a-zA-Z0-9_\-./]+)$/i)[1];
            return `分支 ${b}`;
        }
        if (/^All changes since\s+(.+)$/i.test(norm)) {
            const ref = norm.replace(/^All changes since\s+/i, '').trim();
            return IS_TRADITIONAL ? `自 ${ref} 以來的所有變更` : `自 ${ref} 以来的所有变更`;
        }

        // 3.11 继承权限语句匹配
        if (/^Inherits your\s+(.+?)\s+when working in this project\.?$/i.test(norm)) {
            const m = norm.match(/^Inherits your\s+(.+?)\s+when working in this project\.?$/i);
            const perm = m[1].trim();
            const transPerm = exactMap.get(perm) || lowerMap.get(perm.toLowerCase()) || (perm.includes('全局') || perm.includes('全域') ? perm : (IS_TRADITIONAL ? '全域權限' : '全局权限'));
            return IS_TRADITIONAL ? `在此專案中工作時繼承您的 ${transPerm}。` : `在此项目中工作时继承您的 ${transPerm}。`;
        }
        if (/^Also includes\s+(.+?)\s+when working in this project\.?(?:\s*Learn more\.?)?$/i.test(norm)) {
            const m = norm.match(/^Also includes\s+(.+?)\s+when working in this project\.?(?:\s*Learn more\.?)?$/i);
            const perm = m[1].trim();
            const transPerm = exactMap.get(perm) || lowerMap.get(perm.toLowerCase()) || (perm.includes('全局') || perm.includes('全域') ? perm : (IS_TRADITIONAL ? '全域權限' : '全局权限'));
            return IS_TRADITIONAL ? `在此專案中工作時同樣包含 ${transPerm}。瞭解更多。` : `在此项目中工作时同样包含 ${transPerm}。了解更多。`;
        }

        // 3.12 浏览器子代理与插件目录残片匹配
        if (/Browse and enable plugins from the\s*(?:基于 Google 构建|基於 Google 構建|Built on Google)\s*catalog\.?/i.test(norm)) {
            return IS_TRADITIONAL ? '瀏覽並啟用「基於 Google 構建」目錄中的外掛程式。' : '浏览并启用“基于 Google 构建”目录中的插件。';
        }
        if (/to be installed\.\s*The browser subagent can be invoked by typing/i.test(norm)) {
            return norm.replace(/to be installed\.\s*The browser subagent can be invoked by typing/gi, IS_TRADITIONAL ? '。您可以透過在對話框中輸入' : '。您可以通过在对话框中输入');
        }
        if (/in the conversation input box\.?/i.test(norm)) {
            return norm.replace(/in the conversation input box\.?/gi, IS_TRADITIONAL ? ' 來呼叫瀏覽器子代理。' : ' 来调用浏览器子代理。');
        }

        // 3.13 智能体工具计数 "X tools enabled"
        if (/^(\d+)\s+tools?\s+enabled$/i.test(norm)) {
            return norm.replace(/^(\d+)\s+tools?\s+enabled$/i, IS_TRADITIONAL ? '$1 個工具已啟用' : '$1 个工具已启用');
        }

        // 3.14 确认删除项目弹窗
        if (/^Are you sure you want to delete (the |this )?project (.+?)\??$/i.test(norm)) {
            return norm.replace(/^Are you sure you want to delete (the |this )?project (.+?)\??$/i, (_, __, name) => {
                return IS_TRADITIONAL ? `您確定要刪除專案 ${name} 嗎？` : `您确定要删除项目 ${name} 吗？`;
            });
        }

        // 3.15 代码变更统计 "X files changed", "1 file changed"
        if (/^(\d+)\s+files?\s+changed\b/i.test(norm)) {
            return norm.replace(/^(\d+)\s+files?\s+changed\b/i, (_, num) => {
                return IS_TRADITIONAL ? `${num} 個檔案已變更` : `${num} 个文件已修改`;
            });
        }
        if (/files?\s+changed/i.test(norm)) {
            return norm.replace(/files?\s+changed/gi, IS_TRADITIONAL ? '個檔案已變更' : '个文件已修改');
        }

        // 4. 长句滑动替换 (长度 >= 15 的词条优先替换)
        let modified = raw;
        let matchedPhrase = false;
        for (const [en, cn] of phrases) {
            if (en.length >= 15 && modified.includes(en)) {
                modified = modified.split(en).join(cn);
                matchedPhrase = true;
            }
        }
        if (matchedPhrase) return modified;

        let modifiedNorm = norm;
        let matchedNorm = false;
        for (const [en, cn] of phrases) {
            if (en.length >= 15 && modifiedNorm.includes(en)) {
                modifiedNorm = modifiedNorm.split(en).join(cn);
                matchedNorm = true;
            }
        }
        if (matchedNorm) return modifiedNorm;

        return null;
    }

    /**
     * 翻译 DOM 元素及其属性
     */
    function translateElement(el) {
        if (!el || visitedNodes.has(el)) return;

        // 1. 属性翻译 (placeholder, title, aria-label, data-tooltip)
        const isControl = isUiControl(el);
        if (isControl || !isInsideBlockedZone(el)) {
            for (const attr of ['placeholder', 'title', 'aria-label', 'data-tooltip']) {
                const val = el.getAttribute(attr);
                if (val && !visitedNodes.has(el)) {
                    const trans = translateString(val);
                    if (trans && trans !== val) {
                        el.setAttribute(attr, trans);
                    }
                }
            }
        }

        // 2. 检查子节点
        if (el.shadowRoot) translateNode(el.shadowRoot);
        for (const child of el.childNodes) {
            translateNode(child);
        }
    }

    /**
     * 递归分发翻译节点
     */
    function translateNode(node) {
        if (!node) return;

        try {
            if (node.nodeType === Node.TEXT_NODE) {
                if (visitedNodes.has(node)) return;

                const original = node.nodeValue;
                if (!original || original.trim().length < 1) return;

                // 骨架屏占位与禁区过滤
                if (original.toLowerCase().includes('pack.info')) return;
                if (isInsideBlockedZone(node)) return;

                const trans = translateString(original);
                if (trans && trans !== original) {
                    node.nodeValue = trans;
                    visitedNodes.add(node);
                }
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                translateElement(node);
            }
        } catch (e) {
            // 静默安全保护，绝不中断主进程
        }
    }

    /**
     * 自动拦截并彻底隐藏顶部及界面各处的“打开 / 安装 IDE”多余按钮
     */
    function removeIdeHeaderButtons(scope = document) {
        if (!scope || !scope.querySelectorAll) return;
        try {
            const targets = scope.querySelectorAll('button, a, [role="button"]');
            for (const el of targets) {
                const text = (el.textContent || '').trim();
                const aria = (el.getAttribute('aria-label') || '').trim();
                const title = (el.getAttribute('title') || '').trim();

                const isIdeButton =
                    text === 'Open IDE' || text === '打开 IDE' || text === '開啟 IDE' ||
                    text === 'Install IDE' || text === '安装 IDE' || text === '安裝 IDE' ||
                    text === 'Open in IDE' || text === '在 IDE 中打开' || text === '在 IDE 中開啟' ||
                    text === '打开IDE' || text === '安装IDE' || text === '開啟IDE' || text === '安裝IDE' ||
                    text.includes('Open IDE') || text.includes('Install IDE') ||
                    aria.includes('Open IDE') || aria.includes('Install IDE') ||
                    title.includes('Open IDE') || title.includes('Install IDE');

                if (isIdeButton) {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('width', '0', 'important');
                    el.style.setProperty('height', '0', 'important');
                    el.style.setProperty('margin', '0', 'important');
                    el.style.setProperty('padding', '0', 'important');
                    el.setAttribute('data-ide-hidden', 'true');

                    // 如果父容器仅容纳此 IDE 按钮，连同父容器一同隐藏，彻底防止留下空白占位
                    const parent = el.parentElement;
                    if (parent && parent.children && parent.children.length === 1 && !parent.classList.contains('min-w-0')) {
                        parent.style.setProperty('display', 'none', 'important');
                    }
                }
            }
        } catch (e) {}
    }

    /**
     * 注入全局隐藏 IDE 按钮强力样式规则
     */
    function injectIdeHidingStyle(doc = document) {
        if (!doc || !doc.head || doc.getElementById('antigravity-ide-hider-style')) return;
        try {
            const style = doc.createElement('style');
            style.id = 'antigravity-ide-hider-style';
            style.textContent = `
                [data-ide-hidden="true"],
                button[aria-label*="Install IDE" i],
                button[aria-label*="Open IDE" i],
                button[aria-label*="安装 IDE"],
                button[aria-label*="安裝 IDE"],
                button[aria-label*="打开 IDE"],
                button[aria-label*="開啟 IDE"],
                button[title*="Install IDE" i],
                button[title*="Open IDE" i],
                button[title*="安装 IDE"],
                button[title*="安裝 IDE"],
                button[title*="打开 IDE"],
                button[title*="開啟 IDE"],
                a[href*="antigravity-ide"],
                a[href*="ide-install"] {
                    display: none !important;
                    visibility: hidden !important;
                    width: 0 !important;
                    height: 0 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    border: none !important;
                    pointer-events: none !important;
                }
            `;
            doc.head.appendChild(style);
        } catch (e) {}
    }

    /**
     * =========================================================================
     * 顶部标题栏实时模型额度胶囊组件 (Top-Right Live Model Quota Badge)
     * =========================================================================
     */
    let latestQuotaData = null;
    let isFetchingQuota = false;
    let lastFetchTime = null;
    let quotaPollTimer = null;

    function injectQuotaBadgeStyle(doc = document) {
        if (!doc || !doc.head || doc.getElementById('antigravity-quota-style')) return;
        try {
            const style = doc.createElement('style');
            style.id = 'antigravity-quota-style';
            style.textContent = `
                @keyframes ag-spin { 100% { transform: rotate(360deg); } }
                @keyframes ag-popover-in {
                    from { opacity: 0; transform: translateY(-4px) scale(0.98); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                #antigravity-quota-root {
                    display: inline-flex;
                    align-items: center;
                    margin-left: auto;
                    margin-right: 145px;
                    height: 24px;
                    z-index: 9999;
                    -webkit-app-region: no-drag !important;
                    font-family: system-ui, -apple-system, "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
                    position: relative;
                    user-select: none;
                }
                .ag-quota-pill {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 2px 10px;
                    height: 22px;
                    border-radius: 11px;
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    font-size: 11px;
                    font-weight: 500;
                    color: rgba(255, 255, 255, 0.9);
                    cursor: pointer;
                    box-sizing: border-box;
                    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                    backdrop-filter: blur(8px);
                    -webkit-backdrop-filter: blur(8px);
                }
                .ag-quota-pill:hover {
                    background: rgba(255, 255, 255, 0.16);
                    border-color: rgba(255, 255, 255, 0.28);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
                }
                .ag-quota-dot {
                    width: 7px;
                    height: 7px;
                    border-radius: 50%;
                    display: inline-block;
                    flex-shrink: 0;
                }
                .ag-dot-green { background: #34d399; box-shadow: 0 0 6px rgba(52, 211, 153, 0.7); }
                .ag-dot-purple { background: #a78bfa; box-shadow: 0 0 6px rgba(167, 139, 250, 0.7); }
                .ag-dot-yellow { background: #fbbf24; box-shadow: 0 0 6px rgba(251, 191, 36, 0.7); }
                .ag-dot-red { background: #f87171; box-shadow: 0 0 6px rgba(248, 113, 113, 0.7); }
                .ag-quota-divider {
                    width: 1px;
                    height: 10px;
                    background: rgba(255, 255, 255, 0.2);
                    margin: 0 2px;
                }
                .ag-quota-popover {
                    position: absolute;
                    top: calc(100% + 8px);
                    right: 0;
                    width: 320px;
                    background: #18181b;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                    padding: 14px 16px;
                    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.55), 0 2px 8px rgba(0, 0, 0, 0.3);
                    z-index: 100000;
                    color: #e4e4e7;
                    font-size: 12px;
                    display: none;
                    box-sizing: border-box;
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                }
                .ag-quota-popover.open {
                    display: block;
                    animation: ag-popover-in 0.16s ease-out;
                }
                .ag-pop-head {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding-bottom: 10px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    margin-bottom: 12px;
                }
                .ag-pop-title {
                    font-weight: 600;
                    font-size: 13px;
                    color: #fafafa;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }
                .ag-pop-refresh-btn {
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    color: #d4d4d8;
                    border-radius: 5px;
                    padding: 3px 8px;
                    cursor: pointer;
                    font-size: 11px;
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    transition: all 0.2s;
                }
                .ag-pop-refresh-btn:hover {
                    background: rgba(255, 255, 255, 0.18);
                    color: #ffffff;
                }
                .ag-group {
                    margin-bottom: 14px;
                }
                .ag-group:last-of-type {
                    margin-bottom: 8px;
                }
                .ag-group-name {
                    font-size: 12px;
                    font-weight: 600;
                    color: #a1a1aa;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }
                .ag-meter {
                    margin-bottom: 8px;
                }
                .ag-meter:last-child {
                    margin-bottom: 0;
                }
                .ag-meter-row {
                    display: flex;
                    justify-content: space-between;
                    font-size: 11px;
                    margin-bottom: 4px;
                }
                .ag-meter-label {
                    color: #d4d4d8;
                }
                .ag-meter-pct {
                    font-weight: 600;
                }
                .ag-track {
                    height: 5px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 3px;
                    overflow: hidden;
                }
                .ag-fill {
                    height: 100%;
                    border-radius: 3px;
                    transition: width 0.3s ease;
                }
                .ag-meter-desc {
                    font-size: 10px;
                    color: #71717a;
                    margin-top: 2px;
                }
                .ag-pop-foot {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 10px;
                    padding-top: 8px;
                    border-top: 1px solid rgba(255, 255, 255, 0.08);
                    font-size: 10px;
                    color: #71717a;
                }
            `;
            doc.head.appendChild(style);
        } catch (e) {}
    }

    function formatCountdown(isoString) {
        if (!isoString) return '';
        try {
            const target = new Date(isoString).getTime();
            const now = Date.now();
            const diff = target - now;
            if (diff <= 0) return '即将刷新';
            const totalHours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const days = Math.floor(totalHours / 24);
            const hours = totalHours % 24;
            if (days > 0) return `距离刷新还有 ${days} 天 ${hours} 小时`;
            if (hours > 0) return `距离刷新还有 ${hours} 小时 ${minutes} 分钟`;
            return `距离刷新还有 ${minutes} 分钟`;
        } catch (e) {
            return '';
        }
    }

    function getModelColor(pct, isGemini = true) {
        if (pct < 20) return { dot: 'ag-dot-red', color: '#f87171' };
        if (pct < 50) return { dot: 'ag-dot-yellow', color: '#fbbf24' };
        if (isGemini) return { dot: 'ag-dot-green', color: '#34d399' };
        return { dot: 'ag-dot-purple', color: '#a78bfa' };
    }

    function parseQuotaBuckets(data) {
        let g5h = null, gWeekly = null;
        let c5h = null, cWeekly = null;

        if (data && Array.isArray(data.groups)) {
            for (const g of data.groups) {
                const name = (g.name || '').toLowerCase();
                const isGemini = name.includes('gemini');
                for (const b of (g.buckets || [])) {
                    const period = (b.period || '').toUpperCase();
                    if (period.includes('FIVE_HOURS') || period.includes('5H')) {
                        if (isGemini) g5h = b; else c5h = b;
                    } else if (period.includes('WEEKLY')) {
                        if (isGemini) gWeekly = b; else cWeekly = b;
                    }
                }
            }
        }

        const getPct = (b) => {
            if (!b || typeof b.remainingFraction !== 'number') return 100;
            return Math.min(100, Math.max(0, Math.round(b.remainingFraction * 100)));
        };

        return {
            gemini: {
                pct5h: getPct(g5h),
                time5h: g5h ? g5h.resetTime : null,
                pctWeekly: getPct(gWeekly),
                timeWeekly: gWeekly ? gWeekly.resetTime : null
            },
            claude: {
                pct5h: getPct(c5h),
                time5h: c5h ? c5h.resetTime : null,
                pctWeekly: getPct(cWeekly),
                timeWeekly: cWeekly ? cWeekly.resetTime : null
            }
        };
    }

    function renderQuotaUi() {
        const root = document.getElementById('antigravity-quota-root');
        if (!root) return;

        const info = parseQuotaBuckets(latestQuotaData);
        const gColor = getModelColor(info.gemini.pct5h, true);
        const cColor = getModelColor(info.claude.pct5h, false);

        const pill = root.querySelector('.ag-quota-pill');
        if (pill) {
            pill.innerHTML = `
                <span class="ag-quota-dot ${gColor.dot}"></span>
                <span>Gemini ${info.gemini.pct5h}%</span>
                <span class="ag-quota-divider"></span>
                <span class="ag-quota-dot ${cColor.dot}"></span>
                <span>Claude ${info.claude.pct5h}%</span>
            `;
        }

        const popover = root.querySelector('.ag-quota-popover');
        if (popover) {
            const timeStr = lastFetchTime ? lastFetchTime.toTimeString().split(' ')[0] : '--:--:--';
            const gWeekColor = getModelColor(info.gemini.pctWeekly, true);
            const cWeekColor = getModelColor(info.claude.pctWeekly, false);

            popover.innerHTML = `
                <div class="ag-pop-head">
                    <div class="ag-pop-title">
                        <span>📊</span>
                        <span>模型额度详情</span>
                    </div>
                    <button class="ag-pop-refresh-btn" type="button" title="点击立即刷新额度">
                        <span class="ag-spin-icon">🔄</span>
                        <span>刷新</span>
                    </button>
                </div>
                
                <div class="ag-group">
                    <div class="ag-group-name">
                        <span class="ag-quota-dot ${gColor.dot}"></span>
                        <span>Gemini 模型</span>
                    </div>
                    <div class="ag-meter">
                        <div class="ag-meter-row">
                            <span class="ag-meter-label">5小时限制剩余</span>
                            <span class="ag-meter-pct" style="color: ${gColor.color}">${info.gemini.pct5h}%</span>
                        </div>
                        <div class="ag-track">
                            <div class="ag-fill" style="width: ${info.gemini.pct5h}%; background: ${gColor.color}"></div>
                        </div>
                        <div class="ag-meter-desc">${formatCountdown(info.gemini.time5h)}</div>
                    </div>
                    <div class="ag-meter" style="margin-top: 6px;">
                        <div class="ag-meter-row">
                            <span class="ag-meter-label">周限制剩余</span>
                            <span class="ag-meter-pct" style="color: ${gWeekColor.color}">${info.gemini.pctWeekly}%</span>
                        </div>
                        <div class="ag-track">
                            <div class="ag-fill" style="width: ${info.gemini.pctWeekly}%; background: ${gWeekColor.color}"></div>
                        </div>
                        <div class="ag-meter-desc">${formatCountdown(info.gemini.timeWeekly)}</div>
                    </div>
                </div>

                <div class="ag-group">
                    <div class="ag-group-name">
                        <span class="ag-quota-dot ${cColor.dot}"></span>
                        <span>Claude & GPT 模型</span>
                    </div>
                    <div class="ag-meter">
                        <div class="ag-meter-row">
                            <span class="ag-meter-label">5小时限制剩余</span>
                            <span class="ag-meter-pct" style="color: ${cColor.color}">${info.claude.pct5h}%</span>
                        </div>
                        <div class="ag-track">
                            <div class="ag-fill" style="width: ${info.claude.pct5h}%; background: ${cColor.color}"></div>
                        </div>
                        <div class="ag-meter-desc">${formatCountdown(info.claude.time5h)}</div>
                    </div>
                    <div class="ag-meter" style="margin-top: 6px;">
                        <div class="ag-meter-row">
                            <span class="ag-meter-label">周限制剩余</span>
                            <span class="ag-meter-pct" style="color: ${cWeekColor.color}">${info.claude.pctWeekly}%</span>
                        </div>
                        <div class="ag-track">
                            <div class="ag-fill" style="width: ${info.claude.pctWeekly}%; background: ${cWeekColor.color}"></div>
                        </div>
                        <div class="ag-meter-desc">${formatCountdown(info.claude.timeWeekly)}</div>
                    </div>
                </div>

                <div class="ag-pop-foot">
                    <span>更新于 ${timeStr}</span>
                    <span>Antigravity Orbit</span>
                </div>
            `;

            const refBtn = popover.querySelector('.ag-pop-refresh-btn');
            if (refBtn) {
                refBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const icon = refBtn.querySelector('.ag-spin-icon');
                    if (icon) icon.style.animation = 'ag-spin 0.6s linear infinite';
                    fetchQuotaSummary().finally(() => {
                        if (icon) icon.style.animation = 'none';
                    });
                });
            }
        }
    }

    async function fetchQuotaSummary() {
        if (isFetchingQuota) return latestQuotaData;
        isFetchingQuota = true;

        const csrf = (window.__APP_CONFIG__ && window.__APP_CONFIG__.csrfToken) ? window.__APP_CONFIG__.csrfToken : '';
        try {
            const res = await fetch('/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Connect-Protocol-Version': '1',
                    'x-codeium-csrf-token': csrf
                },
                body: '{}'
            });
            if (res.ok) {
                const data = await res.json();
                latestQuotaData = data;
                lastFetchTime = new Date();
                renderQuotaUi();
                return data;
            }
        } catch (err) {
            // 静默处理网络或端口尚未就绪
        } finally {
            isFetchingQuota = false;
        }
        return latestQuotaData;
    }

    function mountQuotaBadge() {
        const cfg = (typeof CUSTOM_CONFIG !== 'undefined' ? CUSTOM_CONFIG : {}) || {};
        if (cfg.show_quota_badge === false) {
            const existing = document.getElementById('antigravity-quota-root');
            if (existing) existing.remove();
            return;
        }

        const titleBar = document.querySelector('[data-testid="title-menu-bar"]');
        if (!titleBar) return;

        let root = document.getElementById('antigravity-quota-root');
        if (!root) {
            injectQuotaBadgeStyle(document);

            root = document.createElement('div');
            root.id = 'antigravity-quota-root';
            root.innerHTML = `
                <div class="ag-quota-pill" title="点击查看模型额度详情">
                    <span class="ag-quota-dot ag-dot-green"></span>
                    <span>额度载入中...</span>
                </div>
                <div class="ag-quota-popover"></div>
            `;

            const pill = root.querySelector('.ag-quota-pill');
            const popover = root.querySelector('.ag-quota-popover');

            pill.addEventListener('click', (e) => {
                e.stopPropagation();
                popover.classList.toggle('open');
                if (popover.classList.contains('open')) {
                    fetchQuotaSummary();
                }
            });

            document.addEventListener('click', (e) => {
                if (!root.contains(e.target)) {
                    popover.classList.remove('open');
                }
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    popover.classList.remove('open');
                }
            });

            titleBar.appendChild(root);
            fetchQuotaSummary();

            if (!quotaPollTimer) {
                const intervalSec = (cfg.quota_refresh_interval && cfg.quota_refresh_interval >= 5) ? cfg.quota_refresh_interval : 60;
                quotaPollTimer = setInterval(fetchQuotaSummary, intervalSec * 1000);
                window.addEventListener('focus', fetchQuotaSummary);
            }
        }
    }

    /**
     * 启动 MutationObserver 监听引擎
     */
    function startLocalizationObserver() {
        const root = document.body || document.documentElement;
        if (!root) return;

        const cfg = (typeof CUSTOM_CONFIG !== 'undefined' ? CUSTOM_CONFIG : {}) || {};

        if (cfg.hide_ide_buttons !== false) {
            injectIdeHidingStyle(document);
            removeIdeHeaderButtons(root);
        }

        if (cfg.show_quota_badge !== false) {
            mountQuotaBadge();
        }

        const observer = new MutationObserver((mutations) => {
            if (cfg.hide_ide_buttons !== false) {
                removeIdeHeaderButtons(root);
            }
            if (cfg.show_quota_badge !== false && !document.getElementById('antigravity-quota-root')) {
                mountQuotaBadge();
            }
            for (const m of mutations) {
                if (m.type === 'childList') {
                    for (const n of m.addedNodes) {
                        translateNode(n);
                        if (cfg.hide_ide_buttons !== false && n.nodeType === Node.ELEMENT_NODE) {
                            removeIdeHeaderButtons(n);
                        }
                    }
                } else if (m.type === 'characterData') {
                    translateNode(m.target);
                }
            }
        });

        const config = { childList: true, subtree: true, characterData: true };
        try {
            observer.observe(root, config);
            translateNode(root);
        } catch (e) {}

        // Shadow DOM 穿透拦截
        const originalAttachShadow = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function(...args) {
            const shadowRoot = originalAttachShadow.apply(this, args);
            try {
                if (cfg.hide_ide_buttons !== false) {
                    injectIdeHidingStyle(shadowRoot);
                    removeIdeHeaderButtons(shadowRoot);
                }
                observer.observe(shadowRoot, config);
                translateNode(shadowRoot);
            } catch (e) {}
            return shadowRoot;
        };
    }

    // 页面生命周期挂载
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startLocalizationObserver);
    } else {
        startLocalizationObserver();
    }
    window.addEventListener('load', startLocalizationObserver);
    setTimeout(startLocalizationObserver, 50);
    setTimeout(startLocalizationObserver, 150);
    setTimeout(startLocalizationObserver, 300);
    setTimeout(startLocalizationObserver, 600);
    setTimeout(startLocalizationObserver, 1200);
    setTimeout(startLocalizationObserver, 2500);
})();
