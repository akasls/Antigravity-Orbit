import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.config import RESOURCE_DIR, CONFIG_FILE

# 项目静态资源目录与本地化目录
LOCALIZATION_DIR = RESOURCE_DIR / "localization"
ENGINE_SCRIPT = LOCALIZATION_DIR / "engine.js"

class LocalizationManager:
    """Antigravity 界面汉化与本地化管理核心类"""

    @staticmethod
    def _run_subp(cmd, cwd=None, capture_output=True, timeout=None):
        """跨平台执行子进程，Windows 下强力抑制黑控制台窗口弹出"""
        kwargs = {"cwd": str(cwd) if cwd else None}
        if timeout:
            kwargs["timeout"] = timeout
        if capture_output:
            kwargs["capture_output"] = True
            kwargs["text"] = True
            kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = startupinfo
        return subprocess.run(cmd, **kwargs)

    @classmethod
    def check_node_environment(cls, fast: bool = True) -> Tuple[bool, str]:
        """检测系统是否存在 Node.js 环境 (fast=True 仅探测 PATH，0毫秒无开销)"""
        node_exe = shutil.which("node")
        if not node_exe:
            return False, "未在系统中检测到 Node.js 环境"
        if fast:
            return True, "已就绪"
        try:
            res = cls._run_subp([node_exe, "-v"], capture_output=True, timeout=5)
            version = (res.stdout or "").strip()
            return True, version
        except Exception as e:
            return False, f"检测 Node.js 异常: {e}"

    @staticmethod
    def is_asar_patched(asar_path: Path) -> bool:
        """直接检测 app.asar 二进制内容中是否包含 Orbit 注入签名 (耗时 ~1.5ms，100% 精准识别反重力自动更新覆盖)"""
        try:
            if not asar_path or not asar_path.exists():
                return False
            data = asar_path.read_bytes()
            return (
                b"ANTIGRAVITY_LOCALIZATION_START" in data
                or b"ANTIGRAVITY_DYNAMIC_PROXY_START" in data
                or b"ANTIGRAVITY_OPTIMIZATION_START" in data
            )
        except Exception:
            return False

    @classmethod
    def get_status(cls, install_dir: Optional[str] = None, fast: bool = True) -> Dict[str, Any]:
        """获取 Antigravity 客户端及其汉化状态 (默认极速秒级纯 Python 检测)"""
        node_ok, node_ver = cls.check_node_environment(fast=fast)

        status: Dict[str, Any] = {
            "installed": False,
            "install_dir": "",
            "resources_dir": "",
            "is_v2": False,
            "is_localized": False,
            "asar_patched": False,
            "lang": None,
            "has_backup": False,
            "node_available": node_ok,
            "node_version": node_ver if node_ok else None,
        }

        # 快速纯 Python 检测 (毫秒级响应，无子进程阻塞)
        found_dir = cls._fallback_detect_dir(install_dir)
        if found_dir and Path(found_dir).exists():
            status["installed"] = True
            status["install_dir"] = str(found_dir)

            res_dir = Path(found_dir) / "resources"
            if not res_dir.exists():
                res_dir = Path(found_dir) / "Contents" / "Resources"
            if not res_dir.exists():
                res_dir = Path(found_dir)

            status["resources_dir"] = str(res_dir)
            asar = res_dir / "app.asar"
            asar_bak = res_dir / "app.asar.bak"
            meta_file = res_dir / ".localization_info.json"

            status["is_v2"] = asar.exists()
            status["has_backup"] = asar_bak.exists()
            asar_patched = cls.is_asar_patched(asar)
            status["asar_patched"] = asar_patched

            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        status["is_localized"] = bool(meta.get("localized", False)) and asar_patched
                        status["lang"] = meta.get("lang")
                except Exception:
                    pass
            elif asar_patched:
                status["is_localized"] = True
                status["lang"] = "zh-CN"

            if fast:
                return status

        # 若 fast=False，才通过 node engine.js 深入检测
        if not fast and node_ok and ENGINE_SCRIPT.exists():
            cmd = ["node", str(ENGINE_SCRIPT), "--status", "--json"]
            if CONFIG_FILE.exists():
                cmd.extend(["--config-file", str(CONFIG_FILE)])
            if install_dir:
                cmd.extend(["--install-dir", install_dir])
            try:
                res = cls._run_subp(cmd, capture_output=True, timeout=10, cwd=str(RESOURCE_DIR))
                if res.returncode == 0:
                    data = json.loads(res.stdout.strip())
                    status["installed"] = data.get("installed", False)
                    status["install_dir"] = data.get("installDir", "")
                    status["resources_dir"] = data.get("resourcesDir", "")
                    status["is_v2"] = data.get("isV2", False)
                    status["is_localized"] = data.get("isLocalized", False)
                    status["lang"] = data.get("lang")
                    status["has_backup"] = data.get("hasBackup", False)
                    return status
            except Exception:
                pass

        return status

    @classmethod
    def install(
        cls,
        tw: bool = False,
        en: bool = False,
        install_dir: Optional[str] = None,
        no_kill: bool = True,
        stream_output: bool = True
    ) -> Tuple[bool, str]:
        """安装或更新汉化包与优化配置 (强力抑制黑窗口)"""
        node_ok, node_msg = cls.check_node_environment()
        if not node_ok:
            return False, f"无法执行部署: {node_msg}。\n请先安装 Node.js (https://nodejs.org) 并配置 PATH。"

        if not ENGINE_SCRIPT.exists():
            return False, f"未找到核心汉化引擎脚本: {ENGINE_SCRIPT}"

        cmd = ["node", str(ENGINE_SCRIPT)]
        if tw:
            cmd.append("--tw")
        elif en:
            cmd.append("--en")
        from core.config import find_active_config_file
        active_cfg = find_active_config_file()
        if active_cfg.exists():
            cmd.extend(["--config-file", str(active_cfg)])
        elif CONFIG_FILE.exists():
            cmd.extend(["--config-file", str(CONFIG_FILE)])
        if install_dir:
            cmd.extend(["--install-dir", install_dir])
        if no_kill:
            cmd.append("--no-kill")

        try:
            res = cls._run_subp(cmd, cwd=str(RESOURCE_DIR), capture_output=True)
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            return (res.returncode == 0, output.strip() if output.strip() else ("部署成功" if res.returncode == 0 else "部署失败"))
        except Exception as e:
            return False, f"执行汉化引擎异常: {e}"

    @classmethod
    def restore(
        cls,
        install_dir: Optional[str] = None,
        no_kill: bool = True,
        stream_output: bool = True
    ) -> Tuple[bool, str]:
        """卸载汉化，恢复官方原版英文 (强力抑制黑窗口)"""
        node_ok, node_msg = cls.check_node_environment()
        if not node_ok:
            return False, f"无法还原官方英文: {node_msg}。"

        if not ENGINE_SCRIPT.exists():
            return False, f"未找到核心汉化引擎脚本: {ENGINE_SCRIPT}"

        cmd = ["node", str(ENGINE_SCRIPT), "--restore"]
        if install_dir:
            cmd.extend(["--install-dir", install_dir])
        if no_kill:
            cmd.append("--no-kill")

        try:
            res = cls._run_subp(cmd, cwd=str(RESOURCE_DIR), capture_output=True)
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            return (res.returncode == 0, "官方原版英文已成功恢复！" if res.returncode == 0 else f"恢复失败: {output.strip()}")
        except Exception as e:
            return False, f"执行还原操作异常: {e}"

    @classmethod
    def is_running(cls) -> bool:
        """检查 Antigravity 客户端是否正在运行"""
        try:
            if sys.platform == "win32":
                res = cls._run_subp(["tasklist", "/fi", "imagename eq Antigravity.exe", "/nh"], capture_output=True)
                return "antigravity.exe" in (res.stdout or "").lower()
            elif sys.platform == "darwin":
                res = cls._run_subp(["pgrep", "-f", "Antigravity"], capture_output=True)
                return res.returncode == 0
        except Exception:
            pass
        return False

    @classmethod
    def kill_running_antigravity(cls) -> bool:
        """安全彻底终止运行中的 Antigravity 客户端及其所有渲染/GPU子进程"""
        try:
            if sys.platform == "win32":
                cls._run_subp(["taskkill", "/F", "/T", "/IM", "Antigravity.exe"], capture_output=True)
                # 轮询等待所有进程完全退出，彻底释放文件锁与端口
                for _ in range(20):
                    if not cls.is_running():
                        break
                    import time
                    time.sleep(0.15)
            elif sys.platform == "darwin":
                cls._run_subp(["pkill", "-f", "Antigravity"], capture_output=True)
                for _ in range(20):
                    if not cls.is_running():
                        break
                    import time
                    time.sleep(0.15)
            return True
        except Exception:
            return False

    @classmethod
    def is_any_task_running(cls) -> bool:
        """
        探测当前 Antigravity 客户端是否有长任务/智能体正在活跃执行中。
        通过只读模式查询 conversation_summaries.db，若存在 RUNNING 状态或未完全空闲的会话，返回 True。
        """
        try:
            from core.config import DB_PATH
            if not DB_PATH.exists():
                return False
            import sqlite3
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=1.5)
            cur = con.cursor()
            cur.execute(
                "SELECT 1 FROM conversation_summaries WHERE status = 'CASCADE_RUN_STATUS_RUNNING' OR not_fully_idle = 1 LIMIT 1;"
            )
            row = cur.fetchone()
            con.close()
            return bool(row)
        except Exception:
            return False

    @classmethod
    def is_task_running_for_conv(cls, conv_id: str) -> bool:
        """检查指定会话是否正在运行长任务"""
        try:
            from core.config import DB_PATH
            if not DB_PATH.exists():
                return False
            import sqlite3
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=1.5)
            cur = con.cursor()
            cur.execute(
                "SELECT 1 FROM conversation_summaries WHERE conversation_id = ? AND (status = 'CASCADE_RUN_STATUS_RUNNING' OR not_fully_idle = 1) LIMIT 1;",
                (conv_id,)
            )
            row = cur.fetchone()
            con.close()
            return bool(row)
        except Exception:
            return False

    _ls_patch_cache: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    _in_memory_reload_lock = None

    @classmethod
    def _get_reload_lock(cls):
        if cls._in_memory_reload_lock is None:
            import threading
            cls._in_memory_reload_lock = threading.Lock()
        return cls._in_memory_reload_lock

    @classmethod
    def _resolve_ls_hotreload_patches(cls, exe_path: Path) -> Optional[Dict[str, Any]]:
        """
        动态解析 language_server.exe 的 Go 1.20+ pclntab 符号表，
        定位 (*AuthClient).Logout 与 (*Server).AuthLogout 的热重载补丁偏移点。
        结果按 (exe_path, mtime_ns, size) 缓存，首次耗时 ~20ms，后续 0ms。
        """
        try:
            import struct
            import re

            st = exe_path.stat()
            cache_key = (str(exe_path), st.st_mtime_ns, st.st_size)
            if cache_key in cls._ls_patch_cache:
                return cls._ls_patch_cache[cache_key]

            data = exe_path.read_bytes()
            e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
            size_opt_hdr = struct.unpack_from("<H", data, e_lfanew + 20)[0]
            sec_off = e_lfanew + 24 + size_opt_hdr
            _, _, text_rva, _, text_raw_ptr = struct.unpack_from("<8sIIII", data, sec_off)

            pcln_pos = None
            nfunc = 0
            text_start = 0
            funcname_offset = 0
            pcln_offset = 0
            for m in re.finditer(b"\xf1\xff\xff\xff\x00\x00\x01\x08", data):
                pos = m.start()
                nf, _, ts, fn_off, _, _, _, pc_off = struct.unpack_from("<QQQQQQQQ", data, pos + 8)
                if 1000 < nf < 500000:
                    pcln_pos = pos
                    nfunc = nf
                    text_start = ts
                    funcname_offset = fn_off
                    pcln_offset = pc_off
                    break

            if pcln_pos is None:
                return None

            ftab_off = pcln_pos + pcln_offset
            funcnames_base = pcln_pos + funcname_offset

            target_suffixes = {
                "authclient.(*AuthClient).Logout": "logout",
                "authclient.(*AuthClient).tryRestoreToken": "restore",
                "codeassistclient.(*AntigravityHubAuthProvider).SetWIFProvider": "setwif",
                "authclient.(*AuthClient).clearEnterpriseMetadata": "clearent",
                "language_server.(*Server).AuthLogout": "authlogout",
                "language_server.(*Server).stopRemoteControlConnectionAfterLogout": "stopremote",
            }
            found_funcs: Dict[str, Tuple[int, int]] = {}

            for i in range(nfunc):
                entry_rel, func_off = struct.unpack_from("<II", data, ftab_off + i * 8)
                _, name_off = struct.unpack_from("<Ii", data, ftab_off + func_off)
                end_str = data.find(b"\x00", funcnames_base + name_off)
                fname = data[funcnames_base + name_off:end_str].decode("utf-8", errors="ignore")
                for suffix, key in target_suffixes.items():
                    if fname.endswith(suffix):
                        next_entry_rel, _ = struct.unpack_from("<II", data, ftab_off + (i + 1) * 8)
                        va = text_start + entry_rel
                        sz = next_entry_rel - entry_rel
                        found_funcs[key] = (va, sz)
                        break
                if len(found_funcs) == len(target_suffixes):
                    break

            if len(found_funcs) < len(target_suffixes):
                return None

            logout_va, logout_sz = found_funcs["logout"]
            restore_va, _ = found_funcs["restore"]
            setwif_va, _ = found_funcs["setwif"]
            clearent_va, _ = found_funcs["clearent"]
            authlogout_va, authlogout_sz = found_funcs["authlogout"]
            stopremote_va, _ = found_funcs["stopremote"]

            logout_foff = text_raw_ptr + (logout_va - text_start)
            logout_bytes = data[logout_foff:logout_foff + logout_sz]

            setwif_patch = None
            clearent_patch = None
            cleartoken_patch = None

            for off in range(len(logout_bytes) - 5):
                if logout_bytes[off] == 0xE8:
                    rel = struct.unpack_from("<i", logout_bytes, off + 1)[0]
                    call_va = logout_va + off
                    dest_va = call_va + 5 + rel
                    if dest_va == setwif_va and setwif_patch is None:
                        setwif_patch = (call_va, logout_bytes[off:off + 5], b"\x90\x90\x90\x90\x90")
                    elif dest_va == clearent_va and clearent_patch is None:
                        new_rel = restore_va - (call_va + 5)
                        clearent_patch = (call_va, logout_bytes[off:off + 5], b"\xe8" + struct.pack("<i", new_rel))

            idx_clear = logout_bytes.find(b"\x48\x8b\x4a\x28\xff\xd1")
            if idx_clear != -1:
                call_rcx_va = logout_va + idx_clear + 4
                cleartoken_patch = (call_rcx_va, b"\xff\xd1", b"\x31\xc0")

            authlogout_foff = text_raw_ptr + (authlogout_va - text_start)
            authlogout_bytes = data[authlogout_foff:authlogout_foff + authlogout_sz]
            stopremote_patch = None
            for off in range(len(authlogout_bytes) - 5):
                if authlogout_bytes[off] == 0xE8:
                    rel = struct.unpack_from("<i", authlogout_bytes, off + 1)[0]
                    call_va = authlogout_va + off
                    dest_va = call_va + 5 + rel
                    if dest_va == stopremote_va:
                        stopremote_patch = (call_va, authlogout_bytes[off:off + 5], b"\x90\x90\x90\x90\x90")
                        break

            if not (setwif_patch and clearent_patch and cleartoken_patch and stopremote_patch):
                return None

            result = {
                "text_rva": text_rva,
                "patches": [setwif_patch, clearent_patch, cleartoken_patch, stopremote_patch],
            }
            cls._ls_patch_cache[cache_key] = result
            return result
        except Exception:
            return None

    @classmethod
    def get_live_language_server_info(cls) -> Optional[Dict[str, Any]]:
        """获取正在运行的 language_server.exe 的 PID、路径、HTTPS 端口与 CSRF Token"""
        if sys.platform != "win32":
            return None
        try:
            import ssl
            import urllib.request
            import psutil

            ls_pid = None
            ls_exe = None
            ls_csrf = None

            for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
                name = (p.info.get("name") or "").lower()
                if "language_server" in name:
                    ls_pid = p.info["pid"]
                    ls_exe = p.info.get("exe")
                    cmd = p.info.get("cmdline") or []
                    for i, arg in enumerate(cmd):
                        if arg == "--csrf_token" and i + 1 < len(cmd):
                            ls_csrf = cmd[i + 1]
                            break
                    break

            if not ls_pid or not ls_csrf:
                return None

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))
            for conn in psutil.net_connections(kind="inet"):
                if conn.pid == ls_pid and conn.status == "LISTEN":
                    port = conn.laddr.port
                    req = urllib.request.Request(
                        f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus",
                        data=b"{}",
                        headers={"Content-Type": "application/json", "x-codeium-csrf-token": ls_csrf},
                        method="POST",
                    )
                    try:
                        with opener.open(req, timeout=1.5) as resp:
                            body = json.loads(resp.read().decode("utf-8", errors="ignore"))
                            if isinstance(body, dict) and "userStatus" in body:
                                return {
                                    "pid": ls_pid,
                                    "exe": Path(ls_exe) if ls_exe else None,
                                    "port": port,
                                    "csrf": ls_csrf,
                                    "user_status": body["userStatus"],
                                }
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    @classmethod
    def get_live_active_account_email(cls) -> Optional[str]:
        """实时查询反重力后台服务当前生效的账号邮箱"""
        info = cls.get_live_language_server_info()
        if info and isinstance(info.get("user_status"), dict):
            return info["user_status"].get("email") or None
        return None

    @classmethod
    def _cdp_eval_js(cls, ws_url: str, expression: str, timeout: float = 4.0) -> Any:
        """在指定 CDP WebSocket 目标中执行 JS 表达式 (优先使用 websocket-client，内置原生 socket 兜底)"""
        payload = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        })
        try:
            import websocket
            ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
            try:
                ws.send(payload)
                resp = json.loads(ws.recv())
                return resp.get("result", {}).get("result", {}).get("value")
            finally:
                ws.close()
        except Exception:
            pass

        # 纯 Python 标准库 socket WebSocket 客户端兜底 (兼容打包环境无 websocket-client)
        try:
            import socket
            import base64
            import struct
            import urllib.parse

            parsed = urllib.parse.urlparse(ws_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 80
            path = parsed.path or "/"
            key = base64.b64encode(os.urandom(16)).decode("ascii")

            sock = socket.create_connection((host, port), timeout=timeout)
            try:
                handshake = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"Upgrade: websocket\r\n"
                    f"Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {key}\r\n"
                    f"Sec-WebSocket-Version: 13\r\n\r\n"
                )
                sock.sendall(handshake.encode("ascii"))
                buf = b""
                while b"\r\n\r\n" not in buf:
                    chunk = sock.recv(4096)
                    if not chunk:
                        return None
                    buf += chunk

                raw_bytes = payload.encode("utf-8")
                mask_key = os.urandom(4)
                header = bytearray([0x81])
                length = len(raw_bytes)
                if length < 126:
                    header.append(0x80 | length)
                elif length < 65536:
                    header.append(0x80 | 126)
                    header.extend(struct.pack("!H", length))
                else:
                    header.append(0x80 | 127)
                    header.extend(struct.pack("!Q", length))
                header.extend(mask_key)
                masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(raw_bytes))
                sock.sendall(header + masked)

                resp_frame = sock.recv(65536)
                if len(resp_frame) >= 2:
                    plen = resp_frame[1] & 0x7F
                    offset = 2
                    if plen == 126:
                        offset = 4
                    elif plen == 127:
                        offset = 10
                    txt = resp_frame[offset:].decode("utf-8", errors="ignore")
                    obj = json.loads(txt)
                    return obj.get("result", {}).get("result", {}).get("value")
            finally:
                sock.close()
        except Exception:
            return None

    @classmethod
    def sync_renderer_user_status_via_cdp(cls) -> Optional[str]:
        """
        通过 CDP 实时通知 Antigravity 渲染进程刷新 PollingUserStatusProvider 与顶栏额度胶囊，
        使界面设置页与状态栏无需刷新网页即可秒级显示新切换的账号。
        """
        try:
            import urllib.request
            port_candidates = []
            appdata = os.environ.get("APPDATA")
            if appdata:
                port_candidates.append(Path(appdata) / "Antigravity" / "DevToolsActivePort")
            port_candidates.append(Path.home() / "AppData" / "Roaming" / "Antigravity" / "DevToolsActivePort")

            cdp_port = None
            for pf in port_candidates:
                if pf.exists():
                    lines = pf.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if lines and lines[0].strip().isdigit():
                        cdp_port = int(lines[0].strip())
                        break
            if not cdp_port:
                return None

            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{cdp_port}/json", timeout=2.0) as resp:
                targets = json.loads(resp.read().decode("utf-8", errors="ignore"))

            js_sync = """
            (async () => {
                let updatedEmail = null;
                try {
                    if (typeof window.__agRefreshQuota === 'function') {
                        window.__agRefreshQuota();
                    }
                } catch (e) {}

                let rootFiber = null;
                for (const el of [document.getElementById('root'), document.getElementById('app'), document.body, ...(document.body ? document.body.children : [])]) {
                    if (!el) continue;
                    const k = Object.keys(el).find(k => k.startsWith('__reactContainer$') || k.startsWith('__reactFiber$'));
                    if (k && el[k]) {
                        rootFiber = el[k];
                        while (rootFiber.return) rootFiber = rootFiber.return;
                        break;
                    }
                }
                if (!rootFiber) return null;

                const visited = new Set();
                const foundProviders = [];
                function inspectObj(obj, depth = 0) {
                    if (!obj || typeof obj !== 'object' || depth > 6 || visited.has(obj)) return;
                    visited.add(obj);
                    if (obj.lsClient && obj.provider && typeof obj.provider.setState === 'function' && typeof obj.lsClient.getUserStatus === 'function') {
                        foundProviders.push(obj);
                        return;
                    }
                    for (const k of Object.keys(obj)) {
                        if (k.startsWith('_') && k !== '_context' && k !== '_currentValue' && k !== '_currentValue2') continue;
                        try { inspectObj(obj[k], depth + 1); } catch (e) {}
                    }
                }

                const queue = [rootFiber];
                const seenFibers = new Set();
                while (queue.length > 0) {
                    const f = queue.shift();
                    if (!f || seenFibers.has(f)) continue;
                    seenFibers.add(f);
                    if (f.memoizedProps) inspectObj(f.memoizedProps, 0);
                    if (f.type && f.type._context) inspectObj(f.type._context, 0);
                    let ms = f.memoizedState;
                    while (ms) {
                        inspectObj(ms.memoizedState, 0);
                        ms = ms.next;
                    }
                    if (f.child) queue.push(f.child);
                    if (f.sibling) queue.push(f.sibling);
                }

                for (const p of foundProviders) {
                    try {
                        const resp = await p.lsClient.getUserStatus({});
                        if (resp && resp.userStatus) {
                            p.provider.setState(resp.userStatus);
                            updatedEmail = resp.userStatus.email || updatedEmail;
                        }
                    } catch (e) {}
                }
                return updatedEmail;
            })()
            """
            synced_email = None
            for t in targets:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    res = cls._cdp_eval_js(t["webSocketDebuggerUrl"], js_sync, timeout=4.0)
                    if res:
                        synced_email = res
            return synced_email
        except Exception:
            return None

    @classmethod
    def _get_cdp_targets(cls) -> list:
        """读取 DevToolsActivePort 并获取当前存活的 CDP 目标列表"""
        try:
            import urllib.request
            port_candidates = []
            appdata = os.environ.get("APPDATA")
            if appdata:
                port_candidates.append(Path(appdata) / "Antigravity" / "DevToolsActivePort")
            port_candidates.append(Path.home() / "AppData" / "Roaming" / "Antigravity" / "DevToolsActivePort")

            cdp_port = None
            for pf in port_candidates:
                if pf.exists():
                    lines = pf.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if lines and lines[0].strip().isdigit():
                        cdp_port = int(lines[0].strip())
                        break
            if not cdp_port:
                return []

            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{cdp_port}/json", timeout=1.5) as resp:
                targets = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return targets if isinstance(targets, list) else []
        except Exception:
            return []

    @classmethod
    def is_cdp_alive(cls) -> bool:
        """检测当前运行中的 Antigravity 是否存在活跃的 CDP 渲染窗口连接"""
        targets = cls._get_cdp_targets()
        return any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets)

    @classmethod
    def sync_electron_session_proxy_via_cdp(cls) -> bool:
        """
        通过 CDP 实时通知运行中的 Antigravity Electron 进程调用 session.defaultSession.setProxy 立即生效代理，
        实现秒级零重启代理热生效。
        """
        try:
            targets = cls._get_cdp_targets()
            if not targets:
                return False

            js_proxy = """
            (() => {
                if (typeof globalThis.__applyOrbitDynamicProxy === 'function') {
                    globalThis.__applyOrbitDynamicProxy();
                    return true;
                }
                return false;
            })()
            """
            for t in targets:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    cls._cdp_eval_js(t["webSocketDebuggerUrl"], js_proxy, timeout=3.0)
            return True
        except Exception:
            return False

    @classmethod
    def hot_inject_runtime_via_cdp(cls, cfg: Optional[Dict[str, Any]] = None) -> bool:
        """
        【核心能力】免重启、零断连 CDP 实时热注入汉化与界面优化引擎：
        当反重力自动更新导致 preload.js 补丁被重置，或用户在 Orbit 中修改了界面/汉化/额度胶囊开关时，
        直接通过 CDP 向当前运行中的渲染进程注入最新编译的 runtime.js，立刻恢复汉化、极简侧栏、左上角设置与额度胶囊！
        """
        try:
            targets = [t for t in cls._get_cdp_targets() if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            if not targets:
                return False

            if cfg is None:
                from core.config import load_config
                cfg = load_config()
            custom = cfg.get("customization", {})
            lang = custom.get("language", "zh-CN")
            is_tw = (lang == "zh-TW")
            is_en = (lang == "en")

            from core.config import find_active_config_file
            active_cfg = find_active_config_file()
            cfg_path_str = str(active_cfg).replace("\\", "/")

            node_script = (
                f"const {{ LocalizationEngine }} = require('./localization/core/engine');"
                f"const engine = new LocalizationEngine();"
                f"const script = engine.generateRuntimeScript({str(is_tw).lower()}, null, {str(is_en).lower()}, '{cfg_path_str}');"
                f"process.stdout.write(script);"
            )
            res = cls._run_subp(["node", "-e", node_script], cwd=str(RESOURCE_DIR), capture_output=True, timeout=8)
            runtime_js = res.stdout if res.returncode == 0 else ""
            if not runtime_js or len(runtime_js) < 100:
                return False

            injected = False
            for t in targets:
                cls._cdp_eval_js(t["webSocketDebuggerUrl"], runtime_js, timeout=6.0)
                injected = True
            return injected
        except Exception:
            return False

    _auto_heal_lock = None

    @classmethod
    def _get_auto_heal_lock(cls):
        if cls._auto_heal_lock is None:
            import threading
            cls._auto_heal_lock = threading.Lock()
        return cls._auto_heal_lock

    @classmethod
    def auto_heal_if_updated(cls, cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        自动检测反重力客户端是否因自动更新覆盖了 app.asar 或丢失了运行时补丁，
        若是则在不杀进程、不中断任务的前提下静默重打 app.asar 补丁并通过 CDP 实时热恢复所有配置！
        """
        lock = cls._get_auto_heal_lock()
        if not lock.acquire(blocking=False):
            return False, "自愈任务已在执行中"
        try:
            if cfg is None:
                from core.config import load_config
                cfg = load_config()
            custom = cfg.get("customization", {})
            lang = custom.get("language", "zh-CN")
            is_tw = (lang == "zh-TW")
            is_en = (lang == "en")

            # 清理后台待安装更新目录 (防止预下载安装包在下次启动时覆盖)
            if custom.get("disable_auto_update", True) is not False:
                try:
                    local_appdata = os.environ.get("LOCALAPPDATA")
                    if local_appdata:
                        pending_dir = Path(local_appdata) / "antigravity-updater" / "pending"
                        if pending_dir.exists():
                            shutil.rmtree(pending_dir, ignore_errors=True)
                except Exception:
                    pass

            st = cls.get_status(fast=True)
            if not st.get("installed"):
                return False, "未检测到 Antigravity 安装目录"

            repatched_asar = False
            if not st.get("is_localized"):
                ok, msg = cls.install(tw=is_tw, en=is_en, no_kill=True, stream_output=False)
                repatched_asar = ok

            # 若反重力正在运行，检查渲染进程是否已挂载 Orbit Runtime，若未挂载或刚重打补丁则立即通过 CDP 热注入
            if cls.is_running():
                targets = [t for t in cls._get_cdp_targets() if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
                need_cdp_inject = repatched_asar
                if not need_cdp_inject and targets:
                    active_flag = cls._cdp_eval_js(targets[0]["webSocketDebuggerUrl"], "Boolean(window.__orbitRuntimeActive)", timeout=2.0)
                    if not active_flag:
                        need_cdp_inject = True
                if need_cdp_inject and targets:
                    cls.hot_inject_runtime_via_cdp(cfg)
                    cls.sync_electron_session_proxy_via_cdp()
                    return True, "已通过零中断热修复恢复反重力汉化、代理与界面优化配置"

            if repatched_asar:
                return True, "已自动重注反重力更新后的 app.asar 补丁"
            return False, "当前补丁状态正常"
        except Exception as e:
            return False, f"自动自愈异常: {e}"
        finally:
            lock.release()

    @classmethod
    def reload_language_server_in_memory(cls, expected_email: Optional[str] = None) -> Tuple[bool, str]:
        """
        【核心突破】内存级零中断热重载反重力账号 (Zero-Kill In-Memory Hot-Switch)：
        不终止 language_server.exe、不刷新客户端窗口、不打断正在执行的长/短任务流，
        直接在进程内存中驱动 AuthClient.tryRestoreToken + CodeAssistClient.ResetCaches 重新加载系统凭据，
        并通过 CDP 同步更新前端 UI 状态。
        """
        if sys.platform != "win32":
            return False, "仅 Windows 支持内存级热重载"

        lock = cls._get_reload_lock()
        with lock:
            try:
                import ctypes
                from ctypes import wintypes
                import ssl
                import urllib.request

                ls_info = cls.get_live_language_server_info()
                if not ls_info:
                    return False, "未探测到运行中的 language_server.exe 实例"

                ls_pid = ls_info["pid"]
                ls_port = ls_info["port"]
                ls_csrf = ls_info["csrf"]
                ls_exe = ls_info.get("exe")
                if not ls_exe or not ls_exe.exists():
                    target_dir = cls._fallback_detect_dir()
                    if target_dir:
                        ls_exe = Path(target_dir) / "resources" / "bin" / "language_server.exe"
                if not ls_exe or not ls_exe.exists():
                    return False, "未找到 language_server.exe 二进制文件"

                patch_spec = cls._resolve_ls_hotreload_patches(ls_exe)
                if not patch_spec:
                    return False, "未能解析 language_server.exe 符号表偏移"

                PROCESS_VM_OPERATION = 0x0008
                PROCESS_VM_READ = 0x0010
                PROCESS_VM_WRITE = 0x0020
                PROCESS_QUERY_INFORMATION = 0x0400
                PAGE_EXECUTE_READWRITE = 0x40

                k32 = ctypes.WinDLL("kernel32", use_last_error=True)
                psapi = ctypes.WinDLL("psapi", use_last_error=True)

                k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                k32.OpenProcess.restype = wintypes.HANDLE
                k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
                k32.ReadProcessMemory.restype = wintypes.BOOL
                k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
                k32.WriteProcessMemory.restype = wintypes.BOOL
                k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
                k32.VirtualProtectEx.restype = wintypes.BOOL
                k32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
                k32.FlushInstructionCache.restype = wintypes.BOOL
                k32.CloseHandle.argtypes = [wintypes.HANDLE]
                psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
                psapi.EnumProcessModulesEx.restype = wintypes.BOOL

                h_proc = k32.OpenProcess(
                    PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION,
                    False,
                    ls_pid,
                )
                if not h_proc:
                    return False, f"打开 language_server.exe 进程失败 (错误码: {ctypes.get_last_error()})"

                try:
                    h_mods = (wintypes.HMODULE * 1024)()
                    cb_needed = wintypes.DWORD()
                    if not psapi.EnumProcessModulesEx(h_proc, h_mods, ctypes.sizeof(h_mods), ctypes.byref(cb_needed), 0x03):
                        return False, "枚举进程模块基址失败"

                    base_addr = h_mods[0]
                    delta = base_addr + patch_spec["text_rva"]
                    runtime_patches = [
                        (delta + va_off, orig_b, patch_b)
                        for va_off, orig_b, patch_b in patch_spec["patches"]
                    ]

                    # 校验原始机器码指令
                    for addr, orig_b, _ in runtime_patches:
                        buf = ctypes.create_string_buffer(len(orig_b))
                        n_read = ctypes.c_size_t()
                        if not k32.ReadProcessMemory(h_proc, ctypes.c_void_p(addr), buf, len(orig_b), ctypes.byref(n_read)):
                            return False, f"读取内存校验失败 @ 0x{addr:x}"
                        if buf.raw != orig_b:
                            return False, f"内存指令特征不匹配 @ 0x{addr:x}"

                    old_prots = []
                    for addr, _, patch_b in runtime_patches:
                        old_prot = wintypes.DWORD()
                        k32.VirtualProtectEx(h_proc, ctypes.c_void_p(addr), len(patch_b), PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
                        old_prots.append((addr, len(patch_b), old_prot))
                        n_written = ctypes.c_size_t()
                        k32.WriteProcessMemory(h_proc, ctypes.c_void_p(addr), patch_b, len(patch_b), ctypes.byref(n_written))
                        k32.FlushInstructionCache(h_proc, ctypes.c_void_p(addr), len(patch_b))

                    try:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))
                        req = urllib.request.Request(
                            f"https://127.0.0.1:{ls_port}/exa.language_server_pb.LanguageServerService/AuthLogout",
                            data=b"{}",
                            headers={"Content-Type": "application/json", "x-codeium-csrf-token": ls_csrf},
                            method="POST",
                        )
                        with opener.open(req, timeout=8.0) as resp:
                            resp.read()
                    finally:
                        # 无论如何立即还原原始指令字节与内存页属性
                        for (addr, orig_b, _), (_, sz, old_prot) in zip(runtime_patches, old_prots):
                            n_written = ctypes.c_size_t()
                            k32.WriteProcessMemory(h_proc, ctypes.c_void_p(addr), orig_b, len(orig_b), ctypes.byref(n_written))
                            k32.FlushInstructionCache(h_proc, ctypes.c_void_p(addr), len(orig_b))
                            dummy = wintypes.DWORD()
                            k32.VirtualProtectEx(h_proc, ctypes.c_void_p(addr), sz, old_prot.value, ctypes.byref(dummy))
                finally:
                    k32.CloseHandle(h_proc)

                # 验证新账号在 language_server.exe 中已实际生效，并同步前端 UI 状态
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))
                req_status = urllib.request.Request(
                    f"https://127.0.0.1:{ls_port}/exa.language_server_pb.LanguageServerService/GetUserStatus",
                    data=b"{}",
                    headers={"Content-Type": "application/json", "x-codeium-csrf-token": ls_csrf},
                    method="POST",
                )
                # 验证新账号在 language_server.exe 中已实际生效，并同步前端 UI 状态 (轮询最多 2 秒等待异步凭据加载)
                active_email = ""
                for _ in range(8):
                    try:
                        with opener.open(req_status, timeout=2.0) as resp:
                            status_body = json.loads(resp.read().decode("utf-8", errors="ignore"))
                            active_email = status_body.get("userStatus", {}).get("email", "")
                            if not expected_email or (active_email and active_email.lower() == expected_email.lower()):
                                break
                    except Exception:
                        pass
                    import time
                    time.sleep(0.25)

                cls.sync_renderer_user_status_via_cdp()

                return True, f"已通过内存零中断热切换实时生效 (当前生效: {active_email or expected_email or '新账号'})"
            except Exception as e:
                return False, f"内存级热重载异常: {e}"

    @classmethod
    def reload_language_server(cls, force: bool = False, expected_email: Optional[str] = None) -> Tuple[bool, str]:
        """
        优先通过内存零中断热重载 (reload_language_server_in_memory) 实现免重启反重力窗口、不中断运行中任务的秒级切号；
        除非用户显式指定 force=True (强制重启)，否则严格禁止杀进程，100% 杜绝打断正在执行的任务。
        """
        if sys.platform == "win32":
            mem_ok, mem_msg = cls.reload_language_server_in_memory(expected_email=expected_email)
            if mem_ok:
                return True, mem_msg
            if not force:
                return False, f"已自动启用零中断保护，内存热重载跳过杀进程以保护执行中的任务: {mem_msg}"

        if not force:
            return False, "检测到当前有任务正在运行，已自动启用零中断保护，跳过重载以保护任务"

        try:
            if sys.platform == "win32":
                res = cls._run_subp(["taskkill", "/F", "/IM", "language_server.exe"], capture_output=True)
                if res.returncode == 0:
                    return True, "已成功触发反重力后台会话平滑重载"
                return False, "未发现运行中的反重力后台服务"
            elif sys.platform == "darwin":
                res = cls._run_subp(["pkill", "-f", "language_server"], capture_output=True)
                if res.returncode == 0:
                    return True, "已成功触发反重力后台会话平滑热重载"
                return False, "未发现运行中的反重力后台服务"
            return True, "当前系统无需单独重载后台服务"
        except Exception as e:
            return False, f"热重载后台服务异常: {e}"

    @classmethod
    def focus_antigravity(cls) -> bool:
        """若 Antigravity 正在运行且有可见窗口，将其主窗口唤醒并置顶到前台"""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            found_hwnd = None

            # 获取所有 Antigravity.exe 进程的 PID 集合
            pids = set()
            try:
                res = cls._run_subp(["tasklist", "/fi", "imagename eq Antigravity.exe", "/fo", "csv", "/nh"], capture_output=True)
                for line in (res.stdout or "").splitlines():
                    line = line.strip().strip('"')
                    parts = [p.strip().strip('"') for p in line.split('","')]
                    if len(parts) >= 2 and parts[1].isdigit():
                        pids.add(int(parts[1]))
            except Exception:
                pass

            def _enum_win_proc(hwnd, extra):
                nonlocal found_hwnd
                win_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))

                # 必须归属于 Antigravity 进程且不能是 Orbit 自己的窗口
                if pids and win_pid.value not in pids:
                    return True
                if win_pid.value == os.getpid():
                    return True

                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                
                if "Antigravity Orbit" in title:
                    return True

                cls_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buff, 256)
                cls_name = cls_buff.value

                # 识别 Electron 顶层窗口 (Chrome_WidgetWin_1 且处于正常可见或最小化状态)
                is_visible = bool(user32.IsWindowVisible(hwnd))
                is_iconic = bool(user32.IsIconic(hwnd))

                if (is_visible or is_iconic) and (cls_name == "Chrome_WidgetWin_1" or "Antigravity" in title):
                    found_hwnd = hwnd
                    return False
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(_enum_win_proc), 0)
            if found_hwnd:
                # 9 = SW_RESTORE (恢复最小化并显示窗口)
                user32.ShowWindow(found_hwnd, 9)
                user32.SetForegroundWindow(found_hwnd)
                try:
                    user32.SwitchToThisWindow(found_hwnd, True)
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

    @classmethod
    def launch_antigravity(cls, install_dir: Optional[str] = None) -> Tuple[bool, str]:
        """拉起启动 Antigravity 客户端 (杜绝 CREATE_NO_WINDOW 导致的 Chromium 白屏与卡死)"""
        target_dir = cls._fallback_detect_dir(install_dir)
        if not target_dir:
            return False, "未能探测到 Antigravity 安装目录"

        try:
            if sys.platform == "win32":
                exe_path = Path(target_dir) / "Antigravity.exe"
                if exe_path.exists():
                    # 检查是否配置了最大化启动
                    start_maximized = False
                    try:
                        from core.config import load_config
                        cfg = load_config()
                        start_maximized = bool(cfg.get("customization", {}).get("start_maximized", False))
                    except Exception:
                        pass

                    cmd = [str(exe_path)]
                    if start_maximized:
                        cmd.append("--start-maximized")

                    # 如果反重力已经在运行，先尝试激活前台窗口
                    if cls.is_running():
                        if cls.focus_antigravity():
                            return True, "已唤醒并聚焦 Antigravity 客户端窗口"
                        elif not cls.is_cdp_alive() and not cls.is_any_task_running():
                            # 仅当既无可见窗口、又无存活 CDP 渲染目标且无运行中任务时，才判定为休眠后假死的孤儿僵尸进程
                            # 清理无窗口无响应的僵尸进程 (不加 /T，绝对不误杀后台活跃的语言服务)，释放单实例锁后重新拉起
                            try:
                                cls._run_subp(["taskkill", "/F", "/IM", "Antigravity.exe"], capture_output=True)
                                for _ in range(15):
                                    if not cls.is_running():
                                        break
                                    import time
                                    time.sleep(0.1)
                                appdata_dir = os.environ.get("APPDATA")
                                if appdata_dir:
                                    lock_f = Path(appdata_dir) / "Antigravity" / "lockfile"
                                    for _ in range(5):
                                        if lock_f.exists():
                                            try:
                                                lock_f.unlink()
                                                break
                                            except Exception:
                                                import time
                                                time.sleep(0.1)
                                        else:
                                            break
                            except Exception:
                                pass
                    else:
                        # 进程未运行时，主动清理可能因休眠/断电残留的陈旧单实例锁文件，杜绝启动卡死
                        try:
                            appdata_dir = os.environ.get("APPDATA")
                            if appdata_dir:
                                lock_f = Path(appdata_dir) / "Antigravity" / "lockfile"
                                if lock_f.exists():
                                    lock_f.unlink()
                        except Exception:
                            pass

                    # 优先尝试使用 Windows 原生 Shell 启动 (等同于双击，自动触发 Electron second-instance showOrCreateWindow 唤醒)
                    try:
                        if not start_maximized:
                            os.startfile(str(exe_path))
                            return True, "已启动 Antigravity 客户端"
                    except Exception:
                        pass

                    # 备选使用 subprocess.Popen (不使用 DETACHED_PROCESS 避免前台窗口句柄丢失)
                    subprocess.Popen(
                        cmd,
                        cwd=str(target_dir)
                    )
                    return True, "已启动 Antigravity 客户端"
            elif sys.platform == "darwin":
                if cls.is_running():
                    if cls.focus_antigravity():
                        return True, "已唤醒并聚焦 Antigravity 客户端窗口"
                    elif not cls.is_cdp_alive() and not cls.is_any_task_running():
                        cls._run_subp(["pkill", "-x", "Antigravity"], capture_output=True)
                        import time
                        time.sleep(0.5)
                cls._run_subp(["open", str(target_dir)], capture_output=True)
                return True, "已启动 Antigravity 客户端"
        except Exception as e:
            return False, f"拉起客户端失败: {e}"
        return False, "未找到客户端可执行文件"


    @staticmethod
    def _fallback_detect_dir(manual_dir: Optional[str] = None) -> Optional[Path]:
        """跨平台备选路径探测"""
        if manual_dir and Path(manual_dir).exists():
            p = Path(manual_dir).resolve()
            if p.is_file() and p.name == "app.asar":
                p = p.parent
            return p

        candidates = []
        sys_name = platform.system().lower()

        if sys_name == "windows":
            # 常见 Windows 目录
            for drive in ["C", "D", "E", "F"]:
                candidates.append(Path(f"{drive}:/Programs/Antigravity"))
                candidates.append(Path(f"{drive}:/Antigravity"))
            candidates.append(Path("C:/Program Files/Antigravity"))
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                candidates.append(Path(local_appdata) / "Programs" / "antigravity")

        elif sys_name == "darwin":
            candidates.append(Path("/Applications/Antigravity.app"))
            candidates.append(Path.home() / "Applications" / "Antigravity.app")

        for c in candidates:
            if c.exists():
                if (c / "resources" / "app.asar").exists() or (c / "app.asar").exists() or (c / "Contents" / "Resources" / "app.asar").exists():
                    return c
        return None

    @classmethod
    def format_status(cls, status: Dict[str, Any]) -> str:
        """格式化展示状态报告"""
        lines = [
            "=" * 50,
            "🌐【Google Antigravity 客户端与汉化状态】",
            "=" * 50,
        ]

        if not status.get("installed"):
            lines.append("• 客户端状态: 🔴 未检测到 Antigravity 安装目录")
            lines.append("  (提示: 如果已安装，请使用 --dir 参数指定客户端安装路径)")
        else:
            lines.append(f"• 软件路径: {status.get('install_dir')}")
            arch = "Antigravity 2.0+ (ASAR)" if status.get("is_v2") else "Antigravity 1.0 (HTML)"
            lines.append(f"• 架构类型: {arch}")

            is_loc = status.get("is_localized")
            lang = status.get("lang")
            lang_str = "繁体中文 (zh-TW)" if lang == "zh-TW" else ("简体中文 (zh-CN)" if lang == "zh-CN" else "中文语言包")
            brand = status.get("brand_title") or "english"

            if is_loc:
                lines.append(f"• 界面语言: 🟢 已汉化 [{lang_str}]")
            else:
                lines.append("• 界面语言: ⚪ 官方原版英文")

            backup = "🟢 存在 (可随时一键卸载还原)" if status.get("has_backup") else "⚪ 未创建"
            lines.append(f"• 原始备份: {backup}")

        node_ok = status.get("node_available")
        node_ver = status.get("node_version") or "未安装"
        lines.append(f"• Node.js 环境: {'🟢 ' + node_ver if node_ok else '🔴 未检测到 (需安装以执行注入)'}")
        lines.append("=" * 50)
        return "\n".join(lines)
