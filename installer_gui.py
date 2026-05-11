# -*- coding: utf-8 -*-
"""
AI System Optimizer Assistant — Enterprise Installer v4.0
Modes: Install · Modify · Repair · Uninstall
Silent: installer_gui.py --silent [--repair | --uninstall]
"""
import sys, os, subprocess, threading, queue, time, ctypes, shutil
import importlib.util, urllib.request, winreg, json, logging, tempfile
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
ROOT          = Path(__file__).parent.resolve()
APPNAME       = "AI System Optimizer Assistant"
APPNAME_SHORT = "AI System Optimizer"
VERSION       = "1.0.0"
BUILD         = "2025.1"
AUTHOR        = "Mohammad Quasif"
AUTHOR_CRED   = "DBA AI  ·  B.Tech CS"
MODEL         = "qwen2.5:0.5b"
MODEL_SIZE    = "~400 MB"
OLLAMA_DL     = "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
REG_KEY       = r"Software\AISystemOptimizer"
REG_RUN       = r"Software\Microsoft\Windows\CurrentVersion\Run"
LOG_FILE      = ROOT / "installer.log"
DISK_REQ_MB   = 1200
COPYRIGHT     = f"© 2025 {AUTHOR}  ·  MIT License"
SUPPORT_URL   = "github.com/mohammadquasif/ai-system-optimizer-assistant"

CORE_PKGS = [
    ("PyQt6",             "PyQt6"),
    ("pyqtgraph",         "pyqtgraph"),
    ("psutil",            "psutil"),
    ("pyttsx3",           "pyttsx3"),
    ("requests",          "requests"),
    ("httpx",             "httpx"),
    ("openai",            "openai"),
    ("anthropic",         "anthropic"),
    ("pywin32",           "win32api"),
    ("winshell",          "winshell"),
    ("cryptography",      "cryptography"),
    ("schedule",          "schedule"),
    ("APScheduler",       "apscheduler"),
    ("plyer",             "plyer"),
    ("matplotlib",        "matplotlib"),
    ("Pillow",            "PIL"),
    ("colorlog",          "colorlog"),
    ("SpeechRecognition", "speech_recognition"),
]

CRITICAL_FILES = [
    "app.py", "requirements.txt",
    "ai/ai_service.py", "ai/ollama_manager.py",
    "config/settings.py", "monitoring/system_monitor.py",
    "ui/main_window.py",
]

LICENSE_TEXT = """\
MIT License

Copyright (c) 2025 Mohammad Quasif

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

───────────────────────────────────────────────────────────────────────────────

THIRD-PARTY NOTICES

This software incorporates the following third-party components:

  • Ollama  — MIT License  — https://ollama.com
  • PyQt6   — GPL v3 / Commercial  — https://www.riverbankcomputing.com
  • qwen2.5 — Apache 2.0  — https://huggingface.co/Qwen

Full third-party license texts are included with each respective component.
By proceeding, you acknowledge that you have read and agree to this license.
"""

STEP_LABELS = {
    "welcome":        "Welcome",
    "license":        "License",
    "directory":      "Install Location",
    "components":     "Components",
    "dep_check":      "Ready to Install",
    "maintenance":    "Maintenance",
    "repair_scan":    "Repair Analysis",
    "uninstall_opts": "Uninstall Options",
    "progress":       "Installing",
    "done":           "Complete",
}

# ══════════════════════════════════════════════════════════════════════════════
# PALETTE
# ══════════════════════════════════════════════════════════════════════════════
BG    = "#0b1120"
SURF  = "#111827"
SURF2 = "#1a2336"
SURF3 = "#1f2d44"
DARK  = "#070d18"
BORD  = "#1d2d45"
BORD2 = "#2a3f5f"
GRN   = "#16a34a"
GRNL  = "#22c55e"
GRND  = "#15803d"
TEXT  = "#f0f6fc"
TEXT2 = "#7ea3cc"
MUTED = "#445570"
OK    = "#22c55e"
WARN  = "#f59e0b"
ERR   = "#ef4444"
BLUE  = "#38bdf8"
PURP  = "#a78bfa"
RED   = "#dc2626"
REDB  = "#b91c1c"

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════
try:
    logging.basicConfig(
        filename=str(LOG_FILE), level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S", encoding="utf-8",
    )
except Exception:
    logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("installer")

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
def reg_read(name, default=None):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        v, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return v
    except Exception:
        return default

def reg_write(name, value, vtype=winreg.REG_SZ):
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        winreg.SetValueEx(k, name, 0, vtype, value)
        winreg.CloseKey(k)
    except Exception as e:
        _log.warning(f"reg_write({name}): {e}")

def reg_del_val(key_path, name):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, name)
        winreg.CloseKey(k)
    except Exception:
        pass

def reg_del_key(path):
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except Exception:
        pass

def save_install_record(path, comps):
    reg_write("Version",     VERSION)
    reg_write("InstallPath", str(path))
    reg_write("InstallDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    reg_write("Components",  json.dumps(comps))
    _log.info(f"Record saved v{VERSION} @ {path}")

def load_install_record():
    return {
        "version":      reg_read("Version"),
        "install_path": reg_read("InstallPath"),
        "install_date": reg_read("InstallDate"),
        "components":   json.loads(reg_read("Components", "{}")),
    }

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM CHECKS
# ══════════════════════════════════════════════════════════════════════════════
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def get_disk_free_mb(path):
    try:
        return int(shutil.disk_usage(str(Path(path).anchor)).free / 1024 / 1024)
    except Exception:
        return 99999

def get_python_ver():
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"

# ══════════════════════════════════════════════════════════════════════════════
# DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def importable(name):
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def count_pkgs():
    total = len(CORE_PKGS)
    inst  = sum(1 for _, imp in CORE_PKGS if importable(imp))
    return inst, total

def check_ollama():
    try:
        return subprocess.run(["ollama", "--version"],
                              capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False

def check_model(name):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=8)
        return r.returncode == 0 and name.lower() in r.stdout.lower()
    except Exception:
        return False

def scan_installation(install_path):
    issues = []
    missing = [f for f in CRITICAL_FILES if not (install_path / f).exists()]
    if missing:
        issues.append({"id": "files", "severity": "error",
                       "label": f"Application files ({len(missing)} missing)",
                       "detail": ", ".join(missing[:3]) + ("…" if len(missing) > 3 else ""),
                       "fix": "files"})
    inst, total = count_pkgs()
    if inst < total:
        issues.append({"id": "pkgs", "severity": "warning" if inst > total // 2 else "error",
                       "label": f"Python packages ({inst}/{total} installed)",
                       "detail": f"{total - inst} packages missing",
                       "fix": "pkgs"})
    if not check_ollama():
        issues.append({"id": "ollama", "severity": "error",
                       "label": "Ollama AI engine",
                       "detail": "Not installed or missing from PATH",
                       "fix": "ollama"})
    elif not check_model(MODEL):
        issues.append({"id": "model", "severity": "warning",
                       "label": f"AI model  ({MODEL})",
                       "detail": "Not downloaded",
                       "fix": "model"})
    if not importable("pyaudio"):
        issues.append({"id": "audio", "severity": "info",
                       "label": "PyAudio (voice input)",
                       "detail": "Optional — voice commands disabled",
                       "fix": "audio"})
    lnk = Path(os.path.expanduser("~")) / "Desktop" / f"{APPNAME}.lnk"
    if not lnk.exists():
        issues.append({"id": "shortcut", "severity": "info",
                       "label": "Desktop shortcut",
                       "detail": "Missing from Desktop",
                       "fix": "shortcut"})
    return issues

# ══════════════════════════════════════════════════════════════════════════════
# INSTALL WORKERS
# ══════════════════════════════════════════════════════════════════════════════
def pip_install(pkgs, log_fn):
    cmd = [sys.executable, "-m", "pip", "install"] + pkgs + [
        "--quiet", "--no-warn-script-location"
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            s = line.rstrip()
            if s:
                log_fn(s)
                _log.debug(f"pip: {s}")
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        log_fn(f"pip error: {e}")
        _log.error(f"pip: {e}")
        return False

def pip_uninstall(pkgs, log_fn):
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y"] + pkgs,
            capture_output=True, text=True, timeout=120,
        )
        log_fn(r.stdout.strip() or "Packages removed.")
        return r.returncode == 0
    except Exception as e:
        log_fn(f"pip uninstall: {e}")
        return False

def install_pyaudio(log_fn):
    if pip_install(["PyAudio"], log_fn):
        return True
    log_fn("Wheel failed — trying pipwin…")
    pip_install(["pipwin"], log_fn)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pipwin", "install", "pyaudio"],
            capture_output=True, text=True, timeout=300,
        )
        if r.stdout: log_fn(r.stdout.strip())
        return r.returncode == 0
    except Exception as e:
        log_fn(f"pipwin: {e}")
        return False

def install_ollama(log_fn, prog_fn):
    tmp = tempfile.mktemp(suffix=".exe", prefix="ollama_")
    log_fn("Downloading Ollama runtime (~100 MB)…")
    try:
        def _hook(n, bs, total):
            if total > 0:
                prog_fn(min(95, int(n * bs * 100 / total)))
        urllib.request.urlretrieve(OLLAMA_DL, tmp, _hook)
        log_fn("Running Ollama installer (silent)…")
        r = subprocess.run([tmp, "/S"], timeout=300)
        prog_fn(100)
        return r.returncode == 0
    except Exception as e:
        log_fn(f"Ollama: {e}")
        return False
    finally:
        try: os.unlink(tmp)
        except Exception: pass

def pull_model(name, log_fn, prog_fn):
    log_fn(f"Pulling {name} (~400 MB)…")
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            s = line.rstrip()
            if s:
                log_fn(s)
                if "%" in s:
                    try: prog_fn(min(99, int(s.split("%")[0].split()[-1])))
                    except Exception: pass
        proc.wait()
        prog_fn(100)
        return proc.returncode == 0
    except Exception as e:
        log_fn(f"Model pull: {e}")
        return False

def create_shortcuts(install_path, log_fn):
    app_py  = install_path / "app.py"
    desktop = Path(os.path.expanduser("~")) / "Desktop" / f"{APPNAME}.lnk"
    ico     = install_path / "assets" / "icon.ico"
    pw      = Path(sys.executable).with_name("pythonw.exe")
    if not pw.exists(): pw = Path(sys.executable)
    ico_l = f"$s.IconLocation='{ico}';" if ico.exists() else ""
    ps = (f"$ws=New-Object -ComObject WScript.Shell;$s=$ws.CreateShortcut('{desktop}');"
          f"$s.TargetPath='{pw}';$s.Arguments='\"{app_py}\"';"
          f"$s.WorkingDirectory='{install_path}';$s.Description='{APPNAME}';"
          f"{ico_l}$s.Save()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=15)
    log_fn(f"Desktop shortcut: {'created' if r.returncode == 0 else 'failed'}")
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "AISystemOptimizer", 0, winreg.REG_SZ,
                          f'"{pw}" "{app_py}"')
        winreg.CloseKey(k)
        log_fn("Startup entry: registered")
    except Exception as e:
        log_fn(f"Startup entry: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# UNINSTALL WORKERS
# ══════════════════════════════════════════════════════════════════════════════
def kill_app(log_fn):
    for proc in ("AISystemOptimizer.exe",):
        try: subprocess.run(["taskkill", "/F", "/IM", proc],
                            capture_output=True, timeout=8)
        except Exception: pass
    # Use "AI System Optimizer Assistant*" (not "AI System Optimizer*") so the
    # installer window ("AI System Optimizer — Setup …") is not matched and killed.
    for name in ("python.exe", "pythonw.exe"):
        try: subprocess.run(
                ["taskkill", "/F", "/IM", name, "/FI",
                 "WINDOWTITLE eq AI System Optimizer Assistant*"],
                capture_output=True, timeout=8)
        except Exception: pass
    log_fn("Running processes terminated.")

def remove_shortcuts(log_fn):
    lnk = Path(os.path.expanduser("~")) / "Desktop" / f"{APPNAME}.lnk"
    if lnk.exists():
        try: lnk.unlink(); log_fn("Desktop shortcut: removed")
        except Exception as e: log_fn(f"Shortcut: {e}")
    reg_del_val(REG_RUN, "AISystemOptimizer")
    log_fn("Startup registry entry: removed")

def remove_model(name, log_fn):
    try:
        r = subprocess.run(["ollama", "rm", name],
                           capture_output=True, text=True, timeout=30)
        log_fn(f"Model {name}: {'removed' if r.returncode == 0 else 'not found'}")
    except Exception as e:
        log_fn(f"Model removal: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# SILENT MODE
# ══════════════════════════════════════════════════════════════════════════════
def run_silent(action):
    def log(m): print(m); _log.info(m)
    log(f"[Silent] action={action}")
    if action == "install":
        pip_install([p for p, _ in CORE_PKGS], log)
        if not check_ollama(): install_ollama(log, lambda v: None)
        if check_ollama() and not check_model(MODEL):
            pull_model(MODEL, log, lambda v: None)
        create_shortcuts(ROOT, log)
        save_install_record(ROOT, {"pkgs": True, "ollama": True, "model": True})
    elif action == "repair":
        for iss in scan_installation(ROOT):
            fix = iss.get("fix")
            if fix == "pkgs": pip_install([p for p, _ in CORE_PKGS], log)
            elif fix == "ollama": install_ollama(log, lambda v: None)
            elif fix == "model": pull_model(MODEL, log, lambda v: None)
            elif fix == "shortcut": create_shortcuts(ROOT, log)
    elif action == "uninstall":
        kill_app(log); remove_shortcuts(log); reg_del_key(REG_KEY)
    log(f"[Silent] {action} complete.")
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP  v4.0 — polished enterprise layout
# ══════════════════════════════════════════════════════════════════════════════
class InstallerApp(tk.Tk):

    INSTALL_STEPS = ["welcome", "license", "directory", "components",
                     "dep_check", "progress", "done"]
    MODIFY_STEPS  = ["maintenance", "components", "dep_check", "progress", "done"]
    REPAIR_STEPS  = ["maintenance", "repair_scan", "progress", "done"]
    UNINST_STEPS  = ["maintenance", "uninstall_opts", "progress", "done"]

    # Sidebar canvas geometry
    _SB_W  = 220   # canvas + outer frame width
    _CX    = 26    # circle centre x
    _CR    = 12    # circle radius
    _SH    = 50    # step slot height
    _TOP   = 62    # y-centre of first circle

    # ── Init ─────────────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__()
        self.title(f"{APPNAME_SHORT}  —  Setup  v{VERSION}")
        self.geometry("960x640")
        self.minsize(860, 580)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_icon()
        self._apply_styles()

        rec = load_install_record()
        self._inst_ver  = rec["version"]
        self._inst_path = rec["install_path"] or str(ROOT)
        self._inst_date = rec["install_date"]

        self._mode          = "maintenance" if self._inst_ver else "install"
        self._maint_action  = None
        self._steps         = self.INSTALL_STEPS
        self._progress_mode = "install"

        # Options
        self.install_dir     = tk.StringVar(value=str(ROOT))
        self.do_pkgs         = tk.BooleanVar(value=True)
        self.do_ollama       = tk.BooleanVar(value=True)
        self.do_model        = tk.BooleanVar(value=True)
        self.do_audio        = tk.BooleanVar(value=False)
        self.do_shortcut     = tk.BooleanVar(value=True)
        self.do_startup      = tk.BooleanVar(value=True)
        self.license_ok      = tk.BooleanVar(value=False)
        self.uninst_models   = tk.BooleanVar(value=False)
        self.uninst_pkgs     = tk.BooleanVar(value=False)
        self.uninst_logs     = tk.BooleanVar(value=True)
        self.uninst_settings = tk.BooleanVar(value=False)

        # Runtime state
        self._cur_page      = ""
        self._repair_issues = []
        self._errors        = []
        self._log_q         = queue.Queue()
        self._prog_vals     = {}
        self._comp_status   = {}
        self._log_text      = None
        self._worker        = None
        self._det           = {}
        self._wheel_bound   = False
        self._sb_canvas     = None

        self._build_shell()
        self._bind_keys()

        if self._mode == "maintenance":
            self._steps = self.INSTALL_STEPS
            self._navigate("maintenance")
        else:
            self._navigate("welcome")

        self.after(80, self._poll_log)

    # ── Icon & styles ─────────────────────────────────────────────────────────
    def _load_icon(self):
        ico = ROOT / "assets" / "icon.ico"
        if ico.exists():
            try: self.iconbitmap(str(ico))
            except Exception: pass

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TScrollbar", background=SURF2, troughcolor=DARK,
                    arrowcolor=MUTED, bordercolor=BG, width=10)
        s.map("TScrollbar", background=[("active", BORD2)])

        # Python 3.14 ttk requires explicit horizontal layout registration for
        # custom progressbar styles — it no longer falls back to the base layout.
        try:
            _hpb_layout = s.layout("Horizontal.TProgressbar")
        except Exception:
            _hpb_layout = None

        for name, clr, lclr in [
            ("Green", GRN,  GRNL),
            ("Blue",  BLUE, BLUE),
            ("Red",   RED,  REDB),
            ("Warn",  WARN, WARN),
            ("Disk",  BLUE, BLUE),
        ]:
            cfg = dict(troughcolor=SURF2, background=clr,
                       bordercolor=SURF2, lightcolor=lclr,
                       darkcolor=clr, thickness=16)
            s.configure(f"{name}.TProgressbar", **cfg)
            if _hpb_layout:
                try:
                    s.layout(f"Horizontal.{name}.TProgressbar", _hpb_layout)
                    s.configure(f"Horizontal.{name}.TProgressbar", **cfg)
                except Exception:
                    pass

    def _bind_keys(self):
        self.bind("<Return>",  lambda e: self._btn_next.invoke()
                  if str(self._btn_next.cget("state")) == "normal" else None)
        self.bind("<Escape>",  lambda e: self._on_close())
        self.bind("<Alt-F4>",  lambda e: self._on_close())
        self.bind("<Left>",    lambda e: self._on_back())
        self.bind("<Right>",   lambda e: self._on_next())

    # ── Shell — FOOTER PACKED BEFORE BODY so it always occupies bottom space ──
    def _build_shell(self):
        self._build_header()
        self._build_footer()          # reserve footer BEFORE body expands

        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        sb_outer = tk.Frame(body, bg=SURF, width=self._SB_W + 4)
        sb_outer.pack(side=tk.LEFT, fill=tk.Y)
        sb_outer.pack_propagate(False)

        self._sb_canvas = tk.Canvas(sb_outer, width=self._SB_W,
                                    bg=SURF, highlightthickness=0, bd=0)
        self._sb_canvas.pack(fill=tk.BOTH, expand=True)

        # Vertical divider
        tk.Frame(body, bg=BORD2, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Content area — canvas+scrollbar so pages can overflow vertically
        content_wrap = tk.Frame(body, bg=BG)
        content_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._content_vsb = ttk.Scrollbar(content_wrap, orient=tk.VERTICAL)
        self._content_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._content_cv = tk.Canvas(content_wrap, bg=BG,
                                     highlightthickness=0, bd=0,
                                     yscrollcommand=self._content_vsb.set)
        self._content_cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._content_vsb.config(command=self._content_cv.yview)

        self._content = tk.Frame(self._content_cv, bg=BG)
        self._cv_win  = self._content_cv.create_window(
            (0, 0), window=self._content, anchor="nw")

        self._content.bind(
            "<Configure>",
            lambda e: self._content_cv.configure(
                scrollregion=self._content_cv.bbox("all")))
        self._content_cv.bind(
            "<Configure>",
            lambda e: self._content_cv.itemconfig(self._cv_win, width=e.width))
        self._content_cv.bind(
            "<MouseWheel>",
            lambda e: self._content_cv.yview_scroll(-1 * (e.delta // 120), "units"))

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURF, height=86)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        # ── RIGHT SIDE packed first so it always reserves space ──────────────
        right = tk.Frame(hdr, bg=SURF, width=206)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 18))
        right.pack_propagate(False)

        # Vertically center the right content
        right_inner = tk.Frame(right, bg=SURF)
        right_inner.place(relx=1.0, rely=0.5, anchor="e")

        tk.Label(right_inner, text=f"v{VERSION}  ·  Build {BUILD}",
                 bg=SURF, fg=MUTED, font=("Segoe UI", 8)).pack(anchor=tk.E)

        badge_bg  = "#0c1f0e"
        badge = tk.Label(right_inner,
                         text="✓  Verified Publisher",
                         bg=badge_bg, fg=GRNL,
                         font=("Segoe UI", 8, "bold"),
                         padx=9, pady=4)
        badge.pack(anchor=tk.E, pady=(5, 0))

        if not is_admin():
            tk.Label(right_inner, text="Running as current user",
                     bg=SURF, fg=MUTED, font=("Segoe UI", 7)).pack(anchor=tk.E, pady=(3, 0))

        # ── LEFT SIDE fills remaining space ──────────────────────────────────
        left = tk.Frame(hdr, bg=SURF)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(18, 8))

        # Vertically center the left content
        left_inner = tk.Frame(left, bg=SURF)
        left_inner.place(relx=0.0, rely=0.5, anchor="w")

        icon_frame = tk.Frame(left_inner, bg=SURF)
        icon_frame.pack(side=tk.LEFT, padx=(0, 14))

        self._hdr_img = None
        try:
            from PIL import Image, ImageTk
            p = ROOT / "assets" / "icon.png"
            if p.exists():
                img = Image.open(str(p)).resize((44, 44), Image.LANCZOS)
                self._hdr_img = ImageTk.PhotoImage(img)
                tk.Label(icon_frame, image=self._hdr_img,
                         bg=SURF).pack()
        except Exception:
            tk.Label(icon_frame, text="⚡", bg=SURF, fg=GRN,
                     font=("Segoe UI", 26, "bold")).pack()

        name_col = tk.Frame(left_inner, bg=SURF)
        name_col.pack(side=tk.LEFT)

        tk.Label(name_col, text=APPNAME, bg=SURF, fg=TEXT,
                 font=("Segoe UI", 13, "bold"),
                 anchor=tk.W).pack(anchor=tk.W)

        auth_row = tk.Frame(name_col, bg=SURF)
        auth_row.pack(anchor=tk.W, pady=(3, 0))
        tk.Label(auth_row, text=AUTHOR, bg=SURF, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Label(auth_row, text=f"  ·  {AUTHOR_CRED}", bg=SURF, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)

        # Accent underline
        tk.Frame(self, bg=GRN, height=2).pack(fill=tk.X)

    def _build_footer(self):
        # Thin separator
        tk.Frame(self, bg=BORD2, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        ftr = tk.Frame(self, bg=SURF, height=66)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)
        ftr.pack_propagate(False)

        # ── Button group (right side, packed first) ───────────────────────────
        bf = tk.Frame(ftr, bg=SURF)
        bf.pack(side=tk.RIGHT, padx=20, pady=12)

        self._btn_cancel = self._mk_btn(bf, "Cancel",   self._on_close,  cancel=True)
        self._btn_back   = self._mk_btn(bf, "← Back",   self._on_back,   secondary=True)
        self._btn_next   = self._mk_btn(bf, "Next  →",  self._on_next)

        self._btn_cancel.pack(side=tk.LEFT, padx=(0, 14))
        tk.Frame(bf, bg=BORD2, width=1, height=30).pack(side=tk.LEFT, pady=3, padx=(0, 14))
        self._btn_back.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_next.pack(side=tk.LEFT)

        # ── Copyright strip (left side) ───────────────────────────────────────
        left_info = tk.Frame(ftr, bg=SURF)
        left_info.pack(side=tk.LEFT, padx=22, fill=tk.Y)

        copy_inner = tk.Frame(left_info, bg=SURF)
        copy_inner.place(relx=0, rely=0.5, anchor="w")

        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(copy_inner, textvariable=self._status_var,
                                    bg=SURF, fg=TEXT2,
                                    font=("Segoe UI", 9))
        self._status_lbl.pack(anchor=tk.W)

        tk.Label(copy_inner, text=COPYRIGHT,
                 bg=SURF, fg=MUTED, font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(2, 0))

        tk.Label(copy_inner, text=SUPPORT_URL,
                 bg=SURF, fg=BORD2, font=("Segoe UI", 7)).pack(anchor=tk.W, pady=(1, 0))

    def _mk_btn(self, parent, text, cmd, secondary=False, danger=False, cancel=False):
        if danger:      bg, hv, pr, fg = RED,   "#c81e1e", REDB, TEXT
        elif cancel:    bg, hv, pr, fg = SURF2,  SURF3,    BORD2, TEXT2
        elif secondary: bg, hv, pr, fg = SURF2,  SURF3,    BORD,  TEXT2
        else:           bg, hv, pr, fg = GRN,    GRNL,     GRND,  TEXT

        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg,
                      activebackground=hv, activeforeground=TEXT,
                      relief=tk.FLAT, font=("Segoe UI", 10, "bold"),
                      padx=20, pady=7, cursor="hand2", bd=0,
                      highlightthickness=2,
                      highlightbackground=bg,
                      highlightcolor=GRNL)
        b.bind("<Enter>",        lambda e, h=hv: b.config(bg=h))
        b.bind("<Leave>",        lambda e, n=bg: b.config(bg=n))
        b.bind("<ButtonPress>",  lambda e, p=pr: b.config(bg=p))
        b.bind("<ButtonRelease>",lambda e, h=hv: b.config(bg=h))
        b.bind("<FocusIn>",      lambda e: b.config(highlightbackground=GRNL))
        b.bind("<FocusOut>",     lambda e, n=bg: b.config(highlightbackground=n))
        return b

    # ── Sidebar canvas ────────────────────────────────────────────────────────
    def _update_sidebar(self):
        c   = self._sb_canvas
        W   = self._SB_W
        CX  = self._CX
        CR  = self._CR
        SH  = self._SH
        TOP = self._TOP

        c.delete("all")
        c.configure(bg=SURF)

        # Title label
        c.create_text(14, 18, text="SETUP STEPS", anchor="w",
                      fill=MUTED, font=("Segoe UI", 8, "bold"))
        c.create_line(14, 34, W - 8, 34, fill=BORD, width=1)

        cur_idx = (self._steps.index(self._cur_page)
                   if self._cur_page in self._steps else 0)

        n_steps = len(self._steps)
        for i, step_id in enumerate(self._steps):
            cy = TOP + i * SH
            label = STEP_LABELS.get(step_id, step_id.title())

            # Connector line between circles
            if i > 0:
                prev_cy = TOP + (i - 1) * SH
                lclr = GRN if i <= cur_idx else BORD
                c.create_line(CX, prev_cy + CR + 3, CX, cy - CR - 3,
                              fill=lclr, width=2)

            if i < cur_idx:         # completed
                c.create_oval(CX-CR, cy-CR, CX+CR, cy+CR,
                              fill=GRN, outline="")
                c.create_text(CX, cy, text="✓", fill=TEXT,
                              font=("Segoe UI", 9, "bold"))
                c.create_text(CX + CR + 12, cy, text=label, anchor="w",
                              fill=GRNL, font=("Segoe UI", 9))

            elif i == cur_idx:      # active
                c.create_oval(CX-CR-5, cy-CR-5, CX+CR+5, cy+CR+5,
                              outline=GRN, width=1, dash=(4, 3))
                c.create_oval(CX-CR, cy-CR, CX+CR, cy+CR,
                              fill=GRN, outline="")
                c.create_text(CX, cy, text=str(i + 1), fill=TEXT,
                              font=("Segoe UI", 9, "bold"))
                c.create_text(CX + CR + 12, cy, text=label, anchor="w",
                              fill=TEXT, font=("Segoe UI", 10, "bold"))

            else:                   # pending
                c.create_oval(CX-CR, cy-CR, CX+CR, cy+CR,
                              fill=SURF2, outline=BORD2, width=1)
                c.create_text(CX, cy, text=str(i + 1), fill=MUTED,
                              font=("Segoe UI", 9))
                c.create_text(CX + CR + 12, cy, text=label, anchor="w",
                              fill=MUTED, font=("Segoe UI", 9))

        # ── Progress bar ──────────────────────────────────────────────────────
        pct     = int((cur_idx / max(n_steps - 1, 1)) * 100)
        prog_y  = TOP + n_steps * SH + 16

        c.create_text(14, prog_y - 2, text="Progress", anchor="w",
                      fill=MUTED, font=("Segoe UI", 8))
        c.create_text(W - 8, prog_y - 2, text=f"{pct}%", anchor="e",
                      fill=(TEXT if pct > 0 else MUTED), font=("Segoe UI", 8, "bold"))

        BAR_X1, BAR_X2 = 14, W - 8
        BAR_Y1 = prog_y + 10
        BAR_H  = 14
        BAR_Y2 = BAR_Y1 + BAR_H
        BAR_R  = BAR_H // 2

        # Trough (rounded)
        c.create_arc(BAR_X1, BAR_Y1, BAR_X1 + BAR_H, BAR_Y2,
                     start=90, extent=180, fill=BORD2, outline="")
        c.create_arc(BAR_X2 - BAR_H, BAR_Y1, BAR_X2, BAR_Y2,
                     start=270, extent=180, fill=BORD2, outline="")
        c.create_rectangle(BAR_X1 + BAR_R, BAR_Y1, BAR_X2 - BAR_R, BAR_Y2,
                           fill=BORD2, outline="")

        # Fill
        if pct > 0:
            fill_x = BAR_X1 + max(BAR_H, int((BAR_X2 - BAR_X1) * pct / 100))
            fill_x = min(fill_x, BAR_X2)
            c.create_arc(BAR_X1, BAR_Y1, BAR_X1 + BAR_H, BAR_Y2,
                         start=90, extent=180, fill=GRN, outline="")
            if fill_x > BAR_X1 + BAR_H:
                if fill_x >= BAR_X2 - 1:
                    c.create_arc(BAR_X2 - BAR_H, BAR_Y1, BAR_X2, BAR_Y2,
                                 start=270, extent=180, fill=GRN, outline="")
                c.create_rectangle(BAR_X1 + BAR_R, BAR_Y1, fill_x, BAR_Y2,
                                   fill=GRN, outline="")

        # Installed version label
        if self._inst_ver:
            vy = BAR_Y2 + 16
            c.create_line(14, vy, W - 8, vy, fill=BORD, width=1)
            c.create_text(14, vy + 13, text=f"Installed: v{self._inst_ver}",
                          anchor="w", fill=MUTED, font=("Segoe UI", 8))
            if self._inst_date:
                c.create_text(14, vy + 25, text=self._inst_date[:10],
                              anchor="w", fill=BORD2, font=("Segoe UI", 7))

    # ── Navigation ────────────────────────────────────────────────────────────
    def _navigate(self, page_id):
        if self._wheel_bound:
            try: self.unbind_all("<MouseWheel>")
            except Exception: pass
            self._wheel_bound = False

        for w in self._content.winfo_children():
            w.destroy()
        self._cur_page = page_id
        self._log_text = None
        self._status_var.set("")
        # Reset content scroll to top on every page transition
        try: self._content_cv.yview_moveto(0)
        except Exception: pass
        self._update_sidebar()

        {
            "welcome":        self._pg_welcome,
            "license":        self._pg_license,
            "directory":      self._pg_directory,
            "components":     self._pg_components,
            "dep_check":      self._pg_dep_check,
            "maintenance":    self._pg_maintenance,
            "repair_scan":    self._pg_repair_scan,
            "uninstall_opts": self._pg_uninstall_opts,
            "progress":       self._pg_progress,
            "done":           self._pg_done,
        }[page_id]()

    def _on_back(self):
        if self._cur_page in self._steps:
            idx = self._steps.index(self._cur_page)
            if idx > 0 and str(self._btn_back.cget("state")) == "normal":
                self._navigate(self._steps[idx - 1])

    def _on_next(self):
        if self._cur_page in self._steps:
            idx = self._steps.index(self._cur_page)
            if idx < len(self._steps) - 1 and str(self._btn_next.cget("state")) == "normal":
                self._navigate(self._steps[idx + 1])

    def _on_close(self):
        if self._worker and self._worker.is_alive():
            return
        self.destroy()

    # ── Log queue ─────────────────────────────────────────────────────────────
    def _poll_log(self):
        try:
            while True:
                kind, payload = self._log_q.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "prog":
                    cid, val = payload
                    if cid in self._prog_vals:
                        self._prog_vals[cid].set(val)
                elif kind == "status":
                    cid, txt, clr = payload
                    if cid in self._comp_status:
                        sv, cv = self._comp_status[cid]
                        sv.set(txt); cv.set(clr)
                elif kind == "footer":
                    self._status_var.set(payload)
                elif kind == "done":
                    self._errors = payload
                    self._navigate("done")
        except queue.Empty:
            pass
        self.after(80, self._poll_log)

    def _q_log(self, m):         self._log_q.put(("log",    m))
    def _q_prog(self, c, v):     self._log_q.put(("prog",   (c, v)))
    def _q_st(self, c, t, r=MUTED): self._log_q.put(("status", (c, t, r)))
    def _q_foot(self, m):        self._log_q.put(("footer", m))
    def _q_done(self, e):        self._log_q.put(("done",   e))

    def _append_log(self, text):
        if self._log_text is None: return
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, text + "\n")
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _page_frame(self, padx=40, pady=24):
        f = tk.Frame(self._content, bg=BG)
        f.pack(fill=tk.BOTH, expand=True, padx=padx, pady=pady)
        return f

    def _page_title(self, parent, title, sub=""):
        tk.Label(parent, text=title, bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold"),
                 wraplength=580, justify=tk.LEFT).pack(anchor=tk.W)
        if sub:
            tk.Label(parent, text=sub, bg=BG, fg=TEXT2,
                     font=("Segoe UI", 10),
                     wraplength=580, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))
        tk.Frame(parent, bg=BORD2, height=1).pack(fill=tk.X, pady=(14, 14))

    def _hover_btn(self, btn, normal, hover):
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=normal))

    def _mk_check(self, parent, var, bg=SURF, locked=False, command=None):
        """High-contrast canvas checkbox — tkinter Checkbutton is unreadable on dark themes."""
        S = 20
        cv = tk.Canvas(parent, width=S, height=S, bg=bg,
                       highlightthickness=0, bd=0,
                       cursor="arrow" if locked else "hand2")

        def _draw(*_):
            cv.delete("all")
            if var.get():
                fill = "#0e8a38" if locked else GRN
                cv.create_rectangle(2, 2, S-2, S-2, fill=fill, outline=fill)
                # Checkmark: two line segments
                cv.create_line(5, S//2, S//2-1, S-5,
                               fill=TEXT, width=2,
                               capstyle=tk.ROUND, joinstyle=tk.ROUND)
                cv.create_line(S//2-1, S-5, S-4, 5,
                               fill=TEXT, width=2,
                               capstyle=tk.ROUND, joinstyle=tk.ROUND)
            else:
                cv.create_rectangle(2, 2, S-2, S-2,
                                    fill=SURF3, outline=BORD2, width=2)

        def _toggle(e=None):
            if locked:
                return
            var.set(not var.get())
            if command:
                command()

        cv.bind("<Button-1>", _toggle)
        var.trace_add("write", _draw)
        _draw()
        return cv

    def _scrollable(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)
        cv = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=cv.yview)
        sf = tk.Frame(cv, bg=BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor=tk.NW)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        # Bind scroll only to this inner canvas; avoid conflicting with outer content canvas
        cv.bind("<MouseWheel>",
                lambda e, c=cv: c.yview_scroll(-1 * (e.delta // 120), "units"))
        sf.bind("<MouseWheel>",
                lambda e, c=cv: c.yview_scroll(-1 * (e.delta // 120), "units"))
        self._wheel_bound = True
        return sf

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: WELCOME
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_welcome(self):
        self._btn_cancel.config(state=tk.NORMAL)
        self._btn_back.config(state=tk.DISABLED)
        self._btn_next.config(
            text="Next  →", bg=GRN, fg=TEXT, state=tk.NORMAL,
            command=lambda: self._start_detection(lambda: self._navigate("license")))

        f = self._page_frame()
        self._page_title(f, f"Welcome to {APPNAME}",
                         f"Version {VERSION}  ·  {AUTHOR}  ·  {AUTHOR_CRED}")

        # Publisher trust card (subtle)
        trust = tk.Frame(f, bg="#0d1a10", padx=14, pady=9)
        trust.pack(fill=tk.X, pady=(0, 16))
        tk.Frame(trust, bg=GRN, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        col = tk.Frame(trust, bg="#0d1a10")
        col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(col, text="✓  Verified Publisher  ·  MIT License",
                 bg="#0d1a10", fg=GRNL, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        tk.Label(col, text=f"{AUTHOR}  ·  {AUTHOR_CRED}  ·  {SUPPORT_URL}",
                 bg="#0d1a10", fg=TEXT2, font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(2, 0))
        tk.Label(trust, text="\U0001f512", bg="#0d1a10", fg=GRNL,
                 font=("Segoe UI", 12)).pack(side=tk.RIGHT, padx=6)

        # Two-column summary cards
        cols = tk.Frame(f, bg=BG)
        cols.pack(fill=tk.X, pady=(0, 14))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # Left: what will happen
        left = tk.Frame(cols, bg=SURF, padx=18, pady=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(left, text="THIS INSTALLATION WILL",
                 bg=SURF, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 10))
        for text in [
            "Install 18 Python packages",
            "Download Ollama AI engine  (~100 MB)",
            f"Download {MODEL}  (~400 MB)",
            "Create Desktop shortcut",
            "Register Windows startup entry",
        ]:
            row = tk.Frame(left, bg=SURF)
            row.pack(anchor=tk.W, pady=3)
            tk.Label(row, text="•", bg=SURF, fg=GRN,
                     font=("Segoe UI", 10), width=2).pack(side=tk.LEFT)
            tk.Label(row, text=text, bg=SURF, fg=TEXT,
                     font=("Segoe UI", 9),
                     wraplength=240, justify=tk.LEFT).pack(side=tk.LEFT)

        # Right: system info
        right = tk.Frame(cols, bg=SURF, padx=18, pady=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(right, text="SYSTEM INFORMATION",
                 bg=SURF, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 10))

        free    = get_disk_free_mb(ROOT)
        ok_disk = free >= DISK_REQ_MB

        for k, v, clr in [
            ("Python",     get_python_ver(),           TEXT),
            ("Disk req.",  f"~{DISK_REQ_MB:,} MB",     TEXT),
            ("Disk free",  f"{free:,} MB",              OK if ok_disk else ERR),
            ("Platform",   "Windows 64-bit",            TEXT),
            ("Install as", "Current user",              TEXT2),
        ]:
            row = tk.Frame(right, bg=SURF)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=k, bg=SURF, fg=MUTED,
                     font=("Segoe UI", 9), width=13, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=v, bg=SURF, fg=clr,
                     font=("Segoe UI", 9, "bold"), anchor=tk.W).pack(side=tk.LEFT)

        if not ok_disk:
            warn = tk.Frame(f, bg="#1c0a00", padx=14, pady=8)
            warn.pack(fill=tk.X)
            tk.Label(warn,
                     text=f"⚠  Insufficient disk space. {DISK_REQ_MB:,} MB required, {free:,} MB available.",
                     bg="#1c0a00", fg=WARN, font=("Segoe UI", 9),
                     wraplength=560, justify=tk.LEFT).pack(anchor=tk.W)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: LICENSE
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_license(self):
        self._btn_back.config(state=tk.NORMAL, command=lambda: self._navigate("welcome"))
        self._btn_next.config(
            text="I Accept  →", bg=SURF2, fg=MUTED, state=tk.DISABLED,
            command=lambda: self._navigate("directory"))

        lic_text = LICENSE_TEXT
        lic_file = ROOT / "LICENSE"
        if lic_file.exists():
            try: lic_text = lic_file.read_text(encoding="utf-8")
            except Exception: pass

        f = self._page_frame()
        self._page_title(f, "License Agreement",
                         "Please read the following license terms carefully before continuing.")

        txt_frame = tk.Frame(f, bg=BORD2, padx=1, pady=1)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        txt_inner = tk.Frame(txt_frame, bg=DARK)
        txt_inner.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(txt_inner, bg=DARK, fg=TEXT2, font=("Consolas", 9),
                      relief=tk.FLAT, wrap=tk.WORD, padx=16, pady=14,
                      insertbackground=TEXT, state=tk.NORMAL, selectbackground=SURF3)
        tsb = ttk.Scrollbar(txt_inner, command=txt.yview)
        txt.configure(yscrollcommand=tsb.set)
        tsb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, lic_text)
        txt.config(state=tk.DISABLED)

        accept_row = tk.Frame(f, bg=BG, pady=12)
        accept_row.pack(fill=tk.X)

        def _toggle():
            if self.license_ok.get():
                self._btn_next.config(bg=GRN, fg=TEXT, state=tk.NORMAL)
            else:
                self._btn_next.config(bg=SURF2, fg=MUTED, state=tk.DISABLED)

        self._mk_check(accept_row, self.license_ok, bg=BG, command=_toggle).pack(
            side=tk.LEFT, padx=(0, 8))
        tk.Label(accept_row,
                 text="I have read and accept the terms of the License Agreement.",
                 bg=BG, fg=TEXT, font=("Segoe UI", 10)).pack(side=tk.LEFT)

    # ══════════════════════════════════════════════════════════════════════════
    # DETECTION OVERLAY
    # ══════════════════════════════════════════════════════════════════════════
    def _start_detection(self, callback):
        for w in self._content.winfo_children():
            w.destroy()
        self._btn_next.config(state=tk.DISABLED, text="Scanning…", bg=SURF2, fg=MUTED)
        self._btn_back.config(state=tk.DISABLED)

        # Advance sidebar to show next step as current immediately on scan start
        if self._cur_page in self._steps:
            _scan_idx = self._steps.index(self._cur_page)
            if _scan_idx + 1 < len(self._steps):
                self._cur_page = self._steps[_scan_idx + 1]
                self._update_sidebar()
                self._cur_page = self._steps[_scan_idx]

        ov = tk.Frame(self._content, bg=BG)
        ov.pack(fill=tk.BOTH, expand=True)
        tk.Frame(ov, bg=BG).pack(expand=True)

        tk.Label(ov, text="Scanning Your System",
                 bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack()
        sub = tk.Label(ov, text="Initializing…",
                       bg=BG, fg=TEXT2, font=("Segoe UI", 10))
        sub.pack(pady=8)

        pb_v = tk.IntVar(value=0)
        pb = ttk.Progressbar(ov, variable=pb_v, maximum=100,
                             style="Blue.TProgressbar", length=360)
        pb.pack(pady=4)
        pct_lbl = tk.Label(ov, text="0%", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        pct_lbl.pack()
        tk.Frame(ov, bg=BG).pack(expand=True)

        steps = [
            (18,  "Checking Python runtime…"),
            (36,  "Scanning installed packages…"),
            (54,  "Detecting Ollama AI engine…"),
            (72,  f"Checking language model ({MODEL})…"),
            (90,  "Verifying application files…"),
            (100, "Scan complete."),
        ]
        self._scan_i = 0

        def _tick():
            if self._scan_i < len(steps):
                v, msg = steps[self._scan_i]
                pb_v.set(v)
                pct_lbl.config(text=f"{v}%")
                sub.config(text=msg)
                self._scan_i += 1
                self.after(240, _tick)

        self.after(0, _tick)

        def _detect():
            v = sys.version_info
            self._det = {
                "python":  f"{v.major}.{v.minor}.{v.micro}",
                "pkgs":    all(importable(imp) for _, imp in CORE_PKGS),
                "pkg_cnt": count_pkgs(),
                "ollama":  check_ollama(),
                "model":   check_model(MODEL),
                "audio":   importable("pyaudio"),
                "disk_mb": get_disk_free_mb(Path(self.install_dir.get())),
            }
            time.sleep(0.5)
            self.after(0, callback)

        threading.Thread(target=_detect, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: INSTALL DIRECTORY
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_directory(self):
        self._btn_back.config(state=tk.NORMAL,
                              command=lambda: self._navigate("license"))
        self._btn_next.config(
            text="Next  →", bg=GRN, fg=TEXT, state=tk.NORMAL,
            command=lambda: self._navigate("components"))

        f = self._page_frame()
        self._page_title(f, "Install Location",
                         "Choose where to install the application files.")

        tk.Label(f, text="Installation folder", bg=BG, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 6))

        pick = tk.Frame(f, bg=BORD2, padx=1, pady=1)
        pick.pack(fill=tk.X)
        inner = tk.Frame(pick, bg=SURF2)
        inner.pack(fill=tk.X)

        entry = tk.Entry(inner, textvariable=self.install_dir,
                         bg=SURF2, fg=TEXT, insertbackground=TEXT,
                         relief=tk.FLAT, font=("Segoe UI", 10), bd=10)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        disk_var = tk.IntVar(value=0)
        disk_lbl = tk.Label(f)

        def _browse():
            d = filedialog.askdirectory(initialdir=self.install_dir.get())
            if d:
                self.install_dir.set(d)
                _refresh_disk(Path(d))

        browse_btn = tk.Button(inner, text=" Browse… ", command=_browse,
                               bg=SURF3, fg=TEXT, activebackground=BORD2,
                               relief=tk.FLAT, font=("Segoe UI", 9), bd=0, padx=14, pady=9)
        self._hover_btn(browse_btn, SURF3, BORD2)
        browse_btn.pack(side=tk.RIGHT)

        tk.Frame(f, bg=BG, height=8).pack()
        tk.Label(f, text="Disk Space", bg=BG, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        disk_card = tk.Frame(f, bg=SURF, padx=20, pady=18)
        disk_card.pack(fill=tk.X, pady=(8, 0))

        ttk.Progressbar(disk_card, variable=disk_var, maximum=100,
                        style="Disk.TProgressbar").pack(fill=tk.X, pady=(0, 12))

        disk_lbl = tk.Label(disk_card, text="", bg=SURF, fg=TEXT2,
                            font=("Segoe UI", 9))
        disk_lbl.pack(anchor=tk.W)

        req_row = tk.Frame(disk_card, bg=SURF)
        req_row.pack(fill=tk.X, pady=(8, 0))
        for k, v in [("Required:", f"~{DISK_REQ_MB:,} MB"),
                     ("Includes:", "Python packages + Ollama + AI model")]:
            tk.Label(req_row, text=k, bg=SURF, fg=MUTED,
                     font=("Segoe UI", 9), width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(req_row, text=v, bg=SURF, fg=TEXT2,
                     font=("Segoe UI", 9), anchor=tk.W).pack(side=tk.LEFT, padx=(0, 28))

        def _refresh_disk(path):
            free = get_disk_free_mb(path)
            pct  = min(100, int((1 - free / max(free + DISK_REQ_MB, 1)) * 100))
            disk_var.set(pct)
            clr = OK if free >= DISK_REQ_MB else ERR
            disk_lbl.config(
                text=f"Available on {Path(path).anchor.rstrip(chr(92))}: {free:,} MB",
                fg=clr)

        _refresh_disk(Path(self.install_dir.get()))

        tk.Frame(f, bg=BG).pack(expand=True)
        tk.Label(f,
                 text="Note: This app runs from its source directory. "
                      "The path above is used to create Desktop and startup shortcuts.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "italic"),
                 wraplength=560, justify=tk.LEFT).pack(anchor=tk.W)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: COMPONENTS
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_components(self):
        is_modify = self._maint_action == "modify"
        back_tgt  = "maintenance" if is_modify else "directory"

        self._btn_back.config(state=tk.NORMAL,
                              command=lambda: self._navigate(back_tgt))
        self._btn_next.config(
            text="Next  →", bg=GRN, fg=TEXT, state=tk.NORMAL,
            command=lambda: self._start_detection(lambda: self._navigate("dep_check")))

        f = self._page_frame(padx=36)
        self._page_title(
            f,
            "Modify Components" if is_modify else "Select Components",
            "Check items to install. Items already installed are pre-selected.")

        sf = self._scrollable(f)
        det = self._det
        inst_n, total_n = det.get("pkg_cnt", count_pkgs())

        groups = [
            ("Python Runtime", GRNL, [
                ("__py__",
                 f"Python {det.get('python', get_python_ver())}",
                 "Active Python installation — already present",
                 None, True, False),
            ]),
            ("Core Packages", BLUE, [
                ("pkgs",
                 f"Python dependencies  ({inst_n}/{total_n} installed)",
                 "PyQt6  ·  psutil  ·  openai  ·  anthropic  ·  requests  "
                 "·  pywin32  ·  matplotlib  +  11 more",
                 self.do_pkgs, det.get("pkgs", False), False),
            ]),
            ("Ollama AI Engine", PURP, [
                ("ollama",
                 "Ollama runtime",
                 "Local AI inference — runs large language models offline on your hardware",
                 self.do_ollama, det.get("ollama", False), False),
                ("model",
                 f"Language model  ·  {MODEL}",
                 f"Quantized 0.5B model, {MODEL_SIZE} — ultra-fast, low RAM",
                 self.do_model, det.get("model", False), False),
            ]),
            ("Shortcuts & Startup", GRN, [
                ("shortcut",
                 "Desktop shortcut",
                 "Quick-launch shortcut on your Desktop",
                 self.do_shortcut, True, False),
                ("startup",
                 "Windows startup entry",
                 "Launch automatically when Windows starts",
                 self.do_startup, True, False),
            ]),
            ("Audio Support  (Optional)", WARN, [
                ("audio",
                 "PyAudio  —  voice commands",
                 "Microphone input  ·  requires MSVC Build Tools or Python ≤ 3.13",
                 self.do_audio, det.get("audio", False), True),
            ]),
        ]

        for group_title, gclr, items in groups:
            gh = tk.Frame(sf, bg=BG)
            gh.pack(fill=tk.X, padx=4, pady=(14, 4))
            tk.Frame(gh, bg=gclr, width=3, height=14).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
            tk.Label(gh, text=group_title, bg=BG, fg=gclr,
                     font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

            for (cid, name, detail, var, installed, optional) in items:
                card = tk.Frame(sf, bg=SURF, padx=14, pady=12)
                card.pack(fill=tk.X, padx=4, pady=2)
                tk.Frame(card, bg=gclr if installed else (WARN if optional else BORD2),
                         width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

                if var is not None:
                    var.set(not installed)
                    self._mk_check(card, var, bg=SURF).pack(side=tk.LEFT, padx=(0, 8))
                else:
                    tk.Label(card, text="  ", bg=SURF, width=3).pack(side=tk.LEFT)

                mid = tk.Frame(card, bg=SURF)
                mid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
                tk.Label(mid, text=name, bg=SURF, fg=TEXT,
                         font=("Segoe UI", 10, "bold"), anchor=tk.W,
                         wraplength=320).pack(anchor=tk.W)
                tk.Label(mid, text=detail, bg=SURF, fg=TEXT2,
                         font=("Segoe UI", 9), anchor=tk.W,
                         wraplength=320).pack(anchor=tk.W, pady=(2, 0))

                if installed:                        badge, bc = "✓  Installed",   OK
                elif optional:                       badge, bc = "Optional",            WARN
                elif cid in ("shortcut", "startup"): badge, bc = "Will create",        TEXT2
                else:                                badge, bc = "✗  Missing",     ERR
                tk.Label(card, text=badge, bg=SURF, fg=bc,
                         font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=8)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: DEPENDENCY CHECK / READY TO INSTALL
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_dep_check(self):
        self._btn_back.config(state=tk.NORMAL,
                              command=lambda: self._navigate("components"))
        self._btn_next.config(
            text="Install  ▶", bg=GRN, fg=TEXT, state=tk.NORMAL,
            command=lambda: self._navigate("progress"))

        f = self._page_frame()
        self._page_title(f, "Ready to Install",
                         "Review the installation summary below, then click Install.")

        det = self._det
        inst_n, total_n = det.get("pkg_cnt", count_pkgs())

        tbl = tk.Frame(f, bg=SURF)
        tbl.pack(fill=tk.X, pady=(0, 16))

        hrow = tk.Frame(tbl, bg=SURF2, padx=16, pady=10)
        hrow.pack(fill=tk.X)
        for txt, w in [("Component", 36), ("Status", 22), ("Download", 11)]:
            tk.Label(hrow, text=txt, bg=SURF2, fg=MUTED,
                     font=("Segoe UI", 9, "bold"),
                     width=w, anchor=tk.W).pack(side=tk.LEFT)

        tk.Frame(tbl, bg=BORD2, height=1).pack(fill=tk.X)

        rows = []
        if self.do_pkgs.get():
            st  = f"✓  {inst_n}/{total_n} installed" if det.get("pkgs") else f"✗  {total_n - inst_n} missing"
            clr = OK if det.get("pkgs") else WARN
            dl  = "~50 MB" if not det.get("pkgs") else "—"
            rows.append(("Python packages  (18)", st, clr, dl))
        if self.do_ollama.get():
            st  = "✓  Installed" if det.get("ollama") else "✗  Not installed"
            clr = OK if det.get("ollama") else ERR
            dl  = "—" if det.get("ollama") else "~100 MB"
            rows.append(("Ollama AI engine", st, clr, dl))
        if self.do_model.get():
            st  = "✓  Downloaded" if det.get("model") else "✗  Not downloaded"
            clr = OK if det.get("model") else ERR
            dl  = "—" if det.get("model") else MODEL_SIZE
            rows.append((f"Model  ({MODEL})", st, clr, dl))
        if self.do_audio.get():
            st  = "✓  Installed" if det.get("audio") else "○  Will attempt"
            clr = OK if det.get("audio") else WARN
            rows.append(("PyAudio  (voice)", st, clr, "~5 MB"))
        if self.do_shortcut.get() or self.do_startup.get():
            rows.append(("Shortcuts & startup entry", "Will create", TEXT2, "—"))

        for i, (name, status, clr, dl) in enumerate(rows):
            bg = SURF if i % 2 == 0 else SURF2
            row = tk.Frame(tbl, bg=bg, padx=16, pady=12)
            row.pack(fill=tk.X)
            tk.Label(row, text=name, bg=bg, fg=TEXT,
                     font=("Segoe UI", 10), width=36, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=status, bg=bg, fg=clr,
                     font=("Segoe UI", 9, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=dl, bg=bg, fg=TEXT2,
                     font=("Segoe UI", 9), anchor=tk.W).pack(side=tk.LEFT)

        tk.Frame(tbl, bg=BORD2, height=1).pack(fill=tk.X)

        total_dl_mb = 0
        if self.do_ollama.get() and not det.get("ollama"): total_dl_mb += 100
        if self.do_model.get()  and not det.get("model"):  total_dl_mb += 400
        if not det.get("pkgs"):                             total_dl_mb += 50

        summary = tk.Frame(f, bg=SURF2, padx=20, pady=16)
        summary.pack(fill=tk.X)
        for k, v in [
            ("Total download:", f"~{total_dl_mb:,} MB" if total_dl_mb else "Minimal (all cached)"),
            ("Location:",       str(self.install_dir.get())[:70]),
            ("Disk available:", f"{det.get('disk_mb', 0):,} MB"),
            ("Log file:",       str(LOG_FILE)),
        ]:
            row = tk.Frame(summary, bg=SURF2)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=k, bg=SURF2, fg=MUTED,
                     font=("Segoe UI", 9), width=18, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=v, bg=SURF2, fg=TEXT,
                     font=("Segoe UI", 9), anchor=tk.W,
                     wraplength=480).pack(side=tk.LEFT)

        tk.Frame(f, bg=BG).pack(expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: MAINTENANCE MENU
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_maintenance(self):
        self._btn_back.config(state=tk.DISABLED)
        self._btn_next.config(state=tk.DISABLED, text="Select an option…",
                              bg=SURF2, fg=MUTED)
        self._btn_cancel.config(state=tk.NORMAL)

        f = self._page_frame()
        sub = f"Installed: v{self._inst_ver}"
        if self._inst_date:
            sub += f"  ·  {self._inst_date[:10]}"
        self._page_title(f, "Maintenance Mode", sub)

        tk.Label(f, text="What would you like to do?", bg=BG, fg=TEXT2,
                 font=("Segoe UI", 11)).pack(anchor=tk.W, pady=(0, 14))

        selected_card = [None]

        def _tint(w, bg):
            try: w.config(bg=bg)
            except Exception: pass
            for ch in w.winfo_children():
                _tint(ch, bg)

        def _opt(icon, title, sub, action, accent, desc_lines):
            card = tk.Frame(f, bg=SURF, cursor="hand2")
            card.pack(fill=tk.X, pady=5)
            tk.Frame(card, bg=accent, width=4).pack(side=tk.LEFT, fill=tk.Y)

            body = tk.Frame(card, bg=SURF, padx=18, pady=16)
            body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            top_row = tk.Frame(body, bg=SURF)
            top_row.pack(anchor=tk.W)
            tk.Label(top_row, text=icon, bg=SURF, fg=accent,
                     font=("Segoe UI", 14)).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(top_row, text=title, bg=SURF, fg=TEXT,
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)

            tk.Label(body, text=sub, bg=SURF, fg=TEXT2,
                     font=("Segoe UI", 9), anchor=tk.W).pack(anchor=tk.W, pady=(3, 7))

            for line in desc_lines:
                tk.Label(body, text=f"  ›  {line}", bg=SURF, fg=MUTED,
                         font=("Segoe UI", 8), anchor=tk.W).pack(anchor=tk.W, pady=1)

            arr = tk.Label(card, text="›", bg=SURF, fg=MUTED,
                           font=("Segoe UI", 20), padx=18)
            arr.pack(side=tk.RIGHT)

            def _select(a=action, c=card, ac=accent, ar=arr):
                if selected_card[0]:
                    _tint(selected_card[0], SURF)
                selected_card[0] = c
                _tint(c, SURF3)
                ar.config(bg=SURF3, fg=ac)
                self._maint_action = a
                lbl = {"modify": "Modify  →",
                       "repair": "Repair  →",
                       "uninstall": "Uninstall  ▶"}.get(a, "Continue  →")
                nbg = RED if a == "uninstall" else GRN
                self._btn_next.config(state=tk.NORMAL, text=lbl,
                                      bg=nbg, fg=TEXT, command=self._maint_next)

            card.bind("<Button-1>", lambda e: _select())
            for ch in card.winfo_children():
                ch.bind("<Button-1>", lambda e: _select())
            self._hover_btn(card, SURF, SURF3)

        _opt("\U0001f527", "Modify Installation",
             "Add or remove optional components",
             "modify", BLUE,
             ["Change installed components",
              "Add optional features",
              "Adjust shortcuts and startup"])

        _opt("\U0001f528", "Repair Installation",
             "Fix broken or missing components",
             "repair", WARN,
             ["Scan for missing files and packages",
              "Re-download damaged components",
              "Restore shortcuts and registry entries"])

        _opt("\U0001f5d1️", "Uninstall Application",
             "Remove the application from this system",
             "uninstall", RED,
             ["Remove shortcuts and startup entries",
              "Optionally remove AI models, logs, and user data",
              "Clean up all registry keys"])

    def _maint_next(self):
        if self._maint_action == "modify":
            self._steps = self.MODIFY_STEPS
            self._progress_mode = "install"
            self._start_detection(lambda: self._navigate("components"))
        elif self._maint_action == "repair":
            self._steps = self.REPAIR_STEPS
            self._progress_mode = "repair"
            self._start_detection(lambda: self._navigate("repair_scan"))
        elif self._maint_action == "uninstall":
            self._steps = self.UNINST_STEPS
            self._progress_mode = "uninstall"
            self._navigate("uninstall_opts")
        self._update_sidebar()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: REPAIR SCAN
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_repair_scan(self):
        self._btn_back.config(state=tk.NORMAL,
                              command=lambda: self._navigate("maintenance"))
        self._repair_issues = scan_installation(Path(self.install_dir.get()))
        n = len(self._repair_issues)

        self._btn_next.config(
            text="Repair Now  ▶" if n else "Close",
            bg=WARN if n else GRN, fg=BG if n else TEXT, state=tk.NORMAL,
            command=(lambda: self._navigate("progress")) if n else self.destroy)

        f = self._page_frame()
        self._page_title(f, "Repair Analysis",
                         "Scan complete — reviewing installation health.")

        badge_bg  = "#1c0e00" if n else "#0a1f0e"
        badge_fg  = WARN if n else GRNL
        badge_txt = (f"  ⚠  {n} issue{'s' if n > 1 else ''} found — repair recommended"
                     if n else "  ✓  Installation is healthy — no issues detected")
        tk.Label(f, text=badge_txt, bg=badge_bg, fg=badge_fg,
                 font=("Segoe UI", 10, "bold"), padx=16, pady=12,
                 anchor=tk.W).pack(fill=tk.X, pady=(0, 16))

        sev_map = {"error": ("✗", ERR), "warning": ("⚠", WARN), "info": ("ℹ", BLUE)}

        if self._repair_issues:
            for issue in self._repair_issues:
                icon, clr = sev_map.get(issue["severity"], ("•", MUTED))
                card = tk.Frame(f, bg=SURF, padx=14, pady=12)
                card.pack(fill=tk.X, pady=3)
                tk.Frame(card, bg=clr, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
                tk.Label(card, text=icon, bg=SURF, fg=clr,
                         font=("Segoe UI", 12), width=3).pack(side=tk.LEFT)
                mid = tk.Frame(card, bg=SURF)
                mid.pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(mid, text=issue["label"], bg=SURF, fg=TEXT,
                         font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(anchor=tk.W)
                tk.Label(mid, text=issue["detail"], bg=SURF, fg=TEXT2,
                         font=("Segoe UI", 9), anchor=tk.W).pack(anchor=tk.W, pady=(2, 0))
                fix_lbl = "Will fix" if issue["fix"] != "files" else "Manual action"
                fix_clr = GRN if issue["fix"] != "files" else WARN
                tk.Label(card, text=fix_lbl, bg=SURF, fg=fix_clr,
                         font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=10)

        tk.Frame(f, bg=BG).pack(expand=True)
        tk.Label(f, text=f"Log: {LOG_FILE}",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor=tk.W)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: UNINSTALL OPTIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_uninstall_opts(self):
        self._btn_back.config(state=tk.NORMAL,
                              command=lambda: self._navigate("maintenance"))
        self._btn_next.config(
            text="Uninstall  ▶", bg=RED, fg=TEXT, state=tk.NORMAL,
            command=self._confirm_uninstall)

        f = self._page_frame()
        self._page_title(f, "Uninstall Application",
                         "Select what to remove. Items marked ⚠ delete user data permanently.")

        always_var = tk.BooleanVar(value=True)

        def _row(parent, var, title, detail, warn=False, locked=False):
            card = tk.Frame(parent, bg=SURF, padx=14, pady=11)
            card.pack(fill=tk.X, pady=3)
            accent = WARN if warn else BORD2
            tk.Frame(card, bg=accent, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
            if locked:
                var.set(True)
            self._mk_check(card, var, bg=SURF, locked=locked).pack(side=tk.LEFT, padx=(0, 2))
            mid = tk.Frame(card, bg=SURF)
            mid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            tk.Label(mid, text=title, bg=SURF, fg=WARN if warn else TEXT,
                     font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(anchor=tk.W)
            tk.Label(mid, text=detail, bg=SURF, fg=TEXT2,
                     font=("Segoe UI", 9), anchor=tk.W,
                     wraplength=400).pack(anchor=tk.W, pady=(2, 0))
            if warn:
                tk.Label(card, text="⚠", bg=SURF, fg=WARN,
                         font=("Segoe UI", 12)).pack(side=tk.RIGHT, padx=10)

        tk.Label(f, text="ALWAYS REMOVED", bg=BG, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 4))
        _row(f, always_var,
             "Shortcuts & registry entries",
             "Desktop shortcut, Windows startup entry, install registry key",
             locked=True)

        tk.Frame(f, bg=BG, height=6).pack()
        tk.Label(f, text="OPTIONAL — SELECT WHAT ELSE TO REMOVE", bg=BG, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 4))
        _row(f, self.uninst_models,
             f"Downloaded AI model  ({MODEL})",
             "Removes model from Ollama storage — frees ~400 MB", warn=True)
        _row(f, self.uninst_pkgs,
             "Installed Python packages",
             "Uninstalls all packages added by this app — may affect other Python tools", warn=True)
        _row(f, self.uninst_logs,
             "Application logs",
             "Removes installer.log and app.log")
        _row(f, self.uninst_settings,
             "User settings & database",
             "Removes config/app_data.db — chat history and preferences lost permanently", warn=True)

        tk.Frame(f, bg=BG).pack(expand=True)
        warn_box = tk.Frame(f, bg="#14050a", padx=16, pady=10)
        warn_box.pack(fill=tk.X)
        tk.Label(warn_box,
                 text="⚠  Items marked with ⚠ above will permanently delete user data "
                      "and cannot be recovered.",
                 bg="#14050a", fg=WARN, font=("Segoe UI", 9),
                 wraplength=560, justify=tk.LEFT).pack(anchor=tk.W)

    def _confirm_uninstall(self):
        if not messagebox.askyesno(
            "Confirm Uninstall",
            f"Are you sure you want to uninstall {APPNAME}?\n\n"
            "This action cannot be undone.",
            icon="warning", parent=self,
        ):
            return
        self._navigate("progress")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: PROGRESS
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_progress(self):
        self._btn_cancel.config(state=tk.DISABLED)
        self._btn_back.config(state=tk.DISABLED)
        self._btn_next.config(state=tk.DISABLED, text="Working…",
                              bg=SURF2, fg=MUTED)

        titles = {"install":   "Installing Components",
                  "repair":    "Repairing Installation",
                  "uninstall": "Uninstalling Application"}
        subs   = {"install":   "Please wait — do not close this window.",
                  "repair":    "Fixing detected issues…",
                  "uninstall": "Removing application components…"}
        pb_style = {"install":   "Green.TProgressbar",
                    "repair":    "Blue.TProgressbar",
                    "uninstall": "Red.TProgressbar"}.get(self._progress_mode, "Green.TProgressbar")

        f = self._page_frame(padx=36)
        self._page_title(f,
                         titles.get(self._progress_mode, "Working…"),
                         subs.get(self._progress_mode, ""))

        tasks = self._build_tasks()
        self._prog_vals   = {}
        self._comp_status = {}

        for cid, label in tasks:
            row = tk.Frame(f, bg=BG)
            row.pack(fill=tk.X, pady=6)

            # Label column (fixed width)
            tk.Label(row, text=label, bg=BG, fg=TEXT,
                     font=("Segoe UI", 10), width=28,
                     anchor=tk.W).pack(side=tk.LEFT)

            # Status label
            sv = tk.StringVar(value="Waiting…")
            cv = tk.StringVar(value=TEXT2)
            self._comp_status[cid] = (sv, cv)

            slbl = tk.Label(row, textvariable=sv, bg=BG, fg=TEXT2,
                            font=("Segoe UI", 9), width=18, anchor=tk.W)
            slbl.pack(side=tk.LEFT, padx=(4, 8))
            cv.trace_add("write", lambda *a, lbl=slbl, v=cv: lbl.config(fg=v.get()))

            # Progress bar
            pv = tk.IntVar(value=0)
            self._prog_vals[cid] = pv
            ttk.Progressbar(row, variable=pv, maximum=100,
                            style=pb_style, length=200).pack(side=tk.LEFT)

        tk.Frame(f, bg=BORD2, height=1).pack(fill=tk.X, pady=(16, 10))
        tk.Label(f, text="Installation Log", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        log_outer = tk.Frame(f, bg=BORD2, padx=1, pady=1)
        log_outer.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        log_inner = tk.Frame(log_outer, bg=DARK)
        log_inner.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(
            log_inner, bg=DARK, fg=TEXT2, font=("Consolas", 8),
            relief=tk.FLAT, state=tk.DISABLED, wrap=tk.WORD, padx=12, pady=10,
        )
        lsb = ttk.Scrollbar(log_inner, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=lsb.set)
        lsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        self._worker = threading.Thread(target=self._dispatch, daemon=True)
        self._worker.start()

    def _build_tasks(self):
        if self._progress_mode == "install":
            t = []
            if self.do_pkgs.get():    t.append(("pkgs",   "Core Python packages"))
            if self.do_audio.get():   t.append(("audio",  "PyAudio (voice)"))
            if self.do_ollama.get():  t.append(("ollama", "Ollama AI engine"))
            if self.do_model.get():   t.append(("model",  f"Model: {MODEL}"))
            if self.do_shortcut.get() or self.do_startup.get():
                t.append(("shortcuts", "Shortcuts & startup"))
            t.append(("record", "Saving install record"))
            return t or [("noop", "Nothing selected")]

        if self._progress_mode == "repair":
            if not self._repair_issues:
                return [("noop", "No issues found")]
            return [(i["id"], i["label"]) for i in self._repair_issues]

        if self._progress_mode == "uninstall":
            t = [("stop",      "Stopping running processes"),
                 ("shortcuts", "Removing shortcuts & registry")]
            if self.uninst_models.get():   t.append(("models",   f"Model {MODEL}"))
            if self.uninst_pkgs.get():     t.append(("pkgs",     "Python packages"))
            if self.uninst_logs.get():     t.append(("logs",     "Log files"))
            if self.uninst_settings.get(): t.append(("settings", "User data"))
            t.append(("record", "Install record"))
            return t

        return [("noop", "Nothing to do")]

    # ── Worker dispatch ───────────────────────────────────────────────────────
    def _dispatch(self):
        try:
            {"install":   self._w_install,
             "repair":    self._w_repair,
             "uninstall": self._w_uninstall}.get(self._progress_mode, lambda: None)()
        except Exception as exc:
            self._q_log(f"[ERROR] {exc}")
            self._q_done([str(exc)])

    def _w_install(self):
        errors = []
        log  = self._q_log
        prog = self._q_prog
        st   = self._q_st

        if "noop" in self._prog_vals:
            st("noop", "Nothing selected", MUTED)
            self._q_done([])
            return

        if self.do_pkgs.get():
            st("pkgs", "Installing…", BLUE)
            log("── Core packages ──────────────────────────")
            ok = pip_install([p for p, _ in CORE_PKGS], log)
            prog("pkgs", 100)
            st("pkgs", "✓  Done" if ok else "⚠  Partial", OK if ok else WARN)
            if not ok: errors.append("Some packages failed")

        if self.do_audio.get():
            st("audio", "Installing…", BLUE)
            log("── PyAudio ───────────────────────────────────")
            ok = install_pyaudio(log)
            prog("audio", 100)
            st("audio", "✓  Done" if ok else "✗  Failed (needs MSVC)", OK if ok else ERR)
            if not ok: errors.append("PyAudio failed — voice disabled")

        if self.do_ollama.get():
            log("── Ollama ─────────────────────────────────────")
            if check_ollama():
                prog("ollama", 100)
                st("ollama", "✓  Already installed", OK)
            else:
                st("ollama", "Downloading…", BLUE)
                ok = install_ollama(log, lambda v: prog("ollama", v))
                st("ollama", "✓  Done" if ok else "✗  Failed", OK if ok else ERR)
                if not ok: errors.append("Ollama install failed")

        if self.do_model.get():
            log(f"── Model: {MODEL} ─────────────────────────")
            if check_model(MODEL):
                prog("model", 100)
                st("model", "✓  Already ready", OK)
            elif not check_ollama():
                st("model", "✗  Ollama missing", ERR)
                errors.append(f"Cannot pull {MODEL} — Ollama not installed")
            else:
                st("model", "Downloading…", BLUE)
                ok = pull_model(MODEL, log, lambda v: prog("model", v))
                st("model", "✓  Ready" if ok else "✗  Failed", OK if ok else ERR)
                if not ok: errors.append(f"Model {MODEL} failed")

        if "shortcuts" in self._prog_vals:
            log("── Shortcuts ──────────────────────────────────")
            st("shortcuts", "Creating…", BLUE)
            create_shortcuts(Path(self.install_dir.get()), log)
            prog("shortcuts", 100)
            st("shortcuts", "✓  Done", OK)

        if "record" in self._prog_vals:
            st("record", "Saving…", BLUE)
            comps = {"pkgs": self.do_pkgs.get(), "audio": self.do_audio.get(),
                     "ollama": self.do_ollama.get(), "model": self.do_model.get()}
            save_install_record(Path(self.install_dir.get()), comps)
            prog("record", 100)
            st("record", "✓  Done", OK)
            log("Install record saved to registry.")

        self._q_done(errors)

    def _w_repair(self):
        errors = []
        log = self._q_log; prog = self._q_prog; st = self._q_st

        if "noop" in self._prog_vals:
            st("noop", "✓  Healthy", OK); self._q_done([]); return

        for issue in self._repair_issues:
            cid = issue["id"]; fix = issue.get("fix", cid)
            if cid not in self._prog_vals: continue
            st(cid, "Repairing…", BLUE)
            ok = False
            if fix == "pkgs":
                log("── Packages ────────────────────────────────────")
                ok = pip_install([p for p, _ in CORE_PKGS], log)
            elif fix == "ollama":
                log("── Ollama ──────────────────────────────────────")
                ok = install_ollama(log, lambda v: prog(cid, v))
            elif fix == "model":
                log(f"── Model {MODEL} ────────────────────────")
                ok = pull_model(MODEL, log, lambda v: prog(cid, v))
            elif fix == "audio":
                log("── PyAudio ────────────────────────────────────")
                ok = install_pyaudio(log)
            elif fix == "shortcut":
                log("── Shortcuts ──────────────────────────────────")
                create_shortcuts(Path(self.install_dir.get()), log); ok = True
            elif fix == "files":
                log("App source files cannot be auto-restored.")
                log("Please re-download from the project repository.")
                errors.append("Missing app files — re-download required")
            prog(cid, 100)
            st(cid, "✓  Fixed" if ok else "✗  Failed", OK if ok else ERR)
            if not ok and fix not in ("files", "audio"):
                errors.append(f"{cid} repair failed")
        self._q_done(errors)

    def _w_uninstall(self):
        errors = []
        log = self._q_log; prog = self._q_prog; st = self._q_st

        def done(cid, txt=None, clr=OK):
            prog(cid, 100); st(cid, txt or "✓  Done", clr)

        st("stop", "Stopping…", BLUE)
        log("── Stopping processes ──────────────────────────")
        kill_app(log); done("stop")

        st("shortcuts", "Removing…", BLUE)
        log("── Shortcuts & registry ────────────────────────")
        remove_shortcuts(log); done("shortcuts")

        if "models" in self._prog_vals:
            st("models", "Removing…", BLUE)
            log("── AI model ──────────────────────────────────────")
            remove_model(MODEL, log); done("models")

        if "pkgs" in self._prog_vals:
            st("pkgs", "Removing…", BLUE)
            log("── Python packages ───────────────────────────────")
            pip_uninstall([p for p, _ in CORE_PKGS], log); done("pkgs")

        if "logs" in self._prog_vals:
            st("logs", "Removing…", BLUE)
            log("── Log files ──────────────────────────────────────")
            for lf in (ROOT / "installer.log", ROOT / "logs" / "app.log"):
                try:
                    if lf.exists(): lf.unlink(); log(f"Removed: {lf.name}")
                except Exception as e: log(f"{lf.name}: {e}")
            done("logs")

        if "settings" in self._prog_vals:
            st("settings", "Removing…", BLUE)
            log("── User data ──────────────────────────────────────")
            db = ROOT / "config" / "app_data.db"
            try:
                if db.exists(): db.unlink(); log("Removed: app_data.db")
            except Exception as e: log(f"app_data.db: {e}")
            done("settings")

        if "record" in self._prog_vals:
            st("record", "Removing…", BLUE)
            log("── Install record ──────────────────────────────────")
            reg_del_val(REG_RUN, "AISystemOptimizer")
            reg_del_key(REG_KEY)
            log("Registry cleaned.")
            done("record")

        self._q_done(errors)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE: DONE
    # ══════════════════════════════════════════════════════════════════════════
    def _pg_done(self):
        mode = self._progress_mode
        ok   = len(self._errors) == 0

        self._btn_cancel.config(state=tk.DISABLED)
        self._btn_back.config(state=tk.DISABLED)
        if mode == "uninstall":
            self._btn_next.config(text="Close", bg=GRN, fg=TEXT,
                                  state=tk.NORMAL, command=self.destroy)
        elif ok:
            self._btn_next.config(text="Launch App  →", bg=GRN, fg=TEXT,
                                  state=tk.NORMAL, command=self._launch)
        else:
            self._btn_next.config(text="Close", bg=GRN, fg=TEXT,
                                  state=tk.NORMAL, command=self.destroy)

        f = self._page_frame(padx=50, pady=26)

        icon_c = OK if ok else WARN
        icon_t = "✓" if ok else "⚠"
        tk.Label(f, text=icon_t, bg=BG, fg=icon_c,
                 font=("Segoe UI", 54)).pack()

        titles = {("install",   True):  "Installation Complete!",
                  ("install",   False): "Installed with Warnings",
                  ("repair",    True):  "Repair Complete!",
                  ("repair",    False): "Repaired with Warnings",
                  ("uninstall", True):  "Uninstall Complete",
                  ("uninstall", False): "Uninstall Finished"}
        subs   = {("install",   True):  "All selected components installed successfully.",
                  ("install",   False): "Setup completed. Some items may need attention.",
                  ("repair",    True):  "All detected issues have been resolved.",
                  ("repair",    False): "Repair finished with some unresolved issues.",
                  ("uninstall", True):  f"{APPNAME} has been removed from this system.",
                  ("uninstall", False): "Uninstall finished — check the log for details."}

        tk.Label(f, text=titles.get((mode, ok), "Done"),
                 bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(pady=(6, 3))
        tk.Label(f, text=subs.get((mode, ok), ""),
                 bg=BG, fg=TEXT2, font=("Segoe UI", 10)).pack()

        if self._errors:
            tk.Frame(f, bg=BG, height=8).pack()
            for err in self._errors:
                row = tk.Frame(f, bg=SURF, padx=16, pady=9)
                row.pack(fill=tk.X, pady=2)
                tk.Frame(row, bg=WARN, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
                tk.Label(row, text=f"⚠  {err}", bg=SURF, fg=WARN,
                         font=("Segoe UI", 9), anchor=tk.W,
                         wraplength=480).pack(anchor=tk.W)

        tk.Frame(f, bg=BG).pack(expand=True)

        if mode != "uninstall":
            strip = tk.Frame(f, bg=SURF, padx=20, pady=16)
            strip.pack(fill=tk.X)
            path_str = str(ROOT)
            if len(path_str) > 64:
                path_str = path_str[:61] + "…"
            for k, v in [
                ("Version",   f"v{VERSION}  (Build {BUILD})"),
                ("AI model",  MODEL),
                ("Location",  path_str),
                ("Log file",  LOG_FILE.name),
            ]:
                row = tk.Frame(strip, bg=SURF)
                row.pack(fill=tk.X, pady=3)
                tk.Label(row, text=k, bg=SURF, fg=MUTED,
                         font=("Segoe UI", 9), width=14, anchor=tk.W).pack(side=tk.LEFT)
                tk.Label(row, text=v, bg=SURF, fg=TEXT,
                         font=("Segoe UI", 9), anchor=tk.W).pack(side=tk.LEFT)

    def _launch(self):
        app_py = ROOT / "app.py"
        if app_py.exists():
            try:
                pw = Path(sys.executable).with_name("pythonw.exe")
                if not pw.exists(): pw = Path(sys.executable)
                subprocess.Popen([str(pw), str(app_py)], cwd=str(ROOT))
            except Exception as e:
                _log.error(f"Launch: {e}")
        self.destroy()

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    args = sys.argv[1:]
    if "--silent" in args:
        if "--uninstall" in args: run_silent("uninstall")
        elif "--repair"  in args: run_silent("repair")
        else:                     run_silent("install")
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    InstallerApp().mainloop()

if __name__ == "__main__":
    main()
