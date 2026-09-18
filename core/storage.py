import os
import sys
import shutil
import sqlite3
import platform
from pathlib import Path
from typing import Dict, Any, Tuple, List

from core.config import GEMINI_DIR, BRAIN_DIR, DB_PATH


def format_bytes(b: int) -> str:
    """人性化格式化字节大小"""
    if b >= 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024 * 1024):.2f} GB"
    elif b >= 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    elif b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b} B"


class StorageManager:
    """Antigravity 存储与垃圾缓存深度分析及清理管理器"""

    @staticmethod
    def get_electron_user_data_dirs() -> List[Path]:
        """获取全部可能的 Electron 用户数据与 Chromium 缓存目录 (兼容多版本与大小写)"""
        system = platform.system().lower()
        dirs = []
        if system == "windows":
            appdata = os.environ.get("APPDATA", "")
            localappdata = os.environ.get("LOCALAPPDATA", "")
            candidates = [
                Path(appdata) / "Antigravity",
                Path(appdata) / "antigravity",
                Path(localappdata) / "antigravity",
            ]
            for c in candidates:
                if c.exists() and c.is_dir() and c not in dirs:
                    dirs.append(c)
        elif system == "darwin":
            c = Path.home() / "Library" / "Application Support" / "antigravity"
            if c.exists():
                dirs.append(c)
        else:
            c = Path.home() / ".config" / "antigravity"
            if c.exists():
                dirs.append(c)
        return dirs

    @classmethod
    def get_storage_breakdown(cls) -> Dict[str, Any]:
        """分析并返回 Antigravity 各项存储占用与可清理容量"""
        user_data_dirs = cls.get_electron_user_data_dirs()

        # 1. Chromium 渲染死缓存目录
        cache_names = ["Cache", "Code Cache", "DawnWebGPUCache", "DawnGraphiteCache", "blob_storage", "GPUCache"]
        chromium_cache_bytes = 0
        for udir in user_data_dirs:
            for d_name in cache_names:
                target = udir / d_name
                if target.exists() and target.is_dir():
                    try:
                        for f in target.glob("**/*"):
                            try:
                                if f.is_file():
                                    chromium_cache_bytes += f.stat().st_size
                            except Exception:
                                pass
                    except Exception:
                        pass

        # 2. 崩溃日志
        crashes_dir = GEMINI_DIR / "crashes"
        crashes_bytes = 0
        if crashes_dir.exists():
            try:
                crashes_bytes += sum(f.stat().st_size for f in crashes_dir.glob("**/*") if f.is_file())
            except Exception:
                pass

        # 3. 会话历史中的临时任务日志与废弃临时流
        brain_dir = BRAIN_DIR
        brain_total_bytes = 0
        brain_temp_bytes = 0
        session_count = 0
        if brain_dir.exists():
            try:
                for sess in brain_dir.iterdir():
                    if sess.is_dir():
                        session_count += 1
                        # 仅统计临时 task 日志与 scratch 垃圾
                        tasks_dir = sess / ".system_generated" / "tasks"
                        if tasks_dir.exists() and tasks_dir.is_dir():
                            brain_temp_bytes += sum(f.stat().st_size for f in tasks_dir.glob("*.log") if f.is_file())
                        scratch_dir = sess / "scratch"
                        if scratch_dir.exists() and scratch_dir.is_dir():
                            brain_temp_bytes += sum(f.stat().st_size for f in scratch_dir.glob("*") if f.is_file())
            except Exception:
                pass

        # 4. 数据库体积
        db_size = 0
        if DB_PATH.exists():
            try:
                db_size = DB_PATH.stat().st_size
            except Exception:
                pass

        cleanable_bytes = chromium_cache_bytes + crashes_bytes + brain_temp_bytes

        return {
            "chromium_cache_bytes": chromium_cache_bytes,
            "chromium_cache_str": format_bytes(chromium_cache_bytes),
            "crashes_bytes": crashes_bytes,
            "crashes_str": format_bytes(crashes_bytes),
            "brain_temp_bytes": brain_temp_bytes,
            "brain_temp_str": format_bytes(brain_temp_bytes),
            "session_count": session_count,
            "db_size": db_size,
            "db_size_str": format_bytes(db_size),
            "cleanable_bytes": cleanable_bytes,
            "cleanable_total_bytes": cleanable_bytes,
            "cleanable_mb": cleanable_bytes / (1024 * 1024),
            "cleanable_total_str": format_bytes(cleanable_bytes),
        }

    @classmethod
    def clean_storage(cls, clean_cache: bool = True, clean_temp_logs: bool = True, vacuum_db: bool = True) -> Tuple[int, Dict[str, Any]]:
        """
        执行安全深度清理：
        - clean_cache: 清空 Chromium 静态缓存 (重启后自动重新生成，不影响任何配置)
        - clean_temp_logs: 清理历史会话中的临时任务流日志与崩溃记录 (不删对话本体)
        - vacuum_db: 整理 SQLite 碎片
        """
        freed_bytes = 0
        details = {}

        # 1. 清理 Chromium 缓存
        if clean_cache:
            cache_names = ["Cache", "Code Cache", "DawnWebGPUCache", "DawnGraphiteCache", "blob_storage", "GPUCache"]
            cache_freed = 0
            for udir in cls.get_electron_user_data_dirs():
                for d_name in cache_names:
                    target = udir / d_name
                    if target.exists() and target.is_dir():
                        for f in list(target.glob("**/*")):
                            if f.is_file():
                                try:
                                    sz = f.stat().st_size
                                    f.unlink(missing_ok=True)
                                    cache_freed += sz
                                except Exception:
                                    # 忽略正在运行中被 Windows 进程锁定的个别文件
                                    pass
            freed_bytes += cache_freed
            details["chromium_cache_freed"] = cache_freed

        # 2. 清理临时日志与崩溃转储
        if clean_temp_logs:
            temp_freed = 0
            crashes_dir = GEMINI_DIR / "crashes"
            if crashes_dir.exists():
                for f in list(crashes_dir.glob("**/*")):
                    if f.is_file():
                        try:
                            sz = f.stat().st_size
                            f.unlink(missing_ok=True)
                            temp_freed += sz
                        except Exception:
                            pass

            if BRAIN_DIR.exists():
                try:
                    for sess in BRAIN_DIR.iterdir():
                        if sess.is_dir():
                            task_dir = sess / ".system_generated" / "tasks"
                            if task_dir.exists() and task_dir.is_dir():
                                for f in list(task_dir.glob("*.log")):
                                    try:
                                        sz = f.stat().st_size
                                        f.unlink(missing_ok=True)
                                        temp_freed += sz
                                    except Exception:
                                        pass
                            scratch_dir = sess / "scratch"
                            if scratch_dir.exists() and scratch_dir.is_dir():
                                for f in list(scratch_dir.glob("*")):
                                    if f.is_file():
                                        try:
                                            sz = f.stat().st_size
                                            f.unlink(missing_ok=True)
                                            temp_freed += sz
                                        except Exception:
                                            pass
                except Exception:
                    pass

            freed_bytes += temp_freed
            details["temp_logs_freed"] = temp_freed

        # 3. 整理 SQLite 碎片 (VACUUM)
        if vacuum_db and DB_PATH.exists():
            try:
                before_sz = DB_PATH.stat().st_size
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("VACUUM;")
                conn.close()
                after_sz = DB_PATH.stat().st_size
                db_freed = max(0, before_sz - after_sz)
                freed_bytes += db_freed
                details["db_vacuum_freed"] = db_freed
            except Exception as e:
                details["db_vacuum_error"] = str(e)

        return freed_bytes, details
