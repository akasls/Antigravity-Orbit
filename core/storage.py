import os
import sys
import shutil
import sqlite3
import platform
from pathlib import Path
from typing import Dict, Any, Tuple

from core.config import GEMINI_DIR, BRAIN_DIR, DB_PATH

class StorageManager:
    """Antigravity 存储与垃圾缓存深度分析及清理管理器"""

    @staticmethod
    def get_electron_user_data_dir() -> Path:
        """获取 Electron 用户数据与 Chromium 缓存目录"""
        system = platform.system().lower()
        if system == "windows":
            return Path(os.environ.get("APPDATA", "")) / "antigravity"
        elif system == "darwin":
            return Path.home() / "Library" / "Application Support" / "antigravity"
        else:
            return Path.home() / ".config" / "antigravity"

    @classmethod
    def get_storage_breakdown(cls) -> Dict[str, Any]:
        """分析并返回 Antigravity 各项存储占用与可清理容量"""
        user_data = cls.get_electron_user_data_dir()

        # 1. Chromium 渲染死缓存目录
        cache_dirs = ["Cache", "Code Cache", "DawnWebGPUCache", "blob_storage", "GPUCache"]
        chromium_cache_bytes = 0
        if user_data.exists():
            for d_name in cache_dirs:
                target = user_data / d_name
                if target.exists() and target.is_dir():
                    try:
                        chromium_cache_bytes += sum(f.stat().st_size for f in target.glob("**/*") if f.is_file())
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

        # 3. 会话历史与临时中间日志 (brain 目录)
        brain_dir = BRAIN_DIR
        brain_total_bytes = 0
        brain_temp_bytes = 0
        session_count = 0
        if brain_dir.exists():
            for sess in brain_dir.iterdir():
                if sess.is_dir():
                    session_count += 1
                    try:
                        for f in sess.glob("**/*"):
                            if f.is_file():
                                sz = f.stat().st_size
                                brain_total_bytes += sz
                                # 临时任务日志或废弃脚本
                                if ".system_generated" in str(f) or "scratch" in str(f):
                                    brain_temp_bytes += sz
                    except Exception:
                        pass

        # 4. 数据库碎片预估
        db_size = 0
        if DB_PATH.exists():
            try:
                db_size = DB_PATH.stat().st_size
            except Exception:
                pass

        cleanable_bytes = chromium_cache_bytes + crashes_bytes + brain_temp_bytes

        return {
            "user_data_dir": str(user_data),
            "chromium_cache_bytes": chromium_cache_bytes,
            "crashes_bytes": crashes_bytes,
            "brain_temp_bytes": brain_temp_bytes,
            "brain_total_bytes": brain_total_bytes,
            "session_count": session_count,
            "db_size": db_size,
            "cleanable_bytes": cleanable_bytes,
            "cleanable_mb": cleanable_bytes / (1024 * 1024),
            "cleanable_gb": cleanable_bytes / (1024 * 1024 * 1024),
        }

    @classmethod
    def clean_storage(cls, clean_cache: bool = True, clean_temp_logs: bool = True, vacuum_db: bool = True) -> Tuple[int, Dict[str, Any]]:
        """
        执行安全深度清理：
        - clean_cache: 清空 Chromium 静态缓存 (重启后自动重新生成，不影响任何配置)
        - clean_temp_logs: 清理历史会话中的临时系统任务日志与崩溃记录 (不删对话本身)
        - vacuum_db: 整理 SQLite 碎片
        """
        freed_bytes = 0
        details = {}

        # 1. 清理 Chromium 缓存
        if clean_cache:
            user_data = cls.get_electron_user_data_dir()
            cache_dirs = ["Cache", "Code Cache", "DawnWebGPUCache", "blob_storage", "GPUCache"]
            cache_freed = 0
            if user_data.exists():
                for d_name in cache_dirs:
                    target = user_data / d_name
                    if target.exists() and target.is_dir():
                        for f in list(target.glob("**/*")):
                            if f.is_file():
                                try:
                                    sz = f.stat().st_size
                                    f.unlink()
                                    cache_freed += sz
                                except Exception:
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
                            f.unlink()
                            temp_freed += sz
                        except Exception:
                            pass

            if BRAIN_DIR.exists():
                for sess in BRAIN_DIR.iterdir():
                    if sess.is_dir():
                        # 清理 tasks 任务临时流日志
                        task_dir = sess / ".system_generated" / "tasks"
                        if task_dir.exists() and task_dir.is_dir():
                            for f in list(task_dir.glob("*.log")):
                                try:
                                    sz = f.stat().st_size
                                    f.unlink()
                                    temp_freed += sz
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
