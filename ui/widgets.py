"""
Custom PyQt6 Widgets - Reusable glassmorphism / cyberpunk UI components
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty,
    QSequentialAnimationGroup, QRect, QRectF, QPointF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QBrush,
    QFont, QPainterPath, QRadialGradient, QConicalGradient,
)
import math


# ──────────────────────────────────────────────────────────────────
# GLASS CARD
# ──────────────────────────────────────────────────────────────────

class GlassCard(QFrame):
    """A glassmorphism-styled card widget with optional neon border."""

    def __init__(
        self,
        parent=None,
        accent_color: str = "#00D4FF",
        glow: bool = True,
        radius: int = 16,
    ):
        super().__init__(parent)
        self._accent = QColor(accent_color)
        self._glow = glow
        self._radius = radius
        self.setObjectName("GlassCard")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        if glow:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(25)
            shadow.setColor(QColor(accent_color).lighter(120))
            shadow.setOffset(0, 0)
            self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        # Glass fill
        bg = QColor(17, 24, 39, 200)
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # Neon border
        pen = QPen(self._accent)
        pen.setWidth(1)
        self._accent.setAlpha(80)
        pen.setColor(self._accent)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)
        painter.end()


# ──────────────────────────────────────────────────────────────────
# ANIMATED CIRCULAR GAUGE
# ──────────────────────────────────────────────────────────────────

class CircularGauge(QWidget):
    """Animated circular gauge for CPU/RAM/Disk display."""

    def __init__(
        self,
        label: str = "",
        color: str = "#00D4FF",
        parent=None,
        size: int = 120,
    ):
        super().__init__(parent)
        self._value = 0
        self._animated_value = 0
        self._label = label
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size, size)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.setInterval(16)

    def set_value(self, value: float):
        """Set gauge value (0-100) with animation."""
        self._value = max(0, min(100, value))
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _animate_step(self):
        diff = self._value - self._animated_value
        if abs(diff) < 0.5:
            self._animated_value = self._value
            self._anim_timer.stop()
        else:
            self._animated_value += diff * 0.1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._size
        margin = 12
        rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)

        # Background arc
        pen = QPen(QColor(30, 45, 69))
        pen.setWidth(10)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, -225 * 16, -270 * 16)

        # Value arc
        span = int(-270 * 16 * self._animated_value / 100)
        if span != 0:
            c = self._get_value_color()
            gradient = QConicalGradient(rect.center(), 135)
            gradient.setColorAt(0, c)
            gradient.setColorAt(1, c.lighter(150))
            pen2 = QPen(QBrush(gradient), 10)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen2)
            painter.drawArc(rect, -225 * 16, span)

        # Center text: value
        painter.setPen(QColor(232, 244, 253))
        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._animated_value)}%")

        # Label below center
        painter.setPen(QColor(139, 163, 199))
        font2 = QFont("Segoe UI", 7)
        painter.setFont(font2)
        label_rect = QRectF(0, s * 0.65, s, 20)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._label)

        painter.end()

    def _get_value_color(self) -> QColor:
        v = self._animated_value
        if v < 50:
            return QColor("#00FF88")
        elif v < 75:
            return QColor("#FFB800")
        else:
            return QColor("#FF2D55")


# ──────────────────────────────────────────────────────────────────
# NEON BUTTON
# ──────────────────────────────────────────────────────────────────

class NeonButton(QPushButton):
    """Premium neon-glow push button."""

    def __init__(self, text: str, color: str = "#00D4FF", parent=None):
        super().__init__(text, parent)
        self._color = color
        self._base_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}20, stop:1 {color}10);
                color: {color};
                border: 1px solid {color}60;
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI';
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}40, stop:1 {color}20);
                border: 1px solid {color}AA;
                color: white;
            }}
            QPushButton:pressed {{
                background: {color}30;
                border: 1px solid {color};
            }}
            QPushButton:disabled {{
                background: #1E2D4520;
                color: #4A6080;
                border: 1px solid #1E2D45;
            }}
        """
        self.setStyleSheet(self._base_style)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(color))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


# ──────────────────────────────────────────────────────────────────
# METRIC LABEL (small stat display)
# ──────────────────────────────────────────────────────────────────

class MetricLabel(QWidget):
    """Compact metric display: icon + value + label."""

    def __init__(self, icon: str, label: str, color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self._value_lbl = QLabel("--")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: 700; font-family: 'Segoe UI';"
        )

        lbl = QLabel(f"{icon}  {label}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #8BA3C7; font-size: 11px; font-family: 'Segoe UI';")

        layout.addWidget(self._value_lbl)
        layout.addWidget(lbl)

    def set_value(self, text: str):
        self._value_lbl.setText(text)


# ──────────────────────────────────────────────────────────────────
# AI THINKING ANIMATION WIDGET
# ──────────────────────────────────────────────────────────────────

class AIThinkingWidget(QWidget):
    """Animated dots indicator for AI processing state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(12)
        self.setMinimumWidth(200)
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._visible = False

    def start(self):
        self._visible = True
        self._offset = 0
        self._timer.start(30)
        self.show()

    def stop(self):
        self._visible = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._offset = (self._offset + 5) % (self.width() + 100)
        self.update()

    def paintEvent(self, event):
        if not self._visible:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background track
        bg_rect = QRectF(0, 0, self.width(), self.height())
        painter.setBrush(QBrush(QColor("#1E2D45")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg_rect, 6, 6)
        
        # Moving neon chunk
        chunk_width = 80
        x = self._offset - chunk_width
        chunk_rect = QRectF(x, 0, chunk_width, self.height())
        
        # Clip to widget bounds
        painter.setClipRect(self.rect())
        
        grad = QLinearGradient(x, 0, x + chunk_width, 0)
        grad.setColorAt(0, QColor("#7C3AED00"))
        grad.setColorAt(0.5, QColor("#7C3AED"))
        grad.setColorAt(1, QColor("#7C3AED00"))
        
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(chunk_rect, 6, 6)
        painter.end()


# ──────────────────────────────────────────────────────────────────
# MINI SPARKLINE CHART
# ──────────────────────────────────────────────────────────────────

class SparklineChart(QWidget):
    """Simple real-time sparkline chart for metrics history."""

    def __init__(self, color: str = "#00D4FF", max_points: int = 60, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._points: list = []
        self._max = max_points
        self.setMinimumHeight(60)

    def add_point(self, value: float):
        self._points.append(max(0, min(100, value)))
        if len(self._points) > self._max:
            self._points.pop(0)
        self.update()

    def paintEvent(self, event):
        if len(self._points) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 4

        # Background
        painter.fillRect(self.rect(), QColor(13, 18, 33))

        n = len(self._points)
        step = (w - 2 * pad) / max(n - 1, 1)

        def px(i): return pad + i * step
        def py(v): return h - pad - (v / 100) * (h - 2 * pad)

        # Fill path
        path = QPainterPath()
        path.moveTo(px(0), h - pad)
        for i, v in enumerate(self._points):
            path.lineTo(px(i), py(v))
        path.lineTo(px(n - 1), h - pad)
        path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        c = QColor(self._color)
        c.setAlpha(80)
        grad.setColorAt(0, c)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Line
        line_path = QPainterPath()
        line_path.moveTo(px(0), py(self._points[0]))
        for i, v in enumerate(self._points[1:], 1):
            line_path.lineTo(px(i), py(v))
        pen = QPen(self._color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

        painter.end()


# ──────────────────────────────────────────────────────────────────
# STATUS BADGE
# ──────────────────────────────────────────────────────────────────

class StatusBadge(QLabel):
    """Small colored status badge with pulse animation."""

    STATUS_COLORS = {
        "online":   "#00FF88",
        "offline":  "#FF2D55",
        "warning":  "#FFB800",
        "idle":     "#00D4FF",
        "thinking": "#7C3AED",
    }

    def __init__(self, status: str = "offline", parent=None):
        super().__init__(parent)
        self._status = status
        self._pulse = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse_tick)
        self._timer.start(50)
        self.setFixedSize(10, 10)

    def set_status(self, status: str):
        self._status = status
        self.update()

    def _pulse_tick(self):
        self._pulse = (self._pulse + 3) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.STATUS_COLORS.get(self._status, "#4A6080"))

        # Pulse ring
        alpha = int((math.sin(math.radians(self._pulse)) + 1) * 60)
        ring = QColor(color)
        ring.setAlpha(alpha)
        painter.setBrush(QBrush(ring))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 10, 10)

        # Core dot
        painter.setBrush(QBrush(color))
        painter.drawEllipse(2, 2, 6, 6)
        painter.end()


# ──────────────────────────────────────────────────────────────────
# PROGRESS BAR (custom styled)
# ──────────────────────────────────────────────────────────────────

class NeonProgressBar(QProgressBar):
    def __init__(self, color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self.setStyleSheet(f"""
            QProgressBar {{
                background: #1E2D45;
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {color}80);
                border-radius: 3px;
            }}
        """)
