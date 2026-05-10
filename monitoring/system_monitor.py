"""
Monitoring Service - Real-time system metrics using psutil
"""

import psutil
import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    cpu_per_core: List[float] = field(default_factory=list)
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    cpu_temp: Optional[float] = None
    top_processes: List[dict] = field(default_factory=list)
    timestamp: str = ""
    health_score: int = 100


class SystemMonitor:
    """
    Threaded real-time system monitoring service.
    Calls registered callbacks whenever new metrics are available.
    """

    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[SystemMetrics], None]] = []
        self._metrics = SystemMetrics()
        self._prev_net = psutil.net_io_counters()
        self._prev_net_time = time.time()

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────
    def register_callback(self, cb: Callable[[SystemMetrics], None]):
        self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[SystemMetrics], None]):
        self._callbacks = [c for c in self._callbacks if c != cb]

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("SystemMonitor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SystemMonitor stopped.")

    @property
    def latest(self) -> SystemMetrics:
        return self._metrics

    # ─────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────
    def _loop(self):
        while self._running:
            try:
                m = self._collect()
                self._metrics = m
                for cb in list(self._callbacks):
                    try:
                        cb(m)
                    except Exception as e:
                        logger.error(f"Monitor callback error: {e}")
            except Exception as e:
                logger.error(f"Monitor collect error: {e}")
            time.sleep(self.interval)

    def _collect(self) -> SystemMetrics:
        m = SystemMetrics()
        m.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # CPU
        m.cpu_percent = psutil.cpu_percent(interval=None)
        m.cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

        # RAM
        vm = psutil.virtual_memory()
        m.ram_percent = vm.percent
        m.ram_used_gb = round(vm.used / 1e9, 2)
        m.ram_total_gb = round(vm.total / 1e9, 2)

        # Disk
        du = psutil.disk_usage("C:\\")
        m.disk_percent = du.percent
        m.disk_used_gb = round(du.used / 1e9, 2)
        m.disk_total_gb = round(du.total / 1e9, 2)
        m.disk_free_gb = round(du.free / 1e9, 2)

        # Network
        now = time.time()
        net = psutil.net_io_counters()
        elapsed = now - self._prev_net_time
        if elapsed > 0:
            m.network_sent_mb = round((net.bytes_sent - self._prev_net.bytes_sent) / 1e6 / elapsed, 3)
            m.network_recv_mb = round((net.bytes_recv - self._prev_net.bytes_recv) / 1e6 / elapsed, 3)
        self._prev_net = net
        self._prev_net_time = now

        # Temperature (Windows limited, try anyway)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        m.cpu_temp = entries[0].current
                        break
        except Exception:
            m.cpu_temp = None

        # Top Processes
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
                try:
                    info = p.info
                    if info["memory_percent"] is not None and info["memory_percent"] > 0.1:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
            m.top_processes = procs[:10]
        except Exception as e:
            logger.debug(f"Process list error: {e}")

        # Health Score
        m.health_score = self._calc_health(m)
        return m

    @staticmethod
    def _calc_health(m: SystemMetrics) -> int:
        score = 100
        score -= min(30, m.cpu_percent * 0.3)
        score -= min(25, m.ram_percent * 0.25)
        score -= min(25, m.disk_percent * 0.25)
        if m.cpu_temp and m.cpu_temp > 85:
            score -= 20
        elif m.cpu_temp and m.cpu_temp > 75:
            score -= 10
        return max(0, int(score))


def get_startup_apps() -> List[dict]:
    """Return ALL startup apps from: registry Run/RunOnce, startup folders, Task Scheduler."""
    import winreg
    import os
    from pathlib import Path

    startup_apps = []
    seen: set = set()

    def _add(name, path, source, enabled=True):
        key = (name.lower()[:40], path.lower()[:60])
        if key not in seen:
            seen.add(key)
            startup_apps.append({"name": name, "path": path,
                                  "source": source, "enabled": enabled})

    # 1. Registry Run / RunOnce (HKCU + HKLM, 64-bit + 32-bit WOW)
    reg_paths = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run",     "Registry (User)"),
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "Registry (User RunOnce)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",     "Registry (System)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "Registry (System RunOnce)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Registry (32-bit)"),
    ]
    for hive, path, source in reg_paths:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    _add(name, value, source, enabled=True)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass

    # 2. User Startup folder
    user_startup = Path(os.environ.get("APPDATA", "")) / \
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    if user_startup.exists():
        for f in user_startup.iterdir():
            if f.suffix.lower() in (".lnk", ".bat", ".cmd", ".exe", ".url"):
                _add(f.stem, str(f), "Startup Folder (User)", enabled=True)

    # 3. All Users Startup folder
    all_startup = Path(os.environ.get("PROGRAMDATA", "")) / \
        r"Microsoft\Windows\Start Menu\Programs\StartUp"
    if all_startup.exists():
        for f in all_startup.iterdir():
            if f.suffix.lower() in (".lnk", ".bat", ".cmd", ".exe", ".url"):
                _add(f.stem, str(f), "Startup Folder (All Users)", enabled=True)

    # 4. Task Scheduler — catch browser/app background tasks
    try:
        import subprocess
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True, text=True, timeout=10
        )
        keywords = ["chrome", "edge", "brave", "firefox", "opera",
                    "update", "autoupdate", "startup", "onedriv",
                    "skype", "teams", "discord", "zoom", "spotify", "steam"]
        for line in result.stdout.splitlines():
            parts = line.strip().strip('"').split('","')
            if len(parts) >= 3:
                task_name = parts[0].strip('"')
                status = parts[2].strip('"') if len(parts) > 2 else ""
                if any(k in task_name.lower() for k in keywords):
                    enabled = status.lower() in ("ready", "running")
                    _add(task_name, f"Task Scheduler: {task_name}", "Task Scheduler", enabled)
    except Exception:
        pass

    return startup_apps



def get_network_usage() -> list:
    """Identify top processes consuming network bandwidth."""
    import psutil
    net_procs = []
    try:
        # Get all connections
        connections = psutil.net_connections(kind='inet')
        pid_to_conns = {}
        for conn in connections:
            if conn.pid:
                pid_to_conns.setdefault(conn.pid, []).append(conn)
        
        # We can't get per-process bandwidth easily without a capture driver,
        # but we can count active connections and identify high-bandwidth types.
        for pid, conns in pid_to_conns.items():
            try:
                p = psutil.Process(pid)
                name = p.name()
                if name.lower() in ("system", "idle"): continue
                
                # Check connection status
                established = len([c for c in conns if c.status == 'ESTABLISHED'])
                if established > 0:
                    net_procs.append({
                        "pid": pid,
                        "name": name,
                        "connections": established,
                        "type": "High Traffic" if established > 10 else "Active",
                        "path": p.exe() if hasattr(p, 'exe') else ""
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error getting network usage: {e}")
        
    net_procs.sort(key=lambda x: x["connections"], reverse=True)
    return net_procs[:10]


def boost_internet() -> tuple:
    """Perform network optimization actions. Returns (success, log)."""
    import subprocess
    log = []
    success = True
    
    commands = [
        ("Flushing DNS Cache", ["ipconfig", "/flushdns"]),
        ("Resetting Winsock Catalog", ["netsh", "winsock", "reset"]),
        ("Resetting IP Stack", ["netsh", "int", "ip", "reset"]),
        ("Clearing ARP Cache", ["netsh", "interface", "ip", "delete", "arpcache"]),
    ]
    
    for label, cmd in commands:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                log.append(f"✅ {label}: Success")
            else:
                log.append(f"⚠️ {label}: {res.stderr.strip() or 'Partial success'}")
        except Exception as e:
            log.append(f"❌ {label}: Failed ({str(e)})")
            success = False
            
    return success, "\n".join(log)


def get_disk_usage_breakdown() -> dict:
    """Get per-partition disk usage."""
    result = {}
    for part in psutil.disk_partitions(all=False):
        try:
            du = psutil.disk_usage(part.mountpoint)
            result[part.mountpoint] = {
                "total_gb": round(du.total / 1e9, 2),
                "used_gb": round(du.used / 1e9, 2),
                "free_gb": round(du.free / 1e9, 2),
                "percent": du.percent,
                "device": part.device,
                "fstype": part.fstype,
            }
        except PermissionError:
            pass
    return result
