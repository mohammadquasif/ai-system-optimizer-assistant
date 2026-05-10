"""
AI Chat Page - Streaming chat UI with Ollama/OpenAI/Anthropic
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QScrollArea, QFrame, QPushButton, QComboBox,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCursor

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

    def append_text(self, token: str):
        self._text_lbl.setText(self._text_lbl.text() + token)

    def set_text(self, text: str):
        self._text_lbl.setText(text)


# ────────────────────────────────────────────────────────────────
# AI CHAT PAGE
# ────────────────────────────────────────────────────────────────

class AIChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chat_history: list = []  # [{role, content}]
        self._current_bubble: ChatBubble = None
        self._worker_thread: QThread = None
        self._setup_ui()
        self._load_history()

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
        service = AIService.get_instance()
        if service.is_configured:
            available = service.is_available
            if available:
                self._ai_status_dot.set_status("online")
                self._ai_status_lbl.setText("AI Online")
                self._ai_status_lbl.setStyleSheet("color: #00FF88; font-size: 12px; font-family: 'Segoe UI';")
                self._model_lbl.setText(f"Model: {get_setting('ollama_model', '')}")
                self._no_ai_card.hide()
            else:
                self._ai_status_dot.set_status("warning")
                self._ai_status_lbl.setText("AI Offline")
                self._ai_status_lbl.setStyleSheet("color: #FFB800; font-size: 12px; font-family: 'Segoe UI';")
        else:
            self._ai_status_dot.set_status("offline")
            self._no_ai_card.show()

    # ─────────────────────────────────────────────────────────────
    # CHAT OPERATIONS
    # ─────────────────────────────────────────────────────────────

    def send_message_external(self, text: str):
        """Allow other pages/voice to inject a message."""
        self._input.setText(text)
        self._send_message()

    def _send_message(self):
        text = self._input.text().strip()
        if not text:
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

        # Show thinking
        self._thinking.start()
        self._thinking_lbl.show()

        # Start AI response bubble (empty, will stream into it)
        self._current_bubble = self._add_bubble("", "assistant")

        # Background thread
        self._worker_thread = QThread()
        import psutil
        context = (
            f"CPU: {psutil.cpu_percent()}% | "
            f"RAM: {psutil.virtual_memory().percent}% | "
            f"Disk: {psutil.disk_usage('C:\\').percent}%"
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
        self._worker_thread.quit()
        self._worker_thread.wait()

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
