"""
AI System Optimizer - Setup Helper Script
Run by INSTALL.bat to handle Python-level tasks safely
"""
import sys, os, sqlite3

def check_and_fix_db(db_path):
    if not os.path.exists(db_path):
        print("  [INFO] DB not found - will be created on first run.")
        return
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT value FROM settings WHERE key='ollama_model'").fetchone()
        model = row[0] if row else ""
        if model and "qwen2.5:0.5" not in model:
            conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('ai_provider','ollama')")
            conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('ollama_model','qwen2.5:0.5b')")
            conn.commit()
            print(f"  [FIX] Stale model corrected: was [{model}] -> qwen2.5:0.5b")
        elif not model:
            print("  [INFO] No model saved yet - will be set on first launch.")
        else:
            print(f"  [OK]  Model already correct: {model}")
        conn.close()
    except Exception as e:
        print(f"  [WARN] DB check failed: {e}")

def configure_db(db_path):
    """Called at end of install to ensure correct settings"""
    try:
        # Init DB via app settings module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.settings import init_db, set_setting
        init_db()
        set_setting("ai_provider", "ollama")
        set_setting("ollama_model", "qwen2.5:0.5b")
        set_setting("first_run", "false")
        print("  [OK]  AI settings locked to qwen2.5:0.5b")
    except Exception as e:
        print(f"  [WARN] Could not update DB via module: {e}")
        # Fallback: direct sqlite
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('ai_provider','ollama')")
            conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('ollama_model','qwen2.5:0.5b')")
            conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('first_run','false')")
            conn.commit()
            conn.close()
            print("  [OK]  AI settings locked to qwen2.5:0.5b (direct DB)")
        except Exception as e2:
            print(f"  [WARN] Direct DB also failed: {e2}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "config", "app_data.db")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        check_and_fix_db(db_path)
    elif cmd == "configure":
        configure_db(db_path)
    else:
        print(f"  [WARN] Unknown command: {cmd}")
