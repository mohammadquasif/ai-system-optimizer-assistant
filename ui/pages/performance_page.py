"""
Performance & Startup Apps Pages
- Performance: CPU/RAM charts + disk breakdown
- StartupApps: Full AI-powered analysis with RAM usage, recommendations, disable option
- Internet Speed: Built-in speed test
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush
from ui.widgets import GlassCard, NeonButton, NeonProgressBar, SparklineChart
from monitoring.system_monitor import get_startup_apps, get_disk_usage_breakdown
import psutil
import threading


# ─────────────────────────────────────────────────────────────────
# Generic Worker Thread (prevents QTimer.singleShot from non-Qt threads)
# ─────────────────────────────────────────────────────────────────

class _FetchWorker(QThread):
    """Runs a callable in a QThread and emits result on main thread via signal."""
    result_ready = pyqtSignal(object)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        result = self._fn()
        self.result_ready.emit(result)


# ─────────────────────────────────────────────────────────────────
# STARTUP APP — known app database for recommendations
# ─────────────────────────────────────────────────────────────────

STARTUP_KNOWN = {
    "onedrive":      {"rec": "optional", "reason": "Disable if you don't use OneDrive.",
                     "use_case": "Syncs your files to Microsoft OneDrive cloud. Needed for auto-backup.",
                     "ram_est_mb": 80},
    "teams":         {"rec": "optional", "reason": "Slows boot significantly. Disable if not used daily.",
                     "use_case": "Microsoft Teams for video calls & chats. Heavy app, 300+ MB at startup.",
                     "ram_est_mb": 300},
    "docker":        {"rec": "developer", "reason": "Very heavy. Disable if not actively developing.",
                     "use_case": "Docker Desktop runs containers for software development. Uses 500+ MB RAM.",
                     "ram_est_mb": 500},
    "discord":       {"rec": "optional", "reason": "Disable for faster boot if you don't need it at startup.",
                     "use_case": "Gaming & community chat app. Opens on startup consuming ~150 MB RAM.",
                     "ram_est_mb": 150},
    "spotify":       {"rec": "optional", "reason": "Disable — open it manually when you want music.",
                     "use_case": "Music streaming. Safe to remove from startup; open manually when needed.",
                     "ram_est_mb": 100},
    "dropbox":       {"rec": "optional", "reason": "Disable if you don't rely on Dropbox sync.",
                     "use_case": "Syncs files to Dropbox cloud storage. Disable if using OneDrive instead.",
                     "ram_est_mb": 60},
    "googledrive":   {"rec": "optional", "reason": "Disable if not using Google Drive.",
                     "use_case": "Google Drive sync client. Runs in background to sync files with Google Cloud.",
                     "ram_est_mb": 80},
    "slack":         {"rec": "optional", "reason": "Disable for faster boot. Open manually for work.",
                     "use_case": "Work messaging platform. Safe to remove from startup and open manually.",
                     "ram_est_mb": 200},
    "zoom":          {"rec": "optional", "reason": "Remove from startup — open manually before meetings.",
                     "use_case": "Video conferencing. No need to run at startup; launch before meetings.",
                     "ram_est_mb": 80},
    "opera":         {"rec": "remove", "reason": "Browser startup is unnecessary and wastes RAM.",
                     "use_case": "Web browser. No benefit running at Windows startup. Open manually.",
                     "ram_est_mb": 50},
    "brave":         {"rec": "remove", "reason": "Browser startup is unnecessary and wastes RAM.",
                     "use_case": "Privacy-focused web browser. No need to auto-start with Windows.",
                     "ram_est_mb": 50},
    "chrome":        {"rec": "remove", "reason": "Chrome startup is unnecessary. Open manually.",
                     "use_case": "Google Chrome browser. Wastes 50+ MB RAM by starting with Windows.",
                     "ram_est_mb": 50},
    "msedge":        {"rec": "remove", "reason": "Edge startup wastes RAM. Open manually when needed.",
                     "use_case": "Microsoft Edge browser. Pre-loads for faster opening but wastes 50+ MB.",
                     "ram_est_mb": 50},
    "perplexity":    {"rec": "optional", "reason": "Disable if you open it manually.",
                     "use_case": "AI-powered search assistant. No need at startup — open from taskbar.",
                     "ram_est_mb": 80},
    "securityhealth":{"rec": "keep", "reason": "Windows Security — critical. Must keep enabled.",
                     "use_case": "Windows Defender security monitoring. Required for antivirus protection.",
                     "ram_est_mb": 20},
    "rtk":           {"rec": "keep", "reason": "Realtek audio driver — required for sound to work.",
                     "use_case": "Realtek HD Audio driver. Required for speakers and microphone to function.",
                     "ram_est_mb": 10},
    "insync":        {"rec": "optional", "reason": "Disable if not actively using Insync.",
                     "use_case": "Third-party Google Drive sync client. Disable if using Google Drive app directly.",
                     "ram_est_mb": 60},
    "mscopilot":     {"rec": "optional", "reason": "Disable if not using Copilot daily.",
                     "use_case": "Microsoft Copilot AI assistant. Disable from startup to save 100 MB RAM.",
                     "ram_est_mb": 100},
    "aisystemoptimizer": {"rec": "keep", "reason": "This app — greets you on startup.",
                     "use_case": "AI System Optimizer Assistant — your PC optimization tool. Keep for startup greetings.",
                     "ram_est_mb": 60},
    "microsoftlists":{"rec": "optional", "reason": "Can be opened manually when needed.",
                     "use_case": "Microsoft Lists task tracker. No benefit at startup — open manually.",
                     "ram_est_mb": 40},
    "cometsoftware": {"rec": "optional", "reason": "Software updater — can run on-demand instead.",
                     "use_case": "App auto-updater. Can be disabled and run manually to save background RAM.",
                     "ram_est_mb": 30},
    "edgeautolaunch":{"rec": "remove", "reason": "Edge pre-loader — wastes RAM. Remove.",
                     "use_case": "Pre-loads Microsoft Edge in background to make it open faster. Not worth the RAM cost.",
                     "ram_est_mb": 50},
}

REC_COLOR = {
    "keep":      "#00FF88",
    "optional":  "#FFB800",
    "remove":    "#FF2D55",
    "developer": "#00D4FF",
    "unknown":   "#4A6080",
}


def _get_recommendation(app_name: str) -> dict:
    name_lower = app_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for key, info in STARTUP_KNOWN.items():
        if key in name_lower or name_lower.startswith(key):
            return info
    return {
        "rec": "unknown",
        "reason": "Unknown app — research before disabling.",
        "use_case": "Purpose unknown. Search the app name online before disabling.",
        "ram_est_mb": 0,
    }


def _disable_startup_app(app: dict) -> tuple:
    """
    Disable/remove a startup entry from any source.
    Returns (success: bool, message: str)
    """
    import winreg, subprocess, os
    from pathlib import Path

    name   = app.get("name", "")
    source = app.get("source", "")
    path   = app.get("path", "")

    # ── Registry sources ──────────────────────────────────────────
    reg_map = {
        "Registry (User)":        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
        "Registry (User RunOnce)":(winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        "Registry (System)":      (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        "Registry (System RunOnce)":(winreg.HKEY_LOCAL_MACHINE,r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        "Registry (32-bit)":      (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    }
    if source in reg_map:
        hive, reg_path = reg_map[source]
        try:
            key = winreg.OpenKey(hive, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return True, f"Removed '{name}' from {source}."
        except FileNotFoundError:
            return False, f"'{name}' not found in {source}."
        except PermissionError:
            return False, f"Admin rights required to remove '{name}' from {source}."
        except Exception as e:
            return False, str(e)

    # ── Startup Folder sources ─────────────────────────────────────
    if "Startup Folder" in source:
        try:
            p = Path(path)
            if p.exists():
                p.unlink()
                return True, f"Removed '{name}' from startup folder."
            else:
                return False, f"File not found: {path}"
        except PermissionError:
            return False, f"Admin rights required to remove '{name}' from startup folder."
        except Exception as e:
            return False, str(e)

    # ── Task Scheduler ─────────────────────────────────────────────
    if source == "Task Scheduler":
        task_name = name.strip("\\")
        try:
            result = subprocess.run(
                ["schtasks", "/change", "/tn", task_name, "/disable"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return True, f"Disabled Task Scheduler task '{task_name}'."
            else:
                return False, f"Could not disable task: {result.stderr.strip()}"
        except Exception as e:
            return False, str(e)

    return False, f"Unknown source '{source}' — cannot disable automatically."


def _remove_startup_app(app: dict) -> tuple:
    """Full delete — same logic as disable but for Task Scheduler it deletes the task."""
    import winreg, subprocess
    from pathlib import Path

    name   = app.get("name", "")
    source = app.get("source", "")
    path   = app.get("path", "")

    if source == "Task Scheduler":
        task_name = name.strip("\\")
        try:
            result = subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return True, f"Deleted task '{task_name}'."
            else:
                return False, f"Could not delete task: {result.stderr.strip()}"
        except Exception as e:
            return False, str(e)

    # For registry / folder, disable = remove (same thing)
    return _disable_startup_app(app)


# ─────────────────────────────────────────────────────────────────
# PERFORMANCE PAGE
# ─────────────────────────────────────────────────────────────────

class PerformancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_chart = None
        self._ram_chart = None
        self._speed_worker = None  # prevent GC
        self._setup_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start(3000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Scroll Area to handle smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("⚡ Performance Monitor")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        layout.addWidget(title)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        cpu_card = GlassCard(accent_color="#00D4FF")
        cpu_l = QVBoxLayout(cpu_card)
        cpu_l.setContentsMargins(16, 14, 16, 14)
        cpu_l.addWidget(self._label("CPU Usage", "#00D4FF"))
        self._cpu_chart = SparklineChart("#00D4FF")
        cpu_l.addWidget(self._cpu_chart)
        self._cpu_val = QLabel("0%")
        self._cpu_val.setStyleSheet("color: #00D4FF; font-size: 24px; font-weight: 700; font-family: 'Segoe UI';")
        cpu_l.addWidget(self._cpu_val)

        ram_card = GlassCard(accent_color="#7C3AED")
        ram_l = QVBoxLayout(ram_card)
        ram_l.setContentsMargins(16, 14, 16, 14)
        ram_l.addWidget(self._label("RAM Usage", "#7C3AED"))
        self._ram_chart = SparklineChart("#7C3AED")
        ram_l.addWidget(self._ram_chart)
        self._ram_val = QLabel("0%")
        self._ram_val.setStyleSheet("color: #7C3AED; font-size: 24px; font-weight: 700; font-family: 'Segoe UI';")
        ram_l.addWidget(self._ram_val)

        charts_row.addWidget(cpu_card, 1)
        charts_row.addWidget(ram_card, 1)
        layout.addLayout(charts_row)

        # Internet speed card
        speed_card = GlassCard(accent_color="#00D4FF")
        speed_l = QVBoxLayout(speed_card)
        speed_l.setContentsMargins(16, 14, 16, 14)
        speed_hdr = QHBoxLayout()
        speed_hdr.addWidget(self._label("🌐 Internet Speed", "#00D4FF"))
        self._speed_btn = NeonButton("▶ Test Speed", "#00D4FF")
        self._speed_btn.setFixedWidth(120)
        self._speed_btn.clicked.connect(self._run_speed_test)
        speed_hdr.addStretch()
        speed_hdr.addWidget(self._speed_btn)
        speed_l.addLayout(speed_hdr)
        self._speed_result = QLabel("Click 'Test Speed' to measure your internet connection.")
        self._speed_result.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        self._speed_result.setWordWrap(True)
        speed_l.addWidget(self._speed_result)
        layout.addWidget(speed_card)

        # Disk breakdown
        disk_card = GlassCard(accent_color="#00FF88")
        disk_l = QVBoxLayout(disk_card)
        disk_l.setContentsMargins(16, 14, 16, 14)
        disk_l.addWidget(self._label("Disk Usage", "#00FF88"))
        self._disk_container = QVBoxLayout()
        self._disk_container.setSpacing(8)
        disk_l.addLayout(self._disk_container)
        layout.addWidget(disk_card)

        # AI Tips card
        tips_card = GlassCard(accent_color="#7C3AED")
        tips_l = QVBoxLayout(tips_card)
        tips_l.setContentsMargins(16, 14, 16, 14)
        tips_hdr = QHBoxLayout()
        tips_hdr.addWidget(self._label("🧠 AI Performance Tips", "#7C3AED"))
        self._tips_btn = NeonButton("↻ Analyze Now", "#7C3AED")
        self._tips_btn.setFixedWidth(140)
        self._tips_btn.clicked.connect(self._load_tips)
        tips_hdr.addStretch()
        tips_hdr.addWidget(self._tips_btn)
        tips_l.addLayout(tips_hdr)
        self._tips_container = QVBoxLayout()
        self._tips_container.setSpacing(6)
        tips_l.addLayout(self._tips_container)
        layout.addWidget(tips_card)
        
        layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)
        self._refresh()
        QTimer.singleShot(500, self._load_tips)  # Load tips on startup

    def _refresh(self):
        try:
            cpu = psutil.cpu_percent()
            vm  = psutil.virtual_memory()
            self._cpu_val.setText(f"{cpu:.1f}%")
            self._ram_val.setText(f"{vm.percent:.1f}%")
            if self._cpu_chart:
                self._cpu_chart.add_point(cpu)
            if self._ram_chart:
                self._ram_chart.add_point(vm.percent)
            self._refresh_disk()
        except Exception:
            pass

    def _refresh_disk(self):
        while self._disk_container.count():
            item = self._disk_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            for mount, info in get_disk_usage_breakdown().items():
                row = QHBoxLayout()
                lbl = QLabel(f"{mount}  ({info['fstype']})")
                lbl.setStyleSheet("color: #E8F4FD; font-size: 11px; font-family: 'Segoe UI';")
                lbl.setFixedWidth(120)
                bar = NeonProgressBar("#00FF88")
                bar.setValue(int(info["percent"]))
                val_lbl = QLabel(f"{info['used_gb']}/{info['total_gb']} GB  ({info['percent']:.0f}%)")
                val_lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-family: 'Segoe UI';")
                row.addWidget(lbl)
                row.addWidget(bar, 1)
                row.addWidget(val_lbl)
                container = QWidget()
                container.setLayout(row)
                container.setStyleSheet("background: transparent;")
                self._disk_container.addWidget(container)
        except Exception:
            pass

    def _run_speed_test(self):
        self._speed_btn.setEnabled(False)
        self._speed_result.setText("⏳ Testing internet speed... (10-30 seconds)")
        self._speed_result.setStyleSheet("color: #FFB800; font-size: 12px; font-family: 'Segoe UI';")

        def _test():
            try:
                import urllib.request, time
                url = "http://ipv4.download.thinkbroadband.com/1MB.zip"
                start = time.time()
                req = urllib.request.urlopen(url, timeout=25)
                data = req.read()
                elapsed = max(time.time() - start, 0.001)
                dl_mbps = (len(data) / 1e6 * 8) / elapsed
                ping_ms = self._ping_test()
                return f"📥 Download: {dl_mbps:.1f} Mbps   🏓 Ping: {ping_ms} ms", True
            except Exception as e:
                return f"Speed test failed: {e}", False

        def _on_result(r):
            text, ok = r
            self._show_speed(text, ok)

        self._speed_worker = _FetchWorker(_test)
        self._speed_worker.result_ready.connect(_on_result)
        self._speed_worker.start()

    def _ping_test(self) -> str:
        try:
            import subprocess, time
            result = subprocess.run(
                ["ping", "-n", "4", "8.8.8.8"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if "Average" in line or "avg" in line.lower():
                    parts = line.split("=")
                    if parts:
                        return parts[-1].strip().replace("ms", "").strip()
            return "N/A"
        except Exception:
            return "N/A"

    def _show_speed(self, result: str, success: bool):
        self._speed_btn.setEnabled(True)
        color = "#00FF88" if success else "#FF2D55"
        self._speed_result.setText(result)
        self._speed_result.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600; font-family: 'Segoe UI';")

    def update_metrics(self, m):
        pass  # Auto-refreshes via timer

    def _load_tips(self):
        self._tips_btn.setEnabled(False)
        # Clear old tips
        while self._tips_container.count():
            item = self._tips_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        loading = QLabel("⏳ Analyzing your system...")
        loading.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
        self._tips_container.addWidget(loading)

        worker = _FetchWorker(generate_ai_tips)
        worker.result_ready.connect(self._show_tips)
        worker.start()
        self._speed_worker = worker  # reuse ref slot to prevent GC

    def _show_tips(self, tips: list):
        self._tips_btn.setEnabled(True)
        while self._tips_container.count():
            item = self._tips_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for level, msg, color in tips:
            # Outer wrapper so it doesn't stretch full width
            outer = QWidget()
            outer.setStyleSheet("background: transparent;")
            outer_l = QHBoxLayout(outer)
            outer_l.setContentsMargins(0, 0, 0, 0)

            row = QFrame()
            row.setStyleSheet(
                f"background: {color}18; "
                f"border: 1px solid {color}50; "
                "border-radius: 6px; "
            )
            row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(12, 8, 12, 8)
            r_layout.setSpacing(12)

            lvl_lbl = QLabel(level)
            lvl_lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: 700; "
                "font-family: 'Segoe UI'; background: transparent; border: none;"
            )
            lvl_lbl.setFixedWidth(110)

            msg_lbl = QLabel(msg)
            msg_lbl.setStyleSheet(
                "color: #E8F4FD; font-size: 11px; font-family: 'Segoe UI'; "
                "background: transparent; border: none;"
            )
            msg_lbl.setWordWrap(True)
            msg_lbl.setMinimumHeight(30) # Ensure text isn't cut off

            r_layout.addWidget(lvl_lbl)
            r_layout.addWidget(msg_lbl, 1)

            outer_l.addWidget(row, 1)
            self._tips_container.addWidget(outer)


    def _label(self, text, color="#8BA3C7"):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';")
        return l


# ─────────────────────────────────────────────────────────────────
# STARTUP APPS PAGE — with AI recommendations + disable button
# ─────────────────────────────────────────────────────────────────

class StartupAppsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps = []
        self._fetch_worker = None  # prevent GC
        self._disable_workers = []  # prevent GC
        self._setup_ui()
        QTimer.singleShot(300, self._load_apps)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("🚀 Startup Apps")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        refresh_btn = NeonButton("🔄 Refresh", "#00D4FF")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._load_apps)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        info = QLabel(
            "Apps marked 🔴 Remove slow down your boot. "
            "🟡 Optional = safe to disable. 🟢 Keep = system required."
        )
        info.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Summary bar
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            "color: #FFB800; font-size: 11px; font-family: 'Segoe UI'; "
            "background: #FFB80010; border: 1px solid #FFB80030; border-radius: 6px; padding: 6px 12px;"
        )
        self._summary_lbl.setWordWrap(True)
        layout.addWidget(self._summary_lbl)

        # AI Analyze Button
        btn_row = QHBoxLayout()
        self._ai_btn = NeonButton("🤖 Re-analyze with AI", "#7C3AED")
        self._ai_btn.setFixedWidth(180)
        self._ai_btn.clicked.connect(self._reanalyze_with_ai)
        btn_row.addStretch()
        btn_row.addWidget(self._ai_btn)
        layout.addLayout(btn_row)

        card = GlassCard(accent_color="#FF6B00")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)

        # Table: # | Name | Use Case | RAM Est | Status | Suggestion | Action
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["#", "App Name", "Source", "What It Does / AI Advice", "RAM Est.", "AI Rating", "Action"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 160)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #080C18; color: #E8F4FD;
                border: none; gridline-color: #1E2D45;
                font-family: 'Segoe UI'; font-size: 11px;
            }
            QHeaderView::section {
                background: #111827; color: #8BA3C7;
                border: 1px solid #1E2D45; padding: 6px;
                font-family: 'Segoe UI'; font-size: 11px; font-weight: 600;
            }
            QTableWidget::item:alternate { background: #0D1221; }
            QTableWidget::item:selected { background: #1E2D45; }
        """)
        cl.addWidget(self._table)
        layout.addWidget(card, 1)

        # Status message
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;")
        layout.addWidget(self._status_lbl)

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _load_apps(self):
        self._status_lbl.setText("⏳ Loading startup apps...")
        self._table.setRowCount(0)
        # Use QThread so result signal delivers on main thread
        self._fetch_worker = _FetchWorker(get_startup_apps)
        self._fetch_worker.result_ready.connect(self._populate)
        self._fetch_worker.start()

    def _populate(self, apps: list):
        self._apps = apps
        self._table.setRowCount(len(apps))
        self._table.verticalHeader().setDefaultSectionSize(46)

        total_ram = 0
        removable = 0

        for i, app in enumerate(apps):
            name     = app.get("name", "")
            source   = app.get("source", "Registry")
            rec_info = _get_recommendation(name)
            rec      = rec_info["rec"]
            use_case = rec_info.get("use_case", "Unknown purpose.")
            reason   = rec_info["reason"]
            ram_mb   = rec_info["ram_est_mb"]
            total_ram += ram_mb
            if rec in ("remove", "optional"):
                removable += 1

            color = REC_COLOR.get(rec, "#4A6080")

            # Col 0: row number
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setForeground(QBrush(QColor("#4A6080")))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 0, num_item)

            # Col 1: App Name
            item_name = QTableWidgetItem(name)
            item_name.setForeground(QBrush(QColor(color)))
            item_name.setToolTip(app.get("path", ""))
            self._table.setItem(i, 1, item_name)

            # Col 2: Source (Registry/Folder/Task)
            src_short = source.replace("Registry ", "").replace("Startup Folder ", "📁 ")
            if "Task Scheduler" in source:
                src_short = "🗓 Task"
            elif "System" in source:
                src_short = "🖥 Registry"
            elif "User" in source and "RunOnce" not in source:
                src_short = "👤 Registry"
            elif "32-bit" in source:
                src_short = "🖥 Reg 32b"
            item_src = QTableWidgetItem(src_short)
            item_src.setForeground(QBrush(QColor("#8BA3C7")))
            item_src.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_src.setToolTip(source + "\n" + app.get("path", ""))
            self._table.setItem(i, 2, item_src)

            # Col 3: What It Does / AI Advice
            advice_text = f"{use_case}  |  💡 {reason}"
            item_use = QTableWidgetItem(advice_text)
            item_use.setForeground(QBrush(QColor("#E8F4FD")))
            item_use.setToolTip(advice_text)
            self._table.setItem(i, 3, item_use)

            # Col 4: RAM estimate
            ram_text = f"~{ram_mb} MB" if ram_mb > 0 else "?"
            ram_color = "#FF2D55" if ram_mb > 300 else "#FFB800" if ram_mb > 100 else "#8BA3C7"
            item_ram = QTableWidgetItem(ram_text)
            item_ram.setForeground(QBrush(QColor(ram_color)))
            item_ram.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 4, item_ram)

            # Col 5: AI Rating badge
            status_map = {
                "keep":      "✅ Keep",
                "optional":  "🟡 Optional",
                "remove":    "🔴 Remove",
                "developer": "🔵 Dev Tool",
                "unknown":   "❓ Unknown",
            }
            item_status = QTableWidgetItem(status_map.get(rec, "❓"))
            item_status.setForeground(QBrush(QColor(color)))
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 5, item_status)

            # Col 6: Action buttons — Disable + Remove
            if rec != "keep":
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 3, 4, 3)
                btn_layout.setSpacing(6)

                # Disable button (for registry: removes entry; for tasks: disables task)
                dis_btn = QPushButton("⏸ Disable")
                dis_btn.setFixedHeight(26)
                dis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                dis_btn.setStyleSheet("""
                    QPushButton {
                        background: #FFB80020; color: #FFB800;
                        border: 1px solid #FFB80050; border-radius: 5px;
                        font-size: 10px; font-family: 'Segoe UI'; font-weight: 600;
                        padding: 0 8px;
                    }
                    QPushButton:hover { background: #FFB80050; }
                    QPushButton:disabled { color: #4A6080; border-color: #1E2D45; background: transparent; }
                """)
                dis_btn.clicked.connect(lambda _, a=app, r=i: self._do_action(a, r, remove=False))

                # Remove button (hard delete / task delete)
                rem_btn = QPushButton("🗑 Remove")
                rem_btn.setFixedHeight(26)
                rem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                rem_btn.setStyleSheet("""
                    QPushButton {
                        background: #FF2D5520; color: #FF2D55;
                        border: 1px solid #FF2D5550; border-radius: 5px;
                        font-size: 10px; font-family: 'Segoe UI'; font-weight: 600;
                        padding: 0 8px;
                    }
                    QPushButton:hover { background: #FF2D5550; }
                    QPushButton:disabled { color: #4A6080; border-color: #1E2D45; background: transparent; }
                """)
                rem_btn.clicked.connect(lambda _, a=app, r=i: self._do_action(a, r, remove=True))

                btn_layout.addWidget(dis_btn)
                btn_layout.addWidget(rem_btn)
                self._table.setCellWidget(i, 6, btn_widget)

        summary = (
            f"⚡ {len(apps)} startup entries  |  "
            f"~{total_ram} MB RAM at boot  |  "
            f"{removable} can be disabled to speed up boot"
        )
        self._summary_lbl.setText(summary)
        self._status_lbl.setText(f"✅ Loaded {len(apps)} startup entries from all sources")

    def _reanalyze_with_ai(self):
        """Use Ollama to identify unknown startup apps."""
        unknown_apps = []
        for i, app in enumerate(self._apps):
            name = app.get("name", "")
            rec_info = _get_recommendation(name)
            if rec_info["rec"] == "unknown":
                unknown_apps.append((i, name))
        
        if not unknown_apps:
            self._status_lbl.setText("✅ No unknown apps found. All apps identified!")
            return

        self._status_lbl.setText(f"🧠 AI is identifying {len(unknown_apps)} apps...")
        self._ai_btn.setEnabled(False)

        def _ai_task():
            from ai.ai_service import AIService
            service = AIService.get_instance()
            if not service.is_configured:
                return "AI Not Configured"
            
            names = [name for i, name in unknown_apps]
            prompt = (
                f"I have these unknown Windows startup apps: {', '.join(names)}. "
                "Briefly explain what each one likely is in 1 sentence. "
                "Format as 'AppName: Explanation'. One per line."
            )
            try:
                return service.chat(prompt)
            except Exception as e:
                return str(e)

        def _ai_done(result):
            self._ai_btn.setEnabled(True)
            if "Error" in result or "Configured" in result:
                self._status_lbl.setText(f"⚠️ AI error: {result}")
                return

            # Parse results
            lines = result.strip().split("\n")
            count = 0
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    app_name_guess = parts[0].strip().lower()
                    explanation = parts[1].strip()
                    
                    # Match back to row
                    for row_idx, real_name in unknown_apps:
                        if app_name_guess in real_name.lower() or real_name.lower() in app_name_guess:
                            # Update Col 2 (Purpose)
                            item = QTableWidgetItem(f"🤖 {explanation}")
                            item.setForeground(QBrush(QColor("#00D4FF")))
                            item.setToolTip(f"AI Guess: {explanation}")
                            self._table.setItem(row_idx, 2, item)
                            # Update Col 4 (Status)
                            status_item = QTableWidgetItem("🔍 AI Suggest")
                            status_item.setForeground(QBrush(QColor("#00D4FF")))
                            self._table.setItem(row_idx, 4, status_item)
                            count += 1
            
            self._status_lbl.setText(f"✨ AI successfully identified {count} apps!")

        worker = _FetchWorker(_ai_task)
        worker.result_ready.connect(_ai_done)
        worker.start()
        self._disable_workers.append(worker)

    def _do_action(self, app: dict, row: int, remove: bool):
        """Disable or remove a startup entry — source-aware."""
        name = app.get("name", "")
        action_fn = _remove_startup_app if remove else _disable_startup_app
        verb = "Remove" if remove else "Disable"

        def _do():
            return action_fn(app)

        def _update(result):
            success, msg = result
            if success:
                self._status_lbl.setText(f"✅ {verb}d: {msg}")
                self._status_lbl.setStyleSheet(
                    "color: #00FF88; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;"
                )
                # Grey out the entire row
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item:
                        item.setForeground(QBrush(QColor("#4A6080")))
                # Disable both action buttons
                w = self._table.cellWidget(row, 6)
                if w:
                    for btn in w.findChildren(QPushButton):
                        btn.setEnabled(False)
                        btn.setText(f"{'Removed' if remove else 'Disabled'}")
            else:
                self._status_lbl.setText(f"⚠️ {verb} failed: {msg}")
                self._status_lbl.setStyleSheet(
                    "color: #FFB800; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;"
                )

        worker = _FetchWorker(_do)
        worker.result_ready.connect(_update)
        worker.start()
        self._disable_workers.append(worker)

    # Keep backward compat alias
    def _disable_app(self, app_name: str, row: int):
        for i, app in enumerate(self._apps):
            if app.get("name") == app_name:
                self._do_action(app, row, remove=False)
                return


# ─────────────────────────────────────────────────────────────────
# AI TIPS — rule-based performance advisor
# ─────────────────────────────────────────────────────────────────

def generate_ai_tips() -> list:
    """Analyze current system state and return actionable tips."""
    import psutil
    tips = []
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    du = psutil.disk_usage("C:\\")

    if vm.percent > 80:
        tips.append(("🔴 Critical", "RAM usage is very high ({}%). Close unused apps or run memory cleanup.".format(int(vm.percent)), "#FF2D55"))
    elif vm.percent > 60:
        tips.append(("🟡 Warning", "RAM at {}%. Consider disabling startup apps to free memory.".format(int(vm.percent)), "#FFB800"))
    else:
        tips.append(("🟢 Good", "RAM usage is healthy at {}%.".format(int(vm.percent)), "#00FF88"))

    if cpu > 80:
        tips.append(("🔴 CPU High", "CPU at {}%. Check for runaway processes in Task Manager.".format(int(cpu)), "#FF2D55"))
    elif cpu > 50:
        tips.append(("🟡 CPU Moderate", "CPU at {}%. Some apps are heavy — consider a cleanup.".format(int(cpu)), "#FFB800"))

    if du.percent > 90:
        tips.append(("🔴 Disk Critical", "Disk C:\\ is {}% full. Run cleanup immediately to avoid slowdowns.".format(int(du.percent)), "#FF2D55"))
    elif du.percent > 75:
        tips.append(("🟡 Disk Warning", "Disk C:\\ is {}% full. Consider clearing temp files.".format(int(du.percent)), "#FFB800"))
    else:
        tips.append(("🟢 Disk OK", "Disk space healthy — {:.1f} GB free on C:\\." .format(du.free / 1e9), "#00FF88"))

    # Check for heavy startup apps
    try:
        from monitoring.system_monitor import get_startup_apps
        startup = get_startup_apps()
        heavy = [a["name"] for a in startup if any(
            k in a["name"].lower() for k in ["teams", "docker", "discord", "slack"]
        )]
        if heavy:
            tips.append(("💡 Startup Tip", f"Heavy apps in startup: {', '.join(heavy[:3])}. Disable from Startup Apps tab to speed up boot.", "#00D4FF"))
    except Exception:
        pass

    # Check for SSD vs HDD
    try:
        import subprocess
        ps = subprocess.check_output('powershell -NoProfile -Command "Get-PhysicalDisk | Select-Object MediaType"', shell=True).decode()
        if "HDD" in ps:
            tips.append(("💡 Hardware Tip", "You have an HDD detected. Disabling all non-essential startup apps is CRITICAL for your performance.", "#FFB800"))
    except Exception:
        pass

    tips.append(("💡 Best Practice", "Run a system cleanup weekly to keep your PC running at peak speed.", "#7C3AED"))
    tips.append(("💡 Power Tip", "Check 'Power & Sleep settings' — Ensure 'High Performance' mode is active for best speed.", "#00D4FF"))
    return tips
