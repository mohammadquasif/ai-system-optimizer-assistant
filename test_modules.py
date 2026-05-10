import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, '.')

from services.idle_watcher import IdleWatcher
print("IdleWatcher import OK")

from ui.command_input import CommandInputWidget, COMMAND_CHIPS
print(f"CommandInputWidget OK - {len(COMMAND_CHIPS)} chips defined")

from cleanup.cleanup_engine import CleanupEngine
import inspect
params = list(inspect.signature(CleanupEngine.run).parameters.keys())
print(f"CleanupEngine.run has {len(params)} params")
for p in params:
    print(f"  - {p}")

from ai.ollama_manager import MODEL_PRIORITY
names = [m["name"] for m in MODEL_PRIORITY]
print(f"Model priority: {names}")

print("All new modules validated OK!")
