"""
Auto-Setup Progress Dialog
--------------------------
Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
License: Personal Use Only (Non-Commercial)

Uses proper Qt signals for thread-safe UI updates.
Background thread → signal → main thread → UI update.
No QTimer.singleShot from background threads (that was the freeze bug).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QColor, QFont

from ui.widgets import NeonButton, GlassCard, NeonProgressBar, StatusBadge
from ai.ollama_manager import OllamaManager, SetupStep, SystemProfile
from config.settings import set_setting


# ─────────────────────────────────────────────────────────────────
# QThread-based runner — PROPER WAY to run background work in PyQt6
# ─────────────────────────────────────────────────────────────────

class SetupWorker(QObject):
    """Runs OllamaManager in a real QThread with proper signals."""

    step_updated  = pyqtSignal(str, str, str, int)   # name, status, message, progress
    log_updated   = pyqtSignal(str)
    setup_done    = pyqtSignal(bool, str, object)     # success, message, model_dict

    def __init__(self):
        super().__init__()
        self._manager = None

    @pyqtSlot()
    def run(self):
        """Called on the background QThread."""
        def step_cb(step: SetupStep):
            self.step_updated.emit(step.name, step.status, step.message, step.progress)

        def log_cb(msg: str):
            self.log_updated.emit(msg)

        self._manager = OllamaManager(step_cb=step_cb, log_cb=log_cb)
        success, message = self._manager.auto_setup()
        model = self._manager.selected_model
        self.setup_done.emit(success, message, model)


# ─────────────────────────────────────────────────────────────────
# STEP ROW WIDGET
# ─────────────────────────────────────────────────────────────────

STATUS_ICON = {
    "pending":  ("⏳", "#4A6080"),
    "running":  ("⚙️", "#00D4FF"),
    "done":     ("✅", "#00FF88"),
    "failed":   ("❌", "#FF2D55"),
    "skipped":  ("⏭️", "#FFB800"),
}


class StepRow(QWidget):
    def __init__(self, step_name: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        self._icon_lbl = QLabel("⏳")
        self._icon_lbl.setFixedWidth(22)
        self._icon_lbl.setStyleSheet("font-size: 16px;")

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        self._name_lbl = QLabel(step_name)
        self._name_lbl.setStyleSheet(
            "color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI'; font-weight: 600;"
        )
        self._msg_lbl = QLabel("")
        self._msg_lbl.setStyleSheet(
            "color: #4A6080; font-size: 10px; font-family: 'Segoe UI';"
        )
        name_col.addWidget(self._name_lbl)
        name_col.addWidget(self._msg_lbl)

        self._bar = NeonProgressBar("#00D4FF")
        self._bar.setFixedWidth(130)
        self._bar.setValue(0)

        layout.addWidget(self._icon_lbl)
        layout.addLayout(name_col, 1)
        layout.addWidget(self._bar)

    def update_step(self, status: str, message: str, progress: int):
        icon, color = STATUS_ICON.get(status, ("⏳", "#4A6080"))
        self._icon_lbl.setText(icon)
        self._name_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-family: 'Segoe UI'; font-weight: 600;"
        )
        self._msg_lbl.setText(message[:70])
        self._bar.setValue(progress)
        bar_color = (
            "#00FF88" if status == "done" else
            "#FF2D55" if status == "failed" else
            "#FFB800" if status == "skipped" else
            "#00D4FF"
        )
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: #1E2D45; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {bar_color}; border-radius: 3px; }}
        """)


# ─────────────────────────────────────────────────────────────────
# AUTO SETUP DIALOG
# ─────────────────────────────────────────────────────────────────

class AutoSetupDialog(QDialog):
    """
    Thread-safe setup progress dialog.
    Uses QThread + proper signals — no UI freezing.
    """

    setup_complete = pyqtSignal(bool, str, object)

    STEP_NAMES = [
        "Checking Ollama installation",
        "Starting Ollama service",
        "Verifying API connection",
        "Checking model availability",
        "Pulling AI model",
        "Final verification",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI System Optimizer — Setup")
        self.setFixedSize(640, 580)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #0A0E1A, stop:1 #080C18);
                color: #E8F4FD;
            }
        """)
        self._step_rows: dict[str, StepRow] = {}
        self._worker: SetupWorker = None
        self._thread: QThread = None
        self._profile = SystemProfile()
        self._build_ui()
        # Start setup after dialog fully renders
        QTimer.singleShot(400, self._start_setup)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────
        header_row = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 32px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("AI System Optimizer — Setup")
        title.setStyleSheet(
            "color: #00D4FF; font-size: 18px; font-weight: 700; font-family: 'Segoe UI';"
        )
        sub = QLabel("Automatic configuration — no action required")
        sub.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header_row.addWidget(icon_lbl)
        header_row.addLayout(title_col, 1)
        root.addLayout(header_row)

        # ── System Info Card ────────────────────────────────────
        sys_card = GlassCard(accent_color="#7C3AED", glow=False)
        sys_layout = QHBoxLayout(sys_card)
        sys_layout.setContentsMargins(16, 10, 16, 10)
        sys_layout.setSpacing(24)
        specs = [
            ("💾", f"{self._profile.ram_total_gb:.0f} GB RAM"),
            ("🖥️", f"GPU: {'Yes' if self._profile.has_gpu else 'No'}"),
            ("🌐", f"Internet: {'Yes' if self._profile.has_internet else 'No'}"),
            ("⚙️", f"{self._profile.cpu_cores} CPU Cores"),
        ]
        for icon, text in specs:
            col = QVBoxLayout()
            col.setSpacing(1)
            i = QLabel(icon)
            i.setStyleSheet("font-size: 18px;")
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t = QLabel(text)
            t.setStyleSheet("color: #8BA3C7; font-size: 10px; font-family: 'Segoe UI';")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(i)
            col.addWidget(t)
            sys_layout.addLayout(col)
        root.addWidget(sys_card)

        # ── Model label ──────────────────────────────────────────
        self._model_lbl = QLabel("🤖 Detecting best AI model...")
        self._model_lbl.setStyleSheet(
            "color: #00D4FF; font-size: 12px; font-weight: 600; font-family: 'Segoe UI';"
        )
        self._model_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._model_lbl)

        # ── Steps ────────────────────────────────────────────────
        steps_card = GlassCard(accent_color="#1E2D45", glow=False)
        steps_card.setStyleSheet(
            "background: #0D1221; border: 1px solid #1E2D45; border-radius: 14px;"
        )
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setContentsMargins(16, 14, 16, 14)
        steps_layout.setSpacing(4)
        steps_title = QLabel("SETUP PROGRESS")
        steps_title.setStyleSheet(
            "color: #4A6080; font-size: 10px; font-weight: 600; "
            "font-family: 'Segoe UI'; letter-spacing: 1px;"
        )
        steps_layout.addWidget(steps_title)
        for name in self.STEP_NAMES:
            row = StepRow(name)
            self._step_rows[name] = row
            steps_layout.addWidget(row)
        root.addWidget(steps_card)

        # ── Log area ─────────────────────────────────────────────
        self._log_lbl = QLabel("Starting...")
        self._log_lbl.setStyleSheet(
            "color: #4A6080; font-size: 10px; font-family: 'Consolas', monospace; "
            "background: #080C18; border: 1px solid #1E2D45; border-radius: 6px; padding: 6px 10px;"
        )
        self._log_lbl.setWordWrap(True)
        self._log_lbl.setFixedHeight(42)
        root.addWidget(self._log_lbl)

        # ── Buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._skip_btn = NeonButton("Skip AI Setup", "#4A6080")
        self._skip_btn.clicked.connect(self._skip)
        self._done_btn = NeonButton("Continue to App", "#00FF88")
        self._done_btn.setEnabled(False)
        self._done_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._done_btn)
        root.addLayout(btn_row)

    def _start_setup(self):
        """Launch background QThread — UI stays responsive."""
        self._worker = SetupWorker()
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        # Connect signals → UI slots (thread-safe, runs on main thread)
        self._thread.started.connect(self._worker.run)
        self._worker.step_updated.connect(self._on_step_updated)
        self._worker.log_updated.connect(self._on_log_updated)
        self._worker.setup_done.connect(self._on_setup_done)
        self._worker.setup_done.connect(lambda: self._thread.quit())

        self._thread.start()

    # ── Slots (run on main thread) ─────────────────────────────────

    @pyqtSlot(str, str, str, int)
    def _on_step_updated(self, name: str, status: str, message: str, progress: int):
        row = self._step_rows.get(name)
        if row:
            row.update_step(status, message, progress)

    @pyqtSlot(str)
    def _on_log_updated(self, msg: str):
        self._log_lbl.setText(msg[:120])

    @pyqtSlot(bool, str, object)
    def _on_setup_done(self, success: bool, message: str, model):
        if success and model:
            set_setting("ai_provider", "ollama")
            set_setting("ollama_model", model["name"])
            self._model_lbl.setText(
                f"Model: {model['name']} — {model.get('description', '')}"
            )
            self._log_lbl.setText(f"Ready: {message}")
            self._log_lbl.setStyleSheet(
                "color: #00FF88; font-size: 10px; font-family: 'Consolas'; "
                "background: #00FF8810; border: 1px solid #00FF8830; "
                "border-radius: 6px; padding: 6px 10px;"
            )
            self._done_btn.setEnabled(True)
            self._done_btn.setText("Continue to App")
            self._skip_btn.setEnabled(False)
            self.setup_complete.emit(True, message, model)
        else:
            self._log_lbl.setText(f"Warning: {message}")
            self._log_lbl.setStyleSheet(
                "color: #FFB800; font-size: 10px; font-family: 'Consolas'; "
                "background: #FFB80010; border: 1px solid #FFB80030; "
                "border-radius: 6px; padding: 6px 10px;"
            )
            self._done_btn.setEnabled(True)
            self._done_btn.setText("Continue Without AI")
            self.setup_complete.emit(False, message, None)

    def _skip(self):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
        set_setting("ai_provider", "none")
        set_setting("first_run", "false")
        self.setup_complete.emit(False, "Skipped", None)
        self.accept()
