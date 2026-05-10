"""
Internet & Network Optimization Page
------------------------------------
Author: Mohammad Quasif
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QProgressBar,
    QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from ui.widgets import GlassCard, NeonButton, StatusBadge
from monitoring.system_monitor import get_network_usage, boost_internet
import psutil
import time

class InternetPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
        # Timer for live updates
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_stats)
        self._refresh_timer.start(2000)
        
        self._prev_io = psutil.net_io_counters()
        self._prev_time = time.time()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ── Header ───────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("📡 Network & Internet")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        
        self._help_btn = QPushButton("❓ Help")
        self._help_btn.setFixedSize(60, 24)
        self._help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_btn.setToolTip(
            "This page shows real-time network speed and bandwidth hogs.\n\n"
            "• Download/Upload: Your current internet throughput.\n"
            "• Bandwidth Hogs: Apps currently using your connection.\n"
            "• Boost Connection: Clears DNS/Network cache to fix lag.\n"
            "• AI Analyze: Explain why an app is using internet."
        )
        self._help_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #4A6080; border: 1px solid #4A6080; border-radius: 4px; font-size: 10px; }
            QPushButton:hover { color: #00D4FF; border-color: #00D4FF; }
        """)

        self._ai_btn = NeonButton("🧠 AI Analyze", "#7C3AED")
        self._ai_btn.setFixedWidth(140)
        self._ai_btn.clicked.connect(self._analyze_network)

        self._test_btn = NeonButton("⚡ Start Speed Test", "#00D4FF")
        self._test_btn.setFixedWidth(160)
        self._test_btn.clicked.connect(self._run_speed_test)

        self._boost_btn = NeonButton("🚀 Boost Connection", "#00FF88")
        self._boost_btn.setFixedWidth(160)
        self._boost_btn.clicked.connect(self._run_boost)
        
        header.addWidget(title)
        header.addWidget(self._help_btn)
        header.addStretch()
        header.addWidget(self._ai_btn)
        header.addSpacing(10)
        header.addWidget(self._test_btn)
        header.addSpacing(10)
        header.addWidget(self._boost_btn)
        root.addLayout(header)

        # ── Live Speed Cards ─────────────────────────────────────
        speed_row = QHBoxLayout()
        
        self._down_card = GlassCard(accent_color="#00D4FF")
        dl = QVBoxLayout(self._down_card)
        dl.addWidget(QLabel("⬇️ Download Speed"))
        self._down_val = QLabel("0.00 MB/s")
        self._down_val.setStyleSheet("color: #00D4FF; font-size: 24px; font-weight: 700;")
        dl.addWidget(self._down_val)
        
        self._up_card = GlassCard(accent_color="#7C3AED")
        ul = QVBoxLayout(self._up_card)
        ul.addWidget(QLabel("⬆️ Upload Speed"))
        self._up_val = QLabel("0.00 MB/s")
        self._up_val.setStyleSheet("color: #7C3AED; font-size: 24px; font-weight: 700;")
        ul.addWidget(self._up_val)
        
        speed_row.addWidget(self._down_card)
        speed_row.addWidget(self._up_card)
        root.addLayout(speed_row)

        # ── Bandwidth Hogs Table ─────────────────────────────────
        hogs_card = GlassCard(accent_color="#FF2D55")
        hl = QVBoxLayout(hogs_card)
        hl.setContentsMargins(16, 16, 16, 16)
        
        table_title = QHBoxLayout()
        table_title.addWidget(QLabel("🚀 Bandwidth Hogs (Top Network Apps)"))
        table_title.addStretch()
        self._status_badge = StatusBadge("online")
        table_title.addWidget(self._status_badge)
        hl.addLayout(table_title)
        
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Process", "PID", "Connections", "Type"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #0D1221; color: #E8F4FD;
                gridline-color: #1E2D45; border: none;
                font-family: 'Segoe UI'; font-size: 12px;
            }
            QHeaderView::section {
                background: #111827; color: #8BA3C7;
                padding: 8px; border: none; border-bottom: 1px solid #1E2D45;
                font-weight: 600;
            }
        """)
        hl.addWidget(self._table)
        root.addWidget(hogs_card, 1)

        # ── Optimization Log ─────────────────────────────────────
        self._log_lbl = QLabel("Ready for optimization")
        self._log_lbl.setStyleSheet("color: #4A6080; font-size: 11px; font-family: 'Segoe UI';")
        root.addWidget(self._log_lbl)

    def _update_stats(self):
        # 1. Live Speed Calculation
        now = time.time()
        curr_io = psutil.net_io_counters()
        elapsed = now - self._prev_time
        
        if elapsed > 0:
            down = (curr_io.bytes_recv - self._prev_io.bytes_recv) / 1024 / 1024 / elapsed
            up = (curr_io.bytes_sent - self._prev_io.bytes_sent) / 1024 / 1024 / elapsed
            self._down_val.setText(f"{down:.2f} MB/s")
            self._up_val.setText(f"{up:.2f} MB/s")
            
        self._prev_io = curr_io
        self._prev_time = now
        
        # 2. Update Table
        hogs = get_network_usage()
        self._table.setRowCount(len(hogs))
        for i, h in enumerate(hogs):
            self._table.setItem(i, 0, QTableWidgetItem(h["name"]))
            self._table.setItem(i, 1, QTableWidgetItem(str(h["pid"])))
            self._table.setItem(i, 2, QTableWidgetItem(str(h["connections"])))
            
            type_item = QTableWidgetItem(h["type"])
            if h["type"] == "High Traffic":
                type_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(i, 3, type_item)

    def _run_boost(self):
        self._boost_btn.setEnabled(False)
        self._boost_btn.setText("⏳ Boosting...")
        self._log_lbl.setText("Running DNS Flush, Winsock Reset, and stack optimization...")
        
        # Run in worker to avoid UI freeze
        from ui.pages.performance_page import _FetchWorker
        def _task():
            return boost_internet()
            
        self._worker = _FetchWorker(_task)
        self._worker.result_ready.connect(self._on_boost_done)
        self._worker.start()

    def _on_boost_done(self, res):
        success, log = res
        self._boost_btn.setEnabled(True)
        self._boost_btn.setText("🚀 Boost Connection")
        self._log_lbl.setText("Optimization Complete! Network stack refreshed.")

    def _analyze_network(self):
        """Bridge to AI Assistant to analyze selected process or overall network."""
        selected = self._table.currentRow()
        data = None
        
        if selected >= 0:
            # Process selected
            data = {
                "name": self._table.item(selected, 0).text(),
                "pid": self._table.item(selected, 1).text(),
                "conns": self._table.item(selected, 2).text(),
                "type": self._table.item(selected, 3).text()
            }
            prompt = (
                f"Analyze this network process: {data['name']} (PID: {data['pid']}). "
                f"It has {data['conns']} active connections and is marked as {data['type']}. "
                f"Tell me what this app is, why it needs internet, if it's a 'bandwidth hog', "
                f"and if I should consider closing it for better gaming/browsing speed."
            )
        else:
            # Nothing selected — analyze general network
            prompt = (
                "Analyze my overall network health. My current download is "
                f"{self._down_val.text()} and upload is {self._up_val.text()}. "
                "Who is using most of my internet and how can I maximize my speed for better performance?"
            )

        # Trigger MainWindow to navigate to AI Chat and send the prompt
        win = self.window()
        if hasattr(win, '_navigate') and "ai_chat" in win._pages:
            win._navigate("ai_chat")
            win._pages["ai_chat"].send_message_external(prompt)

    def _run_speed_test(self):
        """Perform a real-world download speed test."""
        self._test_btn.setEnabled(False)
        self._test_btn.setText("⏳ Testing...")
        self._log_lbl.setText("Testing download speed using 10MB sample file...")
        
        from ui.pages.performance_page import _FetchWorker
        import urllib.request
        import time

        def _do_test():
            # Reliable 10MB test file from Cloudflare
            url = "https://speed.cloudflare.com/__down?bytes=10485760" 
            try:
                # Add User-Agent to avoid being blocked by CDNs
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                start = time.time()
                with urllib.request.urlopen(req, timeout=30) as response:
                    # Read in chunks to avoid memory spikes and potential hangs
                    while True:
                        chunk = response.read(1024 * 64) # 64KB chunks
                        if not chunk:
                            break
                end = time.time()
                
                duration = end - start
                # 10MB = 10,485,760 bytes = 83,886,080 bits
                mbps = (83.886 / duration) if duration > 0 else 0
                return True, mbps
            except Exception as e:
                return False, str(e)

        self._worker_test = _FetchWorker(_do_test)
        self._worker_test.result_ready.connect(self._on_test_done)
        self._worker_test.start()

    def _on_test_done(self, res):
        success, val = res
        self._test_btn.setEnabled(True)
        self._test_btn.setText("⚡ Start Speed Test")
        if success:
            mbps = val
            self._log_lbl.setText(f"Speed Test Complete: {mbps:.1f} Mbps peak download.")
            self._down_val.setText(f"{mbps/8:.2f} MB/s") # Update the meter too
        else:
            self._log_lbl.setText(f"Speed Test Failed: {val}")
