"""
Browser Optimization Page - Safe cache clearing for Chrome/Edge/Firefox/Brave
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QTextEdit,
)
from PyQt6.QtCore import Qt
from ui.widgets import GlassCard, NeonButton, NeonProgressBar
from cleanup.cleanup_engine import BackgroundCleanup


class BrowserOptimizePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        title = QLabel("🌐 Browser Optimization")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        root.addWidget(title)

        warn = QLabel(
            "ℹ️  Only SAFE items are cleaned: browser cache, GPU shader cache, temp logs.\n"
            "Passwords, bookmarks, extensions, and login sessions are NEVER touched."
        )
        warn.setStyleSheet(
            "color: #00FF88; font-size: 12px; font-family: 'Segoe UI'; "
            "background: #00FF8810; border: 1px solid #00FF8830; "
            "border-radius: 8px; padding: 10px;"
        )
        warn.setWordWrap(True)
        root.addWidget(warn)

        # Browser selector
        browsers_card = GlassCard(accent_color="#00D4FF")
        bl = QVBoxLayout(browsers_card)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(10)
        bl.addWidget(self._lbl("Select Browsers to Optimize:", "#00D4FF", 13, True))

        cb_style = "color: #E8F4FD; font-family: 'Segoe UI'; font-size: 13px; spacing: 8px;"
        self._chrome_cb = QCheckBox("Google Chrome")
        self._chrome_cb.setChecked(True)
        self._edge_cb = QCheckBox("Microsoft Edge")
        self._edge_cb.setChecked(True)
        self._brave_cb = QCheckBox("Brave Browser")
        self._brave_cb.setChecked(True)
        self._firefox_cb = QCheckBox("Mozilla Firefox")
        self._firefox_cb.setChecked(True)

        for cb in [self._chrome_cb, self._edge_cb, self._brave_cb, self._firefox_cb]:
            cb.setStyleSheet(cb_style)
            bl.addWidget(cb)

        bl.addWidget(self._lbl("What will be cleaned: Cache files, GPU shader cache, temp session data", "#8BA3C7"))
        root.addWidget(browsers_card)

        # Optimize button
        btn_row = QHBoxLayout()
        self._opt_btn = NeonButton("▶  Optimize Browsers", "#00D4FF")
        self._opt_btn.setFixedHeight(44)
        self._opt_btn.clicked.connect(self._run_optimization)
        btn_row.addWidget(self._opt_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Progress
        self._progress = NeonProgressBar("#00D4FF")
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        root.addWidget(self._status_lbl)
        root.addWidget(self._progress)

        # Log
        log_card = GlassCard(accent_color="#7C3AED")
        ll = QVBoxLayout(log_card)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.addWidget(self._lbl("Optimization Log", "#7C3AED", 13, True))
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(140)
        self._log.setStyleSheet("""
            QTextEdit {
                background: #080C18; color: #8BA3C7;
                border: 1px solid #1E2D45; border-radius: 8px;
                padding: 8px; font-size: 11px; font-family: 'Consolas';
            }
        """)
        ll.addWidget(self._log)
        root.addWidget(log_card)
        root.addStretch()

    def _run_optimization(self):
        self._opt_btn.setEnabled(False)
        self._log.clear()
        self._log.append("🚀 Starting browser optimization...")

        options = {
            "clean_temp": False,
            "clean_browser_cache": True,
            "clean_recycle": False,
            "clean_thumbnails": False,
            "clean_logs": False,
            "clean_history": False,
            "clean_cookies": False,
        }

        # BackgroundCleanup now uses QThread+signals — callbacks run on main thread
        def progress_cb(msg, pct):
            self._status_lbl.setText(msg)
            self._progress.setValue(pct)
            self._log.append(f"  → {msg}")

        def done_cb(result):
            self._opt_btn.setEnabled(True)
            self._log.append(f"\n✅ {result.summary()}")

        bg = BackgroundCleanup(options, progress_cb=progress_cb, done_cb=done_cb)
        bg.start()



    def _lbl(self, text, color="#8BA3C7", size=12, bold=False):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {'700' if bold else '400'}; font-family: 'Segoe UI';")
        return l
