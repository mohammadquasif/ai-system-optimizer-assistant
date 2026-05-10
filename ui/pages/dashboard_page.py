"""
Dashboard Page - Main overview with system metrics, charts, quick actions
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QFrame, QSizePolicy, QPushButton, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ui.widgets import (
    GlassCard, CircularGauge, NeonButton, SparklineChart,
    MetricLabel, NeonProgressBar, StatusBadge,
)
from monitoring.system_monitor import SystemMetrics


class DashboardPage(QWidget):
    request_cleanup = pyqtSignal()
    request_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_history = []
        self._ram_history = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("System Dashboard")
        title.setStyleSheet(
            "color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';"
        )
        subtitle = QLabel("Real-time monitoring & quick actions")
        subtitle.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self._health_badge = QLabel("● 100")
        self._health_badge.setStyleSheet(
            "color: #00FF88; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';"
        )
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

        self._cpu_gauge = CircularGauge("CPU", "#00D4FF", size=130)
        self._ram_gauge = CircularGauge("RAM", "#7C3AED", size=130)
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
        cpu_card_layout = QVBoxLayout(cpu_card)
        cpu_card_layout.setContentsMargins(16, 14, 16, 14)
        cpu_lbl = QLabel("CPU Usage History")
        cpu_lbl.setStyleSheet("color: #00D4FF; font-size: 12px; font-weight: 600; font-family: 'Segoe UI';")
        cpu_card_layout.addWidget(cpu_lbl)
        self._cpu_chart = SparklineChart(color="#00D4FF")
        cpu_card_layout.addWidget(self._cpu_chart)

        ram_card = GlassCard(accent_color="#7C3AED")
        ram_card_layout = QVBoxLayout(ram_card)
        ram_card_layout.setContentsMargins(16, 14, 16, 14)
        ram_lbl = QLabel("RAM Usage History")
        ram_lbl.setStyleSheet("color: #7C3AED; font-size: 12px; font-weight: 600; font-family: 'Segoe UI';")
        ram_card_layout.addWidget(ram_lbl)
        self._ram_chart = SparklineChart(color="#7C3AED")
        ram_card_layout.addWidget(self._ram_chart)

        charts_row.addWidget(cpu_card, 1)
        charts_row.addWidget(ram_card, 1)
        root.addLayout(charts_row)

        # ── Quick Actions + Stats ────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setSpacing(16)

        # Quick optimize button card
        opt_card = GlassCard(accent_color="#00FF88")
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.setContentsMargins(20, 20, 20, 20)
        opt_layout.setSpacing(12)

        opt_title = QLabel("⚡ Quick Optimize")
        opt_title.setStyleSheet("color: #00FF88; font-size: 14px; font-weight: 700; font-family: 'Segoe UI';")
        opt_desc = QLabel("Safely clean temp files, browser cache,\nand thumbnail cache in one click.")
        opt_desc.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
        opt_desc.setWordWrap(True)

        self._optimize_btn = NeonButton("▶  Run Quick Optimize", "#00FF88")
        self._optimize_btn.clicked.connect(self.request_cleanup.emit)

        self._last_cleanup_lbl = QLabel("Last cleanup: Never")
        self._last_cleanup_lbl.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")

        opt_layout.addWidget(opt_title)
        opt_layout.addWidget(opt_desc)
        opt_layout.addWidget(self._optimize_btn)
        opt_layout.addWidget(self._last_cleanup_lbl)
        opt_layout.addStretch()

        # System info card
        info_card = GlassCard(accent_color="#7C3AED")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(10)

        info_title = QLabel("📊 System Stats")
        info_title.setStyleSheet("color: #7C3AED; font-size: 14px; font-weight: 700; font-family: 'Segoe UI';")
        info_layout.addWidget(info_title)

        self._stat_labels = {}
        stats = [
            ("cpu_cores", "CPU Cores"),
            ("ram_total", "Total RAM"),
            ("disk_total", "Disk Total"),
            ("disk_free", "Disk Free"),
            ("cpu_temp", "CPU Temp"),
        ]
        for key, label_text in stats:
            row = QHBoxLayout()
            k_lbl = QLabel(label_text)
            k_lbl.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
            v_lbl = QLabel("--")
            v_lbl.setStyleSheet("color: #E8F4FD; font-size: 11px; font-weight: 600; font-family: 'Segoe UI';")
            v_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(k_lbl)
            row.addStretch()
            row.addWidget(v_lbl)
            info_layout.addLayout(row)
            self._stat_labels[key] = v_lbl

        info_layout.addStretch()
        self._populate_static_stats()

        actions_row.addWidget(opt_card, 1)
        actions_row.addWidget(info_card, 1)
        root.addLayout(actions_row)

        # ── Top Processes ─────────────────────────────────────────
        procs_card = GlassCard(accent_color="#FF6B00")
        procs_layout = QVBoxLayout(procs_card)
        procs_layout.setContentsMargins(20, 14, 20, 14)
        procs_layout.setSpacing(8)

        procs_title = QLabel("🔥 Top Memory Consumers")
        procs_title.setStyleSheet("color: #FF6B00; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';")
        procs_layout.addWidget(procs_title)

        self._procs_container = QVBoxLayout()
        self._procs_container.setSpacing(4)
        procs_layout.addLayout(self._procs_container)
        root.addWidget(procs_card)

        root.addStretch()

    def _populate_static_stats(self):
        import psutil
        self._stat_labels["cpu_cores"].setText(f"{psutil.cpu_count(logical=True)} cores")
        vm = psutil.virtual_memory()
        self._stat_labels["ram_total"].setText(f"{round(vm.total/1e9,1)} GB")
        du = psutil.disk_usage("C:\\")
        self._stat_labels["disk_total"].setText(f"{round(du.total/1e9,1)} GB")

    def update_metrics(self, m: SystemMetrics):
        """Called from main window with new metrics."""
        self._cpu_gauge.set_value(m.cpu_percent)
        self._ram_gauge.set_value(m.ram_percent)
        self._disk_gauge.set_value(m.disk_percent)
        self._net_metric.set_value(f"↓{m.network_recv_mb:.1f} ↑{m.network_sent_mb:.1f} MB/s")
        self._cpu_chart.add_point(m.cpu_percent)
        self._ram_chart.add_point(m.ram_percent)

        # Health score color
        score = m.health_score
        color = "#00FF88" if score >= 70 else "#FFB800" if score >= 40 else "#FF2D55"
        self._health_badge.setText(f"● {score}")
        self._health_badge.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';"
        )

        self._stat_labels["disk_free"].setText(f"{m.disk_free_gb} GB")
        self._stat_labels["cpu_temp"].setText(
            f"{m.cpu_temp:.0f}°C" if m.cpu_temp else "N/A"
        )

        # Top processes
        self._update_procs(m.top_processes[:5])

    def _update_procs(self, procs: list):
        # Clear old widgets
        while self._procs_container.count():
            item = self._procs_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for p in procs:
            row = QHBoxLayout()
            name = QLabel(str(p.get("name", "Unknown"))[:30])
            name.setStyleSheet("color: #E8F4FD; font-size: 11px; font-family: 'Segoe UI';")

            mem_val = p.get("memory_percent", 0) or 0
            bar = NeonProgressBar("#FF6B00")
            bar.setValue(int(min(100, mem_val * 3)))
            bar.setFixedWidth(100)

            mem_lbl = QLabel(f"{mem_val:.1f}%")
            mem_lbl.setStyleSheet("color: #FF6B00; font-size: 11px; font-family: 'Segoe UI';")
            mem_lbl.setFixedWidth(45)

            row.addWidget(name, 1)
            row.addWidget(bar)
            row.addWidget(mem_lbl)

            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("background: transparent;")
            self._procs_container.addWidget(container)

    def set_last_cleanup(self, text: str):
        self._last_cleanup_lbl.setText(f"Last cleanup: {text}")
