"""
AI System Optimizer Assistant
==============================
Author  : Mohammad Quasif, DBA (AI) | B.Tech (CS)
GitHub  : https://github.com/mohammadquasif/ai-system-optimizer
License : Personal Use Only (Non-Commercial)
Version : 1.0.0

Tags/Keywords (AIEO / SEO):
  ai system optimizer, windows pc optimizer, ollama desktop assistant,
  local ai windows tool, ai performance booster, voice assistant windows,
  one-click pc cleaner, offline ai assistant, llm pc optimizer,
  free ai pc tool, open source windows optimizer, ai copilot desktop,
  on-demand ai, auto close ram free, startup ai assistant

Description:
  A fully automated, AI-powered Windows optimization suite.
  - Runs at startup, greets the user, then auto-closes after idle
  - On demand only — zero background RAM usage when closed
  - Installs itself, downloads Ollama, picks the lightest model (0.5b–1.5b)
  - Safe system cleanup, DNS flush, RAM trim, GPU cache, voice commands
  - Chip-based command UI (click chips, type, or speak)

Usage:
    python app.py          # Run directly
    run.bat                # Windows batch launcher
    AISystemOptimizer.exe  # Packaged EXE (from build.bat)

Startup:
    Added automatically to Windows startup registry by INSTALL.bat
    → Greets user → monitors for 5 min idle → auto-closes → frees RAM
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient, QBrush, QPen

from config.settings import get_setting, set_setting, init_db, logger as app_logger
from ai.ollama_manager import OllamaManager, SystemProfile


# ─────────────────────────────────────────────────────────────────
# SPLASH SCREEN
# ─────────────────────────────────────────────────────────────────

def create_splash() -> QSplashScreen:
    pix = QPixmap(520, 280)
    pix.fill(QColor("#0A0E1A"))
    painter = QPainter(pix)

    grad = QLinearGradient(0, 0, 520, 280)
    grad.setColorAt(0, QColor("#0A0E1A"))
    grad.setColorAt(1, QColor("#0D1221"))
    painter.fillRect(pix.rect(), QBrush(grad))

    pen = QPen(QColor("#00D4FF40"))
    pen.setWidth(1)
    painter.setPen(pen)
    painter.drawRect(0, 0, 519, 279)

    painter.setPen(QColor("#00D4FF"))
    painter.setFont(QFont("Segoe UI", 36))
    painter.drawText(30, 100, "⚡")

    painter.setPen(QColor("#E8F4FD"))
    painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
    painter.drawText(90, 90, "AI System Optimizer")

    painter.setPen(QColor("#8BA3C7"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(90, 115, "Assistant — On-Demand AI")

    painter.setPen(QColor("#4A6080"))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(30, 200, "by Mohammad Quasif, DBA (AI)  •  github.com/mohammadquasif")
    painter.drawText(30, 218, "Powered by Ollama  •  Personal Use License")
    painter.drawText(30, 250, "Initializing — auto-closes after idle...")

    painter.end()
    return QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)


# ─────────────────────────────────────────────────────────────────
# IDLE CLOSE DIALOG
# ─────────────────────────────────────────────────────────────────

def _show_countdown_overlay(window, seconds_left: int):
    """Update the status bar message with idle countdown."""
    try:
        window._status_msg.setText(
            f"⏱️ Idle — closing in {seconds_left}s to free RAM. Click anywhere to cancel."
        )
        window._status_msg.setStyleSheet(
            "color: #FFB800; font-size: 10px; font-family: 'Segoe UI';"
        )
    except Exception:
        pass


def _clear_countdown(window):
    try:
        window._status_msg.setText("System monitoring active")
        window._status_msg.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    app_logger.info("=" * 60)
    app_logger.info("AI System Optimizer Assistant v1.0.0 — Mohammad Quasif")
    app_logger.info("=" * 60)

    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("AI System Optimizer Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Mohammad Quasif")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 11))

    # Show splash
    splash = create_splash()
    splash.show()
    app.processEvents()

    # ── Smart pre-check: skip setup if Ollama + model already ready ──
    from ai.ollama_manager import OllamaManager, PREFERRED_MODELS
    from config.settings import get_setting, set_setting

    first_run       = get_setting("first_run", "true") == "true"
    ollama_ready    = OllamaManager.is_api_running()
    installed_models = OllamaManager.list_installed_models() if ollama_ready else []

    # Check if any preferred model is already installed
    preferred_installed = None
    for pref in PREFERRED_MODELS:
        for inst in installed_models:
            if inst.startswith(pref.split(":")[0]) or inst == pref:
                preferred_installed = inst
                break
        if preferred_installed:
            break

    run_setup = first_run and not (ollama_ready and preferred_installed)

    # If Ollama+model already ready, auto-configure settings without showing dialog
    if ollama_ready and preferred_installed:
        set_setting("ai_provider", "ollama")
        set_setting("ollama_model", preferred_installed)
        set_setting("first_run", "false")
        app_logger.info(f"Fast path: using model {preferred_installed}")

    if run_setup:
        splash.finish(None)
        from ui.auto_setup_dialog import AutoSetupDialog
        dlg = AutoSetupDialog()
        dlg.exec()
        set_setting("first_run", "false")
    else:
        QTimer.singleShot(1800, splash.close)

    # ── Main window ──────────────────────────────────────────────
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    # ── Voice greeting ───────────────────────────────────────────
    if get_setting("voice_enabled", "true") == "true":
        from services.voice_service import VoiceAssistant
        voice = VoiceAssistant()
        voice.start()
        name = get_setting("user_name", "Quasif")
        QTimer.singleShot(2500, lambda: voice.greet(name))
        window._voice = voice

    # ── Idle Watcher — auto-close after 5 min of inactivity ─────
    idle_minutes   = int(get_setting("idle_close_minutes", "5"))
    from services.idle_watcher import IdleWatcher

    idle_watcher = IdleWatcher(
        idle_minutes      = idle_minutes,
        countdown_seconds = 60,
        countdown_cb = lambda secs: QTimer.singleShot(
            0, lambda s=secs: _show_countdown_overlay(window, s)
        ),
        warn_cb  = lambda: QTimer.singleShot(0, lambda: None),
        close_cb = lambda: QTimer.singleShot(0, _do_idle_close),
    )
    idle_watcher.start()
    window._idle_watcher = idle_watcher  # keep reference

    # Cancel countdown on any window interaction
    window.mousePressEvent   = lambda e: (idle_watcher.reset(), _clear_countdown(window))
    window.keyPressEvent     = lambda e: (idle_watcher.reset(), _clear_countdown(window))
    window.wheelEvent        = lambda e: idle_watcher.reset()

    def _do_idle_close():
        """Save state and quit cleanly, freeing all RAM."""
        app_logger.info("IdleWatcher: clean shutdown initiated.")
        if get_setting("voice_enabled", "true") == "true":
            try:
                window._voice.speak("Closing now to free your memory. I will be back when you need me.")
            except Exception:
                pass
        # Small delay for voice to finish
        QTimer.singleShot(2000, lambda: (
            set_setting("last_close_reason", "idle"),
            app.quit()
        ))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
