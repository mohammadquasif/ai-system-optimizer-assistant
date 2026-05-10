"""
AI System Optimizer Assistant - Global Settings & Configuration
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from cryptography.fernet import Fernet

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
APP_NAME = "AI System Optimizer Assistant"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Quasif"

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = CONFIG_DIR / "app_data.db"
KEY_FILE = CONFIG_DIR / ".secret.key"

# Ensure directories exist
for d in [CONFIG_DIR, LOGS_DIR, ASSETS_DIR, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
def setup_logging():
    log_file = LOGS_DIR / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(APP_NAME)

logger = setup_logging()

# ─────────────────────────────────────────────
# ENCRYPTION
# ─────────────────────────────────────────────
def get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key

def encrypt_value(value: str) -> str:
    f = Fernet(get_or_create_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(token: str) -> str:
    try:
        f = Fernet(get_or_create_key())
        return f.decrypt(token.encode()).decode()
    except Exception:
        return ""

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cleanup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                items_cleaned TEXT,
                space_freed_mb REAL,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                provider TEXT
            );
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                schedule TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_run TEXT
            );
        """)
        # Default settings
        defaults = {
            "ai_provider": "none",
            "ollama_model": "qwen2.5:1.5b",
            "ollama_url": "http://localhost:11434",
            "voice_enabled": "true",
            "voice_name": "default",
            "startup_with_windows": "false",
            "minimize_to_tray": "true",
            "auto_cleanup_enabled": "false",
            "theme": "dark",
            "user_name": "Quasif",
            "first_run": "true",
            "openai_key_enc": "",
            "anthropic_key_enc": "",
            "cleanup_temp": "true",
            "cleanup_browser_cache": "true",
            "cleanup_recycle": "false",
            "cleanup_thumbnails": "true",
            "cleanup_logs": "true",
            "cleanup_history": "false",
            "cleanup_cookies": "false",
            "cleanup_sessions": "false",
            "scheduled_cleanup_interval": "daily",
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        conn.commit()

def get_setting(key: str, default: str = "") -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()

# ─────────────────────────────────────────────
# THEME COLORS (Cyberpunk / Glassmorphism)
# ─────────────────────────────────────────────
THEME = {
    "bg_primary":       "#0A0E1A",
    "bg_secondary":     "#0D1221",
    "bg_card":          "#111827",
    "bg_sidebar":       "#080C18",
    "accent_cyan":      "#00D4FF",
    "accent_purple":    "#7C3AED",
    "accent_green":     "#00FF88",
    "accent_orange":    "#FF6B00",
    "accent_red":       "#FF2D55",
    "text_primary":     "#E8F4FD",
    "text_secondary":   "#8BA3C7",
    "text_muted":       "#4A6080",
    "border":           "#1E2D45",
    "border_glow":      "#00D4FF40",
    "gradient_start":   "#00D4FF",
    "gradient_end":     "#7C3AED",
    "neon_glow":        "0 0 20px #00D4FF60",
    "card_bg":          "rgba(17, 24, 39, 0.8)",
}

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0A0E1A;
    color: #E8F4FD;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}
QScrollBar:vertical {
    background: #0D1221;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #00D4FF60;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #0D1221;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #00D4FF60;
    border-radius: 3px;
}
QToolTip {
    background-color: #111827;
    color: #E8F4FD;
    border: 1px solid #00D4FF40;
    border-radius: 6px;
    padding: 4px 8px;
}
"""

# Initialize on import
init_db()
