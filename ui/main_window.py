"""
Main Window - Sidebar navigation, top bar, status bar, system tray
"""

import sys
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSizePolicy,
    QSystemTrayIcon, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont, QAction

from config.settings import THEME, STYLESHEET, get_setting, APP_NAME, APP_VERSION
from monitoring.system_monitor import SystemMonitor
from ai.ai_service import AIService
from services.voice_service import VoiceAssistant, VoiceCommandHandler
from ui.widgets import StatusBadge, GlassCard

from ui.pages.dashboard_page import DashboardPage
from ui.pages.ai_chat_page import AIChatPage
from ui.pages.cleanup_page import CleanupPage
from ui.pages.browser_page import BrowserOptimizePage
from ui.pages.performance_page import PerformancePage, StartupAppsPage
from ui.pages.settings_page import SettingsPage

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# NAV BUTTON
# ────────────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}  {label}", parent)
        self._active = False
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._update_style()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #00D4FF20, stop:1 transparent);
                    color: #00D4FF;
                    border: none;
                    border-left: 3px solid #00D4FF;
                    border-radius: 0;
                    text-align: left;
                    padding: 0 16px;
                    font-size: 13px;
                    font-family: 'Segoe UI';
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8BA3C7;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0;
                    text-align: left;
                    padding: 0 16px;
                    font-size: 13px;
                    font-family: 'Segoe UI';
                }
                QPushButton:hover {
                    background: #1E2D4530;
                    color: #E8F4FD;
                    border-left: 3px solid #00D4FF60;
                }
            """)


# ────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        self._monitor = SystemMonitor(interval=2.0)
        self._voice = VoiceAssistant()
        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, NavButton] = {}
        self._current_page = "dashboard"

        self._setup_tray()
        self._build_ui()
        self._start_services()

    # ────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        main_layout.addWidget(self._build_sidebar())

        # Right side: top bar + content + status bar
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_topbar())
        right.addWidget(self._build_content(), 1)
        right.addWidget(self._build_statusbar())

        right_container = QWidget()
        right_container.setLayout(right)
        main_layout.addWidget(right_container, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background: #080C18; border-right: 1px solid #1E2D45;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / App name
        logo_area = QWidget()
        logo_area.setFixedHeight(70)
        logo_area.setStyleSheet("background: #0A0E1A; border-bottom: 1px solid #1E2D45;")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(16, 12, 16, 12)
        app_name = QLabel("⚡ AI Optimizer")
        app_name.setStyleSheet(
            "color: #00D4FF; font-size: 15px; font-weight: 700; font-family: 'Segoe UI';"
        )
        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")
        logo_layout.addWidget(app_name)
        logo_layout.addWidget(version_lbl)
        layout.addWidget(logo_area)

        # Nav items
        nav_items = [
            ("dashboard",    "🏠", "Dashboard"),
            ("ai_chat",      "🤖", "AI Assistant"),
            ("cleanup",      "🧹", "Cleanup"),
            ("browser",      "🌐", "Browser Optim."),
            ("performance",  "📊", "Performance"),
            ("startup",      "🚀", "Startup Apps"),
            ("settings",     "⚙️", "Settings"),
        ]

        layout.addSpacing(10)
        for key, icon, label in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            self._nav_buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # User name at bottom
        user_lbl = QLabel(f"👤  {get_setting('user_name', 'Quasif')}")
        user_lbl.setStyleSheet("color: #4A6080; font-size: 11px; font-family: 'Segoe UI'; padding: 12px 16px;")
        layout.addWidget(user_lbl)

        return sidebar

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #0A0E1A; border-bottom: 1px solid #1E2D45;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(24)

        # Health score
        self._topbar_health = QLabel("Health: 100")
        self._topbar_health.setStyleSheet(
            "color: #00FF88; font-size: 13px; font-weight: 600; font-family: 'Segoe UI';"
        )

        # AI status
        ai_row = QHBoxLayout()
        ai_row.setSpacing(6)
        self._ai_dot = StatusBadge("offline")
        self._ai_lbl = QLabel("AI: Not configured")
        self._ai_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        ai_row.addWidget(self._ai_dot)
        ai_row.addWidget(self._ai_lbl)

        # Ollama status
        ollama_row = QHBoxLayout()
        ollama_row.setSpacing(6)
        self._ollama_dot = StatusBadge("offline")
        self._ollama_lbl = QLabel("Ollama: Offline")
        self._ollama_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        ollama_row.addWidget(self._ollama_dot)
        ollama_row.addWidget(self._ollama_lbl)

        # Model label
        self._model_lbl = QLabel("")
        self._model_lbl.setStyleSheet("color: #7C3AED; font-size: 12px; font-family: 'Segoe UI';")

        layout.addWidget(self._topbar_health)
        layout.addLayout(ai_row)
        layout.addLayout(ollama_row)
        layout.addWidget(self._model_lbl)
        layout.addStretch()

        # Time
        self._time_lbl = QLabel("")
        self._time_lbl.setStyleSheet("color: #4A6080; font-size: 11px; font-family: 'Segoe UI';")
        layout.addWidget(self._time_lbl)

        time_timer = QTimer(self)
        time_timer.timeout.connect(self._update_time)
        time_timer.start(1000)
        self._update_time()

        return bar

    def _build_content(self) -> QWidget:
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #0A0E1A;")

        # Instantiate pages
        self._pages["dashboard"] = DashboardPage()
        self._pages["ai_chat"] = AIChatPage()
        self._pages["cleanup"] = CleanupPage()
        self._pages["browser"] = BrowserOptimizePage()
        self._pages["performance"] = PerformancePage()
        self._pages["startup"] = StartupAppsPage()
        self._pages["settings"] = SettingsPage()

        for page in self._pages.values():
            self._stack.addWidget(page)

        # Connect signals
        self._pages["dashboard"].request_cleanup.connect(
            lambda: self._navigate("cleanup") or self._pages["cleanup"].run_quick_cleanup()
        )
        self._pages["cleanup"].cleanup_done.connect(self._on_cleanup_done)

        self._navigate("dashboard")
        return self._stack

    def _build_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(30)
        bar.setStyleSheet("background: #080C18; border-top: 1px solid #1E2D45;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(24)

        self._status_last_cleanup = QLabel("Last cleanup: Never")
        self._status_last_cleanup.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")

        self._status_cpu = QLabel("CPU: 0%")
        self._status_cpu.setStyleSheet("color: #00D4FF; font-size: 10px; font-family: 'Segoe UI';")

        self._status_ram = QLabel("RAM: 0%")
        self._status_ram.setStyleSheet("color: #7C3AED; font-size: 10px; font-family: 'Segoe UI';")

        self._status_msg = QLabel("System monitoring active")
        self._status_msg.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")

        layout.addWidget(self._status_last_cleanup)
        layout.addWidget(self._status_cpu)
        layout.addWidget(self._status_ram)
        layout.addStretch()
        layout.addWidget(self._status_msg)
        return bar

    # ────────────────────────────────────────────────────────
    # NAVIGATION
    # ────────────────────────────────────────────────────────

    def _navigate(self, page_key: str):
        if page_key not in self._pages:
            return
        self._current_page = page_key
        self._stack.setCurrentWidget(self._pages[page_key])
        for key, btn in self._nav_buttons.items():
            btn.set_active(key == page_key)

    # ────────────────────────────────────────────────────────
    # SERVICES
    # ────────────────────────────────────────────────────────

    def _start_services(self):
        # System monitor
        self._monitor.register_callback(self._on_metrics)
        self._monitor.start()

        # AI status check timer
        ai_timer = QTimer(self)
        ai_timer.timeout.connect(self._refresh_ai_status)
        ai_timer.start(10000)
        self._refresh_ai_status()

        # Voice greeting
        if get_setting("voice_enabled", "true") == "true":
            self._voice.start()
            name = get_setting("user_name", "Quasif")
            QTimer.singleShot(2000, lambda: self._voice.greet(name))

    def _on_metrics(self, m):
        """Called from monitor thread — update UI via timer-safe signals."""
        # Dashboard
        try:
            self._pages["dashboard"].update_metrics(m)
        except Exception:
            pass

        # Status bar
        color_cpu = "#FF2D55" if m.cpu_percent > 80 else "#00D4FF"
        color_ram = "#FF2D55" if m.ram_percent > 80 else "#7C3AED"
        self._status_cpu.setText(f"CPU: {m.cpu_percent:.0f}%")
        self._status_cpu.setStyleSheet(f"color: {color_cpu}; font-size: 10px; font-family: 'Segoe UI';")
        self._status_ram.setText(f"RAM: {m.ram_percent:.0f}%")
        self._status_ram.setStyleSheet(f"color: {color_ram}; font-size: 10px; font-family: 'Segoe UI';")

        # Health
        score = m.health_score
        color = "#00FF88" if score >= 70 else "#FFB800" if score >= 40 else "#FF2D55"
        self._topbar_health.setText(f"Health: {score}")
        self._topbar_health.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 600; font-family: 'Segoe UI';"
        )

    def _refresh_ai_status(self):
        service = AIService.get_instance()
        from ai.ai_service import OllamaInstaller
        ollama_running = OllamaInstaller.is_running()

        if ollama_running:
            self._ollama_dot.set_status("online")
            self._ollama_lbl.setText("Ollama: Online")
        else:
            self._ollama_dot.set_status("offline")
            self._ollama_lbl.setText("Ollama: Offline")

        if service.is_configured:
            self._ai_dot.set_status("online" if service.is_available else "warning")
            self._ai_lbl.setText(f"AI: {service.provider_name.title()}")
            model = get_setting("ollama_model", "")
            self._model_lbl.setText(f"Model: {model}" if model else "")
        else:
            self._ai_dot.set_status("offline")
            self._ai_lbl.setText("AI: Not configured")
            self._model_lbl.setText("")

    def _on_cleanup_done(self, timestamp: str):
        self._status_last_cleanup.setText(f"Last cleanup: {timestamp}")
        self._pages["dashboard"].set_last_cleanup(timestamp)
        if get_setting("voice_enabled", "true") == "true":
            self._voice.speak("System cleanup complete. Your PC is now optimized.")

    def _update_time(self):
        self._time_lbl.setText(datetime.now().strftime("%H:%M:%S  %d %b %Y"))

    # ────────────────────────────────────────────────────────
    # SYSTEM TRAY
    # ────────────────────────────────────────────────────────

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        # Create a simple colored icon
        pix = QPixmap(32, 32)
        pix.fill(QColor("#0A0E1A"))
        painter = QPainter(pix)
        painter.setPen(QColor("#00D4FF"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
        painter.end()
        self._tray.setIcon(QIcon(pix))
        self._tray.setToolTip("AI System Optimizer Assistant")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #111827; color: #E8F4FD; border: 1px solid #1E2D45; }
            QMenu::item:selected { background: #1E2D45; }
        """)
        show_act = QAction("Show Window", self)
        show_act.triggered.connect(self.show_normal)
        cleanup_act = QAction("Quick Cleanup", self)
        cleanup_act.triggered.connect(lambda: self._pages["cleanup"].run_quick_cleanup())
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(show_act)
        menu.addAction(cleanup_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if get_setting("minimize_to_tray", "true") == "true":
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "AI Optimizer", "Running in background. Double-click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )
        else:
            self._monitor.stop()
            self._voice.stop()
            event.accept()
