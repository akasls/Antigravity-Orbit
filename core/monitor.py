import os
import time
import json
import glob
import sqlite3
import re
import urllib.parse
from pathlib import Path

from .config import BRAIN_DIR, DB_PATH, load_config, load_state, save_state
from .utils import Logger, SingleInstanceLock
from notifiers import get_active_notifiers

# 严格配额熔断特征正则（杜绝将普通代码变量名 quota 或随机哈希中的数字 429 误判为报错）
QUOTA_ERROR_REGEX = re.compile(
    r'(?:resource_?exhausted|quota\s*(?:exceeded|exhausted|limit)|rate\s*limit\s*(?:reached|exceeded)|exceeded\s*your\s*(?:current\s*)?quota|\b429\b.*(?:too\s*many|rate|request)|额度.*(?:耗尽|用完|用尽|不足)|配额.*(?:耗尽|用完|超限))',
    re.IGNORECASE
)

class AntigravityMonitor:
    def __init__(self):
        self.config = load_config()
        self.state = load_state()
        self.last_quota_alerts: dict[str, float] = {}

    def get_conversation_info(self, conv_id: str) -> dict | None:
        if not DB_PATH.exists():
            return None
        try:
            # 使用只读模式连接 SQLite，避免与正在写入的反重力产生文件锁冲突
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2.0)
            cur = con.cursor()
            cur.execute(
                "SELECT title, status, not_fully_idle, workspace_uris FROM conversation_summaries WHERE conversation_id = ?;",
                (conv_id,)
            )
            row = cur.fetchone()
            con.close()
            if row:
                title, status, not_fully_idle, workspace_uris = row
                proj_name = ""
                if workspace_uris:
                    try:
                        uris = json.loads(workspace_uris)
                        if uris and isinstance(uris, list):
                            raw_uri = uris[0]
                            decoded = urllib.parse.unquote(raw_uri)
                            clean = decoded.replace("file:///", "").replace("/", os.sep)
                            proj_name = os.path.basename(os.path.normpath(clean))
                    except Exception:
                        pass
                return {
                    "title": title or "",
                    "status": status or "",
                    "is_idle": (status == "CASCADE_RUN_STATUS_IDLE" and not bool(not_fully_idle)),
                    "project_name": proj_name
                }
        except Exception as e:
            Logger.log(f"读取数据库异常 ({conv_id[:8]}): {e}", echo=False)
        return None

    def initialize_state_if_needed(self, pattern: str):
        """首次运行时记录现存所有会话的最大 step，避免历史消息刷屏"""
        if len(self.state.get("last_seen_steps", {})) == 0:
            Logger.log("首次启动：正在同步现有会话进度，避免历史通知轰炸...")
            count = 0
            for p in glob.glob(pattern):
                parts = Path(p).parts
                if len(parts) >= 4:
                    conv_id = parts[-4]
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        if lines:
                            last_obj = json.loads(lines[-1].strip())
                            if "step_index" in last_obj:
                                self.state["last_seen_steps"][conv_id] = last_obj["step_index"]
                                count += 1
                    except Exception:
                        pass
            save_state(self.state)
            Logger.log(f"初始化完毕，已记录 {count} 个历史会话的基准进度。")

    def dispatch_notification(self, proj_display: str, status: str, summary: str):
        self.config = load_config()
        active_notifiers = get_active_notifiers(self.config)
        if not active_notifiers:
            Logger.log(f"未配置或未开启任何通知渠道，跳过推送 ({status})")
            return
        Logger.log(f"正在向 {len(active_notifiers)} 个渠道分发通知: 工程={proj_display}, 状态={status}")
        for notifier in active_notifiers:
            try:
                notifier.send(proj_display, status, summary)
            except Exception as err:
                Logger.log(f"[{notifier.name}] 推送发生异常: {err}")

    def run_loop(self):
        lock_port = self.config.get("lock_port", 49222)
        lock = SingleInstanceLock(lock_port, notify_callback=self.dispatch_notification)
        if not lock.acquire():
            Logger.log(f"服务已在运行中 (端口 {lock_port} 被占用)，当前进程退出。")
            return

        pid_file = Path(__file__).resolve().parent.parent / ".daemon.pid"
        try:
            pid_file.write_text(str(os.getpid()), encoding="utf-8")
        except Exception:
            pass

        Logger.log(f"Antigravity 监控引擎已启动 (监听端口: {lock_port})，正在监听任务事件...")

        pattern = str(BRAIN_DIR / "*" / ".system_generated" / "logs" / "transcript.jsonl")
        self.initialize_state_if_needed(pattern)

        try:
            while True:
                # 重新载入最新配置（支持热更新）
                self.config = load_config()
                if not self.config.get("enabled", True):
                    time.sleep(self.config.get("scan_interval", 3.0))
                    continue

                active_notifiers = get_active_notifiers(self.config)
                if not active_notifiers:
                    time.sleep(self.config.get("scan_interval", 3.0))
                    continue

                now = time.time()
                for p in glob.glob(pattern):
                    try:
                        # 只扫描 24 小时内活跃的文件
                        if now - os.path.getmtime(p) > 86400:
                            continue

                        parts = Path(p).parts
                        if len(parts) < 4:
                            continue
                        conv_id = parts[-4]
                        last_seen = self.state["last_seen_steps"].get(conv_id, -1)

                        with open(p, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        if not lines:
                            continue

                        # 获取所有比 last_seen 新的行
                        new_entries = []
                        for line in reversed(lines):
                            try:
                                obj = json.loads(line.strip())
                                s_idx = obj.get("step_index")
                                if s_idx is not None and s_idx > last_seen:
                                    new_entries.append(obj)
                                else:
                                    break
                            except Exception:
                                continue

                        if not new_entries:
                            continue

                        max_step = new_entries[0].get("step_index", last_seen)

                        # 寻找模型最终的文本回复
                        target_response = None
                        for entry in new_entries:
                            src = entry.get("source")
                            mtype = entry.get("type")
                            calls = entry.get("tool_calls", [])
                            cnt = entry.get("content", "").strip()

                            if src == "MODEL" and mtype == "PLANNER_RESPONSE" and len(calls) == 0 and cnt:
                                target_response = cnt
                                break

                        if target_response:
                            # 核心防误发机制：检查会话是否彻底进入 IDLE 状态
                            info = self.get_conversation_info(conv_id)
                            if info and not info["is_idle"]:
                                # 仍有后台任务在跑，等待完全结束
                                continue

                            # 格式化工程名
                            if info:
                                p_name = info.get("project_name")
                                p_title = info.get("title")
                                if p_name and p_title and p_name != p_title:
                                    proj_display = f"{p_name} ({p_title})"
                                else:
                                    proj_display = p_name or p_title or "默认工程"
                            else:
                                proj_display = "默认工程"

                            Logger.log(f"检测到任务完成！会话={conv_id[:8]}, 工程={proj_display}, Step={max_step}")

                            self.dispatch_notification(proj_display, "正常完成", target_response)

                            # 更新状态
                            self.state["last_seen_steps"][conv_id] = max_step
                            save_state(self.state)
                        else:
                            # 核心机制：检查会话当前状态
                            info = self.get_conversation_info(conv_id)
                            # 如果会话仍处于活跃执行中（正在调用工具、生成代码等），切勿打扰，等待完全结束或中断
                            if info and not info["is_idle"]:
                                continue

                            # 会话已结束/空闲，但没有最终回复 target_response，此时严格检查是否发生了系统级报错或额度熔断
                            # 1. 过滤：只检查真正的系统报错步骤 (status == 'ERROR' 或 type == 'ERROR_MESSAGE')
                            # 严禁将正常的工具调用结果、代码阅读输出 (status == 'DONE' / 'SUCCESS') 误判为报错
                            error_entries = [
                                e for e in new_entries
                                if e.get("status") == "ERROR" or e.get("type") == "ERROR_MESSAGE"
                            ]

                            if error_entries:
                                is_quota = False
                                error_text = ""
                                for entry in error_entries:
                                    cnt = (entry.get("content") or "")
                                    if QUOTA_ERROR_REGEX.search(cnt):
                                        is_quota = True
                                        error_text = cnt
                                        break
                                    elif not error_text:
                                        error_text = cnt

                                p_name = (info.get("project_name") or info.get("title") or "默认工程") if info else "默认工程"
                                now_ts = time.time()

                                if is_quota and self.config.get("notify_on_quota_exhausted", True):
                                    # 10 分钟告警冷却防连续轰炸
                                    if now_ts - self.last_quota_alerts.get(conv_id, 0) >= 600:
                                        self.last_quota_alerts[conv_id] = now_ts
                                        Logger.log(f"检测到额度耗尽！会话={conv_id[:8]}, 工程={p_name}, Step={max_step}")
                                        self.dispatch_notification(p_name, "任务中断：额度已耗尽", error_text or "模型限额已达上限，任务暂停执行。")
                                elif error_text and self.config.get("notify_on_error", False):
                                    Logger.log(f"检测到任务执行异常！会话={conv_id[:8]}, 工程={p_name}, Step={max_step}")
                                    self.dispatch_notification(p_name, "任务中断：执行异常", error_text[:300])

                            # 推进该会话已检查的步数，避免重复分析已处理步骤
                            self.state["last_seen_steps"][conv_id] = max_step
                            save_state(self.state)

                    except Exception as e:
                        Logger.log(f"扫描异常: {e}", echo=False)

                time.sleep(self.config.get("scan_interval", 3.0))
        finally:
            try:
                if pid_file.exists():
                    pid_file.unlink()
            except Exception:
                pass
            lock.release()
