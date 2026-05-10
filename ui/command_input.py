"""
Command Input Widget — Chips + Text + Voice unified interface
Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
License: Personal Use Only (Non-Commercial)

Replaces raw buttons with a chat-style command area.
User can: click chips | type commands | speak voice commands.
All inputs route through the same command dispatcher.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.widgets import NeonButton


# ─────────────────────────────────────────────────────────────────
# CHIP BUTTON
# ─────────────────────────────────────────────────────────────────

class ChipButton(QPushButton):
    """A pill-shaped chip button for quick command access."""

    def __init__(self, label: str, icon: str = "", color: str = "#00D4FF", parent=None):
        text = f"{icon}  {label}" if icon else label
        super().__init__(text, parent)
        self.command = label
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color}18;
                color: {color};
                border: 1px solid {color}60;
                border-radius: 16px;
                padding: 0 14px;
                font-size: 12px;
                font-family: 'Segoe UI';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color}35;
                border: 1px solid {color}CC;
            }}
            QPushButton:pressed {{
                background: {color}55;
            }}
        """)


# ─────────────────────────────────────────────────────────────────
# COMMAND CHIP DEFINITIONS
# ─────────────────────────────────────────────────────────────────

COMMAND_CHIPS = [
    {"label": "Optimize",      "icon": "⚡", "color": "#00D4FF", "cmd": "optimize"},
    {"label": "Clean",         "icon": "🧹", "color": "#00FF88", "cmd": "clean"},
    {"label": "Status",        "icon": "📊", "color": "#7C3AED", "cmd": "status"},
    {"label": "RAM Free",      "icon": "🧠", "color": "#FFB800", "cmd": "ram"},
    {"label": "DNS Flush",     "icon": "🔗", "color": "#00D4FF", "cmd": "dns"},
    {"label": "Health",        "icon": "❤️", "color": "#FF2D55", "cmd": "health"},
    {"label": "Startup Apps",  "icon": "🚀", "color": "#8B5CF6", "cmd": "startup"},
    {"label": "Voice On",      "icon": "🎙️", "color": "#00FF88", "cmd": "voice"},
    {"label": "Help",          "icon": "💡", "color": "#4A6080", "cmd": "help"},
]


# ─────────────────────────────────────────────────────────────────
# COMMAND INPUT WIDGET
# ─────────────────────────────────────────────────────────────────

class CommandInputWidget(QWidget):
    """
    Unified command input widget.
    Chips row + text input field + send button.
    Emits command_issued(str) for any input method.
    """

    command_issued = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── Chips row ─────────────────────────────────────────────
        chips_label = QLabel("Quick Commands:")
        chips_label.setStyleSheet(
            "color: #4A6080; font-size: 10px; font-family: 'Segoe UI'; "
            "font-weight: 600; letter-spacing: 1px;"
        )
        root.addWidget(chips_label)

        chips_scroll = QScrollArea()
        chips_scroll.setFixedHeight(46)
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        chips_widget = QWidget()
        chips_widget.setStyleSheet("background: transparent;")
        chips_layout = QHBoxLayout(chips_widget)
        chips_layout.setContentsMargins(0, 4, 0, 4)
        chips_layout.setSpacing(8)

        for chip_def in COMMAND_CHIPS:
            chip = ChipButton(chip_def["label"], chip_def["icon"], chip_def["color"])
            chip.clicked.connect(lambda _, c=chip_def["cmd"]: self._emit(c))
            chips_layout.addWidget(chip)
        chips_layout.addStretch()

        chips_scroll.setWidget(chips_widget)
        root.addWidget(chips_scroll)

        # ── Text input row ─────────────────────────────────────────
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question... (e.g. 'clean my PC')")
        self._input.setStyleSheet("""
            QLineEdit {
                background: #0D1221;
                color: #E8F4FD;
                border: 1px solid #1E2D45;
                border-radius: 20px;
                padding: 8px 18px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1px solid #00D4FF80;
            }
        """)
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("➤")
        send_btn.setFixedSize(40, 40)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #00D4FF;
                color: #0A0E1A;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: #00B8E0; }
            QPushButton:pressed { background: #0090B0; }
        """)
        send_btn.clicked.connect(self._on_send)

        voice_btn = QPushButton("🎙️")
        voice_btn.setFixedSize(40, 40)
        voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        voice_btn.setStyleSheet("""
            QPushButton {
                background: #7C3AED20;
                color: #7C3AED;
                border: 1px solid #7C3AED60;
                border-radius: 20px;
                font-size: 16px;
            }
            QPushButton:hover { background: #7C3AED40; }
        """)
        voice_btn.clicked.connect(lambda: self._emit("voice"))
        voice_btn.setToolTip("Click to speak a command")

        input_row.addWidget(self._input, 1)
        input_row.addWidget(voice_btn)
        input_row.addWidget(send_btn)
        root.addLayout(input_row)

    def _on_send(self):
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self._emit(text)

    def _emit(self, command: str):
        self.command_issued.emit(command)

    def set_placeholder(self, text: str):
        self._input.setPlaceholderText(text)
