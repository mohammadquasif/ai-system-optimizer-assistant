"""
Main Window - Fixed thread-safe metrics, voice button, username from system
"""

import os
import sys
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSizePolicy,
    QSystemTrayIcon, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont, QAction

from config.settings import THEME, STYLESHEET, get_setting, set_setting, APP_NAME, APP_VERSION
from monitoring.system_monitor import SystemMonitor, SystemMetrics
from ai.ai_service import AIService
from services.voice_service import VoiceAssistant, VoiceCommandHandler
from ui.widgets import StatusBadge, GlassCard, NeonButton

from ui.pages.dashboard_page import DashboardPage
from ui.pages.ai_chat_page import AIChatPage
from ui.pages.cleanup_page import CleanupPage
from ui.pages.browser_page import BrowserOptimizePage
from ui.pages.performance_page import PerformancePage, StartupAppsPage
from ui.pages.settings_page import SettingsPage
from ui.pages.internet_page import InternetPage

logger = logging.getLogger(__name__)


def _get_system_username() -> str:
    """
    Priority:
    1. Database setting (user_name)
    2. Clean Windows login name
    3. Default 'User'
    """
    # 1. Try Database
    db_name = get_setting("user_name", "")
    if db_name:
        return db_name

    # 2. Try System
    try:
        import getpass, re
        raw = getpass.getuser()
        parts = re.split(r'[^a-zA-Z]+', raw)
        alpha_parts = [p for p in parts if len(p) >= 3]
        if alpha_parts:
            name = max(alpha_parts[:2], key=len)
        elif parts:
            name = parts[0]
        else:
            name = raw
        return name.capitalize()
    except Exception:
        return "User"


# ────────────────────────────────────────────────────────────────
# MONITOR BRIDGE — moves metrics from background thread → main thread
# ────────────────────────────────────────────────────────────────

class MonitorBridge(QObject):
    """Receives metrics from background thread and re-emits on main thread."""
    metrics_ready = pyqtSignal(object)

    def post(self, m: SystemMetrics):
        self.metrics_ready.emit(m)


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
    # Signal emitted from STT background thread — handled on main thread
    voice_command_received = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"AI System Optimizer Assistant v{APP_VERSION}")
        self.setMinimumSize(900, 600)
        # Responsive sizing: detect screen and set proportional window size
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            w = min(1280, int(sg.width() * 0.88))
            h = min(820, int(sg.height() * 0.88))
            self.resize(w, h)
            self.move((sg.width() - w) // 2, (sg.height() - h) // 2)
        else:
            self.resize(1280, 800)

        # App icon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            try:
                QApplication.instance().setWindowIcon(QIcon(icon_path))
            except Exception:
                pass

        self.setStyleSheet(STYLESHEET)

        self._monitor = SystemMonitor(interval=2.0)
        self._bridge  = MonitorBridge()
        self._bridge.metrics_ready.connect(self._on_metrics_main_thread)

        self._voice = VoiceAssistant()
        self._voice_listening = False
        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, NavButton] = {}
        self._current_page = "dashboard"
        self._user_name = _get_system_username()  # MUST be set before _build_ui

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
        main_layout.addWidget(self._build_sidebar())
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
        self._sidebar = QWidget()
        # Responsive: use narrower sidebar on small screens
        screen = QApplication.primaryScreen()
        sw = screen.availableGeometry().width() if screen else 1280
        self._sidebar_expanded = sw >= 1100
        self._sidebar_full_w = 200
        self._sidebar_icon_w = 56
        self._sidebar.setFixedWidth(
            self._sidebar_full_w if self._sidebar_expanded else self._sidebar_icon_w
        )
        self._sidebar.setStyleSheet("background: #080C18; border-right: 1px solid #1E2D45;")
        layout = QVBoxLayout(self._sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo_area = QWidget()
        logo_area.setFixedHeight(60)
        logo_area.setStyleSheet("background: #0A0E1A; border-bottom: 1px solid #1E2D45;")
        logo_layout = QHBoxLayout(logo_area)
        logo_layout.setContentsMargins(10, 8, 10, 8)
        logo_layout.setSpacing(6)
        self._logo_icon = QLabel("⚡")
        self._logo_icon.setStyleSheet("color: #00D4FF; font-size: 18px;")
        self._logo_text = QLabel("AI Optimizer")
        self._logo_text.setStyleSheet(
            "color: #00D4FF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI';"
        )
        self._logo_text.setVisible(self._sidebar_expanded)
        logo_layout.addWidget(self._logo_icon)
        logo_layout.addWidget(self._logo_text, 1)

        # Collapse toggle button
        self._collapse_btn = QPushButton("◀" if self._sidebar_expanded else "▶")
        self._collapse_btn.setFixedSize(20, 20)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #4A6080; border: none; font-size: 10px; }"
            "QPushButton:hover { color: #00D4FF; }"
        )
        self._collapse_btn.clicked.connect(self._toggle_sidebar)
        logo_layout.addWidget(self._collapse_btn)
        layout.addWidget(logo_area)

        nav_items = [
            ("dashboard",   "🏠", "Dashboard"),
            ("ai_chat",     "🤖", "AI Assistant"),
            ("cleanup",     "🧹", "Cleanup"),
            ("browser",     "🌐", "Browser Optim."),
            ("internet",    "📡", "Internet Speed"),
            ("performance", "📊", "Performance"),
            ("startup",     "🚀", "Startup Apps"),
            ("settings",    "⚙️", "Settings"),
        ]
        layout.addSpacing(8)
        self._nav_icon_labels = {}
        for key, icon, label in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            self._nav_buttons[key] = btn
            layout.addWidget(btn)
            self._nav_icon_labels[key] = (icon, label)

        layout.addStretch()

        # Voice command button
        self._voice_btn = QPushButton("🎙️  Voice Command")
        self._voice_btn.setFixedHeight(38)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.clicked.connect(self._toggle_voice)
        self._voice_btn.setStyleSheet("""
            QPushButton {
                background: #1E2D45;
                color: #00D4FF;
                border: 1px solid #00D4FF40;
                border-radius: 6px;
                font-size: 11px;
                font-family: 'Segoe UI';
                margin: 0 8px;
            }
            QPushButton:hover { background: #00D4FF20; border: 1px solid #00D4FF; }
        """)
        layout.addWidget(self._voice_btn)
        layout.addSpacing(4)

        self._user_lbl = QLabel(f"👤  {self._user_name}")
        self._user_lbl.setStyleSheet(
            "color: #4A6080; font-size: 10px; font-family: 'Segoe UI'; padding: 6px 10px;"
        )
        self._user_lbl.setVisible(self._sidebar_expanded)
        layout.addWidget(self._user_lbl)
        return self._sidebar

    def _toggle_sidebar(self):
        """Collapse/expand the sidebar for responsive layouts."""
        self._sidebar_expanded = not self._sidebar_expanded
        w = self._sidebar_full_w if self._sidebar_expanded else self._sidebar_icon_w
        self._sidebar.setFixedWidth(w)
        self._logo_text.setVisible(self._sidebar_expanded)
        self._user_lbl.setVisible(self._sidebar_expanded)
        self._collapse_btn.setText("◀" if self._sidebar_expanded else "▶")
        # Update nav button labels
        for key, btn in self._nav_buttons.items():
            icon, label = self._nav_icon_labels[key]
            if self._sidebar_expanded:
                btn.setText(f"  {icon}  {label}")
            else:
                btn.setText(f" {icon} ")
                btn.setToolTip(label)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #0A0E1A; border-bottom: 1px solid #1E2D45;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(24)

        self._topbar_health = QLabel("Health: --")
        self._topbar_health.setStyleSheet("color: #00FF88; font-size: 13px; font-weight: 600; font-family: 'Segoe UI';")

        ai_row = QHBoxLayout()
        ai_row.setSpacing(6)
        self._ai_dot = StatusBadge("offline")
        self._ai_lbl = QLabel("AI: Checking...")
        self._ai_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        ai_row.addWidget(self._ai_dot)
        ai_row.addWidget(self._ai_lbl)

        ollama_row = QHBoxLayout()
        ollama_row.setSpacing(6)
        self._ollama_dot = StatusBadge("offline")
        self._ollama_lbl = QLabel("Ollama: Checking...")
        self._ollama_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        ollama_row.addWidget(self._ollama_dot)
        ollama_row.addWidget(self._ollama_lbl)

        self._model_lbl = QLabel("")
        self._model_lbl.setStyleSheet("color: #7C3AED; font-size: 12px; font-family: 'Segoe UI';")

        layout.addWidget(self._topbar_health)
        layout.addLayout(ai_row)
        layout.addLayout(ollama_row)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(6)
        self._mic_dot = StatusBadge("offline")
        self._mic_lbl = QLabel("Mic: Off")
        self._mic_lbl.setStyleSheet("color: #4A6080; font-size: 12px; font-family: 'Segoe UI';")
        mic_row.addWidget(self._mic_dot)
        mic_row.addWidget(self._mic_lbl)
        layout.addLayout(mic_row)

        layout.addWidget(self._model_lbl)
        layout.addStretch()

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

        self._pages["dashboard"]   = DashboardPage()
        self._pages["ai_chat"]     = AIChatPage()
        self._pages["cleanup"]     = CleanupPage()
        self._pages["browser"]     = BrowserOptimizePage()
        self._pages["internet"]    = InternetPage()
        self._pages["performance"] = PerformancePage()
        self._pages["startup"]     = StartupAppsPage()
        self._pages["settings"]    = SettingsPage()

        for page in self._pages.values():
            self._stack.addWidget(page)

        self._pages["dashboard"].request_cleanup.connect(self._on_quick_cleanup)
        self._pages["cleanup"].cleanup_done.connect(self._on_cleanup_done)
        self._navigate("dashboard")
        return self._stack

    def _build_statusbar(self) -> QWidget:
        from PyQt6.QtWidgets import QProgressBar
        bar = QWidget()
        bar.setFixedHeight(34)
        bar.setStyleSheet("background: #080C18; border-top: 1px solid #1E2D45;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(20)

        self._status_last_cleanup = QLabel("Last cleanup: Never")
        self._status_last_cleanup.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")
        self._status_cpu = QLabel("CPU: --%")
        self._status_cpu.setStyleSheet("color: #00D4FF; font-size: 10px; font-family: 'Segoe UI';")
        self._status_ram = QLabel("RAM: --%")
        self._status_ram.setStyleSheet("color: #7C3AED; font-size: 10px; font-family: 'Segoe UI';")
        self._status_msg = QLabel("System monitoring active")
        self._status_msg.setStyleSheet("color: #4A6080; font-size: 10px; font-family: 'Segoe UI';")

        # Voice command progress bar + label (hidden until a command runs)
        self._voice_action_lbl = QLabel("")
        self._voice_action_lbl.setStyleSheet(
            "color: #00D4FF; font-size: 10px; font-weight: 600; font-family: 'Segoe UI';"
        )
        self._voice_action_lbl.hide()

        self._voice_progress = QProgressBar()
        self._voice_progress.setFixedWidth(160)
        self._voice_progress.setFixedHeight(6)
        self._voice_progress.setRange(0, 100)
        self._voice_progress.setValue(0)
        self._voice_progress.setTextVisible(False)
        self._voice_progress.setStyleSheet("""
            QProgressBar { background: #1E2D45; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #00D4FF, stop:1 #7C3AED);
                border-radius: 3px;
            }
        """)
        self._voice_progress.hide()

        layout.addWidget(self._status_last_cleanup)
        layout.addWidget(self._status_cpu)
        layout.addWidget(self._status_ram)
        layout.addStretch()
        layout.addWidget(self._voice_action_lbl)
        layout.addWidget(self._voice_progress)
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
        # Monitor — posts to bridge which emits signal on main thread
        self._monitor.register_callback(self._bridge.post)
        self._monitor.start()

        # AI status — check aggressively at first (Ollama may be starting up)
        # then slow down once stable
        self._ai_check_count = 0
        self._refresh_ai_status()
        self._ai_timer = QTimer(self)
        self._ai_timer.timeout.connect(self._refresh_ai_status)
        self._ai_timer.start(5000)  # every 5s initially

        # Voice recognition — emit signal (safe cross-thread delivery to main)
        self.voice_command_received.connect(self._on_voice_command)
        if get_setting("voice_enabled", "true") == "true":
            self._voice.start()
            QTimer.singleShot(2000, lambda: self._voice.greet(self._user_name))
            self._update_mic_status(False)

        # Setup voice command handler with full navigation + action wiring
        def _navigate_and(page: str, action_fn=None):
            """Navigate to page on main thread then optionally run action."""
            QTimer.singleShot(0, lambda: self._navigate(page))
            if action_fn:
                QTimer.singleShot(900, action_fn)

        def _speak_status():
            """Read live system stats via psutil and speak them — no stale data."""
            try:
                import psutil as _ps
                cpu  = _ps.cpu_percent(interval=None)
                vm   = _ps.virtual_memory()
                du   = _ps.disk_usage("C:\\")
                # Derive a simple health label
                if vm.percent > 85 or cpu > 85 or du.percent > 90:
                    health = "under stress"
                elif vm.percent > 65 or cpu > 60:
                    health = "moderate"
                else:
                    health = "healthy"
                self._voice.speak(
                    f"{self._user_name}, your system is {health}. "
                    f"CPU is at {cpu:.0f} percent. "
                    f"RAM is at {vm.percent:.0f} percent, "
                    f"{vm.used / 1e9:.1f} of {vm.total / 1e9:.1f} gigabytes used. "
                    f"Disk C is {du.percent:.0f} percent full."
                )
            except Exception as e:
                logger.error(f"_speak_status error: {e}")
                self._voice.speak("I could not read your system stats right now. Please try again.")

        # Voice progress callback — updates status bar on main thread
        def _voice_progress(msg: str, pct: int):
            QTimer.singleShot(0, lambda m=msg, p=pct: self._on_voice_progress(m, p))

        self._voice_handler = VoiceCommandHandler(
            self._voice,
            {
                "navigate":        lambda page: QTimer.singleShot(0, lambda p=page: self._navigate(p)),
                "cleanup":         lambda: QTimer.singleShot(0, self._pages["cleanup"].run_quick_cleanup),
                "browser_cleanup": lambda: QTimer.singleShot(0,
                    getattr(self._pages["browser"], "_run_optimization", lambda: None)
                ),
                "minimize":        lambda: QTimer.singleShot(0, self.hide),
                "ai_chat":         lambda text="": QTimer.singleShot(0,
                    lambda t=text: self._pages["ai_chat"].send_message_external(t) if t else self._navigate("ai_chat")
                ),
                "status":          _speak_status,
                "internet_check":  self._check_internet_performance,
                "stop_voice":      lambda: QTimer.singleShot(0, self._toggle_voice),
            },
            user_name=self._user_name,
            progress_cb=_voice_progress,
        )

        # Inject command handler into AI chat page for local command interception
        chat_page = self._pages["ai_chat"]
        chat_page.set_command_handler(self._voice_handler)
        chat_page.voice_toggle_requested.connect(self._toggle_voice)


    @pyqtSlot(object)
    def _on_metrics_main_thread(self, m: SystemMetrics):
        """SAFE: called on main thread via signal."""
        try:
            self._pages["dashboard"].update_metrics(m)
        except Exception as e:
            logger.debug(f"Dashboard update error: {e}")

        color_cpu = "#FF2D55" if m.cpu_percent > 80 else "#00D4FF"
        color_ram = "#FF2D55" if m.ram_percent > 80 else "#7C3AED"
        self._status_cpu.setText(f"CPU: {m.cpu_percent:.0f}%")
        self._status_cpu.setStyleSheet(f"color: {color_cpu}; font-size: 10px; font-family: 'Segoe UI';")
        self._status_ram.setText(f"RAM: {m.ram_percent:.0f}%")
        self._status_ram.setStyleSheet(f"color: {color_ram}; font-size: 10px; font-family: 'Segoe UI';")

        score = m.health_score
        color = "#00FF88" if score >= 70 else "#FFB800" if score >= 40 else "#FF2D55"
        self._topbar_health.setText(f"Health: {score}")
        self._topbar_health.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600; font-family: 'Segoe UI';")

    def _refresh_ai_status(self):
        """Non-blocking: check AI status safely using QThread worker."""
        self._ai_check_count = getattr(self, "_ai_check_count", 0) + 1
        if self._ai_check_count == 12:
            self._ai_timer.setInterval(30000)

        def _check():
            from ai.ollama_manager import OllamaManager
            from ai.ai_service import AIService
            ollama_ok = OllamaManager.is_api_running()
            if ollama_ok:
                service = AIService.get_instance()
                service.reload()
                configured = service.is_configured
                model = get_setting("ollama_model", "")
            else:
                configured = False
                model = ""
            return (ollama_ok, configured, model)

        from ui.pages.performance_page import _FetchWorker
        self._ai_worker = _FetchWorker(_check)
        self._ai_worker.result_ready.connect(
            lambda res: self._apply_ai_status(res[0], res[1], res[2])
        )
        self._ai_worker.start()


    def _apply_ai_status(self, ollama_ok: bool, configured: bool, model: str):
        if ollama_ok:
            self._ollama_dot.set_status("online")
            self._ollama_lbl.setText("Ollama: Online")
            self._ollama_lbl.setStyleSheet("color: #00FF88; font-size: 12px; font-family: 'Segoe UI';")
        else:
            self._ollama_dot.set_status("offline")
            self._ollama_lbl.setText("Ollama: Offline")
            self._ollama_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")

        if configured and ollama_ok:
            self._ai_dot.set_status("online")
            self._ai_lbl.setText("AI: Ollama")
            self._ai_lbl.setStyleSheet("color: #00FF88; font-size: 12px; font-family: 'Segoe UI';")
            self._model_lbl.setText(f"Model: {model}" if model else "")
        else:
            self._ai_dot.set_status("offline")
            self._ai_lbl.setText("AI: Offline")
            self._ai_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
            self._model_lbl.setText("")


    def _on_quick_cleanup(self):
        self._navigate("cleanup")
        QTimer.singleShot(100, self._pages["cleanup"].run_quick_cleanup)

    def _on_cleanup_done(self, timestamp: str):
        self._status_last_cleanup.setText(f"Last cleanup: {timestamp}")
        self._pages["dashboard"].set_last_cleanup(timestamp)
        if get_setting("voice_enabled", "true") == "true":
            self._voice.speak(
                f"System cleanup complete, {self._user_name}. "
                "Your PC is now optimized and running faster."
            )

    # ────────────────────────────────────────────────────────
    # VOICE COMMAND TOGGLE
    # ────────────────────────────────────────────────────────

    def _toggle_voice(self):
        """Toggle voice listening on/off. Fixes the if/else logic bug."""
        if self._voice_listening:
            # ── STOP LISTENING ────────────────────────────────────
            self._voice.stop_listening()
            self._voice_listening = False
            self._voice_btn.setText("🎙️  Voice Command")
            self._voice_btn.setStyleSheet("""
                QPushButton {
                    background: #1E2D45; color: #00D4FF;
                    border: 1px solid #00D4FF40; border-radius: 6px;
                    font-size: 12px; font-family: 'Segoe UI'; margin: 0 12px;
                }
                QPushButton:hover { background: #00D4FF20; border: 1px solid #00D4FF; }
            """)
            self._update_mic_status(False)
            self._voice.speak(f"Voice command off, {self._user_name}.")
        else:
            # ── START LISTENING — auto-enable mic + speaker ────────
            self._voice_listening = True
            self._voice_btn.setText("🔴  Listening... (click to stop)")
            self._voice_btn.setStyleSheet("""
                QPushButton {
                    background: #FF2D5520; color: #FF2D55;
                    border: 1px solid #FF2D55; border-radius: 6px;
                    font-size: 12px; font-family: 'Segoe UI'; margin: 0 12px;
                }
                QPushButton:hover { background: #FF2D5540; }
            """)
            # Make sure TTS (speaker) is enabled
            self._voice.set_enabled(True)
            if not self._voice._running:
                self._voice.start()
            self._voice.speak(f"I'm listening, {self._user_name}. What can I do for you?")
            # Use _stt_callback so STT thread crosses safely to main thread via signal
            self._voice.start_listening(self._stt_callback)
            self._update_mic_status(True)

        # Sync mic button state in AI chat page
        if "ai_chat" in self._pages:
            try:
                self._pages["ai_chat"]._mic_btn.update_style(self._voice_listening)
            except Exception:
                pass

    def _update_mic_status(self, listening: bool):
        if listening:
            self._mic_dot.set_status("online")
            self._mic_lbl.setText("Mic: Listening...")
            self._mic_lbl.setStyleSheet("color: #00D4FF; font-size: 12px; font-family: 'Segoe UI';")
        else:
            self._mic_dot.set_status("offline")
            self._mic_lbl.setText("Mic: Off")
            self._mic_lbl.setStyleSheet("color: #4A6080; font-size: 12px; font-family: 'Segoe UI';")

    def _on_voice_progress(self, msg: str, pct: int):
        """Show voice command progress in the status bar."""
        if pct < 0:
            return
        self._voice_action_lbl.setText(msg)
        self._voice_action_lbl.show()
        self._voice_progress.setValue(pct)
        self._voice_progress.show()
        # Auto-hide after completion
        if pct >= 100:
            QTimer.singleShot(2500, self._hide_voice_progress)

    def _hide_voice_progress(self):
        self._voice_action_lbl.hide()
        self._voice_progress.hide()
        self._voice_progress.setValue(0)

    def _on_voice_command(self, text: str):
        """Handle recognized voice command — runs on MAIN THREAD via signal.
        As requested: ALWAYS open AI Assistant page and run command there
        so user sees the question, analysis, and result in chat.
        """
        logger.info(f"[Voice] Redirecting to AI Chat: '{text}'")
        # Visual feedback in status bar
        self._on_voice_progress(f"🎙️ Heard: \"{text}\"", 20)

        # 1. Switch to AI chat page
        self._navigate("ai_chat")

        # 2. Inject and run as a chat message (handles both local actions and AI)
        QTimer.singleShot(100, lambda t=text: self._pages["ai_chat"].send_message_external(t))

        # Clear progress bar after 4 seconds
        QTimer.singleShot(4000, self._hide_voice_progress)

    def _check_internet_performance(self):
        """Analyze bandwidth hogs and offer a boost button — via AI Chat & New Page."""
        from monitoring.system_monitor import get_network_usage
        self._navigate("internet")
        chat = self._pages["ai_chat"]
        
        def _run():
            hogs = get_network_usage()
            if not hogs:
                return "✅ Your network usage is low. No significant bandwidth hogs detected."
            
            report = "🌐 **Network Usage Report**\n" + ("─"*30) + "\n"
            report += "The following apps are actively using your internet:\n\n"
            for h in hogs[:5]:
                report += f"• **{h['name']}** ({h['connections']} active connections) - *{h['type']}*\n"
            
            report += "\n\n💡 **Tip:** If you feel slowness after a browser cleanup, it's usually because the browser is rebuilding its cache. To speed up your connection immediately:\n"
            report += "[BUTTON: 🚀 Boost My Internet | boost_network]"
            return report

        chat._add_system_message("Analyzing your internet connection...")
        from ui.pages.performance_page import _FetchWorker
        worker = _FetchWorker(_run)
        worker.result_ready.connect(lambda res: chat._add_bubble(res, "assistant"))
        worker.start()
        # Ensure worker isn't GC'd
        if not hasattr(self, "_workers"): self._workers = []
        self._workers.append(worker)

    def _stt_callback(self, text: str):
        """Called from STT background thread — emits signal to safely cross to main thread."""
        logger.info(f"[Voice] STT callback: '{text}'")
        self.voice_command_received.emit(text)

    # ────────────────────────────────────────────────────────
    # MISC
    # ────────────────────────────────────────────────────────

    def _update_time(self):
        self._time_lbl.setText(datetime.now().strftime("%H:%M:%S  %d %b %Y"))

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self._tray.setIcon(QIcon(icon_path))
        else:
            # Fallback
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
        menu.setStyleSheet("QMenu { background: #111827; color: #E8F4FD; border: 1px solid #1E2D45; } QMenu::item:selected { background: #1E2D45; }")
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
            self._tray.showMessage("AI Optimizer", "Running in tray.", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self._monitor.stop()
            self._voice.stop()
            event.accept()
