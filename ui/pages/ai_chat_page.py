"""
AI Chat Page - Streaming chat UI with Ollama/OpenAI/Anthropic
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QScrollArea, QFrame, QPushButton, QComboBox,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon

from ui.widgets import GlassCard, NeonButton, AIThinkingWidget, StatusBadge
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

    def __init__(self, message: str, history: list, context: str = ""):
        super().__init__()
        self.message = message
        self.history = history
        self.context = context

    @pyqtSlot()
    def run(self):
        try:
            service = AIService.get_instance()
            full = service.chat(
                self.message,
                history=self.history,
                stream_cb=lambda tok: self.token_received.emit(tok),
                context=self.context,
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        if role == "user":
            bg = "#1E2D45"
            color = "#E8F4FD"
            align = Qt.AlignmentFlag.AlignRight
            border_color = "#00D4FF40"
        else:
            bg = "#111827"
            color = "#E8F4FD"
            align = Qt.AlignmentFlag.AlignLeft
            border_color = "#7C3AED40"

        role_lbl = QLabel("You" if role == "user" else "🤖 AI Assistant")
        role_lbl.setStyleSheet(
            f"color: {'#00D4FF' if role == 'user' else '#7C3AED'}; "
            "font-size: 10px; font-weight: 600; font-family: 'Segoe UI';"
        )
        role_lbl.setAlignment(align)

        self._text_lbl = QLabel(text)
        self._text_lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-family: 'Segoe UI'; "
            "line-height: 1.5;"
        )
        self._text_lbl.setWordWrap(True)
        self._text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(role_lbl)
        layout.addWidget(self._text_lbl)

        self.setStyleSheet(
            f"background: {bg}; border: 1px solid {border_color}; "
            "border-radius: 12px;"
        )
        self.setMaximumWidth(680)

        # Buttons layout
        self._btn_container = QWidget()
        self._btn_layout = QHBoxLayout(self._btn_container)
        self._btn_layout.setContentsMargins(0, 4, 0, 4)
        self._btn_layout.setSpacing(8)
        self._btn_layout.addStretch()
        layout.addWidget(self._btn_container)
        self._btn_container.hide()

    def append_text(self, token: str):
        self._text_lbl.setText(self._text_lbl.text() + token)
        self._parse_buttons()

    def set_text(self, text: str):
        self._text_lbl.setText(text)
        self._parse_buttons()

    def _parse_buttons(self):
        """Look for [BUTTON: Label | Command] in text and create real buttons."""
        import re
        text = self._text_lbl.text()
        matches = re.findall(r"\[BUTTON:\s*(.*?)\s*\|\s*(.*?)\s*\]", text)
        if not matches:
            return

        # Clean text from tags
        clean_text = re.sub(r"\[BUTTON:.*?\]", "", text).strip()
        self._text_lbl.setText(clean_text)

        # Clear existing buttons
        while self._btn_layout.count() > 1:
            item = self._btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for label, cmd in matches:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #7C3AED20; color: #7C3AED;
                    border: 1px solid #7C3AED60; border-radius: 6px;
                    padding: 6px 12px; font-size: 11px; font-weight: 600;
                    font-family: 'Segoe UI';
                }
                QPushButton:hover { background: #7C3AED40; border-color: #7C3AED; }
            """)
            btn.clicked.connect(lambda _, c=cmd: self.parent().parent().parent().parent()._handle_action_btn(c))
            self._btn_layout.insertWidget(self._btn_layout.count()-1, btn)
            self._btn_container.show()


# ────────────────────────────────────────────────────────────────
# AI CHAT PAGE
# ────────────────────────────────────────────────────────────────

class AIChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chat_history: list = []
        self._current_bubble: ChatBubble = None
        self._worker_thread: QThread = None
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
            ("🔍 System Status",    "Analyze my system health and top processes"),
            ("🧹 Clean System",     "Perform a full system cleanup"),
            ("🌐 Browser Cleanup",  "Optimize my browser and clear cache"),
            ("⚡ Performance Tips", "Pro tips to speed up my PC"),
            ("🚀 Startup Apps",     "Identify heavy apps in my startup"),
            ("💾 RAM Usage",        "Which processes are using the most RAM?"),
        ]
        for label, prompt in chip_defs:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #111827; color: #00D4FF;
                    border: 1px solid #00D4FF40; border-radius: 15px;
                    padding: 0 14px; font-size: 11px; font-family: 'Segoe UI';
                }
                QPushButton:hover { background: #1E2D45; border-color: #00D4FF; }
                QPushButton:pressed { background: #00D4FF20; }
            """)
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
        self._input.setStyleSheet("""
            QLineEdit {
                background: #0D1221;
                color: #E8F4FD;
                border: 1px solid #1E2D45;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1px solid #00D4FF60;
            }
        """)
        self._input.returnPressed.connect(self._send_message)

        self._send_btn = NeonButton("Send ➤", "#00D4FF")
        self._send_btn.setFixedWidth(100)
        self._send_btn.clicked.connect(self._send_message)

        self._clear_btn = NeonButton("Clear", "#FF2D55")
        self._clear_btn.setFixedWidth(80)
        self._clear_btn.clicked.connect(self._clear_chat)

        input_layout.addWidget(self._input, 1)
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

    def _chip_clicked(self, prompt: str):
        self._input.setText(prompt)
        self._send_message()

    def _send_message(self):
        text = self._input.text().strip()
        if not text:
            return

        # ── LOCAL COMMAND INTERCEPTION ────────────────────────────
        # Check if message maps to a direct app action before going to AI
        if self._cmd_handler:
            handled = self._cmd_handler.handle_chat(text, speak_response=False)
            if handled:
                # Show user message in chat
                self._input.clear()
                self._add_bubble(text, "user")
                return

        service = AIService.get_instance()
        if not service.is_configured:
            self._add_system_message(
                "AI is not configured. Please go to Settings → AI Configuration."
            )
            return

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

        # Background thread
        self._worker_thread = QThread()
        import psutil
        m = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage('C:\\')
        
        # Get top 5 memory processes
        procs = []
        try:
            for p in psutil.process_iter(['name', 'memory_percent']):
                procs.append(p.info)
            procs = sorted(procs, key=lambda x: x['memory_percent'], reverse=True)[:5]
        except Exception:
            pass
        
        proc_list = ", ".join([f"{p['name']} ({p['memory_percent']:.1f}%)" for p in procs])

        context = (
            f"SYSTEM STATE: CPU={cpu}%, RAM={m.percent}% ({m.available//1024//1024}MB free), "
            f"DISK={disk.percent}% ({disk.free//1024//1024//1024}GB free). "
            f"TOP PROCESSES: {proc_list}. "
            "INSTRUCTIONS: Be productive. If system health is low, recommend specific actions. "
            "Use the format [BUTTON: Label | Action] to suggest tools. "
            "Actions: cleanup, browser, dashboard, performance, status, minimize."
        )
        self._worker = AIWorker(text, self._chat_history[:-1], context=context)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker_thread.start()

    def _on_token(self, token: str):
        if self._current_bubble:
            self._current_bubble.append_text(token)
        self._scroll_to_bottom()

    def _on_finished(self, full_text: str):
        self._chat_history.append({"role": "assistant", "content": full_text})
        self._save_message("assistant", full_text)
        self._thinking.stop()
        self._thinking_lbl.hide()
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._input.setFocus()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
        # Speak the AI response via TTS if handler available
        if self._cmd_handler and full_text:
            snippet = full_text[:200].replace("\n", " ")
            self._cmd_handler.voice.speak(snippet)

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
        if self._current_bubble:
            self._current_bubble.set_text(f"⚠️ Error: {error}")
        self._thinking.stop()
        self._thinking_lbl.hide()
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)

    def _add_bubble(self, text: str, role: str) -> ChatBubble:
        bubble = ChatBubble(text, role)
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
        """Run an app command from a chat button."""
        if not self._cmd_handler:
            return
        
        c = cmd.lower().strip()
        
        # Mapping chat commands to actual handler commands
        cmd_map = {
            "cleanup":     "clean my system",
            "full clean":  "clean my system",
            "browser":     "browser cleanup",
            "optimize":    "clean my system",
            "dashboard":   "open dashboard",
            "performance": "performance tips",
            "status":      "check system status",
            "startup":     "startup apps",
            "minimize":    "minimize"
        }
        
        real_cmd = cmd_map.get(c, c)
        
        # Visual feedback in chat
        self._add_system_message(f"🚀 Executing action: {real_cmd.capitalize()}...")
        
        # Execute via handler
        self._cmd_handler.handle(real_cmd)

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
