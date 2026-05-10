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
    """Return list of startup applications from registry and startup folder."""
    import winreg
    startup_apps = []
    reg_paths = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, path in reg_paths:
        try:
            key = winreg.OpenKey(hive, path)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    startup_apps.append({
                        "name": name,
                        "path": value,
                        "source": "Registry",
                        "enabled": True,
                    })
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass
    return startup_apps


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
