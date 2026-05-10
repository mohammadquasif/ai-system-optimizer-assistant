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
        self._ollama_status_lbl.setWordWrap(True)

        test_ollama_btn = NeonButton("🔌 Test Connection", "#00D4FF")
        test_ollama_btn.clicked.connect(self._test_ollama)

        fix_ollama_btn = NeonButton("🔧 Fix Ollama (Auto Repair)", "#FFB800")
        fix_ollama_btn.clicked.connect(self._fix_ollama)

        reset_ai_btn = NeonButton("🔄 Reset AI Setup", "#7C3AED")
        reset_ai_btn.clicked.connect(self._reset_ai_setup)

        of.addWidget(self._lbl("Ollama URL:"))
        of.addWidget(self._ollama_url)
        of.addWidget(self._lbl("Model (locked to qwen2.5:0.5b):"))
        of.addWidget(self._ollama_model)
        of.addWidget(self._ollama_status_lbl)
        of.addWidget(test_ollama_btn)
        of.addWidget(fix_ollama_btn)
        of.addWidget(reset_ai_btn)
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

    def _reset_ai_setup(self):
        """Clear AI settings and launch Auto Setup dialog."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Reset AI Setup",
            "This will clear your current AI settings and run the auto-setup to download/configure the correct 0.5b model.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Clear settings
            set_setting("ai_provider", "none")
            set_setting("ollama_model", "")
            
            # Launch setup dialog
            try:
                from ui.auto_setup_dialog import AutoSetupDialog
                dlg = AutoSetupDialog(self)
                dlg.exec()
                
                # Refresh local UI fields
                self._provider_combo.setCurrentIndex(1)
                self._ollama_model.setText(get_setting("ollama_model", "qwen2.5:0.5b"))
                self._show_info("✅ AI Setup completed!")
                AIService.get_instance().reload()
            except Exception as e:
                self._show_info(f"❌ Setup error: {e}")

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

        # Desktop shortcut card
        sc_card = GlassCard(accent_color="#00D4FF")
        scl = QVBoxLayout(sc_card)
        scl.setContentsMargins(20, 16, 20, 16)
        scl.setSpacing(10)
        scl.addWidget(self._lbl("🖥️ Desktop & Shortcuts", color="#00D4FF", size=14, bold=True))
        self._sc_status = QLabel("")
        self._sc_status.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")
        self._sc_status.setWordWrap(True)
        create_sc_btn = NeonButton("🔗 Create Desktop Shortcut", "#00D4FF")
        create_sc_btn.clicked.connect(self._create_shortcut)
        scl.addWidget(self._sc_status)
        scl.addWidget(create_sc_btn)
        layout.addWidget(sc_card)

        layout.addStretch()
        return w

    def _save_system(self):
        startup = self._startup_cb.isChecked()
        set_setting("startup_with_windows", "true" if startup else "false")
        set_setting("minimize_to_tray", "true" if self._tray_cb.isChecked() else "false")
        self._configure_startup(startup)
        self._show_info("✅ System settings saved!")

    def _configure_startup(self, enable: bool):
        """Add/remove app from Windows startup registry using correct app.py path."""
        try:
            import winreg, sys, os
            app_py = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "app.py")
            )
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            cmd = f'"{pythonw}" "{app_py}"'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            if enable:
                winreg.SetValueEx(key, "AISystemOptimizer", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "AISystemOptimizer")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            pass

    def _fix_ollama(self):
        """Auto-repair: start service, pull qwen2.5:0.5b, configure settings."""
        self._ollama_status_lbl.setText("⏳ Diagnosing Ollama... please wait.")
        self._ollama_status_lbl.setStyleSheet("color: #FFB800; font-size: 11px; font-family: 'Segoe UI';")

        def _run():
            from ai.ollama_manager import OllamaManager, TARGET_MODEL
            from config.settings import set_setting
            import time, requests

            steps = []

            # Step 1: Check installed
            if not OllamaManager.is_installed():
                QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                    "❌ Ollama not installed!\nPlease run INSTALL.bat or download from https://ollama.com"))
                return
            steps.append("✅ Ollama installed")

            # Step 2: Start service if not running
            if not OllamaManager.is_api_running():
                QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                    "⏳ Starting Ollama service..."))
                OllamaManager._start_service()
                for _ in range(12):
                    time.sleep(1.5)
                    if OllamaManager.is_api_running():
                        break
            if OllamaManager.is_api_running():
                steps.append("✅ Service running")
            else:
                QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                    "❌ Could not start Ollama service.\nTry restarting your PC."))
                return

            # Step 3: Check if 0.5b installed
            installed = OllamaManager.list_installed_models()
            has_05b = any(m.startswith("qwen2.5:0.5") or m == TARGET_MODEL for m in installed)

            if not has_05b:
                QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                    f"⏳ Pulling {TARGET_MODEL} (~400 MB)... this may take a few minutes."))
                try:
                    with requests.post(
                        "http://localhost:11434/api/pull",
                        json={"name": TARGET_MODEL}, stream=True, timeout=900
                    ) as resp:
                        for line in resp.iter_lines():
                            if line:
                                import json as _json
                                d = _json.loads(line)
                                pct = ""
                                if d.get("total", 0) > 0:
                                    pct = f" {int(d.get('completed',0)/d['total']*100)}%"
                                msg = f"⏳ Pulling {TARGET_MODEL}{pct}..."
                                QTimer.singleShot(0, lambda m=msg: self._ollama_status_lbl.setText(m))
                                if d.get("status") == "success":
                                    break
                    steps.append(f"✅ Model {TARGET_MODEL} ready")
                except Exception as e:
                    QTimer.singleShot(0, lambda: self._ollama_status_lbl.setText(
                        f"❌ Pull failed: {e}\nCheck internet connection."))
                    return
            else:
                steps.append(f"✅ Model {TARGET_MODEL} already installed")

            # Step 4: Write correct settings
            set_setting("ai_provider", "ollama")
            set_setting("ollama_model", TARGET_MODEL)
            from ai.ai_service import AIService
            AIService.get_instance().reload()
            steps.append("✅ AI configured and active")

            summary = "\n".join(steps)
            QTimer.singleShot(0, lambda s=summary: (
                self._ollama_status_lbl.setText(f"🎉 Repair complete!\n{s}"),
                self._ollama_status_lbl.setStyleSheet(
                    "color: #00FF88; font-size: 11px; font-family: 'Segoe UI';"
                )
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _create_shortcut(self):
        """Create desktop shortcut and optionally pin to startup."""
        import os, sys
        try:
            import winshell
            from win32com.client import Dispatch
            app_py = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "app.py")
            )
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            icon_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.ico")
            )
            if not os.path.exists(icon_path):
                icon_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.png")
                )

            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "AI System Optimizer.lnk")
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = pythonw
            shortcut.Arguments = f'"{app_py}"'
            shortcut.WorkingDirectory = os.path.dirname(app_py)
            shortcut.Description = "AI System Optimizer Assistant by Mohammad Quasif"
            if os.path.exists(icon_path):
                shortcut.IconLocation = icon_path
            shortcut.save()

            self._sc_status.setText(f"✅ Shortcut created on Desktop:\n{shortcut_path}")
            self._sc_status.setStyleSheet("color: #00FF88; font-size: 11px; font-family: 'Segoe UI';")
        except ImportError:
            self._sc_status.setText(
                "⚠️ winshell not installed.\nRun: pip install winshell pywin32"
            )
            self._sc_status.setStyleSheet("color: #FFB800; font-size: 11px; font-family: 'Segoe UI';")
        except Exception as e:
            self._sc_status.setText(f"❌ Failed: {e}")
            self._sc_status.setStyleSheet("color: #FF2D55; font-size: 11px; font-family: 'Segoe UI';")

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
            "Are you sure you want to uninstall?\n\n"
            "This will:\n"
            "  ✓ Remove from Windows startup\n"
            "  ✓ Delete desktop shortcut\n"
            "  ✓ Clear all saved settings\n"
            "  ✓ Open folder so you can delete it\n\n"
            "Note: Ollama and the AI model are NOT removed.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import sys, os, subprocess
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        results = []

        # 1. Remove from startup registry (all known key names)
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            removed = False
            for reg_name in ["AISystemOptimizer", "AI System Optimizer", "AIOptimizer"]:
                try:
                    winreg.DeleteValue(key, reg_name)
                    removed = True
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            results.append("✅ Removed from startup" if removed else "ℹ️ Not in startup")
        except Exception as e:
            results.append(f"⚠️ Startup: {e}")

        # 2. Delete desktop shortcut
        try:
            desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            sc = os.path.join(desktop, "AI System Optimizer.lnk")
            if os.path.exists(sc):
                os.remove(sc)
                results.append("✅ Desktop shortcut removed")
            else:
                results.append("ℹ️ No desktop shortcut found")
        except Exception as e:
            results.append(f"⚠️ Shortcut: {e}")

        # 3. Clear settings database
        try:
            from config.settings import DB_PATH
            db_p = str(DB_PATH)
            if os.path.exists(db_p):
                import sqlite3
                conn = sqlite3.connect(db_p)
                conn.execute("DELETE FROM settings")
                conn.commit()
                conn.close()
                results.append("✅ Settings cleared")
        except Exception as e:
            results.append(f"⚠️ DB: {e}")

        results_text = "\n".join(results)
        QMessageBox.information(
            self, "✅ Uninstall Complete",
            f"Done:\n{results_text}\n\n"
            f"📁 Delete this folder to finish:\n{app_dir}\n\n"
            "File Explorer will open — just delete the folder.\n"
            "App will now close.",
        )
        try:
            subprocess.Popen(f'explorer "{app_dir}"')
        except Exception:
            pass
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()


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
