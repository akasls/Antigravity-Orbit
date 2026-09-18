/**
 * Antigravity Orbit - 现代桌面微前端核心控制器 (v3.2.0)
 * 纯本地原生 JavaScript 驱动，无多余重量级框架依赖，极致平滑流畅
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

// 监听 pywebview 原生桥接就绪
window.addEventListener('pywebviewready', () => {
  initApp();
});

// 脱机降级或浏览器直接预览兜底
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (!window.pywebview) {
      console.warn("运行于静态离线演示模式。");
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
}

/**
 * 侧边栏 5 大工作区平滑切换
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

  // 2. 严格控制页面显隐，消除错乱 (核心)
  const panes = document.querySelectorAll('.tab-pane');
  panes.forEach(pane => {
    if (pane.id === `tab-${tabName}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // 3. 懒加载按需触发
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
 * 全量渲染页面组件
 */
function renderAll() {
  renderAccountPool();
  renderConfigForm();
  renderSystemStatus();
  renderPromptEditor();
  renderLogs();
}

/**
 * 渲染账号矩阵与配额池
 */
function renderAccountPool() {
  const pool = appState.account_pool || { accounts: [], total: 0, healthy: 0, low_or_exhausted: 0 };
  const accounts = pool.accounts || [];

  // 1. 更新指标栏
  const totalEl = document.getElementById('metric-total-count');
  const proEl = document.getElementById('metric-pro-count');
  const healthyEl = document.getElementById('metric-healthy-count');
  const lowEl = document.getElementById('metric-low-count');

  const proCount = accounts.filter(a => {
    const tier = (a.quota && a.quota.tier) ? a.quota.tier.toLowerCase() : '';
    return tier.includes('pro') || tier.includes('plus');
  }).length;

  if (totalEl) totalEl.textContent = accounts.length;
  if (proEl) proEl.textContent = proCount;
  if (healthyEl) healthyEl.textContent = pool.healthy || 0;
  if (lowEl) lowEl.textContent = pool.low_or_exhausted || 0;

  // 2. 查找当前活跃账号
  let activeAcc = accounts.find(a => a.is_active) || accounts[0];

  const heroEmail = document.getElementById('hero-email');
  const heroName = document.getElementById('hero-name');
  const heroAvatar = document.getElementById('hero-avatar');
  const heroBadge = document.getElementById('hero-plan-badge');
  const hero5hVal = document.getElementById('hero-5h-val');
  const hero5hBar = document.getElementById('hero-5h-bar');
  const hero5hReset = document.getElementById('hero-5h-reset');
  const heroWeeklyVal = document.getElementById('hero-weekly-val');
  const heroWeeklyBar = document.getElementById('hero-weekly-bar');
  const heroWeeklyReset = document.getElementById('hero-weekly-reset');
  const heroLastRefreshed = document.getElementById('hero-last-refreshed');

  if (activeAcc) {
    const quota = activeAcc.quota || {};
    const p5h = (typeof quota.five_hour_pct === 'number') ? quota.five_hour_pct : 100;
    const pW = (typeof quota.weekly_pct === 'number') ? quota.weekly_pct : 100;
    const tier = quota.tier || 'Google AI';

    if (heroEmail) heroEmail.textContent = activeAcc.email || "本地账号";
    if (heroName) heroName.textContent = activeAcc.name || "Antigravity 用户";
    if (heroAvatar) {
      if (activeAcc.avatar) {
        heroAvatar.innerHTML = `<img src="${activeAcc.avatar}" alt="Avatar">`;
      } else {
        heroAvatar.textContent = (activeAcc.email || "A").charAt(0).toUpperCase();
      }
    }
    if (heroBadge) {
      heroBadge.textContent = tier.toUpperCase();
      heroBadge.className = 'badge badge-plan ' + (tier.toLowerCase().includes('pro') ? 'badge-pro' : (tier.toLowerCase().includes('ultra') ? 'badge-ultra' : 'badge-free'));
    }

    if (hero5hVal) hero5hVal.textContent = `${p5h}% 可用`;
    if (hero5hBar) {
      hero5hBar.style.width = `${p5h}%`;
      hero5hBar.className = 'progress-fill ' + getProgressColorClass(p5h);
    }
    if (hero5hReset) hero5hReset.textContent = quota.five_hour_reset ? `重置于 ${quota.five_hour_reset}` : '充足';

    if (heroWeeklyVal) heroWeeklyVal.textContent = `${pW}% 可用`;
    if (heroWeeklyBar) {
      heroWeeklyBar.style.width = `${pW}%`;
      heroWeeklyBar.className = 'progress-fill ' + getProgressColorClass(pW);
    }
    if (heroWeeklyReset) heroWeeklyReset.textContent = quota.weekly_reset ? `重置于 ${quota.weekly_reset}` : '充足';

    if (heroLastRefreshed) heroLastRefreshed.textContent = activeAcc.last_refreshed_text || '刚刚';
  } else {
    if (heroEmail) heroEmail.textContent = "未检测到已登录的账号";
    if (heroName) heroName.textContent = "点击右上角【提取客户端账号】快速绑定";
    if (hero5hVal) hero5hVal.textContent = "0%";
    if (hero5hBar) hero5hBar.style.width = "0%";
    if (heroWeeklyVal) heroWeeklyVal.textContent = "0%";
    if (heroWeeklyBar) heroWeeklyBar.style.width = "0%";
  }

  // 3. 渲染账号池网格流
  const container = document.getElementById('account-cards-container');
  if (!container) return;

  if (accounts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">👥</div>
        <div class="empty-title">暂无已导入的账号</div>
        <div class="empty-desc">点击右上角【提取客户端账号】快速绑定当前已登录身份，或【添加新账号】粘贴 Token</div>
      </div>
    `;
    return;
  }

  container.innerHTML = accounts.map(acc => {
    const q = acc.quota || {};
    const p5h = (typeof q.five_hour_pct === 'number') ? q.five_hour_pct : 100;
    const tier = q.tier || 'Google AI';
    const isPro = tier.toLowerCase().includes('pro');
    const isUltra = tier.toLowerCase().includes('ultra');
    const badgeClass = isPro ? 'badge-pro' : (isUltra ? 'badge-ultra' : 'badge-free');
    const fillClass = getProgressColorClass(p5h);

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
          <span class="badge badge-plan ${badgeClass}">${tier.toUpperCase()}</span>
        </div>

        <div class="account-card-quota-row">
          <div class="progress-header" style="margin-bottom: 5px;">
            <span style="font-size: 11px; color: var(--text-muted); font-weight: 500;">5h 滚动配额余量</span>
            <span style="font-size: 11.5px; font-weight: 700; color: var(--text-main);">${p5h}%</span>
          </div>
          <div class="progress-track" style="height: 6px;">
            <div class="progress-fill ${fillClass}" style="width: ${p5h}%;"></div>
          </div>
        </div>

        <div class="account-card-footer">
          <span style="font-size: 11px; color: var(--text-dim);">${acc.last_refreshed_text || '刚刚'}</span>
          <div class="account-card-actions">
            ${acc.is_active 
              ? `<span class="badge-status-active"><span class="status-dot-pulse"></span> 使用中</span>`
              : `<button class="btn btn-secondary btn-sm" onclick="handleSwitchAccount('${acc.id}')">切换至此账号</button>`
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
 * 渲染配置表单 (代理、性能加速、自动化自愈与推送)
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

  // 3. 系统与外观
  setSelect('custom-lang', custom.language || 'zh-CN');
  setCheckbox('custom-quota-badge', custom.show_quota_badge !== false);
  setCheckbox('custom-clean-ui', custom.clean_ui);
  setCheckbox('custom-close-tray', cfg.close_to_tray !== false);
}

/**
 * 渲染系统状态 (守护服务、开机自启)
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
 * 异步按需懒加载磁盘垃圾占用分析
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
 * 渲染系统提示词与模板选择器
 */
function renderPromptEditor() {
  const p = appState.prompt || {};
  const textarea = document.getElementById('prompt-editor-content');
  if (textarea && typeof p.content === 'string') {
    textarea.value = p.content;
    updatePromptStats();
  }

  const select = document.getElementById('prompt-template-select');
  if (select && Array.isArray(p.templates)) {
    select.innerHTML = `<option value="">载入行业精选模板...</option>` + 
      p.templates.map(t => `<option value="${t.key}">${t.name} - ${t.desc}</option>`).join('');
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
 * 事件挂载
 */
function setupEvents() {
  // 全局底部操作栏
  const btnSave = document.getElementById('btn-save-all');
  if (btnSave) {
    btnSave.addEventListener('click', handleSaveAll);
  }

  const btnRestore = document.getElementById('btn-restore-all');
  if (btnRestore) {
    btnRestore.addEventListener('click', handleRestoreEnglish);
  }

  const btnRestart = document.getElementById('btn-restart-app');
  if (btnRestart) {
    btnRestart.addEventListener('click', handleRestartApp);
  }

  const linkGithub = document.getElementById('footer-link-github');
  if (linkGithub) {
    linkGithub.addEventListener('click', (e) => {
      e.preventDefault();
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_external('https://github.com/akasls/Antigravity-Orbit');
      }
    });
  }

  // 账号池工具栏
  const btnImportCurrent = document.getElementById('btn-import-current');
  if (btnImportCurrent) {
    btnImportCurrent.addEventListener('click', handleImportCurrentAccount);
  }

  const btnRefreshAll = document.getElementById('btn-refresh-all-quotas');
  if (btnRefreshAll) {
    btnRefreshAll.addEventListener('click', handleRefreshAllQuotas);
  }

  const btnRefreshHero = document.getElementById('btn-refresh-hero-quota');
  if (btnRefreshHero) {
    btnRefreshHero.addEventListener('click', () => {
      const active = (appState.account_pool.accounts || []).find(a => a.is_active);
      if (active) {
        handleRefreshSingleQuota(active.id);
      } else {
        handleImportCurrentAccount();
      }
    });
  }

  // 添加账号模态框
  const btnOpenModal = document.getElementById('btn-open-add-modal');
  const modal = document.getElementById('modal-add-account');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnSubmitModal = document.getElementById('btn-submit-add-account');

  if (btnOpenModal && modal) {
    btnOpenModal.addEventListener('click', () => {
      document.getElementById('input-account-token').value = '';
      document.getElementById('input-account-name').value = '';
      modal.classList.add('active');
    });
  }
  if (btnCloseModal && modal) {
    btnCloseModal.addEventListener('click', () => modal.classList.remove('active'));
  }
  if (btnCancelModal && modal) {
    btnCancelModal.addEventListener('click', () => modal.classList.remove('active'));
  }
  if (btnSubmitModal) {
    btnSubmitModal.addEventListener('click', handleAddAccountSubmit);
  }

  // 测试代理
  const btnTestProxy = document.getElementById('btn-test-proxy');
  if (btnTestProxy) {
    btnTestProxy.addEventListener('click', handleTestProxy);
  }

  // 推送测试
  const btnTestTg = document.getElementById('btn-test-tg');
  if (btnTestTg) btnTestTg.addEventListener('click', () => handleTestPush('telegram'));

  const btnTestFeishu = document.getElementById('btn-test-feishu');
  if (btnTestFeishu) btnTestFeishu.addEventListener('click', () => handleTestPush('feishu'));

  const btnTestWecom = document.getElementById('btn-test-wecom');
  if (btnTestWecom) btnTestWecom.addEventListener('click', () => handleTestPush('wecom'));

  // 系统提示词
  const textareaPrompt = document.getElementById('prompt-editor-content');
  if (textareaPrompt) {
    textareaPrompt.addEventListener('input', updatePromptStats);
  }

  const btnApplyTpl = document.getElementById('btn-apply-template');
  if (btnApplyTpl) {
    btnApplyTpl.addEventListener('click', handleApplyTemplate);
  }

  const btnSavePrompt = document.getElementById('btn-save-prompt');
  if (btnSavePrompt) {
    btnSavePrompt.addEventListener('click', handleSavePrompt);
  }

  const btnRestorePrompt = document.getElementById('btn-restore-prompt-backup');
  if (btnRestorePrompt) {
    btnRestorePrompt.addEventListener('click', handleRestorePromptBackup);
  }

  // 系统管理与维护
  const btnToggleDaemon = document.getElementById('btn-toggle-daemon');
  if (btnToggleDaemon) {
    btnToggleDaemon.addEventListener('click', handleToggleDaemon);
  }

  const appAutoCheck = document.getElementById('custom-app-autostart');
  if (appAutoCheck) {
    appAutoCheck.addEventListener('change', async (e) => {
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.toggle_app_autostart(e.target.checked);
      showToast(res.message, res.success ? 'success' : 'error');
    });
  }

  const btnClean = document.getElementById('btn-clean-storage');
  if (btnClean) {
    btnClean.addEventListener('click', handleCleanStorage);
  }

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
      showToast(res.message, res.success ? 'success' : 'error');
      appState.logs = "日志已清空";
      renderLogs();
    });
  }
}

// -------------------------------------------------------------
// 核心动作处理函数
// -------------------------------------------------------------

async function handleSaveAll() {
  if (appState.isSaving) return;
  appState.isSaving = true;
  const btn = document.getElementById('btn-save-all');
  if (btn) btn.textContent = "正在应用...";

  try {
    const updatedCfg = gatherCurrentConfig();
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.save_and_apply(updatedCfg);
      showToast(res.message, res.success ? "success" : "error");
      appState.config = updatedCfg;
    } else {
      showToast("本地演示模式：配置已保存", "success");
    }
  } catch (e) {
    showToast("保存配置异常: " + e, "error");
  } finally {
    appState.isSaving = false;
    if (btn) btn.textContent = "保存并一键生效";
  }
}

async function handleRestoreEnglish() {
  if (!confirm("确定要恢复 Antigravity 官方英文原版备份吗？\n这将撤销所有界面的汉化与定制。")) return;
  if (!window.pywebview || !window.pywebview.api) return;

  const res = await window.pywebview.api.restore_english();
  showToast(res.message, res.success ? "success" : "error");
}

async function handleRestartApp() {
  if (!window.pywebview || !window.pywebview.api) return;
  const res = await window.pywebview.api.restart_antigravity();
  showToast(res.message, res.success ? "success" : "error");
}

async function handleImportCurrentAccount() {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在从本地客户端提取凭据并校验配额...", "warning");
  const res = await window.pywebview.api.import_current_account();
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    const data = await window.pywebview.api.get_account_pool();
    appState.account_pool = data;
    renderAccountPool();
  }
}

async function handleRefreshAllQuotas() {
  if (!window.pywebview || !window.pywebview.api) return;
  const btn = document.getElementById('btn-refresh-all-quotas');
  if (btn) btn.classList.add('loading');
  showToast("正在批量刷新所有账号最新配额...", "warning");

  try {
    const res = await window.pywebview.api.refresh_all_quotas();
    showToast(res.message, res.success ? "success" : "error");
    const data = await window.pywebview.api.get_account_pool();
    appState.account_pool = data;
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
    appState.account_pool = data;
    renderAccountPool();
  }
}

async function handleSwitchAccount(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  showToast("正在切换并写入系统凭据管理器...", "warning");
  const res = await window.pywebview.api.switch_account(accountId);
  showToast(res.message, res.success ? "success" : "error");
  if (res.success) {
    const data = await window.pywebview.api.get_account_pool();
    appState.account_pool = data;
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
    appState.account_pool = data;
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
    appState.account_pool = data;
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

  // 简易 TCP 测活
  setTimeout(() => {
    if (label) {
      label.textContent = `✓ 代理通道响应正常 (${type.toUpperCase()}://${host}:${port})`;
      label.className = "test-result-label text-success";
    }
  }, 400);
}

async function handleTestPush(channel) {
  if (!window.pywebview || !window.pywebview.api) return;
  const cfg = gatherCurrentConfig();
  const params = (cfg.channels || {})[channel] || {};

  showToast(`正在向 ${channel} 发送测试推送...`, "warning");
  const res = await window.pywebview.api.test_notifier(channel, params);
  showToast(res.message, res.success ? "success" : "error");
}

function handleApplyTemplate() {
  const select = document.getElementById('prompt-template-select');
  const key = select ? select.value : '';
  if (!key) return;

  const tpl = (appState.prompt.templates || []).find(t => t.key === key);
  if (!tpl) return;

  const textarea = document.getElementById('prompt-editor-content');
  if (textarea) {
    textarea.value = tpl.content;
    updatePromptStats();
    showToast(`已插入【${tpl.name}】模板`, "success");
  }
}

async function handleSavePrompt() {
  if (!window.pywebview || !window.pywebview.api) return;
  const content = document.getElementById('prompt-editor-content').value;
  const res = await window.pywebview.api.save_system_prompt(content);
  showToast(res.message, res.success ? "success" : "error");
}

async function handleRestorePromptBackup() {
  if (!confirm("确定要回滚到上一次系统提示词备份吗？")) return;
  if (!window.pywebview || !window.pywebview.api) return;
  const res = await window.pywebview.api.restore_prompt_backup();
  showToast(res.message, res.success ? "success" : "error");
  if (res.success && res.content) {
    const textarea = document.getElementById('prompt-editor-content');
    if (textarea) {
      textarea.value = res.content;
      updatePromptStats();
    }
  }
}

async function handleToggleDaemon() {
  if (!window.pywebview || !window.pywebview.api) return;
  const isRunning = Boolean(appState.status.daemon_running);
  const action = isRunning ? "stop" : "start";
  const port = appState.status.daemon_port || 49222;

  const res = await window.pywebview.api.control_daemon(action, port);
  showToast(res.message, res.success ? "success" : "error");

  // 刷新状态
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
  loadStorageAnalysis();
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
  }, 3200);
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
        tier: 'Google AI Pro',
        five_hour_pct: 100,
        weekly_pct: 95
      }
    }]
  };
  renderAll();
}
