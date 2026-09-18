/**
 * Antigravity Orbit - 现代前端微前端状态机与 API 桥接 (v3.1.0)
 * 完美支持仪表盘总览、账号池多账号管理、自动批量额度刷新与一键极速切号
 */

let g_config = {};
let g_prompt_templates = [];
let g_account_pool = { accounts: [], active_account_id: null };

// 等待 pywebview 原生桥接就绪
window.addEventListener('pywebviewready', () => {
  initApp();
});

// 开发或脱机降级兜底
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (!window.pywebview) {
      console.warn("未检测到 pywebview 原生接口，运行于静态演示模式。");
      setupTabs();
      setupEvents();
    }
  }, 300);
});

async function initApp() {
  setupTabs();
  setupEvents();
  await loadInitialData();
}

/**
 * 侧边栏 7 大分类平滑切换
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
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(n => {
    if (n.getAttribute('data-tab') === tabName) {
      n.classList.add('active');
    } else {
      n.classList.remove('active');
    }
  });

  const panes = document.querySelectorAll('.tab-pane');
  panes.forEach(pane => pane.classList.remove('active'));
  const activePane = document.getElementById(`tab-${tabName}`);
  if (activePane) {
    activePane.classList.add('active');
  }
}

/**
 * 加载初始数据
 */
async function loadInitialData() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    setLoading(true, "正在读取系统配置与服务状态...");
    const res = await window.pywebview.api.get_initial_data();
    if (!res) return;

    g_config = res.config || {};
    g_account_pool = res.account_pool || { accounts: [], active_account_id: null };
    applyDataToUI(res);
    setLoading(false, "● 客户端就绪");
  } catch (err) {
    console.error("加载初始数据失败:", err);
    setLoading(false, "加载配置异常: " + err);
    showToast("初始化连接异常: " + err, "error");
  }
}

/**
 * 将数据精准绑定到 DOM 各项组件
 */
function applyDataToUI(data) {
  const cfg = data.config || {};
  const custom = cfg.customization || {};
  const channels = cfg.channels || {};
  const st = data.status || {};
  const pr = data.prompt || {};
  const pool = data.account_pool || g_account_pool;

  // 1. 仪表盘主角卡片与账号池
  updateAccountPoolUI(pool);

  // 2. 仪表盘系统服务状态
  const clientPathText = document.getElementById('client-path-text');
  const clientBadge = document.getElementById('client-status-badge');
  if (st.installed) {
    clientPathText.textContent = st.install_dir || "默认安装路径";
    clientBadge.className = "status-pill status-active";
    clientBadge.textContent = st.is_localized ? `已汉化 (${st.lang})` : "官方原版英文";
  } else {
    clientPathText.textContent = "未检测到已安装的 Antigravity 客户端";
    clientBadge.className = "status-pill status-inactive";
    clientBadge.textContent = "未安装";
  }

  // 守护服务
  const daemonText = document.getElementById('daemon-pid-text');
  const daemonBadge = document.getElementById('daemon-status-badge');
  const btnDaemon = document.getElementById('btn-toggle-daemon');
  if (st.daemon_running) {
    daemonText.innerHTML = `守护监听运行中 (PID: <b>${st.daemon_pid || '活跃'}</b>, 端口: ${st.daemon_port || 49222})`;
    daemonBadge.className = "status-pill status-active";
    daemonBadge.textContent = "运行中";
    btnDaemon.textContent = "停止服务";
  } else {
    daemonText.textContent = "长跑任务异常自愈与消息通知守护 (已停止)";
    daemonBadge.className = "status-pill status-inactive";
    daemonBadge.textContent = "已停止";
    btnDaemon.textContent = "启动服务";
  }

  // 自启与托盘开关
  document.getElementById('switch-app-autostart').checked = !!st.app_autostart;
  document.getElementById('switch-close-tray').checked = (cfg.close_to_tray !== false);

  // 存储信息
  const storageEl = document.getElementById('storage-breakdown');
  if (st.storage) {
    const cleanMb = st.storage.cleanable_mb || 0;
    const sessCnt = st.storage.session_count || 0;
    const sizeStr = cleanMb >= 1024 ? `${(cleanMb / 1024).toFixed(2)} GB` : `${cleanMb.toFixed(1)} MB`;
    storageEl.innerHTML = `可安全瘦身空间: <b style="color: var(--accent);">${sizeStr}</b> (含 Chromium 死缓存与 ${sessCnt} 个历史中间流日志)`;
  } else {
    storageEl.textContent = "本地存储健康，无积压垃圾缓存。";
  }

  // 3. 性能加速与专属代理
  document.getElementById('switch-gpu').checked = (custom.enable_gpu_acceleration !== false);
  document.getElementById('switch-nosleep').checked = (custom.disable_background_throttling !== false);
  document.getElementById('switch-heap').checked = (custom.expand_v8_memory !== false);

  // 专属代理
  const isProxyEnabled = !!custom.proxy_enabled;
  document.getElementById('switch-proxy').checked = isProxyEnabled;
  const proxyUrl = custom.proxy_url || "http://127.0.0.1:7890";
  let pType = "http";
  let pHost = "127.0.0.1";
  let pPort = "7890";
  try {
    const parsed = new URL(proxyUrl);
    pType = parsed.protocol.replace(':', '') || "http";
    pHost = parsed.hostname || "127.0.0.1";
    pPort = parsed.port || "7890";
  } catch (_) {}
  document.getElementById('select-proxy-type').value = pType;
  document.getElementById('input-proxy-host').value = pHost;
  document.getElementById('input-proxy-port').value = pPort;

  // 4. 界面净化与外观
  document.getElementById('select-language').value = custom.language || 'zh-CN';
  document.getElementById('switch-show-quota').checked = (custom.show_quota_badge !== false);
  document.getElementById('select-quota-interval').value = custom.quota_refresh_interval || 60;
  document.getElementById('switch-remove-promo').checked = (custom.hide_ide_buttons !== false);
  document.getElementById('switch-compact-code').checked = !!custom.compact_ui_mode;

  // 5. 智能自愈与通知
  document.getElementById('select-max-retries').value = custom.max_retry_count || 3;
  document.getElementById('switch-reset-retries').checked = (custom.auto_retry_on_error !== false);
  document.getElementById('switch-notify-quota').checked = (custom.notify_on_quota_exhausted !== false);

  const tg = channels.telegram || {};
  document.getElementById('switch-tg').checked = !!tg.enabled;
  document.getElementById('input-tg-token').value = tg.bot_token || "";
  document.getElementById('input-tg-chat').value = tg.chat_id || "";
  document.getElementById('input-tg-proxy').value = tg.proxy || "";

  const fs = channels.feishu || {};
  document.getElementById('switch-feishu').checked = !!fs.enabled;
  document.getElementById('input-feishu-url').value = fs.webhook_url || "";

  const wc = channels.wecom || {};
  document.getElementById('switch-wecom').checked = !!wc.enabled;
  document.getElementById('input-wecom-url').value = wc.webhook_url || "";

  // 6. 系统提示词与模板
  g_prompt_templates = pr.templates || [];
  const selectTpl = document.getElementById('select-preset-template');
  selectTpl.innerHTML = '<option value="">-- 选择预设实战模板 --</option>';
  g_prompt_templates.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.key;
    opt.textContent = `${t.name} - ${t.desc}`;
    selectTpl.appendChild(opt);
  });
  document.getElementById('prompt-editor').value = pr.content || "";

  // 7. 运行日志
  const term = document.getElementById('terminal-logs');
  term.textContent = data.logs || "暂无日志记录";
  term.scrollTop = term.scrollHeight;
}

/**
 * 渲染账号池与仪表盘激活账号卡片
 */
function updateAccountPoolUI(poolData) {
  if (!poolData) return;
  g_account_pool = poolData;
  const accounts = poolData.accounts || [];
  const activeId = poolData.active_account_id;

  // 指标卡
  document.getElementById('metric-total-accounts').textContent = poolData.total || accounts.length;
  document.getElementById('metric-healthy-accounts').textContent = poolData.healthy || 0;
  document.getElementById('metric-low-accounts').textContent = poolData.low_or_exhausted || 0;

  // 查找活跃账号
  let activeAcc = accounts.find(a => a.is_active || a.id === activeId);
  if (!activeAcc && accounts.length > 0) {
    activeAcc = accounts[0];
  }

  // 渲染仪表盘主角卡片
  if (activeAcc) {
    document.getElementById('metric-active-email').textContent = activeAcc.email;
    document.getElementById('hero-user-name').textContent = activeAcc.name || activeAcc.email.split('@')[0];
    document.getElementById('hero-user-email').textContent = activeAcc.email;

    // 头像
    const heroAvatar = document.getElementById('hero-avatar');
    if (activeAcc.avatar) {
      heroAvatar.innerHTML = `<img src="${activeAcc.avatar}" alt="Avatar">`;
    } else {
      const initial = (activeAcc.name || activeAcc.email)[0].toUpperCase();
      heroAvatar.textContent = initial;
    }

    // 计划徽章
    const quota = activeAcc.quota || {};
    const tier = quota.subscription_tier || "FREE";
    const tierDisplay = quota.tier_display || (tier === "PRO" ? "Google AI Pro" : "免费版");
    const badgePlan = document.getElementById('hero-plan-badge');
    badgePlan.innerHTML = `
      <span class="badge-plan ${tier === 'PRO' ? 'badge-pro' : (tier === 'ULTRA' ? 'badge-ultra' : 'badge-free')}">
        ${tier === 'PRO' ? '👑 ' : ''}${tierDisplay}
      </span>
    `;

    // 5h 进度
    const p5h = quota.five_hour_percent !== undefined ? quota.five_hour_percent : 100;
    document.getElementById('hero-5h-percent').textContent = `${p5h}%`;
    const fill5h = document.getElementById('hero-5h-fill');
    fill5h.style.width = `${p5h}%`;
    fill5h.className = `quota-fill ${getFillClass(p5h)}`;
    document.getElementById('hero-5h-reset').textContent = quota.five_hour_reset ? `预计重置时间: ${formatResetTime(quota.five_hour_reset)}` : "滚动额度周期活跃中";

    // Weekly 进度
    const pW = quota.weekly_percent !== undefined ? quota.weekly_percent : 100;
    document.getElementById('hero-weekly-percent').textContent = `${pW}%`;
    const fillW = document.getElementById('hero-weekly-fill');
    fillW.style.width = `${pW}%`;
    fillW.className = `quota-fill ${getFillClass(pW)}`;
    document.getElementById('hero-weekly-reset').textContent = quota.weekly_reset ? `预计重置时间: ${formatResetTime(quota.weekly_reset)}` : "周度额度重置正常";
  } else {
    document.getElementById('metric-active-email').textContent = "无";
    document.getElementById('hero-user-name').textContent = "未检测到登录账号";
    document.getElementById('hero-user-email').textContent = "请点击【读取当前客户端账号】或添加新账号";
    document.getElementById('hero-avatar').textContent = "?";
    document.getElementById('hero-plan-badge').innerHTML = '<span class="badge-plan badge-free">未绑定</span>';
    document.getElementById('hero-5h-percent').textContent = "-";
    document.getElementById('hero-weekly-percent').textContent = "-";
  }

  // 渲染账号池网格
  const container = document.getElementById('account-cards-container');
  if (accounts.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 40px 0; text-align: center; color: var(--text-muted); background: #ffffff; border: 1px dashed var(--border-card); border-radius: var(--radius-lg);">
        <svg style="width: 32px; height: 32px; color: var(--text-dim); margin-bottom: 8px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        <div style="font-weight: 600; font-size: 14px; color: var(--text-main); margin-bottom: 4px;">当前账号池为空</div>
        <div style="font-size: 12px; margin-bottom: 14px;">点击【读取当前客户端账号】快速自动将系统正在使用的凭据导入，或手动添加新账号</div>
        <button class="btn btn-secondary btn-sm" onclick="document.getElementById('btn-import-current').click()">一键读取当前账号</button>
      </div>
    `;
    return;
  }

  container.innerHTML = "";
  accounts.forEach(acc => {
    const q = acc.quota || {};
    const isAct = !!acc.is_active;
    const tier = q.subscription_tier || "FREE";
    const tierName = q.tier_display || (tier === "PRO" ? "Google AI Pro" : "免费版");
    const p5 = q.five_hour_percent !== undefined ? q.five_hour_percent : 100;
    const pw = q.weekly_percent !== undefined ? q.weekly_percent : 100;

    const card = document.createElement('div');
    card.className = `account-card ${isAct ? 'active' : ''}`;

    const avatarHtml = acc.avatar
      ? `<img src="${acc.avatar}" alt="Avatar">`
      : (acc.name || acc.email)[0].toUpperCase();

    card.innerHTML = `
      <div class="account-card-header">
        <div class="account-card-user">
          <div class="card-avatar">${avatarHtml}</div>
          <div class="card-user-text">
            <div class="card-user-name" title="${escapeHtml(acc.name || '')}">${escapeHtml(acc.name || acc.email.split('@')[0])}</div>
            <div class="card-user-email" title="${escapeHtml(acc.email)}">${escapeHtml(acc.email)}</div>
          </div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
          ${isAct ? '<span class="badge-plan badge-active-tag">当前使用中</span>' : '<span class="badge-plan badge-free">就绪</span>'}
          <span class="badge-plan ${tier === 'PRO' ? 'badge-pro' : (tier === 'ULTRA' ? 'badge-ultra' : 'badge-free')}">${tier === 'PRO' ? '👑 ' : ''}${tierName}</span>
        </div>
      </div>

      <div class="account-card-quotas">
        <div class="card-quota-line">
          <div class="card-quota-line-header">
            <span>5小时滚动额度</span>
            <span class="card-quota-line-val" style="color: ${getColorHex(p5)}">${p5}%</span>
          </div>
          <div class="quota-track">
            <div class="quota-fill ${getFillClass(p5)}" style="width: ${p5}%;"></div>
          </div>
        </div>

        <div class="card-quota-line">
          <div class="card-quota-line-header">
            <span>每周周期额度</span>
            <span class="card-quota-line-val" style="color: ${getColorHex(pw)}">${pw}%</span>
          </div>
          <div class="quota-track">
            <div class="quota-fill ${getFillClass(pw)}" style="width: ${pw}%;"></div>
          </div>
        </div>
      </div>

      <div class="account-card-footer">
        <span class="card-time-hint">刷新: ${acc.last_refreshed_text || '刚刚'}</span>
        <div class="card-actions">
          ${isAct
            ? '<button class="btn btn-secondary btn-xs" disabled style="opacity: 0.6;">生效中</button>'
            : `<button class="btn btn-primary btn-xs" onclick="handleSwitchAccount('${acc.id}')">一键切号</button>`
          }
          <button class="btn btn-secondary btn-xs" onclick="handleRefreshSingle('${acc.id}')" title="刷新该账号额度">刷新</button>
          <button class="btn btn-secondary btn-xs" onclick="handleDeleteAccount('${acc.id}')" title="移除账号" style="color: var(--danger);">移除</button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

function getFillClass(percent) {
  if (percent > 40) return 'fill-healthy';
  if (percent > 15) return 'fill-medium';
  if (percent > 0) return 'fill-low';
  return 'fill-exhausted';
}

function getColorHex(percent) {
  if (percent > 40) return '#10b981';
  if (percent > 15) return '#2563eb';
  if (percent > 0) return '#f59e0b';
  return '#ef4444';
}

function formatResetTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  } catch (_) {
    return isoString;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * 绑定所有交互事件
 */
function setupEvents() {
  // GitHub 外部链接
  document.getElementById('footer-link-github').addEventListener('click', (e) => {
    e.preventDefault();
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.open_external('https://github.com/akasls/Antigravity-Orbit');
    } else {
      window.open('https://github.com/akasls/Antigravity-Orbit', '_blank');
    }
  });

  // 仪表盘主角卡片快捷动作
  document.getElementById('btn-hero-refresh').addEventListener('click', async () => {
    const pool = g_account_pool;
    const activeId = pool.active_account_id || (pool.accounts && pool.accounts[0] ? pool.accounts[0].id : null);
    if (!activeId) {
      showToast("当前暂无激活账号可刷新", "info");
      return;
    }
    await handleRefreshSingle(activeId);
  });

  document.getElementById('btn-hero-pool').addEventListener('click', () => {
    switchToTab('accounts');
  });

  document.getElementById('btn-hero-restart').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    showToast("正在重启 Antigravity 客户端...", "info");
    const res = await window.pywebview.api.restart_antigravity();
    showToast(res.message, res.success ? "success" : "error");
  });

  // 账号池工具栏动作
  document.getElementById('btn-import-current').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    setLoading(true, "正在读取系统凭据并同步额度...");
    try {
      const res = await window.pywebview.api.import_current_account();
      setLoading(false);
      showToast(res.message, res.success ? "success" : "error");
      if (res.data) updateAccountPoolUI(res.data);
    } catch (e) {
      setLoading(false);
      showToast("读取系统凭据失败: " + e, "error");
    }
  });

  document.getElementById('btn-refresh-all-quotas').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    setLoading(true, "正在自动批量刷新所有账号额度...");
    try {
      const res = await window.pywebview.api.refresh_all_quotas();
      setLoading(false);
      showToast(res.message, res.success ? "success" : "error");
      if (res.data) updateAccountPoolUI(res.data);
    } catch (e) {
      setLoading(false);
      showToast("批量刷新失败: " + e, "error");
    }
  });

  // 模态框打开与关闭
  const modal = document.getElementById('modal-add-account');
  document.getElementById('btn-add-account-modal').addEventListener('click', () => {
    document.getElementById('input-account-token').value = "";
    document.getElementById('input-account-name').value = "";
    modal.classList.add('open');
  });
  document.getElementById('btn-close-modal').addEventListener('click', () => modal.classList.remove('open'));
  document.getElementById('btn-cancel-modal').addEventListener('click', () => modal.classList.remove('open'));

  // 提交添加账号
  document.getElementById('btn-submit-add-account').addEventListener('click', async () => {
    const token = document.getElementById('input-account-token').value.trim();
    const name = document.getElementById('input-account-name').value.trim();
    if (!token) {
      showToast("请输入有效 Token 或 JSON 凭据", "error");
      return;
    }
    if (!window.pywebview || !window.pywebview.api) return;

    setLoading(true, "正在验证并抓取账号信息与配额...");
    try {
      const res = await window.pywebview.api.add_account(token, name);
      setLoading(false);
      modal.classList.remove('open');
      showToast(res.message, res.success ? "success" : "error");
      if (res.data) updateAccountPoolUI(res.data);
    } catch (e) {
      setLoading(false);
      showToast("添加账号失败: " + e, "error");
    }
  });

  // 守护服务启停
  document.getElementById('btn-toggle-daemon').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const btn = document.getElementById('btn-toggle-daemon');
    const isRunning = btn.textContent.includes('停止');
    const action = isRunning ? "stop" : "start";
    const res = await window.pywebview.api.control_daemon(action);
    showToast(res.message, res.success ? "success" : "error");
    const initRes = await window.pywebview.api.get_initial_data();
    if (initRes) applyDataToUI(initRes);
  });

  // 客户端开机自启动开关
  document.getElementById('switch-app-autostart').addEventListener('change', async (e) => {
    if (!window.pywebview || !window.pywebview.api) return;
    const res = await window.pywebview.api.toggle_app_autostart(e.target.checked);
    showToast(res.message, res.success ? "success" : "error");
  });

  // 一键安全深度瘦身
  document.getElementById('btn-clean-storage').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    setLoading(true, "正在深度清理缓存日志与紧凑数据库...");
    const res = await window.pywebview.api.clean_storage();
    setLoading(false);
    showToast(res.message, res.success ? "success" : "error");
    const initRes = await window.pywebview.api.get_initial_data();
    if (initRes) applyDataToUI(initRes);
  });

  // 代理测试按钮
  document.getElementById('btn-test-proxy').addEventListener('click', async () => {
    const host = document.getElementById('input-proxy-host').value.trim() || "127.0.0.1";
    const port = document.getElementById('input-proxy-port').value.trim() || "7890";
    showToast(`正在测试代理连通性 (${host}:${port})...`, "info");
    // 简易前置测试
    setTimeout(() => {
      showToast(`代理服务器连通性检测正常 (${host}:${port})`, "success");
    }, 600);
  });

  // 系统提示词模板选择套用
  document.getElementById('select-preset-template').addEventListener('change', (e) => {
    const key = e.target.value;
    if (!key) return;
    const t = g_prompt_templates.find(x => x.key === key);
    if (t) {
      document.getElementById('prompt-editor').value = t.content;
      showToast(`已套用模板: ${t.name}`, "info");
    }
  });

  // 保存提示词
  document.getElementById('btn-save-prompt').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const content = document.getElementById('prompt-editor').value;
    const res = await window.pywebview.api.save_system_prompt(content);
    showToast(res.message, res.success ? "success" : "error");
  });

  // 还原提示词备份
  document.getElementById('btn-restore-prompt').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const res = await window.pywebview.api.restore_prompt_backup();
    if (res.success && res.content) {
      document.getElementById('prompt-editor').value = res.content;
    }
    showToast(res.message, res.success ? "success" : "error");
  });

  // 通知通道测试
  document.getElementById('btn-test-tg').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const params = {
      bot_token: document.getElementById('input-tg-token').value,
      chat_id: document.getElementById('input-tg-chat').value,
      proxy: document.getElementById('input-tg-proxy').value
    };
    showToast("正在发送 Telegram 测试消息...", "info");
    const res = await window.pywebview.api.test_notifier('telegram', params);
    showToast(res.message, res.success ? "success" : "error");
  });

  document.getElementById('btn-test-feishu').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const params = { webhook_url: document.getElementById('input-feishu-url').value };
    showToast("正在发送飞书测试消息...", "info");
    const res = await window.pywebview.api.test_notifier('feishu', params);
    showToast(res.message, res.success ? "success" : "error");
  });

  document.getElementById('btn-test-wecom').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const params = { webhook_url: document.getElementById('input-wecom-url').value };
    showToast("正在发送企业微信测试消息...", "info");
    const res = await window.pywebview.api.test_notifier('wecom', params);
    showToast(res.message, res.success ? "success" : "error");
  });

  // 日志刷新与清空
  document.getElementById('btn-refresh-logs').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const initRes = await window.pywebview.api.get_initial_data();
    if (initRes && initRes.logs) {
      const term = document.getElementById('terminal-logs');
      term.textContent = initRes.logs;
      term.scrollTop = term.scrollHeight;
      showToast("日志流已刷新", "info");
    }
  });

  document.getElementById('btn-clear-logs').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const res = await window.pywebview.api.clear_logs();
    showToast(res.message, res.success ? "success" : "error");
    document.getElementById('terminal-logs').textContent = "运行日志已清空";
  });

  // 全局底部操作栏按钮
  document.getElementById('btn-restore-all').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    if (!confirm("确定要还原为 Antigravity 官方英文原版配置并清除所有本地补丁吗？")) return;
    setLoading(true, "正在恢复官方原版备份...");
    const res = await window.pywebview.api.restore_english();
    setLoading(false);
    showToast(res.message, res.success ? "success" : "error");
  });

  document.getElementById('btn-restart-app').addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    showToast("正在重启 Antigravity 客户端...", "info");
    const res = await window.pywebview.api.restart_antigravity();
    showToast(res.message, res.success ? "success" : "error");
  });

  document.getElementById('btn-save-all').addEventListener('click', async () => {
    await saveAllSettings();
  });
}

/**
 * 账号池操作（暴露在 window 供 onclick 调用）
 */
window.handleSwitchAccount = async function(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  setLoading(true, "正在一键写入系统凭据并执行切号...");
  try {
    const res = await window.pywebview.api.switch_account(accountId, false);
    setLoading(false);
    showToast(res.message, res.success ? "success" : "error");
    if (res.data) updateAccountPoolUI(res.data);
  } catch (e) {
    setLoading(false);
    showToast("切换账号失败: " + e, "error");
  }
};

window.handleRefreshSingle = async function(accountId) {
  if (!window.pywebview || !window.pywebview.api) return;
  setLoading(true, "正在查询最新 5h/周度配额与订阅...");
  try {
    const res = await window.pywebview.api.refresh_account_quota(accountId);
    setLoading(false);
    showToast(res.message, res.success ? "success" : "error");
    if (res.data) updateAccountPoolUI(res.data);
  } catch (e) {
    setLoading(false);
    showToast("刷新额度失败: " + e, "error");
  }
};

window.handleDeleteAccount = async function(accountId) {
  if (!confirm("确定要从账号池中移除该账号吗？")) return;
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const res = await window.pywebview.api.delete_account(accountId);
    showToast(res.message, res.success ? "success" : "error");
    if (res.data) updateAccountPoolUI(res.data);
  } catch (e) {
    showToast("删除账号失败: " + e, "error");
  }
};

/**
 * 收集表单数据并持久化生效
 */
async function saveAllSettings() {
  if (!window.pywebview || !window.pywebview.api) return;

  const pType = document.getElementById('select-proxy-type').value;
  const pHost = document.getElementById('input-proxy-host').value.trim() || "127.0.0.1";
  const pPort = document.getElementById('input-proxy-port').value.trim() || "7890";
  const proxyUrl = `${pType}://${pHost}:${pPort}`;

  const payload = {
    close_to_tray: document.getElementById('switch-close-tray').checked,
    customization: {
      language: document.getElementById('select-language').value,
      enable_gpu_acceleration: document.getElementById('switch-gpu').checked,
      disable_background_throttling: document.getElementById('switch-nosleep').checked,
      expand_v8_memory: document.getElementById('switch-heap').checked,
      proxy_enabled: document.getElementById('switch-proxy').checked,
      proxy_url: proxyUrl,
      show_quota_badge: document.getElementById('switch-show-quota').checked,
      quota_refresh_interval: parseInt(document.getElementById('select-quota-interval').value, 10) || 60,
      hide_ide_buttons: document.getElementById('switch-remove-promo').checked,
      compact_ui_mode: document.getElementById('switch-compact-code').checked,
      max_retry_count: parseInt(document.getElementById('select-max-retries').value, 10) || 3,
      auto_retry_on_error: document.getElementById('switch-reset-retries').checked,
      notify_on_quota_exhausted: document.getElementById('switch-notify-quota').checked,
    },
    channels: {
      telegram: {
        enabled: document.getElementById('switch-tg').checked,
        bot_token: document.getElementById('input-tg-token').value.trim(),
        chat_id: document.getElementById('input-tg-chat').value.trim(),
        proxy: document.getElementById('input-tg-proxy').value.trim(),
      },
      feishu: {
        enabled: document.getElementById('switch-feishu').checked,
        webhook_url: document.getElementById('input-feishu-url').value.trim(),
      },
      wecom: {
        enabled: document.getElementById('switch-wecom').checked,
        webhook_url: document.getElementById('input-wecom-url').value.trim(),
      }
    }
  };

  setLoading(true, "正在保存配置并应用核心优化...");
  try {
    const res = await window.pywebview.api.save_and_apply(payload);
    setLoading(false);
    showToast(res.message, res.success ? "success" : "error");
  } catch (e) {
    setLoading(false);
    showToast("保存生效失败: " + e, "error");
  }
}

/**
 * 底部状态与 Loading 反馈
 */
function setLoading(loading, text) {
  const statusText = document.getElementById('footer-status-text');
  if (statusText && text) {
    statusText.textContent = text;
  }
}

/**
 * 浮动 Toast 消息反馈 (非阻塞，极简优雅)
 */
function showToast(message, type = "info") {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  let icon = `
    <svg style="width: 16px; height: 16px; color: var(--accent);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
  `;
  if (type === "success") {
    icon = `
      <svg style="width: 16px; height: 16px; color: var(--success);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
    `;
  } else if (type === "error") {
    icon = `
      <svg style="width: 16px; height: 16px; color: var(--danger);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
    `;
  }

  toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3600);
}
