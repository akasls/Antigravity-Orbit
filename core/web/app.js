/**
 * Antigravity Orbit - 现代前端响应式逻辑与 API 桥接状态机
 */

let g_config = {};
let g_prompt_templates = [];

// 等待 pywebview 原生桥接就绪
window.addEventListener('pywebviewready', () => {
  initApp();
});

// 开发或脱机降级兜底 (如果未通过 pywebview 加载)
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (!window.pywebview) {
      console.warn("未检测到 pywebview 原生接口，运行于静态预览模式。");
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

      // 切换导航选中态
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      // 切换内容面板
      const panes = document.querySelectorAll('.tab-pane');
      panes.forEach(pane => pane.classList.remove('active'));
      const activePane = document.getElementById(`tab-${targetTab}`);
      if (activePane) {
        activePane.classList.add('active');
      }
    });
  });
}

/**
 * 获取并填充初始数据
 */
async function loadInitialData() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    setLoading(true, "正在读取系统配置与服务状态...");
    const res = await window.pywebview.api.get_initial_data();
    if (!res) return;

    g_config = res.config || {};
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

  // 1. 状态与安装路径
  const badgeInstall = document.getElementById('badge-install-status');
  const textInstall = document.getElementById('text-install-path');
  if (st.installed) {
    const langLabel = st.is_localized ? `已汉化 (${st.lang || 'zh-CN'})` : '官方原版英文';
    badgeInstall.className = 'pill-badge green';
    badgeInstall.textContent = `● ${langLabel}`;
    textInstall.textContent = st.install_dir || "默认应用目录";
  } else {
    badgeInstall.className = 'pill-badge red';
    badgeInstall.textContent = '○ 未找到客户端';
    textInstall.textContent = "未自动检测到 Antigravity 安装路径";
  }

  // 2. 守护常驻服务
  const textDaemon = document.getElementById('text-daemon-status');
  const inputDaemonPort = document.getElementById('input-daemon-port');
  inputDaemonPort.value = cfg.lock_port || st.daemon_port || 49222;
  if (st.daemon_running) {
    textDaemon.innerHTML = `<span style="color: var(--success); font-weight:600;">● 正在运行</span> (监听端口: ${inputDaemonPort.value}, PID: ${st.daemon_pid || '活跃'})`;
  } else {
    textDaemon.innerHTML = `<span style="color: var(--text-muted);">○ 未运行</span> (点击右侧启动守护服务)`;
  }

  // 3. 自启动与托盘设置
  document.getElementById('switch-daemon-autostart').checked = !!st.daemon_autostart;
  document.getElementById('switch-app-autostart').checked = !!st.app_autostart;
  document.getElementById('switch-close-to-tray').checked = (cfg.close_to_tray !== false);

  // 4. 存储分析
  const textStorage = document.getElementById('text-storage-info');
  if (st.storage) {
    const cleanMb = st.storage.cleanable_mb || 0;
    const sessCnt = st.storage.session_count || 0;
    const sizeStr = cleanMb >= 1024 ? `${(cleanMb / 1024).toFixed(2)} GB` : `${cleanMb.toFixed(1)} MB`;
    textStorage.textContent = `预计可深度瘦身: ${sizeStr} (含 Chromium 死缓存与 ${sessCnt} 个历史会话中间流日志，不损对话历史)`;
  } else {
    textStorage.textContent = "暂无可深度清理的垃圾缓存";
  }

  // 5. 语言单选
  const currentLang = custom.language || 'zh-CN';
  const langRadio = document.querySelector(`input[name="radio-lang"][value="${currentLang}"]`);
  if (langRadio) langRadio.checked = true;

  // 6. 界面与性能复选框
  document.getElementById('switch-hide-ide').checked = (custom.hide_ide_buttons !== false);
  document.getElementById('switch-compact-ui').checked = !!custom.compact_ui_mode;
  document.getElementById('switch-show-quota').checked = (custom.show_quota_badge !== false);
  document.getElementById('select-quota-interval').value = custom.quota_refresh_interval || 60;

  document.getElementById('switch-gpu-accel').checked = (custom.enable_gpu_acceleration !== false);
  document.getElementById('switch-smooth-scrolling').checked = (custom.enable_smooth_scrolling !== false);
  document.getElementById('switch-unthrottle').checked = (custom.disable_background_throttling !== false);
  document.getElementById('switch-v8-mem').checked = (custom.expand_v8_memory !== false);
  document.getElementById('switch-disable-update').checked = (custom.disable_auto_update !== false);
  document.getElementById('switch-prune-skills').checked = !!custom.prune_guide_skills;
  document.getElementById('switch-telemetry').checked = (custom.disable_telemetry !== false);

  // 7. 专属网络代理
  document.getElementById('switch-proxy-enabled').checked = !!custom.proxy_enabled;
  document.getElementById('input-proxy-url').value = custom.proxy_url || "http://127.0.0.1:10808";

  // 8. 自愈与额度监控
  document.getElementById('switch-auto-retry').checked = (custom.auto_retry_on_error !== false);
  document.getElementById('select-max-retries').value = custom.max_retry_count || 3;
  document.getElementById('switch-notify-quota').checked = (custom.notify_on_quota_exhausted !== false);
  document.getElementById('switch-notify-max-failed').checked = (custom.notify_on_max_retry_failed !== false);

  // 9. 通知渠道
  const tg = channels.telegram || {};
  document.getElementById('switch-tg-enabled').checked = !!tg.enabled;
  document.getElementById('input-tg-token').value = tg.bot_token || "";
  document.getElementById('input-tg-chat').value = tg.chat_id || "";
  document.getElementById('input-tg-proxy').value = tg.proxy || "";

  const fs = channels.feishu || {};
  document.getElementById('switch-fs-enabled').checked = !!fs.enabled;
  document.getElementById('input-fs-url').value = fs.webhook_url || "";

  const wc = channels.wecom || {};
  document.getElementById('switch-wc-enabled').checked = !!wc.enabled;
  document.getElementById('input-wc-url').value = wc.webhook_url || "";

  // 10. 系统提示词与模板
  g_prompt_templates = pr.templates || [];
  const selectTpl = document.getElementById('select-prompt-template');
  selectTpl.innerHTML = "";
  g_prompt_templates.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.key;
    opt.textContent = t.name;
    selectTpl.appendChild(opt);
  });
  document.getElementById('textarea-prompt').value = pr.content || "";

  // 11. 日志终端
  const term = document.getElementById('terminal-logs');
  term.textContent = data.logs || "暂无日志记录";
  term.scrollTop = term.scrollHeight;
}

/**
 * 绑定所有交互事件
 */
function setupEvents() {
  // GitHub 外部链接
  document.getElementById('link-github').addEventListener('click', () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.open_external('https://github.com/akasls/Antigravity-Orbit');
    } else {
      window.open('https://github.com/akasls/Antigravity-Orbit', '_blank');
    }
  });

  // 守护服务启停
  document.getElementById('btn-start-daemon').addEventListener('click', async () => {
    const port = parseInt(document.getElementById('input-daemon-port').value, 10) || 49222;
    setLoading(true, "正在启动后台守护服务...");
    const res = await window.pywebview.api.control_daemon('start', port);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
    await refreshDaemonStatus();
  });

  document.getElementById('btn-stop-daemon').addEventListener('click', async () => {
    setLoading(true, "正在停止后台守护服务...");
    const res = await window.pywebview.api.control_daemon('stop');
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
    await refreshDaemonStatus();
  });

  // 开机自启动开关切换
  document.getElementById('switch-daemon-autostart').addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    const res = await window.pywebview.api.toggle_daemon_autostart(enabled);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  document.getElementById('switch-app-autostart').addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    const res = await window.pywebview.api.toggle_app_autostart(enabled);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  // 深度瘦身
  document.getElementById('btn-clean-storage').addEventListener('click', async () => {
    if (!confirm("即将清理 Chromium 静态渲染缓存、历史会话临时流日志并压缩整理数据库。\n\n此操作完全安全，不会删除您的任何对话记录、代码或配置。是否继续？")) {
      return;
    }
    setLoading(true, "正在进行安全深度瘦身与缓存清理...");
    const res = await window.pywebview.api.clean_storage();
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
    await loadInitialData();
  });

  // 提示词模板套用
  document.getElementById('btn-apply-template').addEventListener('click', () => {
    const selectTpl = document.getElementById('select-prompt-template');
    const key = selectTpl.value;
    const tpl = g_prompt_templates.find(t => t.key === key);
    if (!tpl) {
      showToast("未找到对应的模板", "error");
      return;
    }
    if (!confirm(`确定要将编辑区替换为【${tpl.name}】预设吗？\n\n您可以自由修改，点击右上角“保存系统提示词”才会正式生效。`)) {
      return;
    }
    document.getElementById('textarea-prompt').value = tpl.content;
    showToast(`已套用模板: ${tpl.desc}`, "info");
  });

  // 提示词重载 / 备份恢复 / 保存
  document.getElementById('btn-reload-prompt').addEventListener('click', async () => {
    const res = await window.pywebview.api.get_initial_data();
    if (res && res.prompt) {
      document.getElementById('textarea-prompt').value = res.prompt.content || "";
      showToast("已重新读取系统提示词", "info");
    }
  });

  document.getElementById('btn-restore-prompt-bak').addEventListener('click', async () => {
    if (!confirm("确定要从上一次的历史备份 AGENTS.md.bak 恢复系统提示词吗？")) return;
    setLoading(true, "正在恢复备份...");
    const res = await window.pywebview.api.restore_prompt_backup();
    setLoading(false);
    if (res.success && res.content) {
      document.getElementById('textarea-prompt').value = res.content;
    }
    showToast(res.message, res.success ? 'success' : 'error');
  });

  document.getElementById('btn-save-prompt').addEventListener('click', async () => {
    const content = document.getElementById('textarea-prompt').value.trim();
    setLoading(true, "正在保存系统提示词...");
    const res = await window.pywebview.api.save_system_prompt(content);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  // 通道即时测试
  document.getElementById('btn-test-tg').addEventListener('click', async () => {
    const params = {
      bot_token: document.getElementById('input-tg-token').value.trim(),
      chat_id: document.getElementById('input-tg-chat').value.trim(),
      proxy: document.getElementById('input-tg-proxy').value.trim(),
    };
    setLoading(true, "正在发送 Telegram 测试消息...");
    const res = await window.pywebview.api.test_notifier('telegram', params);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  document.getElementById('btn-test-fs').addEventListener('click', async () => {
    const params = {
      webhook_url: document.getElementById('input-fs-url').value.trim()
    };
    setLoading(true, "正在发送飞书测试消息...");
    const res = await window.pywebview.api.test_notifier('feishu', params);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  document.getElementById('btn-test-wc').addEventListener('click', async () => {
    const params = {
      webhook_url: document.getElementById('input-wc-url').value.trim()
    };
    setLoading(true, "正在发送企业微信测试消息...");
    const res = await window.pywebview.api.test_notifier('wecom', params);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  // 日志刷新 / 清空
  document.getElementById('btn-refresh-logs').addEventListener('click', async () => {
    const res = await window.pywebview.api.get_initial_data();
    const term = document.getElementById('terminal-logs');
    term.textContent = (res && res.logs) ? res.logs : "暂无日志记录";
    term.scrollTop = term.scrollHeight;
    showToast("运行日志已刷新", "info");
  });

  document.getElementById('btn-clear-logs').addEventListener('click', async () => {
    if (!confirm("确定要清空后台守护服务的历史运行日志吗？")) return;
    const res = await window.pywebview.api.clear_logs();
    document.getElementById('terminal-logs').textContent = "运行日志已清空";
    showToast(res.message, res.success ? 'success' : 'error');
  });

  // 底部核心三按钮
  document.getElementById('btn-restore-official').addEventListener('click', async () => {
    if (!confirm("确定要还原 Antigravity 官方原版英文界面并卸载汉化补丁吗？")) return;
    setLoading(true, "正在还原官方原版英文...");
    const res = await window.pywebview.api.restore_english();
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
    await loadInitialData();
  });

  document.getElementById('btn-restart-app').addEventListener('click', async () => {
    setLoading(true, "正在重启 Antigravity 客户端...");
    const res = await window.pywebview.api.restart_antigravity();
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
  });

  document.getElementById('btn-apply-all').addEventListener('click', async () => {
    const newConfig = gatherConfigFromUI();
    setLoading(true, "正在保存配置并应用补丁...");
    const res = await window.pywebview.api.save_and_apply(newConfig);
    setLoading(false);
    showToast(res.message, res.success ? 'success' : 'error');
    await loadInitialData();
  });
}

/**
 * 从页面提取完整配置字典
 */
function gatherConfigFromUI() {
  const langRadio = document.querySelector('input[name="radio-lang"]:checked');
  const lang = langRadio ? langRadio.value : 'zh-CN';

  return {
    close_to_tray: document.getElementById('switch-close-to-tray').checked,
    app_autostart: document.getElementById('switch-app-autostart').checked,
    lock_port: parseInt(document.getElementById('input-daemon-port').value, 10) || 49222,
    customization: {
      language: lang,
      hide_ide_buttons: document.getElementById('switch-hide-ide').checked,
      compact_ui_mode: document.getElementById('switch-compact-ui').checked,
      show_quota_badge: document.getElementById('switch-show-quota').checked,
      quota_refresh_interval: parseInt(document.getElementById('select-quota-interval').value, 10) || 60,
      enable_gpu_acceleration: document.getElementById('switch-gpu-accel').checked,
      enable_smooth_scrolling: document.getElementById('switch-smooth-scrolling').checked,
      disable_background_throttling: document.getElementById('switch-unthrottle').checked,
      expand_v8_memory: document.getElementById('switch-v8-mem').checked,
      disable_auto_update: document.getElementById('switch-disable-update').checked,
      prune_guide_skills: document.getElementById('switch-prune-skills').checked,
      disable_telemetry: document.getElementById('switch-telemetry').checked,
      proxy_enabled: document.getElementById('switch-proxy-enabled').checked,
      proxy_url: document.getElementById('input-proxy-url').value.trim(),
      auto_retry_on_error: document.getElementById('switch-auto-retry').checked,
      max_retry_count: parseInt(document.getElementById('select-max-retries').value, 10) || 3,
      notify_on_quota_exhausted: document.getElementById('switch-notify-quota').checked,
      notify_on_max_retry_failed: document.getElementById('switch-notify-max-failed').checked,
    },
    channels: {
      telegram: {
        enabled: document.getElementById('switch-tg-enabled').checked,
        bot_token: document.getElementById('input-tg-token').value.trim(),
        chat_id: document.getElementById('input-tg-chat').value.trim(),
        proxy: document.getElementById('input-tg-proxy').value.trim(),
      },
      feishu: {
        enabled: document.getElementById('switch-fs-enabled').checked,
        webhook_url: document.getElementById('input-fs-url').value.trim(),
      },
      wecom: {
        enabled: document.getElementById('switch-wc-enabled').checked,
        webhook_url: document.getElementById('input-wc-url').value.trim(),
      }
    }
  };
}

async function refreshDaemonStatus() {
  const res = await window.pywebview.api.get_initial_data();
  if (res && res.status) {
    const textDaemon = document.getElementById('text-daemon-status');
    const inputDaemonPort = document.getElementById('input-daemon-port');
    if (res.status.daemon_running) {
      textDaemon.innerHTML = `<span style="color: var(--success); font-weight:600;">● 正在运行</span> (监听端口: ${inputDaemonPort.value}, PID: ${res.status.daemon_pid || '活跃'})`;
    } else {
      textDaemon.innerHTML = `<span style="color: var(--text-muted);">○ 未运行</span> (点击右侧启动守护服务)`;
    }
  }
}

function setLoading(busy, msg) {
  const statusEl = document.getElementById('footer-status');
  if (msg) statusEl.textContent = msg;

  const btnApply = document.getElementById('btn-apply-all');
  const btnRestore = document.getElementById('btn-restore-official');
  const btnRestart = document.getElementById('btn-restart-app');

  btnApply.disabled = busy;
  btnRestore.disabled = busy;
  btnRestart.disabled = busy;
}

/**
 * 优雅浮动 Toast 消息通知 (非阻塞)
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  let iconSvg = '';
  if (type === 'success') {
    iconSvg = `<svg style="width: 16px; height: 16px; color: var(--success);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
  } else if (type === 'error') {
    iconSvg = `<svg style="width: 16px; height: 16px; color: var(--danger);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
  } else {
    iconSvg = `<svg style="width: 16px; height: 16px; color: var(--accent);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
  }

  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  // 触发动画
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // 3.2 秒后自动消失
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3200);
}
