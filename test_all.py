"""
Full System Test — AI System Optimizer Assistant
Tests: imports, model detection, AI chat, voice TTS
"""
import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []

def check(label, fn):
    try:
        result = fn()
        status = "PASS" if result else "WARN"
        results.append((status, label, str(result)))
        print(f"  [{status}] {label}: {result}")
        return result
    except Exception as e:
        results.append(("FAIL", label, str(e)))
        print(f"  [FAIL] {label}: {e}")
        return False

print("=" * 60)
print("  AI System Optimizer — Full Feature Test")
print("=" * 60)
print()

# 1. Core imports
print("[1] Core Module Imports")
check("ollama_manager", lambda: __import__("ai.ollama_manager") and "OK")
check("cleanup_engine", lambda: __import__("cleanup.cleanup_engine") and "OK")
check("idle_watcher", lambda: __import__("services.idle_watcher") and "OK")
check("ai_service", lambda: __import__("ai.ai_service") and "OK")
check("voice_service", lambda: __import__("services.voice_service") and "OK")
check("command_input_widget", lambda: __import__("ui.command_input") and "OK")
print()

# 2. Ollama detection
print("[2] Ollama & Model Detection")
from ai.ollama_manager import OllamaManager, SystemProfile, PREFERRED_MODELS
check("Ollama API running", OllamaManager.is_api_running)
installed = OllamaManager.list_installed_models()
check("Models installed", lambda: installed)
print(f"    Installed models: {installed}")

profile = SystemProfile()
best = profile.select_best_model()
check("Best model selected", lambda: best["name"])
print(f"    Best model: {best['name']} — {best['description']}")
print(f"    RAM: {profile.ram_total_gb:.1f}GB | GPU: {profile.has_gpu} | Internet: {profile.has_internet}")
print()

# 3. AI settings (what app.py would set)
print("[3] AI Settings Configuration")
from config.settings import get_setting, set_setting
preferred_installed = None
for pref in PREFERRED_MODELS:
    for inst in installed:
        if inst.startswith(pref.split(":")[0]) or inst == pref:
            preferred_installed = inst
            break
    if preferred_installed:
        break

if preferred_installed:
    set_setting("ai_provider", "ollama")
    set_setting("ollama_model", preferred_installed)
    check("ai_provider set", lambda: get_setting("ai_provider") == "ollama")
    check("ollama_model set", lambda: get_setting("ollama_model") == preferred_installed)
    print(f"    Model in settings: {get_setting('ollama_model')}")
else:
    print("  [WARN] No preferred model found in installed list")
print()

# 4. AI Chat
print("[4] AI Chat Test")
from ai.ai_service import AIService, OllamaProvider
AIService._instance = None  # Reset singleton to pick up new settings
service = AIService.get_instance()
check("AI configured", lambda: service.is_configured)
check("AI available (Ollama running)", lambda: service.is_available)

if service.is_configured and service.is_available:
    print("  Sending test message to AI...")
    response = service.chat("Say 'SYSTEM TEST OK' and nothing else.", history=[])
    check("AI responded", lambda: len(response) > 0)
    print(f"    AI response: {response[:100]}")
else:
    print("  [SKIP] AI not available for chat test")
print()

# 5. Voice TTS
print("[5] Voice TTS Test")
try:
    import pyttsx3
    engine = pyttsx3.init()
    check("pyttsx3 TTS init", lambda: engine is not None and "OK")
    engine.stop()
except Exception as e:
    results.append(("FAIL", "pyttsx3 TTS", str(e)))
    print(f"  [FAIL] pyttsx3: {e}")
print()

# 6. Voice STT check
print("[6] Voice STT Dependencies")
check("speech_recognition", lambda: __import__("speech_recognition") and "OK")
try:
    import pyaudio
    check("pyaudio", lambda: "OK")
except ImportError:
    results.append(("WARN", "pyaudio", "Not installed — run: pip install pipwin && pipwin install pyaudio"))
    print("  [WARN] pyaudio: Not installed (voice commands will be disabled)")
    print("         Fix: pip install pipwin && pipwin install pyaudio")
print()

# 7. Cleanup engine
print("[7] Cleanup Engine")
from cleanup.cleanup_engine import CleanupEngine, estimate_cleanup_size
engine = CleanupEngine()
size = estimate_cleanup_size()
check("Cleanup estimate", lambda: size >= 0 and f"{size/1e6:.1f} MB can be freed")
import inspect
params = list(inspect.signature(CleanupEngine.run).parameters.keys())
check("Cleanup tasks count", lambda: f"{len(params)-1} cleanup tasks available")
print()

# 8. Idle watcher
print("[8] Idle Watcher")
from services.idle_watcher import IdleWatcher
fired = []
watcher = IdleWatcher(idle_minutes=99, countdown_seconds=1, close_cb=lambda: fired.append(1))
watcher.start()
import time; time.sleep(0.2)
watcher.reset()
watcher.stop()
check("IdleWatcher starts and stops", lambda: watcher._running == False and "OK")
print()

# Summary
print("=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
warned = sum(1 for r in results if r[0] == "WARN")
failed = sum(1 for r in results if r[0] == "FAIL")
print(f"  RESULTS: {passed} PASSED | {warned} WARNINGS | {failed} FAILED")
print("=" * 60)
for status, label, detail in results:
    if status == "FAIL":
        print(f"  [FAIL] {label}: {detail}")
if failed == 0:
    print()
    print("  All critical systems operational!")
    print("  Run: python app.py")
print()
