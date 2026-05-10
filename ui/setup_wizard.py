"""
AI Setup Wizard - First-launch wizard for AI provider configuration
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.widgets import NeonButton, GlassCard
from config.settings import get_setting, set_setting, encrypt_value
from ai.ai_service import AIService, OllamaInstaller
import threading


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Setup Wizard")
        self.setFixedSize(560, 460)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #0A0E1A; color: #E8F4FD; }
            QLabel { color: #E8F4FD; font-family: 'Segoe UI'; }
        """)
        self._step = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # Header
        header = QLabel("🤖  AI Assistant Setup")
        header.setStyleSheet("color: #00D4FF; font-size: 20px; font-weight: 700; font-family: 'Segoe UI';")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        sub = QLabel("Choose your AI provider to get intelligent optimization suggestions.")
        sub.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1E2D45;")
        layout.addWidget(sep)

        btn_style = lambda color: f"""
            QPushButton {{
                background: {color}15;
                color: {color};
                border: 1px solid {color}50;
                border-radius: 10px;
                padding: 14px 20px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI';
                text-align: left;
            }}
            QPushButton:hover {{
                background: {color}30;
                border: 1px solid {color}AA;
            }}
        """

        # Ollama
        ollama_btn = QPushButton("⚡  Ollama (Local AI — Recommended)\n   Free, private, works offline")
        ollama_btn.setStyleSheet(btn_style("#00D4FF"))
        ollama_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ollama_btn.setFixedHeight(70)
        ollama_btn.clicked.connect(self._choose_ollama)
        layout.addWidget(ollama_btn)

        # OpenAI
        openai_btn = QPushButton("🌐  OpenAI (GPT-4o-mini)\n   Requires API key + internet")
        openai_btn.setStyleSheet(btn_style("#00FF88"))
        openai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        openai_btn.setFixedHeight(70)
        openai_btn.clicked.connect(self._choose_openai)
        layout.addWidget(openai_btn)

        # Anthropic
        claude_btn = QPushButton("🔮  Anthropic Claude\n   Requires API key + internet")
        claude_btn.setStyleSheet(btn_style("#7C3AED"))
        claude_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        claude_btn.setFixedHeight(70)
        claude_btn.clicked.connect(self._choose_anthropic)
        layout.addWidget(claude_btn)

        # Skip
        skip_btn = QPushButton("⏭️  Skip — Use without AI")
        skip_btn.setStyleSheet(btn_style("#4A6080"))
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.setFixedHeight(50)
        skip_btn.clicked.connect(self._skip)
        layout.addWidget(skip_btn)

        # Progress label
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet("color: #00D4FF; font-size: 11px; font-family: 'Segoe UI';")
        layout.addWidget(self._status_lbl)

    def _choose_ollama(self):
        installed = OllamaInstaller.is_installed()
        running = OllamaInstaller.is_running()

        set_setting("ai_provider", "ollama")
        ram = OllamaInstaller.get_ram_gb()
        has_gpu = OllamaInstaller.detect_gpu()
        model = OllamaInstaller.select_model(ram, has_gpu)
        set_setting("ollama_model", model)

        if not installed:
            self._status_lbl.setText("⏳ Downloading and installing Ollama...")
            def _do_install():
                import tempfile, os
                dest = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
                ok = OllamaInstaller.download_installer(dest)
                if ok:
                    OllamaInstaller.install_from_exe(dest)
                self._finalize_ollama(model)
            threading.Thread(target=_do_install, daemon=True).start()
        elif not running:
            self._status_lbl.setText("⏳ Starting Ollama service...")
            threading.Thread(target=lambda: (OllamaInstaller.start_service(), self._finalize_ollama(model)), daemon=True).start()
        else:
            self._finalize_ollama(model)

    def _finalize_ollama(self, model: str):
        self._status_lbl.setText(f"⏳ Pulling model: {model}...")
        from ai.ai_service import OllamaProvider
        p = OllamaProvider(model=model)
        p.pull_model(model, progress_cb=lambda s, pct: QTimer.singleShot(0, lambda: self._status_lbl.setText(f"{s} ({pct}%)")))
        AIService.get_instance().reload()
        set_setting("first_run", "false")
        QTimer.singleShot(0, self.accept)

    def _choose_openai(self):
        key, ok = self._ask_api_key("OpenAI API Key (sk-...)")
        if ok and key:
            set_setting("ai_provider", "openai")
            set_setting("openai_key_enc", encrypt_value(key))
            AIService.get_instance().reload()
            set_setting("first_run", "false")
            self.accept()

    def _choose_anthropic(self):
        key, ok = self._ask_api_key("Anthropic API Key (sk-ant-...)")
        if ok and key:
            set_setting("ai_provider", "anthropic")
            set_setting("anthropic_key_enc", encrypt_value(key))
            AIService.get_instance().reload()
            set_setting("first_run", "false")
            self.accept()

    def _skip(self):
        set_setting("ai_provider", "none")
        set_setting("first_run", "false")
        self.accept()

    def _ask_api_key(self, placeholder: str):
        dlg = QDialog(self)
        dlg.setWindowTitle("Enter API Key")
        dlg.setFixedSize(420, 160)
        dlg.setStyleSheet("QDialog { background: #0A0E1A; } QLabel { color: #E8F4FD; font-family: 'Segoe UI'; }")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        lbl = QLabel("Enter your API key (stored encrypted on disk):")
        lbl.setStyleSheet("color: #8BA3C7; font-size: 12px;")
        key_input = QLineEdit()
        key_input.setPlaceholderText(placeholder)
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setStyleSheet("""
            QLineEdit { background: #0D1221; color: #E8F4FD; border: 1px solid #1E2D45;
                border-radius: 8px; padding: 8px 12px; font-size: 12px; }
        """)
        btn_row = QHBoxLayout()
        ok_btn = NeonButton("✓ Save", "#00D4FF")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = NeonButton("Cancel", "#FF2D55")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addWidget(lbl)
        layout.addWidget(key_input)
        layout.addLayout(btn_row)
        result = dlg.exec()
        return key_input.text().strip(), result == QDialog.DialogCode.Accepted
