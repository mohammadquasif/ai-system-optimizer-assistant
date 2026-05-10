"""
Dashboard Page - Fixed top memory consumers layout, added uninstall button placeholder
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QFrame, QSizePolicy, QPushButton, QSpacerItem,
    QDialog, QTextEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ui.widgets import (
    GlassCard, CircularGauge, NeonButton, SparklineChart,
    MetricLabel, NeonProgressBar, StatusBadge,
)
from monitoring.system_monitor import SystemMetrics
import psutil


class DashboardPage(QWidget):
    request_cleanup = pyqtSignal()
    request_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_history = []
        self._ram_history = []
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("🖥️ System Dashboard")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        subtitle = QLabel("Real-time monitoring & quick actions")
        subtitle.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self._health_badge = QLabel("● 100")
        self._health_badge.setStyleSheet("color: #00FF88; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';")
        health_lbl = QLabel("Health Score")
        health_lbl.setStyleSheet("color: #8BA3C7; font-size: 10px;")
        health_col = QVBoxLayout()
        health_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        health_col.addWidget(self._health_badge)
        health_col.addWidget(health_lbl)

        header.addLayout(title_col)
        header.addStretch()
        header.addLayout(health_col)
        root.addLayout(header)

        # ── Gauges Row ───────────────────────────────────────────
        gauges_card = GlassCard(accent_color="#00D4FF")
        gauges_layout = QHBoxLayout(gauges_card)
        gauges_layout.setContentsMargins(20, 20, 20, 20)
        gauges_layout.setSpacing(0)

        self._cpu_gauge  = CircularGauge("CPU",  "#00D4FF", size=130)
        self._ram_gauge  = CircularGauge("RAM",  "#7C3AED", size=130)
        self._disk_gauge = CircularGauge("DISK", "#00FF88", size=130)
        self._net_metric = MetricLabel("🌐", "Network ↓", "#FFB800")

        for w in [self._cpu_gauge, self._ram_gauge, self._disk_gauge]:
            gauges_layout.addWidget(w, alignment=Qt.AlignmentFlag.AlignCenter)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet("color: #1E2D45; background: #1E2D45; max-width: 1px;")
            gauges_layout.addWidget(sep)
        gauges_layout.addWidget(self._net_metric, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(gauges_card)

        # ── Charts Row ───────────────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        cpu_card = GlassCard(accent_color="#00D4FF")
        cl = QVBoxLayout(cpu_card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.addWidget(self._lbl("CPU Usage History", "#00D4FF"))
        self._cpu_chart = SparklineChart(color="#00D4FF")
        cl.addWidget(self._cpu_chart)
        ram_card = GlassCard(accent_color="#7C3AED")
        rl = QVBoxLayout(ram_card)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.addWidget(self._lbl("RAM Usage History", "#7C3AED"))
        self._ram_chart = SparklineChart(color="#7C3AED")
        rl.addWidget(self._ram_chart)
        charts_row.addWidget(cpu_card, 1)
        charts_row.addWidget(ram_card, 1)
        root.addLayout(charts_row)

        # ── Quick Actions + Stats ────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setSpacing(16)

        opt_card = GlassCard(accent_color="#00FF88")
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.setContentsMargins(20, 20, 20, 20)
        opt_layout.setSpacing(10)
        opt_layout.addWidget(self._lbl("⚡ Quick Optimize", "#00FF88", 14, True))
        desc = QLabel("Safely clean temp files, browser cache,\nand thumbnail cache in one click.")
        desc.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
        desc.setWordWrap(True)
        opt_layout.addWidget(desc)
        self._optimize_btn = NeonButton("▶  Run Quick Optimize", "#00FF88")
        self._optimize_btn.clicked.connect(self.request_cleanup.emit)
        opt_layout.addWidget(self._optimize_btn)
        self._last_cleanup_lbl = QLabel("Last cleanup: Never")
        self._last_cleanup_lbl.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")
        opt_layout.addWidget(self._last_cleanup_lbl)
        opt_layout.addStretch()

        info_card = GlassCard(accent_color="#7C3AED")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(8)
        info_layout.addWidget(self._lbl("📊 System Stats", "#7C3AED", 14, True))
        self._stat_labels = {}
        for key, lbl_text in [
            ("cpu_cores", "CPU Cores"), ("ram_total", "Total RAM"),
            ("disk_total", "Disk Total"), ("disk_free", "Disk Free"),
            ("cpu_temp", "CPU Temp"),
        ]:
            row = QHBoxLayout()
            row.addWidget(self._lbl(lbl_text))
            row.addStretch()
            v = self._lbl("--", "#E8F4FD")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(v)
            info_layout.addLayout(row)
            self._stat_labels[key] = v
        info_layout.addStretch()
        self._populate_static_stats()

        actions_row.addWidget(opt_card, 1)
        actions_row.addWidget(info_card, 1)
        root.addLayout(actions_row)

        # ── Top Memory Consumers — FIXED LAYOUT ──────────────────
        procs_card = GlassCard(accent_color="#FF6B00")
        procs_layout = QVBoxLayout(procs_card)
        procs_layout.setContentsMargins(20, 14, 20, 14)
        procs_layout.setSpacing(6)
        procs_layout.addWidget(self._lbl("🔥 Top Memory Consumers", "#FF6B00", 13, True))

        # Header row
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(self._lbl("Process", "#4A6080", 10))
        hdr_row.addStretch()
        hdr_row.addWidget(self._lbl("RAM %", "#4A6080", 10))
        procs_layout.addLayout(hdr_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1E2D45; max-height: 1px;")
        procs_layout.addWidget(sep)

        self._procs_container = QVBoxLayout()
        self._procs_container.setSpacing(5)
        procs_layout.addLayout(self._procs_container)
        # Populate immediately with current procs
        self._refresh_procs()
        root.addWidget(procs_card)
        root.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _refresh_procs(self):
        """Populate top memory consumers immediately on load."""
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    info = p.info
                    if info["memory_percent"] and info["memory_percent"] > 0.1:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
            self._update_procs(procs[:7])
        except Exception:
            pass

    def _populate_static_stats(self):
        try:
            self._stat_labels["cpu_cores"].setText(f"{psutil.cpu_count(logical=True)} cores")
            vm = psutil.virtual_memory()
            self._stat_labels["ram_total"].setText(f"{round(vm.total/1e9,1)} GB")
            du = psutil.disk_usage("C:\\")
            self._stat_labels["disk_total"].setText(f"{round(du.total/1e9,1)} GB")
        except Exception:
            pass

    def update_metrics(self, m: SystemMetrics):
        """Called from main window with new metrics — always on main thread."""
        self._cpu_gauge.set_value(m.cpu_percent)
        self._ram_gauge.set_value(m.ram_percent)
        self._disk_gauge.set_value(m.disk_percent)
        self._net_metric.set_value(f"↓{m.network_recv_mb:.1f} ↑{m.network_sent_mb:.1f} MB/s")
        self._cpu_chart.add_point(m.cpu_percent)
        self._ram_chart.add_point(m.ram_percent)

        score = m.health_score
        color = "#00FF88" if score >= 70 else "#FFB800" if score >= 40 else "#FF2D55"
        self._health_badge.setText(f"● {score}")
        self._health_badge.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';")

        self._stat_labels["disk_free"].setText(f"{m.disk_free_gb} GB")
        self._stat_labels["cpu_temp"].setText(f"{m.cpu_temp:.0f}°C" if m.cpu_temp else "N/A")

        if m.top_processes:
            self._update_procs(m.top_processes[:7])

    def _update_procs(self, procs: list):
        # Clear old widgets
        while self._procs_container.count():
            item = self._procs_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for p in procs:
            name_str = str(p.get("name", "Unknown"))
            mem_val  = float(p.get("memory_percent", 0) or 0)

            # Container widget for each row
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            # Process name — fixed minimum width so bar doesn't squash it
            name_lbl = QLabel(name_str[:28])
            name_lbl.setStyleSheet("color: #E8F4FD; font-size: 11px; font-family: 'Segoe UI';")
            name_lbl.setFixedWidth(180)
            name_lbl.setToolTip(name_str)

            # Progress bar
            bar = NeonProgressBar("#FF6B00")
            # Scale: 5% RAM = full bar (most processes are under 5%)
            bar.setValue(min(100, int(mem_val * 20)))
            bar.setMinimumWidth(80)

            # Percentage label
            mem_lbl = QLabel(f"{mem_val:.1f}%")
            mem_lbl.setStyleSheet("color: #FF6B00; font-size: 11px; font-weight: 600; font-family: 'Segoe UI';")
            mem_lbl.setFixedWidth(42)
            mem_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row_layout.addWidget(name_lbl)
            row_layout.addWidget(bar, 1)
            row_layout.addWidget(mem_lbl)
            self._procs_container.addWidget(row_widget)

    def set_last_cleanup(self, text: str):
        self._last_cleanup_lbl.setText(f"Last cleanup: {text}")

    def _lbl(self, text, color="#8BA3C7", size=12, bold=False):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {'700' if bold else '400'}; font-family: 'Segoe UI';")
        return l
