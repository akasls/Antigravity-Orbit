/**
 * Antigravity Orbit - 现代桌面核心控制器 (v3.3.4)
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
  isSaving: false,
  isSyncingPool: false // 启动时直接渲染本地持久化状态，绝不伪装全量同步中
};

const refreshingAccountIds = new Set();

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
  startSmartQuotaScheduler();
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

  // 3. 切换至账号池时读取最新本地状态 (不主动批量冲击 Google 接口)
  if (tabName === 'accounts') {
    silentRefreshPool();
  }

  // 4. 切换至性能汉化时分析存储与刷新客户端状态
  if (tabName === 'perf_localization') {
    loadStorageAnalysis();
    updatePerfStatus();
  }

  // 5. 切换至规则与提示词时确保编辑器内容与字数更新
  if (tabName === 'rules_prompts') {
    renderPromptEditor();
    renderCustomPrompts();
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

      // 初次载入完成，平滑关闭全屏骨架同步状态
      appState.isSyncingPool = false;
      renderAll();
    }
  } catch (err) {
    appState.isSyncingPool = false;
    console.error("加载初始数据失败:", err);
    showToast("连接原生后端失败: " + err, "error");
  }
}

let smartQuotaTimer = null;
let isRefreshingQueue = false;
let lastActiveRefreshTime = Date.now();
let lastIdleAccountRefreshTime = Date.now();

/**
 * 智能分级错峰额度刷新调度器 (彻底杜绝 Google 接口并发风控与速率限制)
 * - 使用中账号：独立高频定时刷新 (默认 1 分钟)
 * - 闲置待命账号：独立低频定时刷新 (默认 15 分钟)
 * - 闲置账号之间强制错开至少 15 秒，每次严格仅刷新单个账号，绝不并发批量请求
 */
function startSmartQuotaScheduler() {
  if (smartQuotaTimer) clearInterval(smartQuotaTimer);
  lastActiveRefreshTime = Date.now();
  lastIdleAccountRefreshTime = Date.now();

  // 基础心跳监测，每 5 秒扫描一次配额过期状态
  smartQuotaTimer = setInterval(async () => {
    if (isRefreshingQueue || !window.pywebview || !window.pywebview.api) return;

    const custom = (appState.config && appState.config.customization) || {};
    const activeIntervalSec = parseInt(custom.quota_refresh_active_interval !== undefined 
      ? custom.quota_refresh_active_interval 
      : (custom.quota_refresh_interval || 60)) || 60;
    const idleIntervalSec = parseInt(custom.quota_refresh_idle_interval !== undefined 
      ? custom.quota_refresh_idle_interval 
      : 900) || 900;

    const activeIntervalMs = Math.max(15, activeIntervalSec) * 1000;
    const idleIntervalMs = Math.max(60, idleIntervalSec) * 1000;

    const accounts = (appState.account_pool && appState.account_pool.accounts) || [];
    if (!accounts.length) return;

    const now = Date.now();

    // 1. 优先度最高：检查「使用中」账号是否达到刷新时间
    const activeAcc = accounts.find(a => a.is_active);
    if (activeAcc) {
      const activeLastRefreshed = ((activeAcc.quota && activeAcc.quota.last_refreshed) || 0) * 1000;
      const needActiveRefresh = (now - lastActiveRefreshTime >= activeIntervalMs) && (now - activeLastRefreshed >= activeIntervalMs);

      if (needActiveRefresh) {
        isRefreshingQueue = true;
        lastActiveRefreshTime = now;
        try {
          refreshingAccountIds.add(activeAcc.id);
          renderAccountPool();
          const res = await window.pywebview.api.refresh_account_quota(activeAcc.id);
          if (res && res.data) {
            appState.account_pool = res.data;
          }
        } catch (e) {
          console.warn("[SmartQuota] 刷新活跃账号异常:", e);
        } finally {
          refreshingAccountIds.delete(activeAcc.id);
          isRefreshingQueue = false;
          renderAccountPool();
        }
        return; // 单次心跳仅处理单个账号刷新，避免接口争抢
      }
    }

    // 2. 检查「闲置待命」账号：错峰单个刷新
    // 强制安全间隔：两次闲置账号刷新之间至少相隔 15 秒，彻底消除 Google API 峰值
    if (now - lastIdleAccountRefreshTime < 15000) {
      return;
    }

    const idleAccounts = accounts.filter(a => !a.is_active);
    if (!idleAccounts.length) return;

    // 寻找已经超过 idleIntervalMs 且等待时间最久的一个闲置账号
    let targetIdleAcc = null;
    let oldestRefreshedTime = Infinity;

    for (const acc of idleAccounts) {
      const lastRefreshedSec = (acc.quota && acc.quota.last_refreshed) || 0;
      const lastRefreshedMs = lastRefreshedSec * 1000;
      if (now - lastRefreshedMs >= idleIntervalMs) {
        if (lastRefreshedMs < oldestRefreshedTime) {
          oldestRefreshedTime = lastRefreshedMs;
          targetIdleAcc = acc;
        }
      }
    }

    if (targetIdleAcc) {
      isRefreshingQueue = true;
      lastIdleAccountRefreshTime = now;
      try {
        refreshingAccountIds.add(targetIdleAcc.id);
        renderAccountPool();
        const res = await window.pywebview.api.refresh_account_quota(targetIdleAcc.id);
        if (res && res.data) {
          appState.account_pool = res.data;
        }
      } catch (e) {
        console.warn(`[SmartQuota] 分段刷新闲置账号 ${targetIdleAcc.email} 异常:`, e);
      } finally {
        refreshingAccountIds.delete(targetIdleAcc.id);
        isRefreshingQueue = false;
        renderAccountPool();
      }
    }
  }, 5000);
}

/**
 * 静默读取本地账号池数据 (读取本地缓存，不主动打扰 Google 接口)
 */
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
 * HTML 转义安全函数
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * 全量渲染页面组件
 */
function renderAll() {
  try { renderAccountPool(); } catch (e) { console.error("renderAccountPool error:", e); }
  try { renderConfigForm(); } catch (e) { console.error("renderConfigForm error:", e); }
  try { renderSystemStatus(); } catch (e) { console.error("renderSystemStatus error:", e); }
  try { renderPromptEditor(); } catch (e) { console.error("renderPromptEditor error:", e); }
  try { renderCustomPrompts(); } catch (e) { console.error("renderCustomPrompts error:", e); }
}

function formatResetCountdown(isoStr, percent = 100) {
  if (!isoStr) {
    return percent >= 100 ? '充足' : '';
  }
  try {
    const target = new Date(isoStr).getTime();
    if (isNaN(target)) return percent >= 100 ? '充足' : '';
    const diff = target - Date.now();
    if (diff <= 0) return '已刷新';

    const totalMinutes = Math.floor(diff / 60000);
    const totalHours = Math.floor(totalMinutes / 60);
    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;
    const mins = totalMinutes % 60;

    if (days > 0) {
      return `${days}天${hours}h`;
    }
    if (hours > 0) {
      return `${hours}h${mins}m`;
    }
    if (mins > 0) {
      return `${mins}m`;
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

/**
 * 渲染账号池：支持 Claude 与 Gemini 5H / 周限 对比矩阵
 */
function renderAccountPool() {
  const pool = appState.account_pool || { accounts: [], total: 0, healthy: 0, low_or_exhausted: 0 };
  const accounts = pool.accounts || [];

  // 计算 Pro 账号数量
  const proCount = accounts.filter(acc => {
    const tier = (acc.quota && (acc.quota.tier_display || acc.quota.tier)) || '';
    return tier.toLowerCase().includes('pro');
  }).length;

  // 1. 更新顶部指标卡片
  const totalEl = document.getElementById('metric-total-count');
  const proEl = document.getElementById('metric-pro-count');
  const healthyEl = document.getElementById('metric-healthy-count');
  const lowEl = document.getElementById('metric-low-count');

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

    const c5hReset = formatResetCountdown(q.claude_5h_reset || q.five_hour_reset, c5h);
    const c5hTimeStr = formatExactDateTime(q.claude_5h_reset || q.five_hour_reset);
    const c5hExact = c5hTimeStr ? `下次重置: ${c5hTimeStr} (可用剩余: ${c5h}%)` : (c5h >= 100 ? '当前可用配额 100% 充足' : `当前可用配额: ${c5h}%`);

    const cWReset = formatResetCountdown(q.claude_weekly_reset || q.weekly_reset, cW);
    const cWTimeStr = formatExactDateTime(q.claude_weekly_reset || q.weekly_reset);
    const cWExact = cWTimeStr ? `下次重置: ${cWTimeStr} (可用剩余: ${cW}%)` : (cW >= 100 ? '当前可用配额 100% 充足' : `当前可用配额: ${cW}%`);

    // 解析 Gemini 限额与重置倒计时
    const g5h = (typeof q.gemini_5h_percent === 'number') ? q.gemini_5h_percent 
      : ((typeof q.five_hour_percent === 'number') ? q.five_hour_percent : 100);
    const gW = (typeof q.gemini_weekly_percent === 'number') ? q.gemini_weekly_percent 
      : ((typeof q.weekly_percent === 'number') ? q.weekly_percent : 100);

    const g5hReset = formatResetCountdown(q.gemini_5h_reset || q.five_hour_reset, g5h);
    const g5hTimeStr = formatExactDateTime(q.gemini_5h_reset || q.five_hour_reset);
    const g5hExact = g5hTimeStr ? `下次重置: ${g5hTimeStr} (可用剩余: ${g5h}%)` : (g5h >= 100 ? '当前可用配额 100% 充足' : `当前可用配额: ${g5h}%`);

    const gWReset = formatResetCountdown(q.gemini_weekly_reset || q.weekly_reset, gW);
    const gWTimeStr = formatExactDateTime(q.gemini_weekly_reset || q.weekly_reset);
    const gWExact = gWTimeStr ? `下次重置: ${gWTimeStr} (可用剩余: ${gW}%)` : (gW >= 100 ? '当前可用配额 100% 充足' : `当前可用配额: ${gW}%`);

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
    if (appState.isSyncingPool || refreshingAccountIds.has(acc.id) || q.status === 'SYNCING') {
      statusBadge = '<span class="status-tag status-syncing"><span class="spin-icon-inline">🔄</span> 刷新中</span>';
    } else if (q.status === 'EXPIRED') {
      statusBadge = `<span class="status-tag" style="background:#fef2f2;color:#ef4444;" title="${q.error || '登录授权已过期，请重新登录'}">已失效</span>`;
    } else if (q.status === 'ERROR') {
      statusBadge = `<span class="status-tag" style="background:#fffbeb;color:#d97706;" title="${q.error || '网络连接失败'}">未同步</span>`;
    } else if (q.status === 'FORBIDDEN') {
      statusBadge = '<span class="status-tag" style="background:#fef2f2;color:#ef4444;">受限</span>';
    } else if (minPct <= 0 || q.status === 'EXHAUSTED') {
      statusBadge = '<span class="status-tag" style="background:#fef2f2;color:#ef4444;">耗尽</span>';
    } else if (minPct <= 20 || q.status === 'LOW') {
      statusBadge = '<span class="status-tag" style="background:#fffbeb;color:#d97706;">紧张</span>';
    }


    const avatarHtml = acc.avatar 
      ? `<img src="${acc.avatar}" alt="Avatar">`
      : (acc.email || "A").charAt(0).toUpperCase();

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
            <div class="quota-col-title" title="Claude 与 GPT 模型可用剩余配额">
              <span class="quota-brand-dot claude-dot"></span>
              <span>Claude 剩余</span>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">5H</span>
                ${c5hReset ? `<span class="quota-cell-reset" title="${c5hExact}">${c5hReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap" title="可用剩余: ${c5h}%">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillC5h}" style="width: ${c5h}%;"></div>
                </div>
                <span class="quota-cell-val">${c5h}%</span>
              </div>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">周限</span>
                ${cWReset ? `<span class="quota-cell-reset" title="${cWExact}">${cWReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap" title="可用剩余: ${cW}%">
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
            <div class="quota-col-title" title="Gemini 官方模型可用剩余配额">
              <span class="quota-brand-dot gemini-dot"></span>
              <span>Gemini 剩余</span>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">5H</span>
                ${g5hReset ? `<span class="quota-cell-reset" title="${g5hExact}">${g5hReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap" title="可用剩余: ${g5h}%">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillG5h}" style="width: ${g5h}%;"></div>
                </div>
                <span class="quota-cell-val">${g5h}%</span>
              </div>
            </div>
            <div class="quota-cell">
              <div class="quota-cell-top">
                <span class="quota-cell-label">周限</span>
                ${gWReset ? `<span class="quota-cell-reset" title="${gWExact}">${gWReset}</span>` : ''}
              </div>
              <div class="quota-cell-bar-wrap" title="可用剩余: ${gW}%">
                <div class="progress-track" style="height: 5px;">
                  <div class="progress-fill ${fillGW}" style="width: ${gW}%;"></div>
                </div>
                <span class="quota-cell-val">${gW}%</span>
              </div>
            </div>
          </div>
        </div>

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

  // 1. 性能汉化 (不实时自动保存)
  setCheckbox('custom-opt-gpu', custom.opt_gpu !== false && custom.enable_gpu_acceleration !== false);
  setCheckbox('custom-opt-max-heap', custom.opt_max_heap !== false && custom.expand_v8_memory !== false);
  setCheckbox('custom-opt-nosleep', custom.opt_nosleep !== false && custom.disable_background_throttling !== false);
  setCheckbox('custom-opt-telemetry', custom.opt_telemetry !== false && custom.disable_telemetry !== false);
  setSelect('custom-lang', custom.language || 'zh-CN');
  setCheckbox('custom-quota-badge', custom.show_quota_badge !== false);
  setCheckbox('custom-clean-ui', custom.clean_ui || custom.hide_ide_buttons);
  setCheckbox('custom-start-maximized', custom.start_maximized !== false);
  setCheckbox('custom-prune-skills', custom.prune_guide_skills);

  // 2. 专属网络代理
  setCheckbox('custom-proxy-enabled', custom.proxy_enabled);
  setSelect('custom-proxy-type', custom.proxy_type || 'socks5');
  setInput('custom-proxy-host', custom.proxy_host || '127.0.0.1');
  setInput('custom-proxy-port', custom.proxy_port || 10808);
  setInput('custom-proxy-bypass', custom.proxy_bypass || 'localhost, 127.0.0.1, *.local');

  // 3. 自愈与推送
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
  setInput('feishu-webhook', fs.webhook || fs.webhook_url || '');

  const wc = ch.wecom || {};
  setCheckbox('wecom-enabled', wc.enabled);
  setInput('wecom-webhook', wc.webhook || wc.webhook_url || '');

  // 4. 系统设置
  setCheckbox('custom-close-tray', cfg.close_to_tray !== false);
  const activeInterval = custom.quota_refresh_active_interval !== undefined 
    ? custom.quota_refresh_active_interval 
    : (custom.quota_refresh_interval || 60);
  const idleInterval = custom.quota_refresh_idle_interval !== undefined 
    ? custom.quota_refresh_idle_interval 
    : 900;
  setSelect('custom-quota-refresh-active', String(activeInterval));
  setSelect('custom-quota-refresh-idle', String(idleInterval));
}

/**
 * 渲染系统状态与客户端检测
 */
function renderSystemStatus() {
  const st = appState.status || {};
  const appAutoCheck = document.getElementById('custom-app-autostart');
  if (appAutoCheck) {
    appAutoCheck.checked = Boolean(st.app_autostart);
  }
  updatePerfStatus();
}

function updatePerfStatus() {
  const st = appState.status || {};
  const dirEl = document.getElementById('perf-install-dir');
  const locEl = document.getElementById('perf-loc-status');
  const bakEl = document.getElementById('perf-backup-status');

  if (dirEl) dirEl.textContent = st.install_dir || "未探测到安装目录";
  if (locEl) {
    if (st.is_localized) {
      locEl.innerHTML = `<span class="badge-status-active"><span class="status-dot-pulse"></span> 已注入深度汉化 (${st.lang || 'zh-CN'})</span>`;
    } else {
      locEl.textContent = "官方未汉化原版 (点击【保存并重启】即可一键注入)";
    }
  }
  if (bakEl) {
    bakEl.textContent = st.has_backup ? "已就绪 (app.asar.bak 完整官方备份)" : "未生成备份 (首次应用汉化后自动生成)";
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

async function handleSavePrompt() {
  const textarea = document.getElementById('prompt-editor-content');
  if (!textarea) return;
  const content = textarea.value;
  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前运行于演示模式，无法保存提示词", "warning");
    return;
  }
  try {
    const res = await window.pywebview.api.save_system_prompt(content);
    if (res && res.success) {
      if (appState.prompt) appState.prompt.content = content;
      showToast("全局系统提示词已保存生效！", "success");
    } else {
      showToast(res ? res.message : "保存提示词失败", "error");
    }
  } catch (e) {
    showToast("保存提示词异常: " + e, "error");
  }
}

async function handleRestorePrompt() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const res = await window.pywebview.api.restore_prompt_backup();
    if (res && res.success) {
      const textarea = document.getElementById('prompt-editor-content');
      if (textarea) {
        textarea.value = res.content || '';
        updatePromptStats();
      }
      if (appState.prompt) appState.prompt.content = res.content || '';
      showToast(res.message || "已从备份成功还原系统提示词！", "success");
    } else {
      showToast(res ? res.message : "还原提示词失败", "error");
    }
  } catch (e) {
    showToast("还原提示词异常: " + e, "error");
  }
}

/**
 * 渲染用户自定义提示词库
 */
function renderCustomPrompts() {
  const container = document.getElementById('custom-prompts-container');
  if (!container) return;

  const templates = (appState.prompt && appState.prompt.templates) || [];
  if (!templates || templates.length === 0) {
    container.innerHTML = `
      <div class="custom-prompts-empty">
        暂无提示词模板，点击右上角【新增提示词】添加您的专属系统提示词
      </div>
    `;
    return;
  }

  container.innerHTML = templates.map(t => {
    const title = escapeHtml(t.title || '未命名提示词');
    const content = t.content || '';
    const snippet = escapeHtml(content.trim().slice(0, 90) + (content.length > 90 ? '...' : '')) || '（空提示词内容）';
    const time = escapeHtml(t.updated_at || '');

    return `
      <div class="custom-prompt-card">
        <div class="custom-prompt-card-header">
          <div class="custom-prompt-card-title" title="${title}">${title}</div>
          <div class="custom-prompt-card-actions">
            <button type="button" class="btn-icon-tag" onclick="editCustomPrompt('${t.id}')" title="编辑提示词">✏️</button>
            <button type="button" class="btn-icon-tag" onclick="deleteCustomPrompt('${t.id}')" title="删除提示词">🗑️</button>
          </div>
        </div>
        <div class="custom-prompt-card-preview" title="${escapeHtml(content)}">${snippet}</div>
        <div class="custom-prompt-card-footer">
          <span class="custom-prompt-card-time">${time}</span>
          <button type="button" class="btn btn-accent-light btn-xs" onclick="applyCustomPrompt('${t.id}')" title="一键将此提示词写入反重力 AGENTS.md">⚡ 一键应用</button>
        </div>
      </div>
    `;
  }).join('');
}

function openCustomPromptModal(templateId = null) {
  const modal = document.getElementById('modal-custom-prompt');
  const titleText = document.getElementById('modal-prompt-title-text');
  const idInput = document.getElementById('custom-prompt-id');
  const titleInput = document.getElementById('custom-prompt-title-input');
  const contentInput = document.getElementById('custom-prompt-content-input');
  if (!modal) return;

  if (templateId) {
    const templates = (appState.prompt && appState.prompt.templates) || [];
    const found = templates.find(t => t.id === templateId);
    if (found) {
      if (titleText) titleText.textContent = '编辑提示词';
      if (idInput) idInput.value = found.id;
      if (titleInput) titleInput.value = found.title || '';
      if (contentInput) contentInput.value = found.content || '';
    }
  } else {
    if (titleText) titleText.textContent = '新增提示词';
    if (idInput) idInput.value = '';
    if (titleInput) titleInput.value = '';
    if (contentInput) contentInput.value = '';
  }

  modal.classList.add('active');
  if (titleInput) titleInput.focus();
}

function closeCustomPromptModal() {
  const modal = document.getElementById('modal-custom-prompt');
  if (modal) modal.classList.remove('active');
}

async function handleSaveCustomPromptSubmit() {
  const idInput = document.getElementById('custom-prompt-id');
  const titleInput = document.getElementById('custom-prompt-title-input');
  const contentInput = document.getElementById('custom-prompt-content-input');
  
  const id = idInput ? idInput.value.trim() : '';
  const title = titleInput ? titleInput.value.trim() : '';
  const content = contentInput ? contentInput.value : '';

  if (!title) {
    showToast("请输入提示词标题", "warning");
    return;
  }

  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前为演示模式，无法保存提示词", "warning");
    return;
  }

  try {
    const res = await window.pywebview.api.save_custom_prompt(title, content, id || null);
    if (res && res.success) {
      if (!appState.prompt) appState.prompt = {};
      if (!appState.prompt.templates) appState.prompt.templates = [];

      const savedTpl = res.template;
      if (id) {
        const idx = appState.prompt.templates.findIndex(t => t.id === id);
        if (idx >= 0) {
          appState.prompt.templates[idx] = savedTpl;
        } else {
          appState.prompt.templates.unshift(savedTpl);
        }
      } else {
        appState.prompt.templates.unshift(savedTpl);
      }

      renderCustomPrompts();
      closeCustomPromptModal();
      showToast(res.message || "提示词已成功保存！", "success");
    } else {
      showToast(res ? res.message : "保存提示词失败", "error");
    }
  } catch (e) {
    showToast("保存提示词异常: " + e, "error");
  }
}

async function editCustomPrompt(templateId) {
  openCustomPromptModal(templateId);
}

async function deleteCustomPrompt(templateId) {
  if (!confirm("确定要删除该提示词模板吗？此操作不可恢复。")) {
    return;
  }
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const res = await window.pywebview.api.delete_custom_prompt(templateId);
    if (res && res.success) {
      if (appState.prompt && appState.prompt.templates) {
        appState.prompt.templates = appState.prompt.templates.filter(t => t.id !== templateId);
      }
      renderCustomPrompts();
      showToast("提示词模板已删除", "info");
    } else {
      showToast(res ? res.message : "删除失败", "error");
    }
  } catch (e) {
    showToast("删除提示词异常: " + e, "error");
  }
}

async function applyCustomPrompt(templateId) {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const res = await window.pywebview.api.apply_custom_prompt(templateId);
    if (res && res.success) {
      const textarea = document.getElementById('prompt-editor-content');
      if (textarea) {
        textarea.value = res.content || '';
        updatePromptStats();
      }
      if (appState.prompt) appState.prompt.content = res.content || '';
      showToast(res.message || "已成功应用提示词到全局系统规则！", "success");
    } else {
      showToast(res ? res.message : "应用提示词失败", "error");
    }
  } catch (e) {
    showToast("应用提示词异常: " + e, "error");
  }
}

window.renderCustomPrompts = renderCustomPrompts;
window.openCustomPromptModal = openCustomPromptModal;
window.closeCustomPromptModal = closeCustomPromptModal;
window.editCustomPrompt = editCustomPrompt;
window.deleteCustomPrompt = deleteCustomPrompt;
window.applyCustomPrompt = applyCustomPrompt;


/**
 * 收集当前表单数据
 */
function gatherCurrentConfig() {
  const cfg = JSON.parse(JSON.stringify(appState.config || {}));
  cfg.customization = cfg.customization || {};
  cfg.channels = cfg.channels || {};

  // 1. 性能汉化
  cfg.customization.opt_gpu = getCheckbox('custom-opt-gpu');
  cfg.customization.enable_gpu_acceleration = cfg.customization.opt_gpu;

  cfg.customization.opt_max_heap = getCheckbox('custom-opt-max-heap');
  cfg.customization.expand_v8_memory = cfg.customization.opt_max_heap;

  cfg.customization.opt_nosleep = getCheckbox('custom-opt-nosleep');
  cfg.customization.disable_background_throttling = cfg.customization.opt_nosleep;

  cfg.customization.opt_telemetry = getCheckbox('custom-opt-telemetry');
  cfg.customization.disable_telemetry = cfg.customization.opt_telemetry;

  cfg.customization.language = getSelect('custom-lang') || 'zh-CN';
  cfg.customization.show_quota_badge = getCheckbox('custom-quota-badge');
  cfg.customization.clean_ui = getCheckbox('custom-clean-ui');
  cfg.customization.hide_ide_buttons = cfg.customization.clean_ui;
  cfg.customization.start_maximized = getCheckbox('custom-start-maximized');
  cfg.customization.prune_guide_skills = getCheckbox('custom-prune-skills');

  // 2. 专属网络代理
  cfg.customization.proxy_enabled = getCheckbox('custom-proxy-enabled');
  cfg.customization.proxy_type = getSelect('custom-proxy-type') || 'socks5';
  cfg.customization.proxy_host = getInput('custom-proxy-host') || '127.0.0.1';
  cfg.customization.proxy_port = parseInt(getInput('custom-proxy-port')) || 10808;
  cfg.customization.proxy_bypass = getInput('custom-proxy-bypass');
  const pType = (cfg.customization.proxy_type || 'socks5').toLowerCase();
  cfg.customization.proxy_url = `${pType}://${cfg.customization.proxy_host}:${cfg.customization.proxy_port}`;

  // 3. 自愈与推送
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

  // 4. 系统设置
  cfg.close_to_tray = getCheckbox('custom-close-tray');
  cfg.customization.quota_refresh_active_interval = parseInt(getSelect('custom-quota-refresh-active')) || 60;
  cfg.customization.quota_refresh_idle_interval = parseInt(getSelect('custom-quota-refresh-idle')) || 900;
  cfg.customization.quota_refresh_interval = cfg.customization.quota_refresh_active_interval;

  return cfg;
}

/**
 * 实时修改自动保存生效引擎 (仅代理服务、自愈推送、系统设置生效；性能汉化明确不实时生效)
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
        showToast("配置已保存生效", "success");
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
  // 1. 仅对代理服务、自愈推送、系统设置、Skills裁剪等项绑定实时自动保存 (性能汉化页面明确不实时生效！)
  const autoSaveChecks = [
    'custom-prune-skills',
    'custom-proxy-enabled', 'custom-proxy-type',
    'custom-auto-retry', 'custom-notify-quota',
    'tg-enabled', 'feishu-enabled', 'wecom-enabled',
    'custom-close-tray', 'custom-quota-refresh-active', 'custom-quota-refresh-idle'
  ];
  autoSaveChecks.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        triggerAutoSave(0);
        if (id === 'custom-quota-refresh-active' || id === 'custom-quota-refresh-idle') {
          startSmartQuotaScheduler();
        }
      });
    }
  });

  const autoSaveTexts = [
    'custom-proxy-host', 'custom-proxy-port', 'custom-proxy-bypass', 'custom-max-retries',
    'tg-bot-token', 'tg-chat-id', 'tg-proxy', 'feishu-webhook', 'wecom-webhook'
  ];
  autoSaveTexts.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => triggerAutoSave(0));
      el.addEventListener('input', () => triggerAutoSave(600));
    }
  });

  // 2. 性能汉化页面专属操作按钮 (初始化、还原、保存并重启)
  const btnPerfSaveRestart = document.getElementById('btn-perf-save-restart');
  if (btnPerfSaveRestart) {
    btnPerfSaveRestart.addEventListener('click', handlePerfSaveAndRestart);
  }

  const btnPerfRestore = document.getElementById('btn-perf-restore');
  if (btnPerfRestore) {
    btnPerfRestore.addEventListener('click', handlePerfRestore);
  }

  const btnPerfInit = document.getElementById('btn-perf-init');
  if (btnPerfInit) {
    btnPerfInit.addEventListener('click', handleOpenInitModal);
  }

  const btnCloseInitModal = document.getElementById('btn-close-init-modal');
  const btnCancelInitModal = document.getElementById('btn-cancel-init-modal');
  const btnConfirmInit = document.getElementById('btn-confirm-init');
  if (btnCloseInitModal) btnCloseInitModal.addEventListener('click', handleCloseInitModal);
  if (btnCancelInitModal) btnCancelInitModal.addEventListener('click', handleCloseInitModal);
  if (btnConfirmInit) btnConfirmInit.addEventListener('click', handleExecuteInit);

  // 3. 专属代理保存按钮
  const btnSaveProxy = document.getElementById('btn-save-proxy');
  if (btnSaveProxy) {
    btnSaveProxy.addEventListener('click', handleSaveProxy);
  }

  // 4. 账号池工具栏按钮：登录、导入、导出、刷新
  const btnOpenOAuthModal = document.getElementById('btn-open-oauth-modal');
  if (btnOpenOAuthModal) {
    btnOpenOAuthModal.addEventListener('click', handleOpenOAuthModal);
  }

  const btnOpenAddModal = document.getElementById('btn-open-add-modal');
  const modalAdd = document.getElementById('modal-add-account');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnSubmitModal = document.getElementById('btn-submit-add-account');

  if (btnOpenAddModal && modalAdd) {
    btnOpenAddModal.addEventListener('click', () => {
      resetAddAccountModal();
      modalAdd.classList.add('active');
    });
  }
  if (btnCloseModal && modalAdd) {
    btnCloseModal.addEventListener('click', () => {
      resetAddAccountModal();
      modalAdd.classList.remove('active');
    });
  }
  if (btnCancelModal && modalAdd) {
    btnCancelModal.addEventListener('click', () => {
      resetAddAccountModal();
      modalAdd.classList.remove('active');
    });
  }
  if (btnSubmitModal) {
    btnSubmitModal.addEventListener('click', handleAddAccountSubmit);
  }

  const btnExportAccounts = document.getElementById('btn-export-accounts');
  if (btnExportAccounts) {
    btnExportAccounts.addEventListener('click', handleExportAccounts);
  }

  const btnCloseExportModal = document.getElementById('btn-close-export-modal');
  const btnCloseExportModal2 = document.getElementById('btn-close-export-modal2');
  const btnCopyExportJson = document.getElementById('btn-copy-export-json');
  const btnDownloadExportJson = document.getElementById('btn-download-export-json');
  if (btnCloseExportModal) btnCloseExportModal.addEventListener('click', handleCloseExportModal);
  if (btnCloseExportModal2) btnCloseExportModal2.addEventListener('click', handleCloseExportModal);
  if (btnCopyExportJson) btnCopyExportJson.addEventListener('click', handleCopyExportJson);
  if (btnDownloadExportJson) btnDownloadExportJson.addEventListener('click', handleDownloadExportJson);

  const btnRefreshAll = document.getElementById('btn-refresh-all-quotas');
  if (btnRefreshAll) {
    btnRefreshAll.addEventListener('click', handleRefreshAllQuotas);
  }

  // 5. Google OAuth 网页登录弹窗
  const btnCloseOAuthModal = document.getElementById('btn-close-oauth-modal');
  const btnCancelOAuthModal = document.getElementById('btn-cancel-oauth-modal');
  const btnStartOAuthBrowser = document.getElementById('btn-start-oauth-browser');
  const btnSubmitOAuthCode = document.getElementById('btn-submit-oauth-code');

  if (btnCloseOAuthModal) btnCloseOAuthModal.addEventListener('click', handleCloseOAuthModal);
  if (btnCancelOAuthModal) btnCancelOAuthModal.addEventListener('click', handleCloseOAuthModal);
  if (btnStartOAuthBrowser) btnStartOAuthBrowser.addEventListener('click', handleStartOAuthBrowser);
  if (btnSubmitOAuthCode) btnSubmitOAuthCode.addEventListener('click', handleSubmitOAuthCode);

  // 6. 代理探测与测试
  const btnDetectProxy = document.getElementById('btn-detect-proxy');
  if (btnDetectProxy) btnDetectProxy.addEventListener('click', handleDetectProxy);

  const btnTestProxy = document.getElementById('btn-test-proxy');
  if (btnTestProxy) btnTestProxy.addEventListener('click', handleTestProxy);

  // 7. 推送测试
  const btnTestTg = document.getElementById('btn-test-tg');
  if (btnTestTg) btnTestTg.addEventListener('click', () => handleTestPush('telegram'));

  const btnTestFeishu = document.getElementById('btn-test-feishu');
  if (btnTestFeishu) btnTestFeishu.addEventListener('click', () => handleTestPush('feishu'));

  const btnTestWecom = document.getElementById('btn-test-wecom');
  if (btnTestWecom) btnTestWecom.addEventListener('click', () => handleTestPush('wecom'));

  // 8. 磁盘深度瘦身
  const btnClean = document.getElementById('btn-clean-storage');
  if (btnClean) btnClean.addEventListener('click', handleCleanStorage);

  // 9. 系统提示词 (输入实时自动保存 + 手动按钮保存)
  let promptAutoSaveTimer = null;
  const textareaPrompt = document.getElementById('prompt-editor-content');
  if (textareaPrompt) {
    textareaPrompt.addEventListener('input', () => {
      updatePromptStats();
      if (promptAutoSaveTimer) clearTimeout(promptAutoSaveTimer);
      promptAutoSaveTimer = setTimeout(async () => {
        const content = textareaPrompt.value;
        if (window.pywebview && window.pywebview.api) {
          const res = await window.pywebview.api.save_system_prompt(content);
          if (res && res.success) {
            if (appState.prompt) appState.prompt.content = content;
            showToast("系统提示词已自动保存生效", "success");
          }
        }
      }, 800);
    });
  }

  const btnSavePrompt = document.getElementById('btn-save-prompt');
  if (btnSavePrompt) btnSavePrompt.addEventListener('click', handleSavePrompt);

  const btnRestorePrompt = document.getElementById('btn-restore-prompt');
  if (btnRestorePrompt) btnRestorePrompt.addEventListener('click', handleRestorePrompt);

  // 9.1 自定义提示词库
  const btnAddCustomPrompt = document.getElementById('btn-add-custom-prompt');
  if (btnAddCustomPrompt) btnAddCustomPrompt.addEventListener('click', () => openCustomPromptModal());

  const btnClosePromptModal = document.getElementById('btn-close-prompt-modal');
  if (btnClosePromptModal) btnClosePromptModal.addEventListener('click', closeCustomPromptModal);

  const btnCancelPromptModal = document.getElementById('btn-cancel-prompt-modal');
  if (btnCancelPromptModal) btnCancelPromptModal.addEventListener('click', closeCustomPromptModal);

  const btnSubmitPromptModal = document.getElementById('btn-submit-prompt-modal');
  if (btnSubmitPromptModal) btnSubmitPromptModal.addEventListener('click', handleSaveCustomPromptSubmit);

  // 10. 系统设置：开机自启、打开配置目录、访问 GitHub
  const appAutoCheck = document.getElementById('custom-app-autostart');
  if (appAutoCheck) {
    appAutoCheck.addEventListener('change', async (e) => {
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.toggle_app_autostart(e.target.checked);
      showToast(res.message, res.success ? 'success' : 'error');
    });
  }

  const btnOpenConfigFolder = document.getElementById('btn-open-config-folder');
  if (btnOpenConfigFolder) {
    btnOpenConfigFolder.addEventListener('click', async () => {
      if (!window.pywebview || !window.pywebview.api) return;
      await window.pywebview.api.open_config_dir();
    });
  }

  const btnOpenGithub = document.getElementById('btn-open-github');
  if (btnOpenGithub) {
    btnOpenGithub.addEventListener('click', () => {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_external('https://github.com/akasls/Antigravity-Orbit');
      } else {
        window.open('https://github.com/akasls/Antigravity-Orbit', '_blank');
      }
    });
  }
}

// -------------------------------------------------------------
// 网络代理探测与连通性测试
// -------------------------------------------------------------

async function handleDetectProxy() {
  if (!window.pywebview || !window.pywebview.api) return;
  const label = document.getElementById('proxy-test-result');
  if (label) {
    label.style.color = '#3b82f6';
    label.innerText = '正在智能扫描本机代理端口 (10808/7890/7897/10809)...';
  }
  showToast('正在探测本机可用代理端口...', 'info');

  try {
    const res = await window.pywebview.api.detect_local_proxy();
    if (res && res.detected) {
      setInput('custom-proxy-host', res.host || '127.0.0.1');
      setInput('custom-proxy-port', res.port || 10808);
      setSelect('custom-proxy-type', res.type || 'socks5');
      setCheckbox('custom-proxy-enabled', true);

      if (label) {
        label.style.color = '#10b981';
        label.innerText = `✓ ${res.message}`;
      }
      showToast(res.message, 'success');
      triggerAutoSave(0);
    } else {
      if (label) {
        label.style.color = '#ef4444';
        label.innerText = `✕ ${res.message || '未检测到正在运行的代理'}`;
      }
      showToast(res.message || '未扫描到可用代理', 'warning');
    }
  } catch (e) {
    if (label) {
      label.style.color = '#ef4444';
      label.innerText = `✕ 探测失败: ${e}`;
    }
    showToast('探测失败: ' + e, 'error');
  }
}

async function handleTestProxy() {
  if (!window.pywebview || !window.pywebview.api) return;
  const host = getInput('custom-proxy-host') || '127.0.0.1';
  const port = parseInt(getInput('custom-proxy-port')) || 10808;
  const type = getSelect('custom-proxy-type') || 'socks5';
  const label = document.getElementById('proxy-test-result');

  if (label) {
    label.style.color = '#3b82f6';
    label.innerText = `正在测试 ${type.toUpperCase()} ${host}:${port} 连通性并握手 Google...`;
  }

  try {
    const res = await window.pywebview.api.test_proxy(host, port, type);
    if (label) {
      label.style.color = res.success ? '#10b981' : '#ef4444';
      label.innerText = res.success ? `✓ ${res.message}` : `✕ ${res.message}`;
    }
    showToast(res.message, res.success ? 'success' : 'error');
  } catch (e) {
    if (label) {
      label.style.color = '#ef4444';
      label.innerText = `✕ 测试异常: ${e}`;
    }
    showToast('测试异常: ' + e, 'error');
  }
}

async function handleTestPush(channel) {
  if (!window.pywebview || !window.pywebview.api) return;
  let params = {};
  if (channel === 'telegram') {
    params = {
      bot_token: getInput('tg-bot-token'),
      chat_id: getInput('tg-chat-id'),
      proxy: getInput('tg-proxy')
    };
  } else if (channel === 'feishu') {
    params = { webhook_url: getInput('feishu-webhook') };
  } else if (channel === 'wecom') {
    params = { webhook_url: getInput('wecom-webhook') };
  }

  showToast(`正在发送 ${channel} 测试通知...`, 'info');
  try {
    const res = await window.pywebview.api.test_notifier(channel, params);
    showToast(res.message, res.success ? 'success' : 'error');
  } catch (e) {
    showToast(`测试异常: ${e}`, 'error');
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
  appState.isSyncingPool = true;
  renderAccountPool();

  try {
    const res = await window.pywebview.api.refresh_all_quotas();
    showToast(res.message, res.success ? "success" : "error");
    if (res && res.data) {
      appState.account_pool = res.data;
    } else {
      const data = await window.pywebview.api.get_account_pool();
      if (data && data.success) {
        appState.account_pool = data.data;
      } else if (data && data.accounts) {
        appState.account_pool = data;
      }
    }
  } catch (e) {
    showToast("刷新失败: " + e, "error");
  } finally {
    appState.isSyncingPool = false;
    if (btn) btn.classList.remove('loading');
    renderAccountPool();
  }
}

async function handleRefreshSingleQuota(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在更新该账号配额...", "warning");
  refreshingAccountIds.add(accountId);
  renderAccountPool();

  try {
    const res = await window.pywebview.api.refresh_account_quota(accountId);
    showToast(res.message, res.success ? "success" : "error");
    if (res && res.success) {
      const data = await window.pywebview.api.get_account_pool();
      if (data && data.success) {
        appState.account_pool = data.data;
      } else if (data && data.accounts) {
        appState.account_pool = data;
      }
    }
  } catch (e) {
    showToast("刷新异常: " + e, "error");
  } finally {
    refreshingAccountIds.delete(accountId);
    renderAccountPool();
  }
}

async function handleSwitchAccount(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在切换账号并重启反重力客户端...", "warning");
  const res = await window.pywebview.api.switch_account(accountId, true);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    if (res.data) {
      appState.account_pool = res.data;
    } else {
      const data = await window.pywebview.api.get_account_pool();
      if (data && data.success) {
        appState.account_pool = data.data;
      } else if (data && data.accounts) {
        appState.account_pool = data;
      }
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

function resetAddAccountModal() {
  const tokenEl = document.getElementById('input-account-token');
  const nameEl = document.getElementById('input-account-name');
  const btnSubmit = document.getElementById('btn-submit-add-account');
  const btnCancel = document.getElementById('btn-cancel-modal');
  const btnClose = document.getElementById('btn-close-modal');
  const progressBox = document.getElementById('import-progress-box');
  const progressBar = document.getElementById('import-progress-bar');
  const progressStatus = document.getElementById('import-progress-status');
  const progressCount = document.getElementById('import-progress-count');
  const progressLog = document.getElementById('import-progress-log');

  if (tokenEl) {
    tokenEl.value = '';
    tokenEl.disabled = false;
  }
  if (nameEl) {
    nameEl.value = '';
    nameEl.disabled = false;
  }
  if (btnSubmit) {
    btnSubmit.disabled = false;
    btnSubmit.classList.remove('loading');
    btnSubmit.textContent = '验证并导入';
  }
  if (btnCancel) {
    btnCancel.disabled = false;
    btnCancel.textContent = '取消';
  }
  if (btnClose) btnClose.disabled = false;
  if (progressBox) progressBox.style.display = 'none';
  if (progressBar) {
    progressBar.style.width = '0%';
    progressBar.className = 'progress-fill';
  }
  if (progressStatus) progressStatus.innerHTML = '<span class="status-dot-pulse"></span> 正在校验中...';
  if (progressCount) progressCount.textContent = '0 / 0';
  if (progressLog) progressLog.innerHTML = '';
}

function parseImportItems(rawText) {
  const text = (rawText || '').trim();
  if (!text) return [];

  // 1. 优先尝试解析 JSON 格式
  if (text.startsWith('[') || text.startsWith('{')) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        return parsed.map(item => typeof item === 'string' ? item : JSON.stringify(item));
      }
      if (parsed && Array.isArray(parsed.accounts)) {
        return parsed.accounts.map(item => typeof item === 'string' ? item : JSON.stringify(item));
      }
      return [text];
    } catch (_) {}
  }

  // 2. 多行文本模式 (一行一条 Token)
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  if (lines.length > 1) {
    return lines;
  }

  return [text];
}

async function handleAddAccountSubmit() {
  const tokenInput = (document.getElementById('input-account-token').value || '').trim();
  const customName = (document.getElementById('input-account-name').value || '').trim();

  if (!tokenInput) {
    showToast("请输入 refresh_token 或凭据 JSON", "warning");
    return;
  }

  const items = parseImportItems(tokenInput);
  if (!items.length) {
    showToast("未检测到有效账号数据", "warning");
    return;
  }

  const tokenEl = document.getElementById('input-account-token');
  const nameEl = document.getElementById('input-account-name');
  const btnSubmit = document.getElementById('btn-submit-add-account');
  const btnCancel = document.getElementById('btn-cancel-modal');
  const btnClose = document.getElementById('btn-close-modal');
  const progressBox = document.getElementById('import-progress-box');
  const progressBar = document.getElementById('import-progress-bar');
  const progressStatus = document.getElementById('import-progress-status');
  const progressCount = document.getElementById('import-progress-count');
  const progressLog = document.getElementById('import-progress-log');

  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前环境不支持导入", "warning");
    return;
  }

  // 1. 立即锁定表单与按钮，给用户最强明确反馈
  if (tokenEl) tokenEl.disabled = true;
  if (nameEl) nameEl.disabled = true;
  if (btnCancel) btnCancel.disabled = true;
  if (btnClose) btnClose.disabled = true;
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.classList.add('loading');
    btnSubmit.textContent = items.length > 1 ? '正在批量导入...' : '正在验证导入...';
  }

  // 2. 立即展开导入进度指示面板
  if (progressBox) progressBox.style.display = 'flex';
  if (progressLog) progressLog.innerHTML = '';

  const total = items.length;
  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < total; i++) {
    const item = items[i];
    const itemNum = i + 1;

    // 智能提取可读账号摘要
    let hint = `账号 #${itemNum}`;
    try {
      if (item.startsWith('{')) {
        const obj = JSON.parse(item);
        if (obj.email) hint = obj.email;
        else if (obj.name) hint = obj.name;
      }
    } catch (_) {}

    if (hint === `账号 #${itemNum}` && item.length > 20) {
      hint = item.slice(0, 10) + '...' + item.slice(-6);
    }

    // 实时更新当前正在处理的账号
    if (progressStatus) {
      progressStatus.innerHTML = `<span class="status-dot-pulse"></span> 正在导入 (${itemNum}/${total}): <strong>${escapeHtml(hint)}</strong>`;
    }
    if (progressCount) {
      progressCount.textContent = `${itemNum} / ${total}`;
    }
    if (progressBar) {
      const pct = Math.round(((itemNum - 0.5) / total) * 100);
      progressBar.style.width = `${pct}%`;
    }

    try {
      const itemCustomName = total === 1 ? (customName || null) : null;
      const res = await window.pywebview.api.add_account(item, itemCustomName);

      if (res && res.success) {
        successCount++;
        if (res.data) appState.account_pool = res.data;
        if (progressLog) {
          const logItem = document.createElement('div');
          logItem.className = 'import-log-item success';
          logItem.innerHTML = `<span style="color:#10b981; font-weight:600;">✓ [${itemNum}/${total}]</span> ${escapeHtml(res.message || hint + ' 导入成功')}`;
          progressLog.appendChild(logItem);
          progressLog.scrollTop = progressLog.scrollHeight;
        }
      } else {
        failCount++;
        if (progressLog) {
          const logItem = document.createElement('div');
          logItem.className = 'import-log-item error';
          logItem.innerHTML = `<span style="color:#ef4444; font-weight:600;">✕ [${itemNum}/${total}]</span> ${escapeHtml((res && res.message) || hint + ' 导入失败')}`;
          progressLog.appendChild(logItem);
          progressLog.scrollTop = progressLog.scrollHeight;
        }
      }
    } catch (e) {
      failCount++;
      if (progressLog) {
        const logItem = document.createElement('div');
        logItem.className = 'import-log-item error';
        logItem.innerHTML = `<span style="color:#ef4444; font-weight:600;">✕ [${itemNum}/${total}]</span> 网络异常: ${escapeHtml(String(e))}`;
        progressLog.appendChild(logItem);
        progressLog.scrollTop = progressLog.scrollHeight;
      }
    }

    if (progressBar) {
      const pct = Math.round((itemNum / total) * 100);
      progressBar.style.width = `${pct}%`;
    }

    if (total > 1 && i < total - 1) {
      await new Promise(r => setTimeout(r, 180));
    }
  }

  // 3. 刷新最新账号池
  try {
    const data = await window.pywebview.api.get_account_pool();
    if (data && data.success && data.data) {
      appState.account_pool = data.data;
    }
    renderAccountPool();
  } catch (_) {}

  if (progressBar) progressBar.style.width = '100%';
  if (progressCount) progressCount.textContent = `${total} / ${total}`;

  // 4. 完成结果展示
  if (failCount === 0) {
    if (progressStatus) {
      progressStatus.innerHTML = `<span style="color:#10b981; font-weight:600;">✓ 全部导入成功！共 ${successCount} 个账号</span>`;
    }
    showToast(`成功批量导入 ${successCount} 个账号！`, 'success');
    if (btnSubmit) {
      btnSubmit.classList.remove('loading');
      btnSubmit.textContent = '完成';
    }
    setTimeout(() => {
      document.getElementById('modal-add-account').classList.remove('active');
      resetAddAccountModal();
    }, 1200);
  } else {
    if (progressStatus) {
      progressStatus.innerHTML = `<span style="color:#f59e0b; font-weight:600;">导入完成：成功 ${successCount} 个，失败 ${failCount} 个</span>`;
    }
    showToast(`导入完成：成功 ${successCount} 个，失败 ${failCount} 个`, failCount === total ? 'error' : 'warning');
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.classList.remove('loading');
      btnSubmit.textContent = '重新导入';
    }
    if (btnCancel) {
      btnCancel.disabled = false;
      btnCancel.textContent = '关闭';
    }
    if (btnClose) btnClose.disabled = false;
    if (tokenEl) tokenEl.disabled = false;
    if (nameEl) nameEl.disabled = false;
  }
}

async function handlePerfSaveAndRestart() {
  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前环境不支持保存重启", "warning");
    return;
  }
  const btn = document.getElementById('btn-perf-save-restart');
  if (btn) btn.classList.add('loading');
  showToast("正在保存补丁配置并重启 Antigravity...", "warning");
  try {
    const cfg = gatherCurrentConfig();
    const res = await window.pywebview.api.save_and_restart(cfg);
    showToast(res.message, res.success ? "success" : "error");
    const data = await window.pywebview.api.get_initial_data();
    if (data && data.status) {
      appState.status = data.status;
      renderSystemStatus();
    }
  } catch (e) {
    showToast("保存重启异常: " + e, "error");
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

async function handlePerfRestore() {
  if (!confirm("确定要恢复 Antigravity 官方英文原版备份吗？\n这将撤销所有汉化与定制。")) return;
  if (!window.pywebview || !window.pywebview.api) return;

  const btn = document.getElementById('btn-perf-restore');
  if (btn) btn.classList.add('loading');
  showToast("正在还原官方原生英文备份...", "warning");
  try {
    const res = await window.pywebview.api.restore_english();
    showToast(res.message, res.success ? "success" : "error");
    const data = await window.pywebview.api.get_initial_data();
    if (data && data.status) {
      appState.status = data.status;
      renderSystemStatus();
    }
  } catch (e) {
    showToast("还原失败: " + e, "error");
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

function handleOpenInitModal() {
  const modal = document.getElementById('modal-confirm-init');
  if (modal) modal.classList.add('active');
}

function handleCloseInitModal() {
  const modal = document.getElementById('modal-confirm-init');
  if (modal) modal.classList.remove('active');
}

async function handleExecuteInit() {
  handleCloseInitModal();
  if (!window.pywebview || !window.pywebview.api) return;

  const btn = document.getElementById('btn-perf-init');
  if (btn) btn.classList.add('loading');
  showToast("正在彻底初始化 Antigravity 客户端...", "warning");
  try {
    const res = await window.pywebview.api.reset_antigravity_full();
    showToast(res.message, res.success ? "success" : "error");
    const data = await window.pywebview.api.get_initial_data();
    if (data) {
      appState.config = data.config;
      appState.status = data.status;
      renderConfigForm();
      renderSystemStatus();
    }
  } catch (e) {
    showToast("初始化异常: " + e, "error");
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

function handleSaveProxy() {
  triggerAutoSave(0);
  showToast("代理服务配置已即时保存生效", "success");
}

let currentExportFormat = 'cockpit';

async function switchExportFormat(fmt) {
  currentExportFormat = fmt;
  const btnCockpit = document.getElementById('btn-export-fmt-cockpit');
  const btnFull = document.getElementById('btn-export-fmt-full');
  if (btnCockpit && btnFull) {
    if (fmt === 'cockpit') {
      btnCockpit.className = 'btn btn-xs btn-primary';
      btnFull.className = 'btn btn-xs btn-secondary';
    } else {
      btnCockpit.className = 'btn btn-xs btn-secondary';
      btnFull.className = 'btn btn-xs btn-primary';
    }
  }
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const res = await window.pywebview.api.export_accounts_data(fmt);
    if (res && res.success) {
      const textarea = document.getElementById('export-accounts-json');
      if (textarea) textarea.value = res.json_str || '';
      showToast(res.message, "success");
    }
  } catch (e) {
    console.error(e);
  }
}

async function handleExportAccounts() {
  if (!window.pywebview || !window.pywebview.api) {
    showToast("当前环境不支持导出", "warning");
    return;
  }
  try {
    const res = await window.pywebview.api.export_accounts_data(currentExportFormat);
    if (res && res.success) {
      const textarea = document.getElementById('export-accounts-json');
      if (textarea) textarea.value = res.json_str || '';
      const modal = document.getElementById('modal-export-accounts');
      if (modal) modal.classList.add('active');
      showToast(res.message, "success");
    } else {
      showToast(res ? res.message : "导出账号失败", "error");
    }
  } catch (e) {
    showToast("导出异常: " + e, "error");
  }
}

function handleCloseExportModal() {
  const modal = document.getElementById('modal-export-accounts');
  if (modal) modal.classList.remove('active');
}

function handleCopyExportJson() {
  const textarea = document.getElementById('export-accounts-json');
  if (!textarea || !textarea.value) {
    showToast("无账号数据可复制", "warning");
    return;
  }
  navigator.clipboard.writeText(textarea.value).then(() => {
    showToast("账号凭据 JSON 已成功复制到剪贴板！", "success");
  }).catch(() => {
    textarea.select();
    document.execCommand('copy');
    showToast("账号凭据已复制", "success");
  });
}

function handleDownloadExportJson() {
  const textarea = document.getElementById('export-accounts-json');
  const text = (textarea ? textarea.value : '').trim();
  if (!text) {
    showToast("无数据可导出", "warning");
    return;
  }
  try {
    const blob = new Blob([text], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const filename = currentExportFormat === 'cockpit'
      ? `cockpit_accounts_${new Date().toISOString().slice(0, 10)}.json`
      : `antigravity_accounts_backup_${new Date().toISOString().slice(0, 10)}.json`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`已下载 ${currentExportFormat === 'cockpit' ? 'Cockpit 格式' : '完整备份'} 文件`, "success");
  } catch (e) {
    showToast("下载文件失败: " + e, "error");
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
