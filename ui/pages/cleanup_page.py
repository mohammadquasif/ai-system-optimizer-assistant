"""
Cleanup Page - Interactive cleanup UI with checkboxes, progress, and results
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QScrollArea, QFrame, QProgressBar, QTextEdit, QSizePolicy,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QColor

from ui.widgets import GlassCard, NeonButton, NeonProgressBar
from cleanup.cleanup_engine import BackgroundCleanup, estimate_cleanup_size
from config.settings import get_setting, set_setting, get_db
from datetime import datetime


class CleanupPage(QWidget):
    cleanup_done = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._setup_ui()
        self._estimate_space()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # Header
        title = QLabel("🧹 System Cleanup")
        title.setStyleSheet(
            "color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';"
        )
        self._estimate_lbl = QLabel("Estimating cleanup size...")
        self._estimate_lbl.setStyleSheet("color: #00FF88; font-size: 13px; font-family: 'Segoe UI';")
        root.addWidget(title)
        root.addWidget(self._estimate_lbl)

        # ── Options ─────────────────────────────────────────────
        opts_card = GlassCard(accent_color="#00FF88")
        opts_layout = QVBoxLayout(opts_card)
        opts_layout.setContentsMargins(24, 20, 24, 20)
        opts_layout.setSpacing(6)

        opts_title = QLabel("Select cleanup items:")
        opts_title.setStyleSheet(
            "color: #00FF88; font-size: 14px; font-weight: 700; font-family: 'Segoe UI';"
        )
        opts_layout.addWidget(opts_title)

        # Safe options (enabled by default)
        safe_label = QLabel("✅ Safe Cleanup (Recommended)")
        safe_label.setStyleSheet("color: #8BA3C7; font-size: 11px; font-weight: 600; font-family: 'Segoe UI'; margin-top: 8px;")
        opts_layout.addWidget(safe_label)

        checkbox_style = """
            QCheckBox {
                color: #E8F4FD;
                font-size: 12px;
                font-family: 'Segoe UI';
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #1E2D45;
                background: #0D1221;
            }
            QCheckBox::indicator:checked {
                background: #00D4FF;
                border: 1px solid #00D4FF;
                image: url(none);
            }
        """

        self._checkboxes = {}
        safe_options = [
            ("clean_temp",          "Windows Temp Files (%TEMP%)",             True),
            ("clean_thumbnails",    "Thumbnail Cache",                          True),
            ("clean_browser_cache", "Browser Cache (Chrome, Edge, Brave, Firefox)", True),
            ("clean_logs",          "Temporary Log Files",                      True),
            ("clean_recycle",       "Empty Recycle Bin",                        False),
        ]

        for key, label, default in safe_options:
            cb = QCheckBox(label)
            cb.setChecked(get_setting(key, "true" if default else "false") == "true")
            cb.setStyleSheet(checkbox_style)
            opts_layout.addWidget(cb)
            self._checkboxes[key] = cb

        # Risky options
        risky_label = QLabel("⚠️ Risky Cleanup (Disabled by default — use with caution)")
        risky_label.setStyleSheet("color: #FFB800; font-size: 11px; font-weight: 600; font-family: 'Segoe UI'; margin-top: 12px;")
        opts_layout.addWidget(risky_label)

        risky_options = [
            ("clean_history",  "Clear Browser History ⚠️",   False),
            ("clean_cookies",  "Clear Cookies (will log you out) ⚠️", False),
        ]
        for key, label, default in risky_options:
            cb = QCheckBox(label)
            cb.setChecked(False)
            cb.setStyleSheet(checkbox_style.replace("#00D4FF", "#FFB800"))
            opts_layout.addWidget(cb)
            self._checkboxes[key] = cb

        root.addWidget(opts_card)

        # ── Action buttons ──────────────────────────────────────
        btn_row = QHBoxLayout()
        self._start_btn = NeonButton("▶  Start Cleanup", "#00FF88")
        self._start_btn.setFixedHeight(44)
        self._start_btn.clicked.connect(self._confirm_and_run)

        self._estimate_btn = NeonButton("🔍 Re-estimate Size", "#00D4FF")
        self._estimate_btn.clicked.connect(self._estimate_space)

        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._estimate_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Progress ────────────────────────────────────────────
        self._progress_card = GlassCard(accent_color="#00D4FF")
        prog_layout = QVBoxLayout(self._progress_card)
        prog_layout.setContentsMargins(20, 16, 20, 16)
        self._progress_lbl = QLabel("Ready")
        self._progress_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        self._progress_bar = NeonProgressBar("#00D4FF")
        prog_layout.addWidget(self._progress_lbl)
        prog_layout.addWidget(self._progress_bar)
        self._progress_card.hide()
        root.addWidget(self._progress_card)

        # ── Result log ──────────────────────────────────────────
        log_card = GlassCard(accent_color="#7C3AED")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 14)
        log_title = QLabel("Cleanup Log")
        log_title.setStyleSheet("color: #7C3AED; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';")
        log_layout.addWidget(log_title)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFixedHeight(140)
        self._log_text.setStyleSheet("""
            QTextEdit {
                background: #080C18;
                color: #8BA3C7;
                border: 1px solid #1E2D45;
                border-radius: 8px;
                padding: 8px;
                font-size: 11px;
                font-family: 'Consolas', 'Courier New';
            }
        """)
        log_layout.addWidget(self._log_text)
        root.addWidget(log_card)
        root.addStretch()

    def _estimate_space(self):
        self._estimate_lbl.setText("⏳ Estimating...")
        QTimer.singleShot(100, self._do_estimate)

    def _do_estimate(self):
        try:
            size_bytes = estimate_cleanup_size()
            if size_bytes > 1e9:
                text = f"~{size_bytes/1e9:.2f} GB can be freed"
            elif size_bytes > 1e6:
                text = f"~{size_bytes/1e6:.0f} MB can be freed"
            else:
                text = f"~{size_bytes/1e3:.0f} KB can be freed"
            self._estimate_lbl.setText(f"💾 Estimated: {text}")
        except Exception:
            self._estimate_lbl.setText("Estimate unavailable")

    def _confirm_and_run(self):
        # Check for risky options
        risky_selected = (
            self._checkboxes["clean_history"].isChecked()
            or self._checkboxes["clean_cookies"].isChecked()
        )

        if risky_selected:
            msg = QMessageBox(self)
            msg.setWindowTitle("⚠️ Risky Cleanup Warning")
            msg.setText(
                "You have selected one or more risky cleanup options:\n\n"
                "• Browser History: will erase your browsing history\n"
                "• Cookies: will log you out of all websites\n\n"
                "These cannot be undone. Passwords and bookmarks are NOT affected.\n\n"
                "Do you want to continue?"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            msg.setStyleSheet("""
                QMessageBox { background: #0A0E1A; color: #E8F4FD; }
                QLabel { color: #E8F4FD; font-family: 'Segoe UI'; }
                QPushButton { background: #111827; color: #E8F4FD; border: 1px solid #1E2D45;
                    border-radius: 6px; padding: 6px 16px; }
            """)
            if msg.exec() != QMessageBox.StandardButton.Yes:
                return

        self._run_cleanup()

    def _run_cleanup(self):
        if self._is_running:
            return
        self._is_running = True
        self._start_btn.setEnabled(False)
        self._progress_card.show()
        self._log_text.clear()
        self._log("🚀 Starting cleanup...")

        options = {
            key: cb.isChecked() for key, cb in self._checkboxes.items()
        }

        # Thread-safe: post UI updates to main thread via QTimer
        def progress_cb(msg: str, pct: int):
            QTimer.singleShot(0, lambda m=msg, p=pct: (
                self._progress_lbl.setText(m),
                self._progress_bar.setValue(p),
                self._log(f"  → {m}"),
            ))

        def done_cb(result):
            def _finish(r=result):
                self._is_running = False
                self._start_btn.setEnabled(True)
                self._log(f"\n✅ {r.summary()}")
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.cleanup_done.emit(now)
                try:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO cleanup_history (timestamp, items_cleaned, space_freed_mb, status) VALUES (?, ?, ?, ?)",
                            (now, str(list(options.keys())), r.space_freed_mb, "success"),
                        )
                        conn.commit()
                except Exception:
                    pass
            QTimer.singleShot(0, _finish)

        bg = BackgroundCleanup(options, progress_cb=progress_cb, done_cb=done_cb)
        bg.start()

    def _log(self, msg: str):
        self._log_text.append(msg)
        self._log_text.verticalScrollBar().setValue(
            self._log_text.verticalScrollBar().maximum()
        )

    def run_quick_cleanup(self):
        """Called from dashboard quick optimize button."""
        self._run_cleanup()
