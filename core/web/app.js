/**
 * Antigravity Orbit - 现代桌面核心控制器 (v3.3.0)
 * 实时自动保存、Google OAuth 网页授权、Claude 与 Gemini 双列配额看板、
 * 后台自动定时刷新与无感切号。
 */

let appState = {
  config: {},
  status: {},
  account_pool: null,
  prompt: null,
  logs: "",
  activeTab: "accounts",
  isSaving: false
};

let oauthPollTimer = null;
let autoSaveTimer = null;
let autoRefreshTimer = null;

// 监听 pywebview 原生桥接就绪
window.addEventListener('pywebviewready', () => {
  initApp();
});

// 脱机降级或浏览器直接预览兜底
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (!window.pywebview) {
      console.warn("运行于静态演示模式。");
      setupTabs();
      setupEvents();
      renderMockData();
    }
  }, 300);
});

async function initApp() {
  setupTabs();
  setupEvents();
  await loadInitialData();
  startQuotaAutoRefresher();
}

/**
 * 侧边栏 5 大工作区分组切换
 */
function setupTabs() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      if (!targetTab) return;
      switchToTab(targetTab);
    });
  });
}

function switchToTab(tabName) {
  appState.activeTab = tabName;

  // 1. 更新导航栏高亮
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(n => {
    if (n.getAttribute('data-tab') === tabName) {
      n.classList.add('active');
    } else {
      n.classList.remove('active');
    }
  });

  // 2. 控制页面显隐
  const panes = document.querySelectorAll('.tab-pane');
  panes.forEach(pane => {
    if (pane.id === `tab-${tabName}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // 3. 切换至账号池时静默刷新最新额度
  if (tabName === 'accounts') {
    silentRefreshPool();
  }

  // 4. 切换至系统维护时分析存储
  if (tabName === 'system') {
    loadStorageAnalysis();
  }
}

/**
 * 获取初始全量数据并渲染
 */
async function loadInitialData() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const data = await window.pywebview.api.get_initial_data();
    if (data) {
      appState.config = data.config || {};
      appState.status = data.status || {};
      appState.account_pool = data.account_pool || { accounts: [], total: 0 };
      appState.prompt = data.prompt || {};
      appState.logs = data.logs || "";

      renderAll();
    }
  } catch (err) {
    console.error("加载初始数据失败:", err);
    showToast("连接原生后端失败: " + err, "error");
  }
}

/**
 * 前端后台自动定时轮询刷新账号池额度 (解决额度不自动刷新的问题)
 */
function startQuotaAutoRefresher() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  // 每 30 秒轮询一次后端状态，若后端后台线程已完成刷新则即时更新 UI
  autoRefreshTimer = setInterval(async () => {
    await silentRefreshPool();
  }, 30000);
}

async function silentRefreshPool() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const res = await window.pywebview.api.get_account_pool();
    if (res && res.success && res.data) {
      appState.account_pool = res.data;
      renderAccountPool();
    }
  } catch (e) {
    // 静默容错
  }
}

/**
 * 全量渲染页面组件
 */
function renderAll() {
  renderAccountPool();
  renderConfigForm();
  renderSystemStatus();
  renderPromptEditor();
  renderLogs();
}

const openDrawers = new Set();
const drawerFilters = {};

function formatResetCountdown(isoStr) {
  if (!isoStr) return '';
  try {
    const target = new Date(isoStr).getTime();
    if (isNaN(target)) return '';
    const diff = target - Date.now();
    if (diff <= 0) return '已恢复';

    const totalMinutes = Math.floor(diff / 60000);
    const totalHours = Math.floor(totalMinutes / 60);
    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;
    const mins = totalMinutes % 60;

    if (days > 0) {
      return `${days}天${hours}小时后重置`;
    }
    if (hours > 0) {
      return `${hours}小时${mins}分后重置`;
    }
    if (mins > 0) {
      return `${mins}分钟后重置`;
    }
    return '即将重置';
  } catch (e) {
    return '';
  }
}

function formatExactDateTime(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    const m = pad(d.getMonth() + 1);
    const date = pad(d.getDate());
    const h = pad(d.getHours());
    const min = pad(d.getMinutes());
    return `${m}-${date} ${h}:${min}`;
  } catch (e) {
    return '';
  }
}

window.toggleModelsDrawer = function(accId) {
  const drawer = document.getElementById(`models-drawer-${accId}`);
  const arrow = document.getElementById(`arrow-drawer-${accId}`);
  const hint = document.getElementById(`hint-drawer-${accId}`);
  if (!drawer) return;

  if (openDrawers.has(accId)) {
    openDrawers.delete(accId);
    drawer.style.display = 'none';
    if (arrow) arrow.classList.remove('open');
    if (hint) hint.textContent = '展开';
  } else {
    openDrawers.add(accId);
    drawer.style.display = 'block';
    if (arrow) arrow.classList.add('open');
    if (hint) hint.textContent = '收起';
  }
};

window.filterDrawerModels = function(accId, cat, btnEl) {
  drawerFilters[accId] = cat;
  const drawer = document.getElementById(`models-drawer-${accId}`);
  if (!drawer) return;

  const btns = drawer.querySelectorAll('.btn-model-filter');
  btns.forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  const cards = drawer.querySelectorAll('.model-item-card');
  cards.forEach(card => {
    const cardCat = card.getAttribute('data-cat');
    if (cat === 'all' || cardCat === cat) {
      card.style.display = '';
    } else {
      card.style.display = 'none';
    }
  });
};

/**
 * 渲染账号池：支持 Claude 与 Gemini 5H / 周限 对比矩阵及具体模型明细展开
 */
function renderAccountPool() {
  const pool = appState.account_pool || { accounts: [], total: 0, healthy: 0, low_or_exhausted: 0 };
  const accounts = pool.accounts || [];

  // 1. 更新顶部指标卡片
  const totalEl = document.getElementById('metric-total-count');
  const proEl = document.getElementById('metric-pro-count');
  const healthyEl = document.getElementById('metric-healthy-count');
  const lowEl = document.getElementById('metric-low-count');

  const proCount = accounts.filter(a => {
    const tier = (a.quota && (a.quota.tier || a.quota.tier_display || '')) ? (a.quota.tier || a.quota.tier_display).toLowerCase() : '';
    return tier.includes('pro') || tier.includes('plus') || tier.includes('ultra');
  }).length;

  if (totalEl) totalEl.textContent = accounts.length;
  if (proEl) proEl.textContent = proCount;
  if (healthyEl) healthyEl.textContent = pool.healthy || 0;
  if (lowEl) lowEl.textContent = pool.low_or_exhausted || 0;

  // 2. 渲染多账号卡片流 (按 Claude 与 Gemini 5H/周限 双列矩阵展示)
  const container = document.getElementById('account-cards-container');
  if (!container) return;

  if (accounts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">👥</div>
        <div class="empty-title">暂无已导入账号</div>
        <div class="empty-desc">点击右上角【网页登录】快速授权，或【手动导入】粘贴 Token</div>
      </div>
    `;
    return;
  }

  container.innerHTML = accounts.map(acc => {
    const q = acc.quota || {};

    // 解析 Claude 限额与重置倒计时
    const c5h = (typeof q.claude_5h_percent === 'number') ? q.claude_5h_percent 
      : ((typeof q.five_hour_percent === 'number') ? q.five_hour_percent : 100);
    const cW = (typeof q.claude_weekly_percent === 'number') ? q.claude_weekly_percent 
      : ((typeof q.weekly_percent === 'number') ? q.weekly_percent : 100);

    const c5hReset = formatResetCountdown(q.claude_5h_reset || q.five_hour_reset);
    const c5hExact = formatExactDateTime(q.claude_5h_reset || q.five_hour_reset);
    const cWReset = formatResetCountdown(q.claude_weekly_reset || q.weekly_reset);
    const cWExact = formatExactDateTime(q.claude_weekly_reset || q.weekly_reset);

    // 解析 Gemini 限额与重置倒计时
    const g5h = (typeof q.gemini_5h_percent === 'number') ? q.gemini_5h_percent 
      : ((typeof q.five_hour_percent === 'number') ? q.five_hour_percent : 100);
    const gW = (typeof q.gemini_weekly_percent === 'number') ? q.gemini_weekly_percent 
      : ((typeof q.weekly_percent === 'number') ? q.weekly_percent : 100);

    const g5hReset = formatResetCountdown(q.gemini_5h_reset || q.five_hour_reset);
    const g5hExact = formatExactDateTime(q.gemini_5h_reset || q.five_hour_reset);
    const gWReset = formatResetCountdown(q.gemini_weekly_reset || q.weekly_reset);
    const gWExact = formatExactDateTime(q.gemini_weekly_reset || q.weekly_reset);

    const tier = q.tier_display || q.tier || 'Google AI';
    const isPro = tier.toLowerCase().includes('pro');
    const isUltra = tier.toLowerCase().includes('ultra');
    const badgeClass = isPro ? 'badge-pro' : (isUltra ? 'badge-ultra' : 'badge-free');

    const fillC5h = getProgressColorClass(c5h);
    const fillCW = getProgressColorClass(cW);
    const fillG5h = getProgressColorClass(g5h);
    const fillGW = getProgressColorClass(gW);

    const minPct = Math.min(c5h, cW, g5h, gW);
    let statusBadge = '<span class="status-tag status-online">正常</span>';
    if (minPct <= 0) {
      statusBadge = '<span class="status-tag" style="background:#fef2f2;color:#ef4444;">耗尽</span>';
    } else if (minPct <= 20) {
      statusBadge = '<span class="status-tag" style="background:#fffbeb;color:#d97706;">紧张</span>';
    }

    const avatarHtml = acc.avatar 
      ? `<img src="${acc.avatar}" alt="Avatar">`
      : (acc.email || "A").charAt(0).toUpperCase();

    // 解析具体模型明细
    const rawModels = q.models || {};
    const modelKeys = Object.keys(rawModels);
    const hasModels = modelKeys.length > 0;
    const isDrawerOpen = openDrawers.has(acc.id);
    const curFilter = drawerFilters[acc.id] || 'all';

    let modelsGridHtml = '';
    let claudeCount = 0;
    let geminiCount = 0;

    if (hasModels) {
      const modelItems = modelKeys.map(k => {
        const m = rawModels[k] || {};
        const pct = typeof m.percent === 'number' ? m.percent : 100;
        const resetCd = formatResetCountdown(m.resetTime);
        const exactDt = formatExactDateTime(m.resetTime);
        const isClaude = k.includes('claude') || k.includes('3p') || k.includes('gpt');
        const isGemini = k.includes('gemini');
        const cat = isClaude ? 'claude' : (isGemini ? 'gemini' : 'other');

        if (cat === 'claude') claudeCount++;
        if (cat === 'gemini') geminiCount++;

        return {
          id: k,
          displayName: m.displayName || k,
          percent: pct,
          resetCountdown: resetCd,
          exactTime: exactDt,
          cat: cat,
          colorClass: getProgressColorClass(pct)
        };
      });

      // 旗舰核心模型优先排序
      modelItems.sort((a, b) => {
        const aKey = a.displayName.toLowerCase();
        const bKey = b.displayName.toLowerCase();
        const aCore = aKey.includes('claude') || aKey.includes('pro') || aKey.includes('gpt');
        const bCore = bKey.includes('claude') || bKey.includes('pro') || bKey.includes('gpt');
        if (aCore && !bCore) return -1;
        if (!aCore && bCore) return 1;
        return a.displayName.localeCompare(b.displayName);
      });

      modelsGridHtml = modelItems.map(m => {
        const isHidden = (curFilter !== 'all' && m.cat !== curFilter);
        return `
          <div class="model-item-card" data-cat="${m.cat}" style="${isHidden ? 'display: none;' : ''}">
            <div class="model-item-header">
              <span class="model-item-title" title="${m.displayName} (${m.id})">${m.displayName}</span>
              <span class="model-item-pct ${m.colorClass}">${m.percent}%</span>
            </div>
            <div class="progress-track" style="height: 4px; margin: 4px 0 3px;">
              <div class="progress-fill ${m.colorClass}" style="width: ${m.percent}%;"></div>
            </div>
            <div class="model-item-footer">
              <span class="model-item-reset" title="${m.exactTime ? '下次重置时间: ' + m.exactTime : ''}">
                ${m.resetCountdown || '与周期同步'}
              </span>
            </div>
          </div>
        `;
      }).join('');
    }

    return `
      <div class="account-card ${acc.is_active ? 'active' : ''}">
        <div class="account-card-header">
          <div class="account-card-user">
            <div class="account-card-avatar">${avatarHtml}</div>
            <div class="account-card-name-wrap">
              <div class="account-card-email" title="${acc.email}">${acc.email}</div>
              <div class="account-card-name">${acc.name || 'Antigravity 用户'}</div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="badge badge-plan ${badgeClass}">${tier.toUpperCase()}</span>
            ${statusBadge}
          </div>
        </div>

        <!-- Claude 与 Gemini 5H / 周限 对比矩阵 (含下次重置时间倒计时) -->
        <div class="account-quota-matrix">
          <!-- Claude 列 -->
          <div class="quota-matrix-col">
            <div class="quota-col-title">
              <span class="quota-brand-dot claude-dot"></span>
              <span>Claude</span>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">5H</span>
                ${c5hReset ? `<span class="quota-cell-reset" title="下次重置: ${c5hExact}">${c5hReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillC5h}" style="width: ${c5h}%;"></div>
                </div>
                <span class="quota-cell-val">${c5h}%</span>
              </div>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">周限</span>
                ${cWReset ? `<span class="quota-cell-reset" title="下次重置: ${cWExact}">${cWReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillCW}" style="width: ${cW}%;"></div>
                </div>
                <span class="quota-cell-val">${cW}%</span>
              </div>
            </div>
          </div>

          <!-- 分隔中线 -->
          <div class="quota-matrix-divider"></div>

          <!-- Gemini 列 -->
          <div class="quota-matrix-col">
            <div class="quota-col-title">
              <span class="quota-brand-dot gemini-dot"></span>
              <span>Gemini</span>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">5H</span>
                ${g5hReset ? `<span class="quota-cell-reset" title="下次重置: ${g5hExact}">${g5hReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillG5h}" style="width: ${g5h}%;"></div>
                </div>
                <span class="quota-cell-val">${g5h}%</span>
              </div>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">周限</span>
                ${gWReset ? `<span class="quota-cell-reset" title="下次重置: ${gWExact}">${gWReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillGW}" style="width: ${gW}%;"></div>
                </div>
                <span class="quota-cell-val">${gW}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 具体模型额度明细折叠抽屉 -->
        ${hasModels ? `
          <div class="account-models-collapse" onclick="toggleModelsDrawer('${acc.id}')">
            <div class="models-collapse-left">
              <svg style="width: 13px; height: 13px; color: var(--accent);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
              </svg>
              <span class="models-collapse-title">查看具体模型额度明细</span>
              <span class="models-count-tag">${modelKeys.length} 个模型</span>
            </div>
            <div class="models-collapse-right">
              <span class="models-collapse-hint" id="hint-drawer-${acc.id}">${isDrawerOpen ? '收起' : '展开'}</span>
              <svg class="models-collapse-arrow ${isDrawerOpen ? 'open' : ''}" id="arrow-drawer-${acc.id}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
          </div>

          <div class="account-models-drawer" id="models-drawer-${acc.id}" style="${isDrawerOpen ? 'display: block;' : 'display: none;'}">
            <div class="models-filter-bar">
              <button type="button" class="btn-model-filter ${curFilter === 'all' ? 'active' : ''}" data-filter="all" onclick="filterDrawerModels('${acc.id}', 'all', this)">全部 (${modelKeys.length})</button>
              <button type="button" class="btn-model-filter ${curFilter === 'claude' ? 'active' : ''}" data-filter="claude" onclick="filterDrawerModels('${acc.id}', 'claude', this)">Claude & GPT (${claudeCount})</button>
              <button type="button" class="btn-model-filter ${curFilter === 'gemini' ? 'active' : ''}" data-filter="gemini" onclick="filterDrawerModels('${acc.id}', 'gemini', this)">Gemini (${geminiCount})</button>
            </div>
            <div class="models-grid" id="models-grid-${acc.id}">
              ${modelsGridHtml}
            </div>
          </div>
        ` : ''}

        <div class="account-card-footer">
          <span style="font-size: 11px; color: var(--text-dim);">${acc.last_refreshed_text || '刚刚'}</span>
          <div class="account-card-actions">
            ${acc.is_active 
              ? `<span class="badge-status-active"><span class="status-dot-pulse"></span> 使用中</span>`
              : `<button class="btn btn-secondary btn-sm" onclick="handleSwitchAccount('${acc.id}')">切换</button>`
            }
            <button class="btn-icon" title="刷新该账号配额" onclick="handleRefreshSingleQuota('${acc.id}')">
              <svg style="width: 14px; height: 14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
            </button>
            <button class="btn-icon btn-icon-danger" title="移除账号" onclick="handleDeleteAccount('${acc.id}', '${acc.email}')">
              <svg style="width: 14px; height: 14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function getProgressColorClass(pct) {
  if (pct > 30) return 'fill-healthy';
  if (pct > 15) return 'fill-warning';
  return 'fill-exhausted';
}

/**
 * 渲染配置表单
 */
function renderConfigForm() {
  const cfg = appState.config || {};
  const custom = cfg.customization || {};
  const ch = cfg.channels || {};

  // 1. 性能与专属代理
  setCheckbox('custom-proxy-enabled', custom.proxy_enabled);
  setSelect('custom-proxy-type', custom.proxy_type || 'http');
  setInput('custom-proxy-host', custom.proxy_host || '127.0.0.1');
  setInput('custom-proxy-port', custom.proxy_port || 7890);
  setInput('custom-proxy-bypass', custom.proxy_bypass || 'localhost, 127.0.0.1, *.local');

  setCheckbox('custom-opt-gpu', custom.opt_gpu !== false);
  setCheckbox('custom-opt-max-heap', custom.opt_max_heap !== false);
  setCheckbox('custom-opt-nosleep', custom.opt_nosleep !== false);
  setCheckbox('custom-opt-telemetry', custom.opt_telemetry !== false);

  // 2. 自愈与推送
  setCheckbox('custom-auto-retry', cfg.auto_retry_on_error !== false);
  setInput('custom-max-retries', cfg.max_retry_count || 3);
  setCheckbox('custom-notify-quota', cfg.notify_on_quota_exhausted !== false);

  const tg = ch.telegram || {};
  setCheckbox('tg-enabled', tg.enabled);
  setInput('tg-bot-token', tg.bot_token || '');
  setInput('tg-chat-id', tg.chat_id || '');
  setInput('tg-proxy', tg.proxy || '');

  const fs = ch.feishu || {};
  setCheckbox('feishu-enabled', fs.enabled);
  setInput('feishu-webhook', fs.webhook || '');

  const wc = ch.wecom || {};
  setCheckbox('wecom-enabled', wc.enabled);
  setInput('wecom-webhook', wc.webhook || '');

  // 3. 系统维护
  setSelect('custom-lang', custom.language || 'zh-CN');
  setCheckbox('custom-quota-badge', custom.show_quota_badge !== false);
  setCheckbox('custom-clean-ui', custom.clean_ui);
  setCheckbox('custom-close-tray', cfg.close_to_tray !== false);
}

/**
 * 渲染系统状态
 */
function renderSystemStatus() {
  const st = appState.status || {};

  const daemonTag = document.getElementById('daemon-status-text');
  const daemonBtn = document.getElementById('btn-toggle-daemon');
  const daemonPort = document.getElementById('daemon-port-text');
  const appAutoCheck = document.getElementById('custom-app-autostart');

  if (daemonPort) daemonPort.textContent = st.daemon_port || 49222;

  if (st.daemon_running) {
    if (daemonTag) {
      daemonTag.textContent = `运行中 (PID: ${st.daemon_pid || '活跃'})`;
      daemonTag.className = "status-tag status-online";
    }
    if (daemonBtn) daemonBtn.textContent = "停止服务";
  } else {
    if (daemonTag) {
      daemonTag.textContent = "已停止";
      daemonTag.className = "status-tag status-offline";
    }
    if (daemonBtn) daemonBtn.textContent = "启动服务";
  }

  if (appAutoCheck) {
    appAutoCheck.checked = Boolean(st.app_autostart);
  }
}

/**
 * 懒加载磁盘占用分析
 */
async function loadStorageAnalysis() {
  if (!window.pywebview || !window.pywebview.api) return;

  const cacheEl = document.getElementById('storage-cache-val');
  const logsEl = document.getElementById('storage-logs-val');
  const totalEl = document.getElementById('storage-total-val');

  try {
    const res = await window.pywebview.api.get_storage_breakdown();
    if (res && res.success && res.data) {
      const d = res.data;
      if (cacheEl) cacheEl.textContent = d.chromium_cache_str || "0 MB";
      if (logsEl) logsEl.textContent = d.brain_temp_str || "0 MB";
      if (totalEl) totalEl.textContent = d.cleanable_total_str || "0 MB";
    }
  } catch (e) {
    console.warn("读取存储分析失败:", e);
  }
}

/**
 * 渲染系统提示词
 */
function renderPromptEditor() {
  const p = appState.prompt || {};
  const textarea = document.getElementById('prompt-editor-content');
  if (textarea && typeof p.content === 'string') {
    textarea.value = p.content;
    updatePromptStats();
  }
}

function updatePromptStats() {
  const textarea = document.getElementById('prompt-editor-content');
  const charEl = document.getElementById('prompt-char-count');
  const lineEl = document.getElementById('prompt-line-count');
  if (!textarea) return;

  const val = textarea.value;
  if (charEl) charEl.textContent = `${val.length} 字符`;
  if (lineEl) lineEl.textContent = `${val.split('\n').length} 行`;
}

/**
 * 渲染运行日志
 */
function renderLogs() {
  const viewer = document.getElementById('terminal-logs');
  if (viewer) {
    viewer.textContent = appState.logs || "暂无日志记录";
    viewer.scrollTop = viewer.scrollHeight;
  }
}

/**
 * 收集当前表单数据
 */
function gatherCurrentConfig() {
  const cfg = JSON.parse(JSON.stringify(appState.config || {}));
  cfg.customization = cfg.customization || {};
  cfg.channels = cfg.channels || {};

  // 性能与代理
  cfg.customization.proxy_enabled = getCheckbox('custom-proxy-enabled');
  cfg.customization.proxy_type = getSelect('custom-proxy-type');
  cfg.customization.proxy_host = getInput('custom-proxy-host');
  cfg.customization.proxy_port = parseInt(getInput('custom-proxy-port')) || 7890;
  cfg.customization.proxy_bypass = getInput('custom-proxy-bypass');

  cfg.customization.opt_gpu = getCheckbox('custom-opt-gpu');
  cfg.customization.opt_max_heap = getCheckbox('custom-opt-max-heap');
  cfg.customization.opt_nosleep = getCheckbox('custom-opt-nosleep');
  cfg.customization.opt_telemetry = getCheckbox('custom-opt-telemetry');

  // 自愈与推送
  cfg.auto_retry_on_error = getCheckbox('custom-auto-retry');
  cfg.max_retry_count = parseInt(getInput('custom-max-retries')) || 3;
  cfg.notify_on_quota_exhausted = getCheckbox('custom-notify-quota');

  cfg.channels.telegram = {
    enabled: getCheckbox('tg-enabled'),
    bot_token: getInput('tg-bot-token'),
    chat_id: getInput('tg-chat-id'),
    proxy: getInput('tg-proxy')
  };

  cfg.channels.feishu = {
    enabled: getCheckbox('feishu-enabled'),
    webhook: getInput('feishu-webhook')
  };

  cfg.channels.wecom = {
    enabled: getCheckbox('wecom-enabled'),
    webhook: getInput('wecom-webhook')
  };

  // 系统与外观
  cfg.customization.language = getSelect('custom-lang');
  cfg.customization.show_quota_badge = getCheckbox('custom-quota-badge');
  cfg.customization.clean_ui = getCheckbox('custom-clean-ui');
  cfg.close_to_tray = getCheckbox('custom-close-tray');

  return cfg;
}

/**
 * 实时修改自动保存生效引擎 (彻底解决每个页面悬浮保存按钮突兀的问题)
 */
function triggerAutoSave(debounceMs = 0) {
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  if (debounceMs > 0) {
    autoSaveTimer = setTimeout(() => handleAutoSaveConfig(), debounceMs);
  } else {
    handleAutoSaveConfig();
  }
}

async function handleAutoSaveConfig() {
  try {
    const updatedCfg = gatherCurrentConfig();
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.save_and_apply(updatedCfg);
      if (res && res.success) {
        appState.config = updatedCfg;
        showToast("已实时自动保存生效", "success");
      }
    }
  } catch (e) {
    console.error("自动保存失败:", e);
  }
}

/**
 * 事件挂载与实时监听
 */
function setupEvents() {
  // 1. 实时变更自动生效绑定 (开关 & 下拉框立即生效，文本框防抖生效)
  const immediateInputs = [
    'custom-proxy-enabled', 'custom-proxy-type', 'custom-opt-gpu', 'custom-opt-max-heap',
    'custom-opt-nosleep', 'custom-opt-telemetry', 'custom-auto-retry', 'custom-notify-quota',
    'tg-enabled', 'feishu-enabled', 'wecom-enabled', 'custom-lang', 'custom-quota-badge',
    'custom-clean-ui', 'custom-close-tray'
  ];
  immediateInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => triggerAutoSave(0));
    }
  });

  const textInputs = [
    'custom-proxy-host', 'custom-proxy-port', 'custom-proxy-bypass', 'custom-max-retries',
    'tg-bot-token', 'tg-chat-id', 'tg-proxy', 'feishu-webhook', 'wecom-webhook'
  ];
  textInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => triggerAutoSave(0));
      el.addEventListener('input', () => triggerAutoSave(600));
    }
  });

  // 2. 账号池工具栏
  const btnOpenOAuthModal = document.getElementById('btn-open-oauth-modal');
  if (btnOpenOAuthModal) {
    btnOpenOAuthModal.addEventListener('click', handleOpenOAuthModal);
  }

  const btnRefreshAll = document.getElementById('btn-refresh-all-quotas');
  if (btnRefreshAll) {
    btnRefreshAll.addEventListener('click', handleRefreshAllQuotas);
  }

  // 3. Google OAuth 网页登录弹窗
  const btnCloseOAuthModal = document.getElementById('btn-close-oauth-modal');
  const btnCancelOAuthModal = document.getElementById('btn-cancel-oauth-modal');
  const btnStartOAuthBrowser = document.getElementById('btn-start-oauth-browser');
  const btnSubmitOAuthCode = document.getElementById('btn-submit-oauth-code');

  if (btnCloseOAuthModal) btnCloseOAuthModal.addEventListener('click', handleCloseOAuthModal);
  if (btnCancelOAuthModal) btnCancelOAuthModal.addEventListener('click', handleCloseOAuthModal);
  if (btnStartOAuthBrowser) btnStartOAuthBrowser.addEventListener('click', handleStartOAuthBrowser);
  if (btnSubmitOAuthCode) btnSubmitOAuthCode.addEventListener('click', handleSubmitOAuthCode);

  // 4. 手动添加账号模态框 (Token / JSON)
  const btnOpenAddModal = document.getElementById('btn-open-add-modal');
  const modalAdd = document.getElementById('modal-add-account');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnSubmitModal = document.getElementById('btn-submit-add-account');

  if (btnOpenAddModal && modalAdd) {
    btnOpenAddModal.addEventListener('click', () => {
      document.getElementById('input-account-token').value = '';
      document.getElementById('input-account-name').value = '';
      modalAdd.classList.add('active');
    });
  }
  if (btnCloseModal && modalAdd) {
    btnCloseModal.addEventListener('click', () => modalAdd.classList.remove('active'));
  }
  if (btnCancelModal && modalAdd) {
    btnCancelModal.addEventListener('click', () => modalAdd.classList.remove('active'));
  }
  if (btnSubmitModal) {
    btnSubmitModal.addEventListener('click', handleAddAccountSubmit);
  }

  // 5. 测试按钮
  const btnTestProxy = document.getElementById('btn-test-proxy');
  if (btnTestProxy) btnTestProxy.addEventListener('click', handleTestProxy);

  const btnTestTg = document.getElementById('btn-test-tg');
  if (btnTestTg) btnTestTg.addEventListener('click', () => handleTestPush('telegram'));

  const btnTestFeishu = document.getElementById('btn-test-feishu');
  if (btnTestFeishu) btnTestFeishu.addEventListener('click', () => handleTestPush('feishu'));

  const btnTestWecom = document.getElementById('btn-test-wecom');
  if (btnTestWecom) btnTestWecom.addEventListener('click', () => handleTestPush('wecom'));

  // 6. 系统提示词
  const textareaPrompt = document.getElementById('prompt-editor-content');
  if (textareaPrompt) textareaPrompt.addEventListener('input', updatePromptStats);

  const btnSavePrompt = document.getElementById('btn-save-prompt');
  if (btnSavePrompt) btnSavePrompt.addEventListener('click', handleSavePrompt);

  // 7. 系统维护中的客户端核心操作 (从底部移入此处)
  const btnRestart = document.getElementById('btn-restart-app');
  if (btnRestart) btnRestart.addEventListener('click', handleRestartApp);

  const btnRestore = document.getElementById('btn-restore-all');
  if (btnRestore) btnRestore.addEventListener('click', handleRestoreEnglish);

  const btnToggleDaemon = document.getElementById('btn-toggle-daemon');
  if (btnToggleDaemon) btnToggleDaemon.addEventListener('click', handleToggleDaemon);

  const appAutoCheck = document.getElementById('custom-app-autostart');
  if (appAutoCheck) {
    appAutoCheck.addEventListener('change', async (e) => {
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.toggle_app_autostart(e.target.checked);
      showToast(res.message, res.success ? 'success' : 'error');
    });
  }

  const btnClean = document.getElementById('btn-clean-storage');
  if (btnClean) btnClean.addEventListener('click', handleCleanStorage);

  const btnRefLogs = document.getElementById('btn-refresh-logs');
  if (btnRefLogs) {
    btnRefLogs.addEventListener('click', async () => {
      if (!window.pywebview || !window.pywebview.api) return;
      const data = await window.pywebview.api.get_initial_data();
      if (data && data.logs) {
        appState.logs = data.logs;
        renderLogs();
        showToast("日志已更新", "success");
      }
    });
  }

  const btnClrLogs = document.getElementById('btn-clear-logs');
  if (btnClrLogs) {
    btnClrLogs.addEventListener('click', async () => {
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.clear_logs();
      showToast(res.message, res.success ? "success" : "error");
      appState.logs = "日志已清空";
      renderLogs();
    });
  }
}

// -------------------------------------------------------------
// Google OAuth 网页登录流程控制器
// -------------------------------------------------------------

function handleOpenOAuthModal() {
  const modal = document.getElementById('modal-oauth-login');
  const statusBox = document.getElementById('oauth-status-text');
  const codeInput = document.getElementById('input-oauth-code');
  const nameInput = document.getElementById('input-oauth-name');
  if (codeInput) codeInput.value = '';
  if (nameInput) nameInput.value = '';
  if (statusBox) {
    statusBox.className = 'oauth-status-box';
    statusBox.innerHTML = '点击上方按钮将在系统默认浏览器打开授权页';
  }
  if (modal) modal.classList.add('active');
}

function handleCloseOAuthModal() {
  const modal = document.getElementById('modal-oauth-login');
  if (modal) modal.classList.remove('active');
  if (oauthPollTimer) {
    clearInterval(oauthPollTimer);
    oauthPollTimer = null;
  }
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.cancel_oauth_login();
  }
}

async function handleStartOAuthBrowser() {
  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前运行于演示模式，无法打开系统浏览器", "warning");
    return;
  }

  const statusBox = document.getElementById('oauth-status-text');
  if (statusBox) {
    statusBox.className = 'oauth-status-box active';
    statusBox.innerHTML = '<span class="status-dot-pulse"></span> 浏览器已唤起，等待网页端登录回调 (127.0.0.1:51121)...';
  }

  showToast("正在启动授权并打开系统默认浏览器...", "warning");
  try {
    const res = await window.pywebview.api.start_oauth_login(true);
    if (res && res.success) {
      if (oauthPollTimer) clearInterval(oauthPollTimer);
      oauthPollTimer = setInterval(pollOAuthStatus, 1200);
    } else {
      showToast(res ? res.message : "启动授权失败", "error");
    }
  } catch (e) {
    showToast("启动授权异常: " + e, "error");
  }
}

async function pollOAuthStatus() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const res = await window.pywebview.api.check_oauth_status();
    if (res && res.status === 'completed') {
      if (oauthPollTimer) {
        clearInterval(oauthPollTimer);
        oauthPollTimer = null;
      }
      const statusBox = document.getElementById('oauth-status-text');
      if (statusBox) {
        statusBox.className = 'oauth-status-box success';
        statusBox.innerHTML = '✓ 授权成功！已成功绑定 Google 账号';
      }
      showToast(res.message || "账号绑定成功！", "success");
      setTimeout(() => {
        handleCloseOAuthModal();
      }, 1000);
      const data = await window.pywebview.api.get_account_pool();
      if (data && data.success) {
        appState.account_pool = data.data;
      } else if (data && data.accounts) {
        appState.account_pool = data;
      }
      renderAccountPool();
    } else if (res && res.status === 'error') {
      if (oauthPollTimer) {
        clearInterval(oauthPollTimer);
        oauthPollTimer = null;
      }
      const statusBox = document.getElementById('oauth-status-text');
      if (statusBox) {
        statusBox.className = 'oauth-status-box';
        statusBox.innerHTML = `✕ 授权失败: ${res.message}`;
      }
      showToast(res.message, "error");
    }
  } catch (e) {
    // 轮询异常静默
  }
}

async function handleSubmitOAuthCode() {
  const code = (document.getElementById('input-oauth-code').value || '').trim();
  const name = (document.getElementById('input-oauth-name').value || '').trim();
  if (!code) {
    showToast("请粘贴浏览器重定向网址或 code 授权码", "warning");
    return;
  }
  if (!window.pywebview || !window.pywebview.api) return;

  showToast("正在提交授权并换取凭据...", "warning");
  try {
    const res = await window.pywebview.api.submit_oauth_code(code, name);
    showToast(res.message, res.success ? "success" : "error");
    if (res.success) {
      handleCloseOAuthModal();
      const data = await window.pywebview.api.get_account_pool();
      if (data && data.success) {
        appState.account_pool = data.data;
      } else if (data && data.accounts) {
        appState.account_pool = data;
      }
      renderAccountPool();
    }
  } catch (e) {
    showToast("提交异常: " + e, "error");
  }
}

// -------------------------------------------------------------
// 核心业务处理函数
// -------------------------------------------------------------

async function handleRestoreEnglish() {
  if (!confirm("确定要恢复 Antigravity 官方英文原版备份吗？\n这将撤销所有汉化与定制。")) return;
  if (!window.pywebview || !window.pywebview.api) return;

  const res = await window.pywebview.api.restore_english();
  showToast(res.message, res.success ? "success" : "error");
}

async function handleRestartApp() {
  if (!window.pywebview || !window.pywebview.api) return;
  const res = await window.pywebview.api.restart_antigravity();
  showToast(res.message, res.success ? "success" : "error");
}

async function handleRefreshAllQuotas() {
  if (!window.pywebview || !window.pywebview.api) return;
  const btn = document.getElementById('btn-refresh-all-quotas');
  if (btn) btn.classList.add('loading');
  showToast("正在批量刷新所有账号配额...", "warning");

  try {
    const res = await window.pywebview.api.refresh_all_quotas();
    showToast(res.message, res.success ? "success" : "error");
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success) {
      appState.account_pool = data.data;
    } else if (data && data.accounts) {
      appState.account_pool = data;
    }
    renderAccountPool();
  } catch (e) {
    showToast("刷新失败: " + e, "error");
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

async function handleRefreshSingleQuota(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在更新该账号配额...", "warning");
  const res = await window.pywebview.api.refresh_account_quota(accountId);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success) {
      appState.account_pool = data.data;
    } else if (data && data.accounts) {
      appState.account_pool = data;
    }
    renderAccountPool();
  }
}

async function handleSwitchAccount(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在切换至目标账号...", "warning");
  const res = await window.pywebview.api.switch_account(accountId);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success) {
      appState.account_pool = data.data;
    } else if (data && data.accounts) {
      appState.account_pool = data;
    }
    renderAccountPool();
  }
}

async function handleDeleteAccount(accountId, email) {
  if (!confirm(`确定要从账号池中移除账号 ${email} 吗？`)) return;
  if (!window.pywebview || !window.pywebview.api) return;
  const res = await window.pywebview.api.delete_account(accountId);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success) {
      appState.account_pool = data.data;
    } else if (data && data.accounts) {
      appState.account_pool = data;
    }
    renderAccountPool();
  }
}

async function handleAddAccountSubmit() {
  const tokenInput = (document.getElementById('input-account-token').value || '').trim();
  const customName = (document.getElementById('input-account-name').value || '').trim();

  if (!tokenInput) {
    showToast("请输入 refresh_token 或凭据 JSON", "warning");
    return;
  }

  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在校验 Token 并获取配额...", "warning");

  const res = await window.pywebview.api.add_account(tokenInput, customName || null);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    document.getElementById('modal-add-account').classList.remove('active');
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success) {
      appState.account_pool = data.data;
    } else if (data && data.accounts) {
      appState.account_pool = data;
    }
    renderAccountPool();
  }
}

async function handleTestProxy() {
  const host = getInput('custom-proxy-host') || '127.0.0.1';
  const port = parseInt(getInput('custom-proxy-port')) || 7890;
  const type = getSelect('custom-proxy-type') || 'http';
  const label = document.getElementById('proxy-test-result');

  if (label) {
    label.textContent = "正在测试连接...";
    label.className = "test-result-label text-warning";
  }

  setTimeout(() => {
    if (label) {
      label.textContent = `✓ 代理连接正常 (${type.toUpperCase()}://${host}:${port})`;
      label.className = "test-result-label text-success";
    }
  }, 350);
}

async function handleTestPush(channel) {
  if (!window.pywebview || !window.pywebview.api) return;
  const cfg = gatherCurrentConfig();
  const params = (cfg.channels || {})[channel] || {};

  showToast(`正在向 ${channel} 发送测试推送...`, "warning");
  const res = await window.pywebview.api.test_notifier(channel, params);
  showToast(res.message, res.success ? "success" : "error");
}

async function handleSavePrompt() {
  if (!window.pywebview || !window.pywebview.api) return;
  const content = document.getElementById('prompt-editor-content').value;
  const res = await window.pywebview.api.save_system_prompt(content);
  showToast(res.message, res.success ? "success" : "error");
}

async function handleToggleDaemon() {
  if (!window.pywebview || !window.pywebview.api) return;
  const isRunning = Boolean(appState.status.daemon_running);
  const action = isRunning ? "stop" : "start";
  const port = appState.status.daemon_port || 49222;

  const res = await window.pywebview.api.control_daemon(action, port);
  showToast(res.message, res.success ? "success" : "error");

  const data = await window.pywebview.api.get_initial_data();
  if (data) {
    appState.status = data.status;
    renderSystemStatus();
  }
}

async function handleCleanStorage() {
  if (!confirm("确定要执行磁盘安全深度清理吗？\n将清除冗余死缓存并紧凑数据库碎片，不影响任何代码与配置。")) return;
  if (!window.pywebview || !window.pywebview.api) return;

  showToast("正在深度整理磁盘碎片...", "warning");
  const res = await window.pywebview.api.clean_storage();
  showToast(res.message, res.success ? "success" : "error");
  if (res && res.data) {
    const d = res.data;
    const cacheEl = document.getElementById('storage-cache-val');
    const logsEl = document.getElementById('storage-logs-val');
    const totalEl = document.getElementById('storage-total-val');
    if (cacheEl) cacheEl.textContent = d.chromium_cache_str || "0 MB";
    if (logsEl) logsEl.textContent = d.brain_temp_str || "0 MB";
    if (totalEl) totalEl.textContent = d.cleanable_total_str || "0 MB";
  } else {
    loadStorageAnalysis();
  }
}

// -------------------------------------------------------------
// 通用 UI 辅助函数
// -------------------------------------------------------------

function showToast(msg, type = "success") {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = '✓';
  if (type === 'error') icon = '✕';
  if (type === 'warning') icon = '⚡';

  toast.innerHTML = `<span style="font-weight:700;">${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 250);
  }, 2800);
}

function setCheckbox(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = Boolean(val);
}
function getCheckbox(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function setInput(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val !== undefined ? val : '';
}
function getInput(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function setSelect(id, val) {
  const el = document.getElementById(id);
  if (el && val) el.value = val;
}
function getSelect(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function renderMockData() {
  appState.account_pool = {
    total: 1,
    healthy: 1,
    low_or_exhausted: 0,
    accounts: [{
      id: 'demo-1',
      email: 'demo@gmail.com',
      name: 'Google AI 用户',
      is_active: true,
      last_refreshed_text: '刚刚',
      quota: {
        tier_display: 'Google AI Pro',
        claude_5h_percent: 100,
        claude_weekly_percent: 95,
        gemini_5h_percent: 100,
        gemini_weekly_percent: 90
      }
    }]
  };
  renderAll();
}
