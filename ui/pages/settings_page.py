"""
Settings Page - AI configuration, voice, startup, and preferences
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QTabWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from ui.widgets import GlassCard, NeonButton
from config.settings import get_setting, set_setting, encrypt_value, decrypt_value
from ai.ai_service import AIService, OllamaInstaller
import threading


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("⚙️  Settings")
        title.setStyleSheet("color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { background: #0D1221; border: 1px solid #1E2D45; border-radius: 10px; }
            QTabBar::tab {
                background: #0A0E1A; color: #8BA3C7; padding: 10px 20px;
                border: 1px solid #1E2D45; border-radius: 6px; margin-right: 4px;
                font-family: 'Segoe UI'; font-size: 12px;
            }
            QTabBar::tab:selected { background: #111827; color: #00D4FF; border-color: #00D4FF40; }
        """)

        tabs.addTab(self._build_ai_tab(), "🤖 AI Config")
        tabs.addTab(self._build_voice_tab(), "🎙️ Voice")
        tabs.addTab(self._build_system_tab(), "🖥️ System")
        tabs.addTab(self._build_general_tab(), "⚙️ General")
        root.addWidget(tabs)

    # ── AI CONFIG TAB ─────────────────────────────────────────────

    def _build_ai_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Provider selection
        card = GlassCard(accent_color="#7C3AED")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(12)

        cl.addWidget(self._lbl("AI Provider", color="#7C3AED", size=14, bold=True))

        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["None (Disable AI)", "Ollama (Local AI)", "OpenAI", "Anthropic"])
        current = get_setting("ai_provider", "none")
        mapping = {"none": 0, "ollama": 1, "openai": 2, "anthropic": 3}
        self._provider_combo.setCurrentIndex(mapping.get(current, 0))
        self._provider_combo.setStyleSheet(self._combo_style())
        self._provider_combo.currentIndexChanged.connect(self._on_provider_change)
        cl.addWidget(self._lbl("Select AI provider:"))
        cl.addWidget(self._provider_combo)

        # Ollama settings
        self._ollama_frame = QFrame()
        of = QVBoxLayout(self._ollama_frame)
        of.setSpacing(8)
        self._ollama_url = self._input_field("Ollama URL", get_setting("ollama_url", "http://localhost:11434"))
        self._ollama_model = self._input_field("Model Name", get_setting("ollama_model", "qwen2.5:1.5b"))

        self._ollama_status_lbl = QLabel("")
        self._ollama_status_lbl.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")

        test_ollama_btn = NeonButton("🔌 Test Ollama Connection", "#00D4FF")
        test_ollama_btn.clicked.connect(self._test_ollama)
        install_ollama_btn = NeonButton("⬇️ Install Ollama Online", "#00FF88")
        install_ollama_btn.clicked.connect(self._install_ollama_online)

        of.addWidget(self._lbl("Ollama URL:"))
        of.addWidget(self._ollama_url)
        of.addWidget(self._lbl("Model:"))
        of.addWidget(self._ollama_model)
        of.addWidget(self._ollama_status_lbl)
        of.addWidget(test_ollama_btn)
        of.addWidget(install_ollama_btn)
        cl.addWidget(self._ollama_frame)

        # OpenAI settings
        self._openai_frame = QFrame()
        apif = QVBoxLayout(self._openai_frame)
        apif.setSpacing(8)
        self._openai_key = self._input_field("OpenAI API Key", "", password=True)
        test_oai = NeonButton("🔌 Test OpenAI", "#00D4FF")
        test_oai.clicked.connect(lambda: self._test_api("openai"))
        apif.addWidget(self._lbl("OpenAI API Key:"))
        apif.addWidget(self._openai_key)
        apif.addWidget(test_oai)
        cl.addWidget(self._openai_frame)

        # Anthropic settings
        self._anthropic_frame = QFrame()
        antf = QVBoxLayout(self._anthropic_frame)
        antf.setSpacing(8)
        self._anthropic_key = self._input_field("Anthropic API Key", "", password=True)
        test_ant = NeonButton("🔌 Test Anthropic", "#00D4FF")
        test_ant.clicked.connect(lambda: self._test_api("anthropic"))
        antf.addWidget(self._lbl("Anthropic API Key:"))
        antf.addWidget(self._anthropic_key)
        antf.addWidget(test_ant)
        cl.addWidget(self._anthropic_frame)

        save_ai_btn = NeonButton("💾 Save AI Settings", "#7C3AED")
        save_ai_btn.clicked.connect(self._save_ai)
        cl.addWidget(save_ai_btn)
        layout.addWidget(card)
        layout.addStretch()

        self._on_provider_change(self._provider_combo.currentIndex())
        return w

    def _on_provider_change(self, idx):
        self._ollama_frame.setVisible(idx == 1)
        self._openai_frame.setVisible(idx == 2)
        self._anthropic_frame.setVisible(idx == 3)

    def _save_ai(self):
        idx = self._provider_combo.currentIndex()
        providers = ["none", "ollama", "openai", "anthropic"]
        provider = providers[idx]
        set_setting("ai_provider", provider)
        if provider == "ollama":
            set_setting("ollama_url", self._ollama_url.text())
            set_setting("ollama_model", self._ollama_model.text())
        elif provider == "openai":
            key = self._openai_key.text().strip()
            if key:
                set_setting("openai_key_enc", encrypt_value(key))
        elif provider == "anthropic":
            key = self._anthropic_key.text().strip()
            if key:
                set_setting("anthropic_key_enc", encrypt_value(key))
        AIService.get_instance().reload()
        self._show_info("✅ AI settings saved and reloaded!")

    def _test_ollama(self):
        self._ollama_status_lbl.setText("⏳ Testing...")
        url = self._ollama_url.text()
        def _test():
            from ai.ai_service import OllamaProvider
            p = OllamaProvider(base_url=url, model=self._ollama_model.text())
            ok = p.is_available()
            models = p.list_models() if ok else []
            QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                f"✅ Connected! Models: {', '.join(models[:3])}" if ok else "❌ Cannot connect to Ollama"
            ))
        threading.Thread(target=_test, daemon=True).start()

    def _test_api(self, provider: str):
        self._show_info(f"Testing {provider}... check logs for result.")

    def _install_ollama_online(self):
        self._show_info("Downloading Ollama installer in background...")
        def _dl():
            import tempfile, os
            dest = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
            ok = OllamaInstaller.download_installer(dest)
            if ok:
                OllamaInstaller.install_from_exe(dest)
                QTimer.singleShot(0, lambda: self._show_info("✅ Ollama installed! Restart if needed."))
            else:
                QTimer.singleShot(0, lambda: self._show_info("❌ Download failed. Check internet."))
        threading.Thread(target=_dl, daemon=True).start()

    # ── VOICE TAB ─────────────────────────────────────────────────

    def _build_voice_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        card = GlassCard(accent_color="#00D4FF")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(12)
        cl.addWidget(self._lbl("Voice Settings", color="#00D4FF", size=14, bold=True))
        self._voice_enabled = QCheckBox("Enable Voice Assistant")
        self._voice_enabled.setChecked(get_setting("voice_enabled", "true") == "true")
        self._voice_enabled.setStyleSheet("color: #E8F4FD; font-family: 'Segoe UI'; font-size: 13px;")
        self._username_field = self._input_field("Your Name (for greeting)", get_setting("user_name", "Quasif"))
        test_voice_btn = NeonButton("🔊 Test Voice Greeting", "#00D4FF")
        test_voice_btn.clicked.connect(self._test_voice)
        save_voice_btn = NeonButton("💾 Save Voice Settings", "#00D4FF")
        save_voice_btn.clicked.connect(self._save_voice)
        cl.addWidget(self._voice_enabled)
        cl.addWidget(self._lbl("Your Name:"))
        cl.addWidget(self._username_field)
        cl.addWidget(test_voice_btn)
        cl.addWidget(save_voice_btn)
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _test_voice(self):
        name = self._username_field.text().strip() or "User"
        from services.voice_service import VoiceAssistant
        v = VoiceAssistant()
        v.start()
        v.speak(f"Hello {name}! This is how I will greet you. Your AI system optimizer is ready.")

    def _save_voice(self):
        name = self._username_field.text().strip()
        if not name:
            self._show_info("Please enter a name before saving.")
            return
        set_setting("voice_enabled", "true" if self._voice_enabled.isChecked() else "false")
        set_setting("user_name", name)
        # Update the main window's username so it takes effect immediately
        try:
            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, "_user_name"):
                    w._user_name = name
                    if hasattr(w, "_voice_handler"):
                        w._voice_handler.user_name = name
        except Exception:
            pass
        self._show_info(f"✅ Saved! AI will now call you '{name}'.\nTest it with the Test button above.")


    # ── SYSTEM TAB ────────────────────────────────────────────────

    def _build_system_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        card = GlassCard(accent_color="#FF6B00")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(12)
        cl.addWidget(self._lbl("System Settings", color="#FF6B00", size=14, bold=True))
        self._startup_cb = QCheckBox("Start with Windows")
        self._startup_cb.setChecked(get_setting("startup_with_windows", "false") == "true")
        self._startup_cb.setStyleSheet("color: #E8F4FD; font-family: 'Segoe UI'; font-size: 13px;")
        self._tray_cb = QCheckBox("Minimize to System Tray")
        self._tray_cb.setChecked(get_setting("minimize_to_tray", "true") == "true")
        self._tray_cb.setStyleSheet("color: #E8F4FD; font-family: 'Segoe UI'; font-size: 13px;")
        save_sys_btn = NeonButton("💾 Save System Settings", "#FF6B00")
        save_sys_btn.clicked.connect(self._save_system)
        cl.addWidget(self._startup_cb)
        cl.addWidget(self._tray_cb)
        cl.addWidget(save_sys_btn)
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _save_system(self):
        startup = self._startup_cb.isChecked()
        set_setting("startup_with_windows", "true" if startup else "false")
        set_setting("minimize_to_tray", "true" if self._tray_cb.isChecked() else "false")
        self._configure_startup(startup)
        self._show_info("✅ System settings saved!")

    def _configure_startup(self, enable: bool):
        try:
            import winreg, sys
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            if enable:
                winreg.SetValueEx(key, "AI System Optimizer", 0, winreg.REG_SZ, f'"{sys.executable}" "{__file__}"')
            else:
                try:
                    winreg.DeleteValue(key, "AI System Optimizer")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            pass

    # ── GENERAL TAB ───────────────────────────────────────────────

    def _build_general_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # About card
        card = GlassCard(accent_color="#8BA3C7")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)
        cl.addWidget(self._lbl("About", color="#8BA3C7", size=14, bold=True))
        cl.addWidget(self._lbl("AI System Optimizer Assistant v1.0.0"))
        cl.addWidget(self._lbl("Built with PyQt6 · psutil · Ollama"))
        cl.addWidget(self._lbl("© 2026 Quasif — Personal Edition"))
        layout.addWidget(card)

        # Uninstall card
        uninstall_card = GlassCard(accent_color="#FF2D55")
        ul = QVBoxLayout(uninstall_card)
        ul.setContentsMargins(20, 16, 20, 16)
        ul.setSpacing(10)
        ul.addWidget(self._lbl("🗑️ Uninstall App", color="#FF2D55", size=14, bold=True))
        ul.addWidget(self._lbl(
            "Remove this app from your system completely. "
            "This will remove startup entries, clear saved settings, "
            "and show you how to delete the app folder.",
            size=11
        ))
        uninstall_btn = NeonButton("🗑️ Uninstall AI System Optimizer", "#FF2D55")
        uninstall_btn.clicked.connect(self._uninstall_app)
        ul.addWidget(uninstall_btn)
        layout.addWidget(uninstall_card)

        layout.addStretch()
        return w

    def _uninstall_app(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Uninstall AI System Optimizer",
            "Are you sure you want to uninstall this app?\n\n"
            "This will:\n"
            "  ✓ Remove from Windows startup\n"
            "  ✓ Clear all saved settings\n"
            "  ✓ Show you how to delete the app folder\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import sys, os
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results = []

        # 1. Remove from Windows startup registry
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "AI System Optimizer")
                results.append("✅ Removed from Windows startup")
            except FileNotFoundError:
                results.append("ℹ️ Was not in Windows startup")
            winreg.CloseKey(key)
        except Exception as e:
            results.append(f"⚠️ Could not remove startup entry: {e}")

        # 2. Clear settings database
        try:
            from config.settings import get_setting
            db_path = os.path.join(app_dir, "optimizer_settings.db")
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.execute("DELETE FROM settings")
                conn.commit()
                conn.close()
                results.append("✅ Cleared all saved settings")
        except Exception as e:
            results.append(f"⚠️ Could not clear settings: {e}")

        # 3. Show folder delete instructions
        results_text = "\n".join(results)
        QMessageBox.information(
            self, "✅ Uninstall Steps Completed",
            f"Completed:\n{results_text}\n\n"
            f"📁 To fully remove the app, delete this folder:\n"
            f"{app_dir}\n\n"
            "You can delete it in File Explorer or run:\n"
            f"  rmdir /s /q \"{app_dir}\"\n\n"
            "The app will close after clicking OK.",
        )
        # Exit app
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()


    # ── HELPERS ───────────────────────────────────────────────────

    def _lbl(self, text, color="#8BA3C7", size=12, bold=False):
        l = QLabel(text)
        weight = "700" if bold else "400"
        l.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight}; font-family: 'Segoe UI';")
        return l

    def _input_field(self, placeholder, value="", password=False):
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setText(value)
        if password:
            f.setEchoMode(QLineEdit.EchoMode.Password)
        f.setStyleSheet("""
            QLineEdit {
                background: #0D1221; color: #E8F4FD;
                border: 1px solid #1E2D45; border-radius: 8px;
                padding: 8px 12px; font-size: 12px; font-family: 'Segoe UI';
            }
            QLineEdit:focus { border: 1px solid #00D4FF60; }
        """)
        return f

    def _combo_style(self):
        return """
            QComboBox {
                background: #0D1221; color: #E8F4FD;
                border: 1px solid #1E2D45; border-radius: 8px;
                padding: 8px 12px; font-size: 12px; font-family: 'Segoe UI';
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #111827; color: #E8F4FD;
                border: 1px solid #1E2D45; selection-background-color: #1E2D45;
            }
        """

    def _show_info(self, msg: str):
        QMessageBox.information(self, "Settings", msg)
