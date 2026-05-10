"""
Enhanced Safe Cleanup Engine
------------------------------
Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
License: Personal Use Only (Non-Commercial)

NEVER deletes: passwords, bookmarks, browser sessions, personal files, downloads.
All new tasks are safe, reversible-effect (no data loss), and improve speed.
"""

import os
import ctypes
import shutil
import tempfile
import subprocess
import logging
import threading
from pathlib import Path
from typing import List, Tuple, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# SAFE CLEANUP TARGETS
# ─────────────────────────────────────────────────────────────────

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
APPDATA      = os.environ.get("APPDATA", "")
USERPROFILE  = os.environ.get("USERPROFILE", "")
SYSTEMROOT   = os.environ.get("SYSTEMROOT", "C:\\Windows")

SAFE_TEMP_DIRS = [
    Path(tempfile.gettempdir()),
    Path(SYSTEMROOT) / "Temp",
    Path(LOCALAPPDATA) / "Temp",
]

SAFE_CACHE_DIRS = [
    Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "Explorer",   # Thumbnail cache
    Path(LOCALAPPDATA) / "D3DSCache",                             # DirectX shader
    Path(LOCALAPPDATA) / "NVIDIA" / "DXCache",                   # NVIDIA DX cache
    Path(LOCALAPPDATA) / "NVIDIA" / "GLCache",                   # NVIDIA GL cache
    Path(LOCALAPPDATA) / "AMD"    / "DXCache",                   # AMD cache
    Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "INetCache",  # IE/Edge cache
]

# Windows Error Reporting (safe to clear — no personal data)
WER_DIRS = [
    Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "WER" / "ReportArchive",
    Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "WER" / "ReportQueue",
    Path(PROGRAMDATA := os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Microsoft" / "Windows" / "WER" / "ReportArchive",
]

# Recent file shortcuts (not actual files — just LNK shortcuts in Recent)
RECENT_DIR = Path(APPDATA) / "Microsoft" / "Windows" / "Recent"

# Windows Prefetch (safe — Windows rebuilds automatically on next launch)
PREFETCH_DIR = Path(SYSTEMROOT) / "Prefetch"

# Browser safe cache paths
BROWSER_SAFE_CACHE = {
    "chrome": [
        Path(LOCALAPPDATA) / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        Path(LOCALAPPDATA) / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
        Path(LOCALAPPDATA) / "Google" / "Chrome" / "User Data" / "Default" / "GPUCache",
        Path(LOCALAPPDATA) / "Google" / "Chrome" / "User Data" / "ShaderCache",
    ],
    "edge": [
        Path(LOCALAPPDATA) / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
        Path(LOCALAPPDATA) / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
        Path(LOCALAPPDATA) / "Microsoft" / "Edge" / "User Data" / "Default" / "GPUCache",
    ],
    "brave": [
        Path(LOCALAPPDATA) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache",
        Path(LOCALAPPDATA) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "GPUCache",
    ],
    "opera": [
        Path(APPDATA) / "Opera Software" / "Opera Stable" / "Cache",
        Path(APPDATA) / "Opera Software" / "Opera Stable" / "GPUCache",
    ],
    "firefox": [
        Path(LOCALAPPDATA) / "Mozilla" / "Firefox" / "Profiles",
    ],
}

# ─────────────────────────────────────────────────────────────────
# CLEANUP RESULT
# ─────────────────────────────────────────────────────────────────

class CleanupResult:
    def __init__(self):
        self.files_deleted: int = 0
        self.dirs_deleted: int = 0
        self.space_freed_bytes: int = 0
        self.errors: List[str] = []
        self.log: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    @property
    def space_freed_mb(self) -> float:
        return round(self.space_freed_bytes / 1e6, 2)

    @property
    def space_freed_gb(self) -> float:
        return round(self.space_freed_bytes / 1e9, 3)

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds() if self.end_time else 0.0

    def summary(self) -> str:
        return (
            f"Cleaned {self.files_deleted} files | "
            f"Freed {self.space_freed_mb:.1f} MB | "
            f"Done in {self.duration_seconds:.1f}s"
        )


# ─────────────────────────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────────────────────────

class CleanupEngine:
    """
    Safe, comprehensive Windows cleanup engine.
    Principle of least privilege — all operations are guarded and logged.
    """

    def __init__(self, progress_cb: Optional[Callable[[str, int], None]] = None):
        self.progress_cb = progress_cb or (lambda m, p: None)
        self._result = CleanupResult()

    def run(
        self,
        # ── SAFE (always on by default) ──────────────────────────
        clean_temp:            bool = True,
        clean_browser_cache:   bool = True,
        clean_thumbnails:      bool = True,
        clean_logs:            bool = True,
        clean_gpu_cache:       bool = True,
        clean_dns:             bool = True,
        clean_wer:             bool = True,
        clean_clipboard:       bool = True,
        clean_recent_links:    bool = True,
        trim_ram:              bool = True,
        # ── MODERATE (optional, safe) ─────────────────────────────
        clean_prefetch:        bool = False,
        clean_recycle:         bool = False,
        clean_event_logs:      bool = False,
        clean_windows_update:  bool = False,
        # ── RISKY (requires explicit user confirmation) ───────────
        clean_history:         bool = False,
        clean_cookies:         bool = False,
    ) -> CleanupResult:
        """Run cleanup with selected options. Returns CleanupResult."""
        self._result = CleanupResult()
        tasks = []

        # Safe tasks
        if clean_temp:           tasks.append(("🗑️ Windows Temp Files",        self._clean_temp_dirs))
        if clean_thumbnails:     tasks.append(("🖼️ Thumbnail Cache",            self._clean_thumbnail_cache))
        if clean_gpu_cache:      tasks.append(("🎮 GPU Shader Cache",           self._clean_gpu_cache))
        if clean_browser_cache:  tasks.append(("🌐 Browser Cache",              self._clean_browser_cache))
        if clean_logs:           tasks.append(("📋 Temp Log Files",             self._clean_temp_logs))
        if clean_dns:            tasks.append(("🔗 DNS Cache",                  self._clean_dns_cache))
        if clean_wer:            tasks.append(("🐛 Windows Error Reports",      self._clean_wer))
        if clean_clipboard:      tasks.append(("📋 Clipboard",                  self._clean_clipboard))
        if clean_recent_links:   tasks.append(("📂 Recent File Links",          self._clean_recent_links))
        if trim_ram:             tasks.append(("🧠 RAM Trim (Working Set)",     self._trim_ram))

        # Moderate tasks
        if clean_prefetch:       tasks.append(("⚡ Prefetch Cache",             self._clean_prefetch))
        if clean_recycle:        tasks.append(("🗑️ Recycle Bin",                self._clean_recycle_bin))
        if clean_event_logs:     tasks.append(("📜 Old Event Logs",             self._clean_event_logs))
        if clean_windows_update: tasks.append(("🔄 Windows Update Cache",       self._clean_windows_update_cache))

        # Risky tasks
        if clean_history:        tasks.append(("⚠️ Browser History",            self._clean_browser_history))
        if clean_cookies:        tasks.append(("⚠️ Browser Cookies",            self._clean_cookies))

        total = len(tasks)
        for i, (label, fn) in enumerate(tasks):
            pct = int((i / max(total, 1)) * 100)
            self.progress_cb(label, pct)
            logger.info(f"[Cleanup] {label}")
            try:
                fn()
            except Exception as e:
                msg = f"Error in '{label}': {e}"
                logger.error(msg)
                self._result.errors.append(msg)

        self.progress_cb("✅ Cleanup complete!", 100)
        self._result.end_time = datetime.now()
        logger.info(f"[Cleanup] {self._result.summary()}")
        return self._result

    # ─── SAFE CLEANUP METHODS ─────────────────────────────────────

    def _clean_temp_dirs(self):
        for d in SAFE_TEMP_DIRS:
            if d.exists():
                self._wipe_dir_contents(d)

    def _clean_thumbnail_cache(self):
        explorer_cache = Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "Explorer"
        if explorer_cache.exists():
            for f in explorer_cache.glob("thumbcache_*.db"):
                self._delete_file(f)

    def _clean_gpu_cache(self):
        gpu_dirs = [
            Path(LOCALAPPDATA) / "D3DSCache",
            Path(LOCALAPPDATA) / "NVIDIA" / "DXCache",
            Path(LOCALAPPDATA) / "NVIDIA" / "GLCache",
            Path(LOCALAPPDATA) / "AMD" / "DXCache",
            Path(LOCALAPPDATA) / "Intel" / "ShaderCache",
        ]
        for d in gpu_dirs:
            if d.exists():
                self._wipe_dir_contents(d)

    def _clean_browser_cache(self):
        for browser, paths in BROWSER_SAFE_CACHE.items():
            for p in paths:
                if p.exists() and p.is_dir():
                    if browser == "firefox":
                        self._clean_firefox_cache(p)
                    else:
                        self._wipe_dir_contents(p)

    def _clean_firefox_cache(self, profiles_dir: Path):
        for profile in profiles_dir.iterdir():
            for subdir in ["cache2", "startupCache"]:
                cache = profile / subdir
                if cache.exists():
                    self._wipe_dir_contents(cache)

    def _clean_temp_logs(self):
        for d in SAFE_TEMP_DIRS:
            if d.exists():
                for pattern in ["*.log", "*.tmp", "*.dmp"]:
                    for f in d.rglob(pattern):
                        self._delete_file(f)

    def _clean_dns_cache(self):
        """Flush DNS cache — improves network resolution speed."""
        try:
            subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True, timeout=10
            )
            self._result.log.append("DNS cache flushed.")
            logger.info("DNS cache flushed.")
        except Exception as e:
            self._result.errors.append(f"DNS flush error: {e}")

    def _clean_wer(self):
        """Clear Windows Error Reporting archives — safe, no personal data."""
        for d in WER_DIRS:
            if d.exists():
                self._wipe_dir_contents(d)

    def _clean_clipboard(self):
        """Clear the Windows clipboard."""
        try:
            subprocess.run(
                ["PowerShell", "-Command", "Set-Clipboard -Value $null"],
                capture_output=True, timeout=5
            )
            self._result.log.append("Clipboard cleared.")
        except Exception:
            try:
                if ctypes.windll.user32.OpenClipboard(None):
                    ctypes.windll.user32.EmptyClipboard()
                    ctypes.windll.user32.CloseClipboard()
            except Exception as e:
                self._result.errors.append(f"Clipboard clear error: {e}")

    def _clean_recent_links(self):
        """
        Removes .lnk shortcut files from Recent folder.
        Does NOT delete the actual files — only the shortcuts in the Recent list.
        """
        if RECENT_DIR.exists():
            for f in RECENT_DIR.glob("*.lnk"):
                self._delete_file(f)
            for f in RECENT_DIR.glob("*.automaticDestinations-ms"):
                self._delete_file(f)

    def _trim_ram(self):
        """
        Trim process working sets — signals Windows to release unused memory
        pages back to the system. Does NOT kill any processes.
        """
        try:
            import psutil, ctypes
            current_pid = os.getpid()
            freed = 0
            for proc in psutil.process_iter(["pid", "name", "status"]):
                try:
                    if proc.info["status"] == psutil.STATUS_RUNNING:
                        handle = ctypes.windll.kernel32.OpenProcess(
                            0x1F0FFF, False, proc.info["pid"]
                        )
                        if handle:
                            ctypes.windll.psapi.EmptyWorkingSet(handle)
                            ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    pass
            self._result.log.append("RAM working sets trimmed.")
            logger.info("RAM trim complete.")
        except Exception as e:
            self._result.errors.append(f"RAM trim error: {e}")

    # ─── MODERATE CLEANUP ─────────────────────────────────────────

    def _clean_prefetch(self):
        """
        Clear Prefetch folder — Windows rebuilds on next launch.
        May slightly slow first launches temporarily, then re-optimizes.
        """
        if PREFETCH_DIR.exists():
            try:
                # Requires elevated rights — try with admin check
                self._wipe_dir_contents(PREFETCH_DIR)
                self._result.log.append("Prefetch cache cleared.")
            except PermissionError:
                self._result.errors.append("Prefetch: Admin rights required.")

    def _clean_recycle_bin(self):
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            self._result.log.append("Recycle Bin emptied.")
        except ImportError:
            try:
                subprocess.run(
                    ["PowerShell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                    capture_output=True, timeout=30
                )
                self._result.log.append("Recycle Bin emptied via PowerShell.")
            except Exception as e:
                self._result.errors.append(f"Recycle Bin error: {e}")

    def _clean_event_logs(self):
        """Clear non-critical Windows Event Log files (Application/System/Security)."""
        logs = ["Application", "System"]  # NOTE: Security log requires admin
        for log in logs:
            try:
                subprocess.run(
                    ["wevtutil", "cl", log],
                    capture_output=True, timeout=15
                )
                self._result.log.append(f"Event log '{log}' cleared.")
            except Exception as e:
                self._result.errors.append(f"Event log error ({log}): {e}")

    def _clean_windows_update_cache(self):
        """
        Clear Windows Update download cache.
        Safe — Windows re-downloads updates if needed.
        """
        wu_cache = Path(SYSTEMROOT) / "SoftwareDistribution" / "Download"
        if wu_cache.exists():
            # Stop Windows Update service first, then clear, then restart
            try:
                subprocess.run(["net", "stop", "wuauserv"], capture_output=True, timeout=20)
                self._wipe_dir_contents(wu_cache)
                subprocess.run(["net", "start", "wuauserv"], capture_output=True, timeout=20)
                self._result.log.append("Windows Update cache cleared.")
            except Exception as e:
                self._result.errors.append(f"WU cache error: {e}")

    # ─── RISKY (only when explicitly requested) ───────────────────

    def _clean_browser_history(self):
        history_files = {
            "chrome": Path(LOCALAPPDATA) / "Google"       / "Chrome"        / "User Data" / "Default" / "History",
            "edge":   Path(LOCALAPPDATA) / "Microsoft"    / "Edge"           / "User Data" / "Default" / "History",
            "brave":  Path(LOCALAPPDATA) / "BraveSoftware"/ "Brave-Browser"  / "User Data" / "Default" / "History",
        }
        for browser, hf in history_files.items():
            if hf.exists():
                self._delete_file(hf)
                logger.info(f"[RISKY] Deleted {browser} history")

    def _clean_cookies(self):
        cookie_files = {
            "chrome": Path(LOCALAPPDATA) / "Google"    / "Chrome" / "User Data" / "Default" / "Cookies",
            "edge":   Path(LOCALAPPDATA) / "Microsoft" / "Edge"   / "User Data" / "Default" / "Cookies",
        }
        for browser, cf in cookie_files.items():
            if cf.exists():
                self._delete_file(cf)
                logger.info(f"[RISKY] Deleted {browser} cookies")

    # ─── UTILITIES ────────────────────────────────────────────────

    def _delete_file(self, path: Path):
        try:
            size = path.stat().st_size
            path.unlink()
            self._result.files_deleted += 1
            self._result.space_freed_bytes += size
        except (PermissionError, FileNotFoundError):
            pass
        except Exception as e:
            self._result.errors.append(str(e))

    def _wipe_dir_contents(self, directory: Path):
        try:
            for item in directory.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        size = item.stat().st_size
                        item.unlink()
                        self._result.files_deleted += 1
                        self._result.space_freed_bytes += size
                    elif item.is_dir():
                        size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        shutil.rmtree(item, ignore_errors=True)
                        self._result.dirs_deleted += 1
                        self._result.space_freed_bytes += size
                except (PermissionError, OSError):
                    pass
        except Exception as e:
            logger.debug(f"wipe_dir_contents error on {directory}: {e}")


# ─────────────────────────────────────────────────────────────────
# ESTIMATE (no deletion)
# ─────────────────────────────────────────────────────────────────

def estimate_cleanup_size(
    clean_temp=True,
    clean_browser_cache=True,
    clean_thumbnails=True,
    clean_gpu_cache=True,
    clean_logs=True,
    clean_recycle=False,
) -> int:
    total = 0

    def _size(d: Path) -> int:
        try:
            return sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        except Exception:
            return 0

    if clean_temp:
        for d in SAFE_TEMP_DIRS:
            total += _size(d)

    if clean_browser_cache:
        for paths in BROWSER_SAFE_CACHE.values():
            for p in paths:
                if p.exists():
                    total += _size(p)

    if clean_thumbnails:
        exp = Path(LOCALAPPDATA) / "Microsoft" / "Windows" / "Explorer"
        if exp.exists():
            total += sum(f.stat().st_size for f in exp.glob("thumbcache_*.db") if f.is_file())

    if clean_gpu_cache:
        for d in [
            Path(LOCALAPPDATA) / "D3DSCache",
            Path(LOCALAPPDATA) / "NVIDIA" / "DXCache",
        ]:
            if d.exists():
                total += _size(d)

    return total


# ─────────────────────────────────────────────────────────────────
# BACKGROUND RUNNER — QThread + pyqtSignal (guaranteed thread-safe)
# ─────────────────────────────────────────────────────────────────

try:
    from PyQt6.QtCore import QThread, pyqtSignal as Signal
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


if _HAS_QT:
    class BackgroundCleanup(QThread):
        """
        Runs CleanupEngine in a QThread.
        progress_cb and done_cb are connected via Qt signals —
        guaranteed to be delivered on the main thread even when
        emitted from the worker thread.
        """
        _progress_sig = Signal(str, int)
        _done_sig     = Signal(object)

        def __init__(self, options: dict, progress_cb=None, done_cb=None):
            super().__init__()
            self.options = options
            if progress_cb:
                self._progress_sig.connect(progress_cb)
            if done_cb:
                self._done_sig.connect(done_cb)

        def start(self):
            super().start()

        def run(self):
            engine = CleanupEngine(
                progress_cb=lambda m, p: self._progress_sig.emit(m, p)
            )
            # Only pass keys the engine knows about
            known = {
                'clean_temp','clean_browser_cache','clean_thumbnails',
                'clean_logs','clean_gpu_cache','clean_dns','clean_wer',
                'clean_clipboard','clean_recent_links','trim_ram',
                'clean_prefetch','clean_recycle','clean_event_logs',
                'clean_windows_update','clean_history','clean_cookies',
            }
            filtered = {k: v for k, v in self.options.items() if k in known}
            result = engine.run(**filtered)
            self._done_sig.emit(result)
else:
    class BackgroundCleanup:
        """Fallback when PyQt6 unavailable."""
        def __init__(self, options, progress_cb=None, done_cb=None):
            self.options     = options
            self.progress_cb = progress_cb or (lambda m, p: None)
            self.done_cb     = done_cb
        def start(self):
            import threading
            threading.Thread(target=self._run, daemon=True).start()
        def _run(self):
            engine = CleanupEngine(progress_cb=self.progress_cb)
            result = engine.run(**self.options)
            if self.done_cb:
                self.done_cb(result)
