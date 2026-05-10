"""
Performance & Startup Apps Pages
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from ui.widgets import GlassCard, NeonButton, NeonProgressBar, SparklineChart
from monitoring.system_monitor import get_startup_apps, get_disk_usage_breakdown
import psutil


class PerformancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_chart = None
        self._ram_chart = None
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

        # Charts row
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
        cpu = psutil.cpu_percent()
        vm = psutil.virtual_memory()
        self._cpu_val.setText(f"{cpu:.1f}%")
        self._ram_val.setText(f"{vm.percent:.1f}%")
        if self._cpu_chart:
            self._cpu_chart.add_point(cpu)
        if self._ram_chart:
            self._ram_chart.add_point(vm.percent)
        self._refresh_disk()

    def _refresh_disk(self):
        while self._disk_container.count():
            item = self._disk_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

    def update_metrics(self, m):
        pass  # Charts auto-refresh via timer

    def _label(self, text, color="#8BA3C7"):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';")
        return l


class StartupAppsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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

        info = QLabel("These apps start automatically with Windows. Disabling them can improve boot time.")
        info.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        info.setWordWrap(True)
        root.addWidget(info)

        card = GlassCard(accent_color="#FF6B00")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["App Name", "Path", "Source"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #080C18; color: #E8F4FD;
                border: none; gridline-color: #1E2D45;
                font-family: 'Segoe UI'; font-size: 11px;
            }
            QHeaderView::section {
                background: #111827; color: #8BA3C7;
                border: 1px solid #1E2D45; padding: 6px;
                font-family: 'Segoe UI'; font-size: 11px;
            }
            QTableWidget::item:alternate { background: #0D1221; }
        """)
        cl.addWidget(self._table)
        root.addWidget(card, 1)

    def _load_apps(self):
        apps = get_startup_apps()
        self._table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self._table.setItem(i, 0, QTableWidgetItem(app.get("name", "")))
            self._table.setItem(i, 1, QTableWidgetItem(app.get("path", "")[:80]))
            self._table.setItem(i, 2, QTableWidgetItem(app.get("source", "")))
