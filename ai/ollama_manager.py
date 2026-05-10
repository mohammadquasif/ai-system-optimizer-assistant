"""
Ollama Lifecycle Manager
------------------------
Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
License: Personal Use Only (Non-Commercial)

Smart model detection — USES INSTALLED MODELS FIRST.
Only downloads if nothing compatible is installed.
"""

import os
import sys
import time
import json
import shutil
import logging
import platform
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Optional, Callable, Tuple
import requests
import psutil

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

OLLAMA_API_BASE      = "http://localhost:11434"
OLLAMA_WIN_INSTALLER = "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"

# Preferred models — smallest first (max 1.5b)
# These are the models we PREFER to use or install
PREFERRED_MODELS = [
    "qwen2.5:0.5b",
    "qwen2.5:1b",
    "llama3.2:1b",
    "qwen2.5:1.5b",
]

# Full model priority list with metadata
MODEL_PRIORITY = [
    {
        "name": "qwen2.5:0.5b",
        "min_ram_gb": 2,
        "requires_gpu": False,
        "size_gb": 0.4,
        "description": "Ultra-fast 0.5B — lowest RAM usage (recommended for all systems)",
    },
    {
        "name": "qwen2.5:1b",
        "min_ram_gb": 2,
        "requires_gpu": False,
        "size_gb": 0.8,
        "description": "Qwen2.5 1B — best balance of speed and quality",
    },
    {
        "name": "llama3.2:1b",
        "min_ram_gb": 2,
        "requires_gpu": False,
        "size_gb": 0.9,
        "description": "Llama 3.2 1B — excellent quality at 1B",
    },
    {
        "name": "qwen2.5:1.5b",
        "min_ram_gb": 3,
        "requires_gpu": False,
        "size_gb": 1.0,
        "description": "Qwen2.5 1.5B — maximum quality within 1.5B limit",
    },
]

OFFLINE_INSTALLER_PATHS = [
    Path(__file__).parent.parent / "installer" / "ollama" / "OllamaSetup.exe",
    Path(os.environ.get("USERPROFILE", "")) / "Downloads" / "OllamaSetup.exe",
]


# ─────────────────────────────────────────────────────────────────
# SYSTEM PROFILE
# ─────────────────────────────────────────────────────────────────

class SystemProfile:
    """Detect hardware capabilities to auto-select the right model."""

    def __init__(self):
        self.ram_total_gb = psutil.virtual_memory().total / 1e9
        self.ram_free_gb  = psutil.virtual_memory().available / 1e9
        self.has_gpu      = self._detect_gpu()
        self.has_internet  = self._check_internet()
        self.cpu_cores    = psutil.cpu_count(logical=True)
        self.platform     = platform.system()

    @staticmethod
    def _detect_gpu() -> bool:
        for cmd in [["nvidia-smi"], ["wmic", "path", "win32_VideoController", "get", "name"]]:
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _check_internet() -> bool:
        for host in ["8.8.8.8", "1.1.1.1"]:
            try:
                requests.get(f"http://{host}", timeout=3)
                return True
            except Exception:
                pass
        return False

    def select_best_model(self) -> dict:
        """
        SMART SELECTION:
        1. Check what's already installed → use that if it's in our preferred list
        2. If nothing installed → select best to download (smallest that fits RAM)
        """
        # First: check installed models
        try:
            installed = OllamaManager.list_installed_models()
            if installed:
                # Check if any PREFERRED model is already installed
                for preferred in PREFERRED_MODELS:
                    for inst in installed:
                        if inst.startswith(preferred.split(":")[0]) or inst == preferred:
                            # Found a match — use it
                            meta = next((m for m in MODEL_PRIORITY if m["name"] == preferred), None)
                            if meta:
                                logger.info(f"Using already-installed model: {inst}")
                                return meta
                # No preferred model installed but something else is — use first installed
                # if it's reasonably small (not a huge model)
                first = installed[0]
                logger.info(f"Using existing installed model: {first}")
                return {
                    "name": first,
                    "min_ram_gb": 2,
                    "requires_gpu": False,
                    "size_gb": 1.0,
                    "description": f"Existing installed model: {first}",
                }
        except Exception:
            pass

        # Nothing installed — pick smallest that fits RAM
        for model in MODEL_PRIORITY:
            if self.ram_free_gb >= model["min_ram_gb"]:
                return model
        return MODEL_PRIORITY[0]

    def summary(self) -> str:
        return (
            f"RAM: {self.ram_total_gb:.1f} GB total / {self.ram_free_gb:.1f} GB free | "
            f"GPU: {'Yes' if self.has_gpu else 'No'} | "
            f"Internet: {'Yes' if self.has_internet else 'No'} | "
            f"CPU: {self.cpu_cores} cores"
        )


# ─────────────────────────────────────────────────────────────────
# STEP RESULT
# ─────────────────────────────────────────────────────────────────

class SetupStep:
    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        self.message = ""
        self.progress = 0

    def ok(self, msg=""):
        self.status = "done"
        self.message = msg
        self.progress = 100

    def fail(self, msg=""):
        self.status = "failed"
        self.message = msg

    def skip(self, msg=""):
        self.status = "skipped"
        self.message = msg
        self.progress = 100

    def running(self, msg="", pct=0):
        self.status = "running"
        self.message = msg
        self.progress = pct


# ─────────────────────────────────────────────────────────────────
# OLLAMA MANAGER
# ─────────────────────────────────────────────────────────────────

class OllamaManager:
    """
    Smart Ollama lifecycle manager.
    Uses installed models first. Only downloads if nothing is available.
    """

    def __init__(
        self,
        step_cb:     Optional[Callable[[SetupStep], None]] = None,
        progress_cb: Optional[Callable[[str, int], None]]  = None,
        log_cb:      Optional[Callable[[str], None]]       = None,
    ):
        self.step_cb     = step_cb     or (lambda s: None)
        self.progress_cb = progress_cb or (lambda m, p: None)
        self.log_cb      = log_cb      or (lambda m: None)
        self.profile     = SystemProfile()
        self.selected_model: Optional[dict] = None
        self._steps: list[SetupStep] = []

    def _log(self, msg: str):
        logger.info(msg)
        self.log_cb(msg)

    def _emit(self, step: SetupStep):
        self.step_cb(step)

    # ─── PUBLIC: Full Auto-Setup ───────────────────────────────────

    def auto_setup(self) -> Tuple[bool, str]:
        """
        Smart auto-setup:
        - If Ollama running AND compatible model installed → mark all done, return immediately
        - Otherwise run full setup pipeline
        """
        self._log(f"System: {self.profile.summary()}")

        # ── FAST PATH: Already fully ready ────────────────────────
        if self.is_api_running():
            installed = self.list_installed_models()
            self._log(f"Installed models: {installed}")
            if installed:
                self.selected_model = self.profile.select_best_model()
                self._log(f"Using model: {self.selected_model['name']}")
                # Mark all steps as done/skipped quickly
                for name in [
                    "Checking Ollama installation",
                    "Starting Ollama service",
                    "Verifying API connection",
                    "Checking model availability",
                    "Pulling AI model",
                    "Final verification",
                ]:
                    step = SetupStep(name)
                    if name == "Pulling AI model":
                        step.skip(f"Model '{self.selected_model['name']}' already installed")
                    else:
                        step.ok("Already ready")
                    self._emit(step)
                    time.sleep(0.05)  # Small delay so UI can render each step
                return True, f"Ready — using model: {self.selected_model['name']}"

        # ── FULL SETUP PATH ────────────────────────────────────────
        self.selected_model = self.profile.select_best_model()
        self._log(f"Target model: {self.selected_model['name']}")

        steps_fns = [
            ("Checking Ollama installation",  self._step_check_installed),
            ("Starting Ollama service",        self._step_start_service),
            ("Verifying API connection",       self._step_verify_api),
            ("Checking model availability",    self._step_check_model),
            ("Pulling AI model",               self._step_pull_model),
            ("Final verification",             self._step_final_verify),
        ]

        for name, fn in steps_fns:
            step = SetupStep(name)
            self._steps.append(step)
            step.running(f"Starting: {name}...")
            self._emit(step)
            try:
                fn(step)
            except Exception as e:
                step.fail(str(e))
                self._log(f"[ERROR] {name}: {e}")
            self._emit(step)
            if step.status == "failed":
                return False, f"Failed at: {name} — {step.message}"

        return True, f"Ready — model: {self.selected_model['name']}"

    # ─── STEPS ────────────────────────────────────────────────────

    def _step_check_installed(self, step: SetupStep):
        if self.is_installed():
            step.ok("Ollama installed")
            return

        step.running("Installing Ollama...", 10)
        self._emit(step)

        for offline_path in OFFLINE_INSTALLER_PATHS:
            if offline_path.exists():
                step.running("Installing from offline package...", 30)
                self._emit(step)
                if self._install_exe(str(offline_path)):
                    step.ok("Installed from offline package")
                    return
                else:
                    step.fail("Offline installer failed.")
                    return

        if not self.profile.has_internet:
            step.fail("No internet + no offline installer. Place OllamaSetup.exe in installer/ollama/")
            return

        dest = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
        step.running("Downloading Ollama...", 20)
        self._emit(step)

        def dl_prog(pct):
            step.running(f"Downloading Ollama... {pct}%", pct // 2)
            self._emit(step)

        if self._download_file(OLLAMA_WIN_INSTALLER, str(dest), dl_prog):
            step.running("Installing Ollama...", 60)
            self._emit(step)
            if self._install_exe(str(dest)):
                time.sleep(3)
                step.ok("Ollama installed")
            else:
                step.fail("Installation failed.")
        else:
            step.fail("Download failed.")

    def _step_start_service(self, step: SetupStep):
        if self.is_api_running():
            step.ok("Service running")
            return
        step.running("Starting service...", 30)
        self._emit(step)
        self._start_service()
        for i in range(10):
            time.sleep(1.5)
            step.running(f"Waiting... ({i+1}/10)", 30 + i * 5)
            self._emit(step)
            if self.is_api_running():
                step.ok("Service started")
                return
        step.fail("Service did not start.")

    def _step_verify_api(self, step: SetupStep):
        if self.is_api_running():
            step.ok(f"API ready at {OLLAMA_API_BASE}")
        else:
            step.fail(f"Cannot reach {OLLAMA_API_BASE}")

    def _step_check_model(self, step: SetupStep):
        model_name = self.selected_model["name"]
        installed  = self.list_installed_models()
        self._log(f"Installed models: {installed}")
        if any(m.startswith(model_name.split(":")[0]) for m in installed):
            step.ok(f"Model '{model_name}' installed")
        else:
            step.ok(f"Model '{model_name}' not found — will pull")

    def _step_pull_model(self, step: SetupStep):
        model_name = self.selected_model["name"]
        installed  = self.list_installed_models()

        if any(m.startswith(model_name.split(":")[0]) for m in installed):
            step.skip(f"'{model_name}' already installed")
            return

        if not self.profile.has_internet:
            models_dir = Path(__file__).parent.parent / "models"
            if models_dir.exists() and any(models_dir.iterdir()):
                step.ok("Using bundled offline model")
                return
            step.fail("No internet + no model installed.")
            return

        size_text = f"{self.selected_model['size_gb']} GB"
        step.running(f"Pulling {model_name} ({size_text})...", 5)
        self._emit(step)

        if self._pull_model(model_name, step):
            step.ok(f"Model '{model_name}' ready")
        else:
            # Try fallback
            fallback = next((m for m in MODEL_PRIORITY if m["name"] != model_name), None)
            if fallback:
                self.selected_model = fallback
                step.running(f"Trying fallback: {fallback['name']}...", 10)
                self._emit(step)
                if self._pull_model(fallback["name"], step):
                    step.ok(f"Fallback '{fallback['name']}' ready")
                else:
                    step.fail("Could not pull any model.")
            else:
                step.fail(f"Failed to pull '{model_name}'.")

    def _step_final_verify(self, step: SetupStep):
        step.running("Verifying AI response...", 50)
        self._emit(step)
        try:
            r = requests.post(
                f"{OLLAMA_API_BASE}/api/generate",
                json={"model": self.selected_model["name"], "prompt": "Say OK", "stream": False},
                timeout=30,
            )
            if r.status_code == 200:
                step.ok("AI verified — Everything ready!")
            else:
                step.fail(f"HTTP {r.status_code}")
        except Exception as e:
            step.fail(f"Verify failed: {e}")

    # ─── UTILITIES ────────────────────────────────────────────────

    @staticmethod
    def is_installed() -> bool:
        return shutil.which("ollama") is not None

    @staticmethod
    def is_api_running() -> bool:
        try:
            r = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_installed_models() -> list[str]:
        try:
            r = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=5)
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
        return []

    @staticmethod
    def _start_service():
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.error(f"_start_service error: {e}")

    @staticmethod
    def _install_exe(path: str) -> bool:
        try:
            return subprocess.run([path, "/S"], timeout=180).returncode == 0
        except Exception as e:
            logger.error(f"_install_exe error: {e}")
            return False

    @staticmethod
    def _download_file(url: str, dest: str, progress_cb=None) -> bool:
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and progress_cb:
                        progress_cb(int(downloaded * 100 / total))
            return True
        except Exception as e:
            logger.error(f"_download_file error: {e}")
            return False

    def _pull_model(self, model_name: str, step: SetupStep) -> bool:
        try:
            with requests.post(
                f"{OLLAMA_API_BASE}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=900,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    status = data.get("status", "")
                    total  = data.get("total", 0)
                    done   = data.get("completed", 0)
                    pct    = int((done / total) * 90) if total > 0 else 0
                    msg    = f"Pulling {model_name}: {status} ({pct}%)"
                    step.running(msg, 5 + pct)
                    self._log(msg)
                    self._emit(step)
                    if status == "success":
                        return True
        except Exception as e:
            logger.error(f"_pull_model error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
# BACKGROUND RUNNER — uses Qt signals via callbacks
# ─────────────────────────────────────────────────────────────────

class OllamaSetupRunner:
    """Run OllamaManager.auto_setup() in a QThread-safe way."""

    def __init__(self, step_cb=None, log_cb=None, done_cb=None):
        self.manager = OllamaManager(step_cb=step_cb, log_cb=log_cb)
        self.done_cb = done_cb
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        success, message = self.manager.auto_setup()
        if self.done_cb:
            self.done_cb(success, message, self.manager.selected_model)
