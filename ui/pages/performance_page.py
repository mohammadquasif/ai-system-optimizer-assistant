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
    "onedrive":          {"rec": "optional", "reason": "Cloud sync. Disable if you don't use OneDrive.", "ram_est_mb": 80},
    "teams":             {"rec": "optional", "reason": "MS Teams auto-start. Slows boot. Disable if not used.", "ram_est_mb": 300},
    "docker":            {"rec": "developer", "reason": "Docker Desktop. Heavy (500+ MB). Disable if not developing.", "ram_est_mb": 500},
    "discord":           {"rec": "optional", "reason": "Gaming chat. Disable if you don't need it at startup.", "ram_est_mb": 150},
    "spotify":           {"rec": "optional", "reason": "Music player. Disable for faster boot.", "ram_est_mb": 100},
    "dropbox":           {"rec": "optional", "reason": "Cloud sync. Disable if not using Dropbox.", "ram_est_mb": 60},
    "googledrive":       {"rec": "optional", "reason": "Google Drive sync. Disable if not needed.", "ram_est_mb": 80},
    "slack":             {"rec": "optional", "reason": "Work chat. Disable for faster boot if not needed.", "ram_est_mb": 200},
    "zoom":              {"rec": "optional", "reason": "Video meetings. Safe to disable from startup.", "ram_est_mb": 80},
    "opera":             {"rec": "remove", "reason": "Browser at startup is unnecessary.", "ram_est_mb": 50},
    "brave":             {"rec": "remove", "reason": "Browser at startup is unnecessary.", "ram_est_mb": 50},
    "chrome":            {"rec": "remove", "reason": "Browser at startup is unnecessary.", "ram_est_mb": 50},
    "msedge":            {"rec": "remove", "reason": "Edge at startup is unnecessary.", "ram_est_mb": 50},
    "perplexity":        {"rec": "optional", "reason": "AI search app. Disable if you open it manually.", "ram_est_mb": 80},
    "securityhealth":    {"rec": "keep", "reason": "Windows Security — important. Keep enabled.", "ram_est_mb": 20},
    "rtk":               {"rec": "keep", "reason": "Realtek audio driver. Required for sound.", "ram_est_mb": 10},
    "insync":            {"rec": "optional", "reason": "Cloud sync tool. Disable if not needed.", "ram_est_mb": 60},
    "mscopilot":         {"rec": "optional", "reason": "MS Copilot. Disable if not using at startup.", "ram_est_mb": 100},
    "aisystemoptimizer": {"rec": "keep", "reason": "This app — greets you on startup. Keep if desired.", "ram_est_mb": 60},
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
    return {"rec": "unknown", "reason": "Unknown app — research before disabling.", "ram_est_mb": 0}


def _disable_startup_app(app_name: str) -> bool:
    """Remove an app from Windows startup registry (current user only)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


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
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("⚡ Performance Monitor")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        root.addWidget(title)

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
        root.addLayout(charts_row)

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
        root.addWidget(speed_card)

        # Disk breakdown
        disk_card = GlassCard(accent_color="#00FF88")
        disk_l = QVBoxLayout(disk_card)
        disk_l.setContentsMargins(16, 14, 16, 14)
        disk_l.addWidget(self._label("Disk Usage", "#00FF88"))
        self._disk_container = QVBoxLayout()
        self._disk_container.setSpacing(8)
        disk_l.addLayout(self._disk_container)
        root.addWidget(disk_card)
        root.addStretch()
        self._refresh()

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
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("🚀 Startup Apps")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        refresh_btn = NeonButton("🔄 Refresh", "#00D4FF")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._load_apps)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        info = QLabel(
            "Apps marked 🔴 Remove slow down your boot. "
            "🟡 Optional = safe to disable. 🟢 Keep = system required."
        )
        info.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        info.setWordWrap(True)
        root.addWidget(info)

        # Summary bar
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            "color: #FFB800; font-size: 11px; font-family: 'Segoe UI'; "
            "background: #FFB80010; border: 1px solid #FFB80030; border-radius: 6px; padding: 6px 12px;"
        )
        self._summary_lbl.setWordWrap(True)
        root.addWidget(self._summary_lbl)

        card = GlassCard(accent_color="#FF6B00")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)

        # Table: Name | RAM Est | Recommendation | Reason | Disable
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["App Name", "RAM Est.", "Status", "AI Suggestion", "Action"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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
        root.addWidget(card, 1)

        # Status message
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;")
        root.addWidget(self._status_lbl)

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

        total_ram = 0
        removable = 0

        for i, app in enumerate(apps):
            name = app.get("name", "")
            path = app.get("path", "")
            rec_info = _get_recommendation(name)
            rec  = rec_info["rec"]
            reason = rec_info["reason"]
            ram_mb = rec_info["ram_est_mb"]
            total_ram += ram_mb
            if rec in ("remove", "optional"):
                removable += 1

            color = REC_COLOR.get(rec, "#4A6080")

            # Col 0: App Name
            item_name = QTableWidgetItem(name)
            item_name.setForeground(QBrush(QColor(color)))
            self._table.setItem(i, 0, item_name)

            # Col 1: RAM estimate
            ram_text = f"~{ram_mb} MB" if ram_mb > 0 else "Unknown"
            item_ram = QTableWidgetItem(ram_text)
            item_ram.setForeground(QBrush(QColor("#FFB800" if ram_mb > 200 else "#8BA3C7")))
            item_ram.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 1, item_ram)

            # Col 2: Status badge
            status_map = {
                "keep": "✅ Keep",
                "optional": "🟡 Optional",
                "remove": "🔴 Remove",
                "developer": "🔵 Dev Tool",
                "unknown": "❓ Unknown",
            }
            item_status = QTableWidgetItem(status_map.get(rec, "❓ Unknown"))
            item_status.setForeground(QBrush(QColor(color)))
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 2, item_status)

            # Col 3: Reason / AI suggestion
            item_reason = QTableWidgetItem(reason)
            item_reason.setForeground(QBrush(QColor("#8BA3C7")))
            self._table.setItem(i, 3, item_reason)

            # Col 4: Disable button (only for optional/remove)
            if rec in ("optional", "remove", "unknown"):
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                disable_btn = QPushButton("Disable")
                disable_btn.setFixedHeight(24)
                disable_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                disable_btn.setStyleSheet("""
                    QPushButton {
                        background: #FF2D5520; color: #FF2D55;
                        border: 1px solid #FF2D5540; border-radius: 4px;
                        font-size: 10px; font-family: 'Segoe UI'; padding: 0 8px;
                    }
                    QPushButton:hover { background: #FF2D5540; }
                    QPushButton:disabled { color: #4A6080; border-color: #1E2D45; background: transparent; }
                """)
                disable_btn.clicked.connect(lambda _, n=name, r=i: self._disable_app(n, r))
                btn_layout.addWidget(disable_btn)
                btn_layout.addStretch()
                btn_widget.setStyleSheet("background: transparent;")
                self._table.setCellWidget(i, 4, btn_widget)

        # Summary bar
        summary = (
            f"⚡ {len(apps)} startup apps detected  |  "
            f"~{total_ram} MB RAM used at startup  |  "
            f"{removable} apps can be disabled to free RAM and speed up boot"
        )
        self._summary_lbl.setText(summary)
        self._status_lbl.setText(f"✅ Loaded {len(apps)} startup apps")

    def _disable_app(self, app_name: str, row: int):
        """Disable startup entry for this app."""
        def _do():
            return _disable_startup_app(app_name)

        def _update(success):
            if success:
                self._status_lbl.setText(f"✅ Disabled: {app_name}. Restart to take effect.")
                self._status_lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;")
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item:
                        item.setForeground(QBrush(QColor("#4A6080")))
                w = self._table.cellWidget(row, 4)
                if w:
                    btn = w.findChild(QPushButton)
                    if btn:
                        btn.setEnabled(False)
                        btn.setText("Disabled")
            else:
                self._status_lbl.setText(f"⚠️ Could not disable {app_name} — may need admin rights.")
                self._status_lbl.setStyleSheet("color: #FFB800; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;")

        worker = _FetchWorker(_do)
        worker.result_ready.connect(_update)
        worker.start()
        self._disable_workers.append(worker)  # prevent GC
