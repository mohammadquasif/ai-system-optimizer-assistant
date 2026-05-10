"""
AI Chat Page - Streaming chat UI
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QScrollArea, QFrame, QPushButton, QComboBox,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon

from ui.widgets import GlassCard, NeonButton, NeonIconButton, AIThinkingWidget, StatusBadge
from ai.ai_service import AIService
from config.settings import get_setting, get_db
from datetime import datetime


# ────────────────────────────────────────────────────────────────
# AI Worker (runs in background thread)
# ────────────────────────────────────────────────────────────────

class AIWorker(QObject):
    token_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, message: str, history: list, context_fn=None):
        """context_fn is a callable that builds the system context.
        It is called INSIDE the background thread to avoid blocking the UI."""
        super().__init__()
        self.message = message
        self.history = history
        self._context_fn = context_fn  # callable, run in bg thread

    @pyqtSlot()
    def run(self):
        try:
            # Build context in background thread - safe, never blocks UI
            context = ""
            if self._context_fn:
                try:
                    context = self._context_fn()
                except Exception:
                    context = ""
            service = AIService.get_instance()
            full = service.chat(
                self.message,
                history=self.history,
                stream_cb=lambda tok: self.token_received.emit(tok),
                context=context,
            )
            self.finished.emit(full)
        except Exception as e:
            self.error.emit(str(e))


# ────────────────────────────────────────────────────────────────
# CHAT BUBBLE
# ────────────────────────────────────────────────────────────────

class ChatBubble(QFrame):
    def __init__(self, text: str, role: str = "user", parent=None):
        super().__init__(parent)
        self._role = role
        self._full_text = text  # accumulate here during streaming
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        if role == "user":
            bg, color, align = "#1E2D45", "#E8F4FD", Qt.AlignmentFlag.AlignRight
            border_color = "#00D4FF40"
            name_color = "#00D4FF"
        else:
            bg, color, align = "#0D1525", "#E8F4FD", Qt.AlignmentFlag.AlignLeft
            border_color = "#7C3AED60"
            name_color = "#7C3AED"

        role_lbl = QLabel("You" if role == "user" else "🤖 AI Assistant")
        role_lbl.setStyleSheet(
            f"color: {name_color}; font-size: 10px; font-weight: 700; "
            "font-family: 'Segoe UI'; background: transparent;"
        )
        role_lbl.setAlignment(align)
        layout.addWidget(role_lbl)

        # Use QTextEdit for AI (supports long text, no layout thrash)
        # Use QLabel for user (short, single-line)
        if role == "assistant":
            self._text_edit = QTextEdit()
            self._text_edit.setReadOnly(True)
            self._text_edit.setPlainText(text)
            self._text_edit.setStyleSheet(
                f"color: {color}; font-size: 13px; font-family: 'Segoe UI'; "
                "background: transparent; border: none; padding: 0px;"
            )
            self._text_edit.setMinimumHeight(40)
            self._text_edit.setMaximumHeight(600)
            self._text_edit.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            self._text_edit.document().contentsChanged.connect(self._auto_resize)
            layout.addWidget(self._text_edit)
            self._text_lbl = None
        else:
            self._text_lbl = QLabel(text)
            self._text_lbl.setStyleSheet(
                f"color: {color}; font-size: 13px; font-family: 'Segoe UI';"
            )
            self._text_lbl.setWordWrap(True)
            self._text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(self._text_lbl)
            self._text_edit = None

        self.setStyleSheet(
            f"ChatBubble {{ background: {bg}; border: 1px solid {border_color}; "
            "border-radius: 12px; }}"
        )
        self.setMaximumWidth(720)

        # Action buttons container
        self._btn_container = QWidget()
        self._btn_container.setStyleSheet("background: transparent;")
        self._btn_layout = QHBoxLayout(self._btn_container)
        self._btn_layout.setContentsMargins(0, 4, 0, 0)
        self._btn_layout.setSpacing(8)
        self._btn_layout.addStretch()
        layout.addWidget(self._btn_container)
        self._btn_container.hide()

        self._action_callback = None

    def _auto_resize(self):
        """Resize QTextEdit to fit content without scrollbar."""
        if self._text_edit:
            doc_h = int(self._text_edit.document().size().height())
            self._text_edit.setFixedHeight(min(max(doc_h + 16, 40), 600))

    def set_action_callback(self, fn):
        self._action_callback = fn

    def append_text(self, token: str):
        """Called per streaming token - NEVER parse buttons here."""
        self._full_text += token
        if self._text_edit:
            # Efficient append via cursor
            cursor = self._text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(token)
            self._text_edit.setTextCursor(cursor)
        elif self._text_lbl:
            self._text_lbl.setText(self._full_text)

    def finalize(self):
        """Call ONCE after streaming ends to parse buttons and clean text."""
        self._parse_buttons()

    def set_text(self, text: str):
        self._full_text = text
        if self._text_edit:
            self._text_edit.setPlainText(text)
        elif self._text_lbl:
            self._text_lbl.setText(text)

    def _parse_buttons(self):
        """Parse [BUTTON: Label | Command] tags. Called once after streaming completes."""
        import re
        text = self._full_text
        matches = re.findall(r"\[BUTTON:\s*(.*?)\s*\|\s*(.*?)\s*\]", text)
        if not matches:
            return
        clean_text = re.sub(r"\[BUTTON:.*?\]", "", text).strip()
        self._full_text = clean_text
        if self._text_edit:
            self._text_edit.setPlainText(clean_text)
        elif self._text_lbl:
            self._text_lbl.setText(clean_text)
        # Clear existing buttons
        while self._btn_layout.count() > 1:
            item = self._btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for label, cmd in matches:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #7C3AED20; color: #A78BFA;"
                "  border: 1px solid #7C3AED80; border-radius: 6px;"
                "  padding: 5px 14px; font-size: 11px; font-weight: 600;"
                "  font-family: 'Segoe UI';"
                "}"
                "QPushButton:hover { background: #7C3AED50; border-color: #A78BFA; }"
            )
            btn.clicked.connect(
                lambda _, c=cmd: self._action_callback(c) if self._action_callback else None
            )
            self._btn_layout.insertWidget(self._btn_layout.count() - 1, btn)
            self._btn_container.show()


# ────────────────────────────────────────────────────────────────
# AI CHAT PAGE
# ────────────────────────────────────────────────────────────────

class AIChatPage(QWidget):
    voice_toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chat_history: list = []
        self._current_bubble: ChatBubble = None
        self._worker_thread: QThread = None
        self._worker: AIWorker = None
        self._is_processing: bool = False   # guard against double-send
        self._cmd_handler = None   # injected by MainWindow after init
        self._setup_ui()
        self._load_history()

    def set_command_handler(self, handler):
        """Allow MainWindow to inject VoiceCommandHandler for local command routing."""
        self._cmd_handler = handler

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Header ───────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("🤖 AI Assistant")
        title.setStyleSheet(
            "color: #E8F4FD; font-size: 22px; font-weight: 700; font-family: 'Segoe UI';"
        )
        self._status_row = QHBoxLayout()
        self._ai_status_dot = StatusBadge("offline")
        self._ai_status_lbl = QLabel("AI Not Configured")
        self._ai_status_lbl.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        self._model_lbl = QLabel("")
        self._model_lbl.setStyleSheet("color: #7C3AED; font-size: 12px; font-family: 'Segoe UI';")
        self._status_row.addWidget(self._ai_status_dot)
        self._status_row.addWidget(self._ai_status_lbl)
        self._status_row.addSpacing(16)
        self._status_row.addWidget(self._model_lbl)
        self._status_row.addStretch()

        header.addWidget(title)
        header.addStretch()
        header.addLayout(self._status_row)
        root.addLayout(header)

        # ── Not configured notice ─────────────────────────────────
        self._no_ai_card = GlassCard(accent_color="#FFB800")
        no_ai_layout = QVBoxLayout(self._no_ai_card)
        no_ai_layout.setContentsMargins(24, 20, 24, 20)
        no_ai_lbl = QLabel("⚠️  AI Assistant Not Configured")
        no_ai_lbl.setStyleSheet(
            "color: #FFB800; font-size: 15px; font-weight: 700; font-family: 'Segoe UI';"
        )
        no_ai_desc = QLabel(
            "Go to Settings → AI Configuration to set up Ollama (local AI), "
            "OpenAI, or Anthropic."
        )
        no_ai_desc.setStyleSheet("color: #8BA3C7; font-size: 12px; font-family: 'Segoe UI';")
        no_ai_desc.setWordWrap(True)
        no_ai_layout.addWidget(no_ai_lbl)
        no_ai_layout.addWidget(no_ai_desc)
        root.addWidget(self._no_ai_card)

        # ── Chat scroll area ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #080C18; border: 1px solid #1E2D45; border-radius: 12px; }"
        )
        self._chat_container = QWidget()
        self._chat_container.setStyleSheet("background: transparent;")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(16, 16, 16, 16)
        self._chat_layout.setSpacing(12)
        self._chat_layout.addStretch()
        self._scroll.setWidget(self._chat_container)
        root.addWidget(self._scroll, 1)

        # ── Thinking indicator ────────────────────────────────────
        thinking_row = QHBoxLayout()
        self._thinking = AIThinkingWidget()
        self._thinking.hide()
        self._thinking_lbl = QLabel("AI is thinking...")
        self._thinking_lbl.setStyleSheet("color: #7C3AED; font-size: 11px; font-family: 'Segoe UI';")
        self._thinking_lbl.hide()
        thinking_row.addWidget(self._thinking)
        thinking_row.addWidget(self._thinking_lbl)
        thinking_row.addStretch()
        root.addLayout(thinking_row)

        # ── Quick chip buttons ────────────────────────────────────
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chip_defs = [
            ("📋 Full Report",      "Generate a full structured system health report. Include sections: Health Score, CPU Analysis, RAM Analysis, Disk Health, Top Memory Hogs, Startup Impact, and Recommendations with [BUTTON: Label | Action] for each fix."),
            ("🌐 Internet Speed",   "Who is using my internet bandwidth? Analyze network hogs and provide [BUTTON: Boost Internet | boost_network] to fix lag."),
            ("🚀 Boost Internet",   "Run a network optimization now. Flush DNS, reset Winsock and clear ARP cache to fix connection issues. [BUTTON: Boost Connection | boost_network]"),
            ("🧹 Clean System",     "My system needs cleanup. What is consuming most resources? Give me [BUTTON: Full Clean | cleanup] and explain what will be freed."),
            ("⚡ RAM Analysis",     "Analyze my RAM usage in detail. Which processes are RAM hogs? Give [BUTTON: Clean Memory | cleanup] and [BUTTON: Check Startup | startup] buttons."),
            ("🚀 Startup Impact",   "How many startup apps are slowing my boot? Analyze startup load and give me [BUTTON: Manage Startup | startup] to fix it."),
        ]
        for label, prompt in chip_defs:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #111827; color: #00D4FF;"
                "  border: 1px solid #00D4FF40; border-radius: 15px;"
                "  padding: 0 14px; font-size: 11px; font-family: 'Segoe UI';"
                "}"
                "QPushButton:hover { background: #1E2D45; border-color: #00D4FF; }"
                "QPushButton:pressed { background: #00D4FF20; }"
            )
            btn.clicked.connect(lambda _, p=prompt: self._chip_clicked(p))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        root.addLayout(chips_row)

        # ── Input row ─────────────────────────────────────────────
        input_card = GlassCard(accent_color="#00D4FF")
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(12)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask AI anything about your system... (Press Enter to send)")
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background: #0D1221; color: #E8F4FD;"
            "  border: 1px solid #1E2D45; border-radius: 8px;"
            "  padding: 10px 14px; font-size: 13px; font-family: 'Segoe UI';"
            "}"
            "QLineEdit:focus { border: 1px solid #00D4FF60; }"
        )
        self._input.returnPressed.connect(self._send_message)

        self._send_btn = NeonButton("Send ➤", "#00D4FF")
        self._send_btn.setFixedWidth(100)
        self._send_btn.clicked.connect(self._send_message)

        self._mic_btn = NeonIconButton("🎙️", "#7C3AED")
        self._mic_btn.setToolTip("Click to activate voice - mic + speaker auto-enable")
        self._mic_btn.clicked.connect(self._on_mic_clicked)

        self._clear_btn = NeonButton("Clear", "#FF2D55")
        self._clear_btn.setFixedWidth(80)
        self._clear_btn.clicked.connect(self._clear_chat)

        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(self._mic_btn)
        input_layout.addWidget(self._send_btn)
        input_layout.addWidget(self._clear_btn)
        root.addWidget(input_card)

        # Initial refresh
        QTimer.singleShot(500, self._refresh_ai_status)

    # ─────────────────────────────────────────────────────────────
    # AI STATUS
    # ─────────────────────────────────────────────────────────────

    def _refresh_ai_status(self):
        """Non-blocking: check AI status safely using QThread worker."""
        def _check():
            try:
                service = AIService.get_instance()
                configured = service.is_configured
                if not configured:
                    return (False, False, "")
                available = service.is_available
                model = get_setting("ollama_model", "")
                return (True, available, model)
            except Exception:
                return (False, False, "")

        from ui.pages.performance_page import _FetchWorker
        self._status_worker = _FetchWorker(_check)
        self._status_worker.result_ready.connect(
            lambda res: self._apply_status(res[0], res[1], res[2])
        )
        self._status_worker.start()

    def _apply_status(self, configured: bool, available: bool, model: str):
        if configured and available:
            self._ai_status_dot.set_status("online")
            self._ai_status_lbl.setText("AI Online")
            self._ai_status_lbl.setStyleSheet("color: #00FF88; font-size: 12px; font-family: 'Segoe UI';")
            self._model_lbl.setText(f"Model: {model}")
            self._no_ai_card.hide()
        elif configured:
            self._ai_status_dot.set_status("warning")
            self._ai_status_lbl.setText("AI Offline")
            self._ai_status_lbl.setStyleSheet("color: #FFB800; font-size: 12px; font-family: 'Segoe UI';")
        else:
            self._ai_status_dot.set_status("offline")
            self._ai_status_lbl.setText("AI Not Configured")
            self._no_ai_card.show()

    # ─────────────────────────────────────────────────────────────
    # CHAT OPERATIONS
    # ─────────────────────────────────────────────────────────────

    def send_message_external(self, text: str):
        """Allow other pages/voice to inject a message."""
        self._input.setText(text)
        self._send_message()

    def _on_mic_clicked(self):
        """Auto-enable both mic (STT) and speaker (TTS) then toggle voice."""
        # Ensure voice assistant is running before toggling
        try:
            win = self.window()
            if hasattr(win, '_voice') and win._voice:
                win._voice.set_enabled(True)
                if not win._voice._running:
                    win._voice.start()
        except Exception:
            pass
        self.voice_toggle_requested.emit()

    def _chip_clicked(self, prompt: str):
        self._input.setText(prompt)
        self._send_message()

    def _send_message(self):
        text = self._input.text().strip()
        if not text:
            return

        # Guard: don't start a new request while one is in progress
        if self._is_processing:
            self._add_system_message("Still processing... please wait.")
            return

        # ── LOCAL COMMAND INTERCEPTION ─────────────────────────────────
        if self._cmd_handler:
            handled, resp_text = self._cmd_handler.handle_chat(text, speak_response=True)
            if handled:
                self._input.clear()
                self._add_bubble(text, "user")
                # Show the 'analyzed' response in the chat bubble too
                QTimer.singleShot(400, lambda: self._add_bubble(resp_text, "assistant"))
                return

        service = AIService.get_instance()
        if not service.is_configured:
            self._add_system_message(
                "AI is not configured. Please go to Settings → AI Configuration."
            )
            return

        self._is_processing = True
        self._input.clear()
        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)

        # Add user bubble
        self._add_bubble(text, "user")
        self._chat_history.append({"role": "user", "content": text})
        self._save_message("user", text)

        # Show thinking with status updates
        self._thinking.start()
        self._thinking_lbl.setText("AI is analyzing your system...")
        self._thinking_lbl.show()

        # Simulate steps for a "pro" feel
        def _update_step(step_idx):
            steps = [
                "🔍 Gathering system metrics...",
                "📊 Checking RAM & CPU peaks...",
                "🧠 Generating AI recommendation...",
                "✨ Finalizing report..."
            ]
            if step_idx < len(steps):
                self._thinking_lbl.setText(steps[step_idx])
                QTimer.singleShot(800, lambda: _update_step(step_idx + 1))
        
        _update_step(0)

        # Start AI response bubble
        prefix = ""
        if any(k in text.lower() for k in ["analyze", "status", "how is my", "report"]):
            prefix = "📊 **System Analysis Report**\n" + ("─"*40) + "\n\n"
        self._current_bubble = self._add_bubble(prefix, "assistant")

        # ── Start background thread - context built INSIDE thread ──
        self._worker_thread = QThread()
        self._worker = AIWorker(text, self._chat_history[:-1],
                                context_fn=self._build_system_context)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        # Safe teardown - never call thread.wait() on main thread
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.start()

    def _on_token(self, token: str):
        if self._current_bubble:
            self._current_bubble.append_text(token)
        self._scroll_to_bottom()

    def _on_finished(self, full_text: str):
        """Called on main thread via Qt signal - safe to update UI here."""
        self._is_processing = False
        self._chat_history.append({"role": "assistant", "content": full_text})
        self._save_message("assistant", full_text)
        self._thinking.stop()
        self._thinking_lbl.hide()
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._input.setFocus()
        # Finalize the bubble: parse [BUTTON:] tags now that full text is received
        if self._current_bubble:
            self._current_bubble.finalize()
            self._current_bubble = None
        self._worker_thread = None
        self._worker = None
        # Speak a clean summary via TTS
        if self._cmd_handler and full_text:
            try:
                self._cmd_handler.voice.set_enabled(True)
                if not self._cmd_handler.voice._running:
                    self._cmd_handler.voice.start()
                import re
                clean = re.sub(r'\[BUTTON:.*?\]', '', full_text).strip()
                snippet = clean[:250].replace("\n", " ")
                self._cmd_handler.voice.speak(snippet)
            except Exception:
                pass

    def _build_system_context(self) -> str:
        """Build a rich, real-time system context string from pre-written system monitor data."""
        try:
            import psutil
            from monitoring.system_monitor import get_startup_apps, get_disk_usage_breakdown

            # --- Live metrics ---
            cpu = psutil.cpu_percent(interval=None)
            cpu_cores = psutil.cpu_count(logical=False)
            cpu_logical = psutil.cpu_count(logical=True)
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk breakdown (all partitions)
            disks = get_disk_usage_breakdown()
            disk_str = " | ".join(
                f"{mp}:{info['used_gb']:.1f}/{info['total_gb']:.1f}GB ({info['percent']}%)"
                for mp, info in disks.items()
            )

            # Network
            from monitoring.system_monitor import get_network_usage
            net_hogs = get_network_usage()
            net_hogs_str = ", ".join([f"{h['name']} ({h['connections']} conns)" for h in net_hogs[:5]])
            net = psutil.net_io_counters()
            net_str = (
                f"Sent:{net.bytes_sent//1024//1024}MB "
                f"Recv:{net.bytes_recv//1024//1024}MB | Hogs: {net_hogs_str or 'None'}"
            )

            # Temperature
            temp_str = "N/A"
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for entries in temps.values():
                        if entries:
                            temp_str = f"{entries[0].current:.0f}°C"
                            break
            except Exception:
                pass

            # Top processes by RAM + CPU
            procs = []
            try:
                for p in psutil.process_iter(['name', 'memory_percent', 'cpu_percent']):
                    try:
                        info = p.info
                        if info['memory_percent'] and info['memory_percent'] > 0.1:
                            procs.append(info)
                    except Exception:
                        pass
            except Exception:
                pass

            # Top processes by RAM + CPU formatting
            top_by_ram = "None"
            try:
                if procs:
                    procs.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
                    top_by_ram = ", ".join(
                        f"{p['name']}(RAM:{p['memory_percent']:.1f}% CPU:{p.get('cpu_percent',0):.1f}%)"
                        for p in procs[:6]
                    )
            except Exception:
                pass

            # Startup apps
            try:
                startup_list = get_startup_apps()
                startup_str = f"{len(startup_list)} entries: " + ", ".join([s['name'] for s in startup_list[:4]])
            except Exception:
                startup_str = "unknown"

            # Health score from main window monitor if available
            health = "N/A"
            try:
                win = self.window()
                if hasattr(win, '_monitor') and win._monitor.latest:
                    health = str(win._monitor.latest.health_score)
            except Exception:
                pass

            context = (
                f"=== LIVE SYSTEM SNAPSHOT FOR AI ===\n"
                f"User: {os.environ.get('USERNAME', 'User')} | Health: {health}/100\n"
                f"CPU: {cpu}% ({cpu_cores} Cores) | Temp: {temp_str}\n"
                f"RAM: {vm.percent}% used ({vm.used//1e6:.0f}/{vm.total//1e6:.0f} MB)\n"
                f"DISK: {disk_str}\n"
                f"NETWORK: {net_str}\n"
                f"STARTUP: {startup_str}\n"
                f"TOP PROCESSES: {top_by_ram}\n"
                f"\n=== CRITICAL INSTRUCTIONS ===\n"
                f"1. YOU HAVE ACCESS TO THIS DATA. NEVER say 'I need to access logs' or 'Check manually'.\n"
                f"2. Reference the apps listed in TOP PROCESSES or NETWORK Hogs by name.\n"
                f"3. If the user asks about network, mention {net_hogs_str or 'low usage'} specifically.\n"
                f"4. Suggest [BUTTON: Label | Action] for every fix. Action list: cleanup, browser, startup, boost_network.\n"
            )
            return context
        except Exception as e:
            return f"SYSTEM: Could not gather full metrics ({e}). Provide best-effort analysis."

    def _local_action_reply(self, text: str) -> str:
        """Return a friendly spoken+displayed reply for locally handled commands."""
        name = self._cmd_handler.user_name if self._cmd_handler else "there"
        t = text.lower()
        if any(k in t for k in ["clean", "cleanup", "optimize"]):
            return f"Sure {name}! Let me clean your system right now. Check the Cleanup tab for live logs."
        if any(k in t for k in ["browser"]):
            return f"Sure {name}! Opening browser cleanup now. This will clear cache safely."
        if any(k in t for k in ["status", "health", "how is my"]):
            return f"Checking your system status, {name}. I'll report back shortly."
        if any(k in t for k in ["help", "commands"]):
            return (f"Here's what I can do, {name}: say 'clean my system', "
                    "'browser cleanup', 'check status', 'performance tips', or ask me anything!")
        return f"Sure {name}, let me take care of that for you!"

    def _on_error(self, error: str):
        self._is_processing = False
        self._worker_thread = None
        self._worker = None
        if self._current_bubble:
            self._current_bubble.set_text(f"⚠️ Error: {error}")
        self._thinking.stop()
        self._thinking_lbl.hide()
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)

    def _add_bubble(self, text: str, role: str) -> ChatBubble:
        bubble = ChatBubble(text, role)
        # Inject callback so buttons work without fragile parent() chain
        bubble.set_action_callback(self._handle_action_btn)
        align = Qt.AlignmentFlag.AlignRight if role == "user" else Qt.AlignmentFlag.AlignLeft
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble, 0, align)
        self._scroll_to_bottom()
        return bubble

    def _add_system_message(self, text: str):
        lbl = QLabel(f"ℹ️ {text}")
        lbl.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI'; padding: 4px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, lbl)

    def _handle_action_btn(self, cmd: str):
        """Run an app command from a chat bubble button - always on main thread."""
        if not self._cmd_handler:
            return
        c = cmd.lower().strip()
        cmd_map = {
            "cleanup":     "clean my system",
            "full clean":  "clean my system",
            "browser":     "browser cleanup",
            "optimize":    "clean my system",
            "dashboard":   "open dashboard",
            "performance": "performance tips",
            "status":      "check system status",
            "startup":     "startup apps",
            "minimize":    "minimize",
            "boost_network": "boost my internet",
        }
        real_cmd = cmd_map.get(c, c)

        if real_cmd == "boost my internet":
            self._add_system_message("🚀 Running network optimization (DNS Flush & Winsock Reset)...")
            from monitoring.system_monitor import boost_internet
            from ui.pages.performance_page import _FetchWorker
            def _do_boost():
                success, log = boost_internet()
                return log
            worker = _FetchWorker(_do_boost)
            worker.result_ready.connect(lambda log: self._add_bubble(f"✅ **Internet Boost Complete**\n\n{log}", "assistant"))
            worker.start()
            return

        self._add_system_message(f"🚀 Executing: {real_cmd.capitalize()}...")
        # QTimer.singleShot(0) ensures this runs on main thread even if called from a signal
        QTimer.singleShot(0, lambda rc=real_cmd: self._cmd_handler.handle(rc))

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _clear_chat(self):
        self._chat_history.clear()
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _save_message(self, role: str, content: str):
        try:
            from config.settings import get_db, get_setting
            provider = get_setting("ai_provider", "none")
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO ai_chat_history (timestamp, role, content, provider) VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), role, content, provider),
                )
                conn.commit()
        except Exception:
            pass

    def _load_history(self):
        """Load last 20 messages from DB on startup."""
        try:
            from config.settings import get_db
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT role, content FROM ai_chat_history ORDER BY id DESC LIMIT 20"
                ).fetchall()
                rows.reverse()
                for row in rows:
                    self._add_bubble(row["content"], row["role"])
        except Exception:
            pass
