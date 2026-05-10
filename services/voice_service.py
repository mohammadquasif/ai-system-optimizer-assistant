"""
Voice Assistant Service - pyttsx3 (TTS) + SpeechRecognition (STT)
Runs in a dedicated background thread to avoid blocking the UI.

VoiceCommandHandler: full command interpreter with navigation callbacks.
"""

import threading
import logging
import time
import queue
from typing import Optional, Callable
from datetime import datetime
from config.settings import get_setting

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    Text-to-Speech + Speech-to-Text assistant.
    All audio operations happen on a dedicated thread.
    """

    def __init__(self, on_command: Optional[Callable[[str], None]] = None):
        self._tts_queue: queue.Queue = queue.Queue()
        self._on_command = on_command
        self._running = False
        self._engine = None
        self._listening = False
        self._tts_thread: Optional[threading.Thread] = None
        self._stt_thread: Optional[threading.Thread] = None
        self._enabled = get_setting("voice_enabled", "true") == "true"

    # ─────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────

    def start(self):
        if self._running:
            return  # already running
        if not self._enabled:
            logger.info("Voice assistant disabled in settings.")
            return
        self._running = True
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True)
        self._tts_thread.start()
        logger.info("VoiceAssistant TTS thread started.")

    def stop(self):
        self._running = False
        self._listening = False
        self._tts_queue.put(None)  # Sentinel to unblock queue
        logger.info("VoiceAssistant stopped.")

    def speak(self, text: str, priority: bool = False):
        """Enqueue text for TTS output."""
        if not self._enabled:
            return
        if priority:
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except queue.Empty:
                    break
        self._tts_queue.put(text)
        logger.debug(f"TTS queued: {text[:80]}")

    def greet(self, name: str = "there"):
        """Speak a context-aware startup greeting."""
        hour = datetime.now().hour
        period = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"
        self.speak(
            f"Good {period} {name}. Your AI System Optimizer is ready. "
            "System monitoring is active.",
            priority=True,
        )

    def start_listening(self, callback: Optional[Callable[[str], None]] = None):
        """Start STT listening in background thread (idempotent)."""
        if self._listening:
            logger.debug("[STT] Already listening, skipping start.")
            return
        cb = callback or self._on_command
        self._listening = True
        self._stt_thread = threading.Thread(target=self._stt_loop, args=(cb,), daemon=True)
        self._stt_thread.start()
        logger.info("[STT] Listening thread started.")

    def stop_listening(self):
        self._listening = False
        logger.info("[STT] Listening stopped.")

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    # ─────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────

    def _init_tts_engine(self):
        """Initialize pyttsx3 engine (must be called on the TTS thread)."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            if voices:
                for v in voices:
                    if "english" in v.name.lower() or "en" in v.id.lower():
                        engine.setProperty("voice", v.id)
                        break
            engine.setProperty("rate", 170)
            engine.setProperty("volume", 0.95)
            return engine
        except Exception as e:
            logger.error(f"TTS engine init failed: {e}")
            return None

    def _tts_loop(self):
        """TTS worker loop — runs on dedicated thread."""
        engine = self._init_tts_engine()
        if engine is None:
            logger.warning("TTS unavailable. Voice features disabled.")
            return

        while self._running:
            try:
                text = self._tts_queue.get(timeout=1)
                if text is None:
                    break
                logger.info(f"[TTS] Speaking: {text[:80]}")
                engine.say(text)
                engine.runAndWait()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS error: {e}")
                time.sleep(0.5)

    def _stt_loop(self, callback: Optional[Callable[[str], None]]):
        """STT listener loop — runs continuously until stop_listening() called."""
        try:
            import speech_recognition as sr
        except ImportError:
            logger.warning("speech_recognition not installed. STT disabled.")
            self._listening = False
            return

        try:
            import pyaudio  # noqa
        except ImportError:
            logger.warning("PyAudio not installed. STT disabled.")
            self._listening = False
            return

        try:
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.8  # faster response after speaking

            with sr.Microphone() as source:
                logger.info("[STT] Calibrating ambient noise...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.6)
                except Exception:
                    pass
                logger.info("[STT] Ready. Listening for voice commands...")

                while self._listening:
                    try:
                        audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                        text = None
                        try:
                            text = recognizer.recognize_google(audio, language="en-US")
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError:
                            # Offline fallback
                            try:
                                text = recognizer.recognize_sphinx(audio)
                            except Exception:
                                continue

                        if text and text.strip():
                            logger.info(f"[STT] Recognized: '{text}'")
                            if callback:
                                callback(text.strip())
                    except sr.WaitTimeoutError:
                        continue
                    except OSError as e:
                        logger.warning(f"[STT] Mic error: {e}")
                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f"[STT] listen error: {e}")
                        time.sleep(0.5)
        except OSError as e:
            logger.warning(f"[STT] Microphone not available: {e}")
        except Exception as e:
            logger.error(f"[STT] Loop error: {e}")
        finally:
            self._listening = False
            logger.info("[STT] Listening thread exited.")


# ─────────────────────────────────────────────────────────────────
# COMMAND INTERPRETER
# ─────────────────────────────────────────────────────────────────

class VoiceCommandHandler:
    """
    Full command interpreter for voice AND typed chat commands.

    When user says/types a command:
      → Speaks "Sure {name}, I'm on it!" immediately
      → Shows progress in UI via progress_cb
      → Executes action
      → Speaks completion
      → If confused → asks clarifying question with options
    """

    # Intent definitions: (keywords, action_key, spoken_name)
    INTENTS = [
        (["clean my system", "cleanup my system", "clean the system", "system cleanup",
          "optimize my pc", "speed up my pc", "clean up pc", "clean pc",
          "run cleanup", "quick clean", "clean system"],
         "cleanup", "System Cleanup"),

        (["browser", "browser cache", "clean browser", "browser cleanup",
          "clear browser", "chrome cache", "edge cache", "firefox cache",
          "clear cache"],
         "browser_cleanup", "Browser Cleanup"),

        (["status", "health", "how is my system", "how is my pc",
          "system performance", "ram usage", "cpu usage",
          "check my system", "system check"],
         "status", "System Status"),

        (["performance", "tips", "performance tips", "startup apps",
          "startup", "boot apps"],
         "performance", "Performance"),

        (["internet", "speed", "internet speed", "slow internet", "wifi", "network",
          "connection", "boost internet", "fix internet", "check internet",
          "bandwidth", "who is using my internet", "internet page", "network page"],
         "internet", "Internet"),

        (["dashboard", "home", "overview", "main screen"],
         "dashboard", "Dashboard"),

        (["ai", "chat", "ask ai", "open ai", "ai assistant", "assistant"],
         "ai_chat", "AI Assistant"),

        (["minimize", "hide", "minimize window"],
         "minimize", "Minimize"),

        (["close", "goodbye", "bye", "exit", "quit"],
         "exit", "Exit"),

        (["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "good night"],
         "greet", "Greeting"),

        (["help", "what can you do", "commands", "what to say", "options"],
         "help", "Help"),
    ]

    # Ambiguous terms that need clarification
    AMBIGUOUS = {
        "clean": [
            ("Clean my entire system (temp files, cache, GPU cache)", "clean my system"),
            ("Clean only the browser cache", "browser cleanup"),
        ],
        "clear": [
            ("Clear system temp files and cache", "clean my system"),
            ("Clear browser cache only", "browser cleanup"),
        ],
        "stop": [
            ("Minimize the app", "minimize"),
            ("Stop listening (turn off mic)", "__stop_voice__"),
        ],
        "open": [
            ("Open the AI assistant chat", "ai assistant"),
            ("Open the performance page", "performance tips"),
            ("Open the dashboard", "dashboard"),
        ],
    }

    def __init__(self, voice: VoiceAssistant, actions: dict, user_name: str = "",
                 progress_cb=None):
        self.voice = voice
        self.user_name = user_name or "there"
        self.actions = actions
        self._progress_cb = progress_cb  # callable(message: str, percent: int) or None
        self._pending_clarification = None  # list of (label, command) options
        self._import_threading()

    def _import_threading(self):
        import threading as _t
        self._threading = _t

    def _name(self):
        return self.user_name

    def _progress(self, msg: str, pct: int = -1):
        """Emit progress update to UI (if callback registered)."""
        if self._progress_cb:
            try:
                self._progress_cb(msg, pct)
            except Exception:
                pass

    # ── Public entry points ───────────────────────────────────────

    def handle(self, text: str) -> tuple:
        """
        Process a command from voice recognition or a chat button.
        Returns (handled: bool, response_text: str)
        """
        t = text.lower().strip()
        name = self._name()
        logger.info(f"[VoiceCmd] Handling: '{t}'")

        # ── If we are waiting for a clarification choice ──────────
        if self._pending_clarification:
            return self._resolve_clarification(t)

        # ── Match intent ──────────────────────────────────────────
        matched_action = None
        matched_label  = None
        for keywords, action_key, spoken_name in self.INTENTS:
            if any(kw in t for kw in keywords):
                matched_action = action_key
                matched_label  = spoken_name
                break

        # ── Check ambiguous single-word triggers ──────────────────
        if matched_action is None:
            for trigger, options in self.AMBIGUOUS.items():
                if t == trigger or t.startswith(trigger + " "):
                    return self._ask_clarification(trigger, options)

        if matched_action is None:
            return False, ""  # Not handled — pass to AI

        # ── Execute matched intent ────────────────────────────────
        return self._execute(matched_action, matched_label, t)

    def handle_chat(self, text: str, speak_response: bool = True) -> tuple:
        """
        Process command typed in the AI chat box.
        Returns (handled: bool, response_text: str)
        """
        t = text.lower().strip()

        # Only intercept if the FULL phrase matches a direct action
        direct_triggers = {
            "clean my system", "cleanup my system", "system cleanup",
            "browser cleanup", "clean browser", "browser cache",
            "check status", "system status", "system health",
            "open dashboard", "go to dashboard",
            "open performance", "performance tips", "startup apps",
            "minimize", "minimize app",
            "open ai chat", "ai assistant",
            "help", "what can you do",
        }
        if t in direct_triggers:
            # We pass speak_response=False if we only want the text, 
            # but usually we want both.
            return self.handle(text)
        return False, ""

    def _execute(self, action_key: str, spoken_name: str, original_text: str) -> tuple:
        """Execute an action with full spoken feedback + progress."""
        name = self._name()

        if action_key == "greet":
            msg = f"Hello {name}! I'm here. Say 'clean my system', 'check status', 'browser cleanup', or 'help' to see all commands."
            self.voice.speak(msg)
            return True, msg

        if action_key == "help":
            msg = f"Sure {name}! Here's what I can do. Say: clean my system, browser cleanup, check system status, open dashboard, performance tips, open AI assistant, or minimize."
            self.voice.speak(msg)
            return True, msg

        if action_key == "exit":
            msg = f"Sure {name}, minimizing now. I'll be here when you need me."
            self.voice.speak(msg)
            self._do("minimize")
            return True, msg

        if action_key == "minimize":
            msg = f"Sure {name}, minimizing."
            self.voice.speak(msg)
            self._do("minimize")
            return True, msg

        if action_key == "status":
            msg = f"Sure {name}, checking your system status right now."
            self.voice.speak(msg)
            self._progress("🔍 Reading system metrics...", 20)
            self._do("status")
            self._progress("✅ System status complete.", 100)
            return True, msg

        if action_key == "cleanup":
            msg = f"Sure {name}, I'm starting a full system cleanup right now. You can watch the progress in the Cleanup tab."
            self.voice.speak(msg)
            self._progress("🗑️ Starting system cleanup...", 10)
            self._do("navigate", "cleanup")
            self._threading.Timer(0.9, lambda: (
                self._progress("🗑️ Running cleanup engine...", 40),
                self._do("cleanup"),
            )).start()
            return True, msg

        if action_key == "browser_cleanup":
            msg = f"Sure {name}, opening browser cleanup. This will clear cache safely."
            self.voice.speak(msg)
            self._progress("🌐 Starting browser cleanup...", 10)
            self._do("navigate", "browser")
            self._threading.Timer(0.9, lambda: (
                self._progress("🌐 Running browser optimization...", 40),
                self._do("browser_cleanup"),
            )).start()
            return True, msg

        if action_key == "performance":
            msg = f"Sure {name}, opening the performance and startup apps page."
            self.voice.speak(msg)
            self._progress("⚡ Loading performance data...", 30)
            self._do("navigate", "performance")
            return True, msg

        if action_key == "internet":
            msg = f"Sure {name}, analyzing your network connection right now."
            self.voice.speak(msg)
            self._progress("🌐 Analyzing bandwidth usage...", 20)
            self._do("internet_check")
            return True, msg

        if action_key == "dashboard":
            msg = f"Sure {name}, taking you to the dashboard."
            self.voice.speak(msg)
            self._progress("🏠 Navigating to dashboard...", 50)
            self._do("navigate", "dashboard")
            return True, msg

        if action_key == "ai_chat":
            msg = f"Sure {name}, opening AI assistant. Ask me anything!"
            self.voice.speak(msg)
            self._do("navigate", "ai_chat")
            return True, msg

        return False, ""

    def _ask_clarification(self, trigger: str, options: list) -> tuple:
        """Speak clarification options when command is ambiguous."""
        self._pending_clarification = options
        name = self._name()

        option_text = ". ".join(
            f"Say option {i+1} for {label}" for i, (label, _) in enumerate(options)
        )
        msg = f"I heard '{trigger}', {name}. Did you mean: {option_text}?"
        self.voice.speak(msg)
        logger.info(f"[VoiceCmd] Clarification requested for '{trigger}'")
        return True, msg  # handled (waiting for follow-up)

    def _resolve_clarification(self, text: str) -> tuple:
        """Resolve a pending clarification with user's follow-up."""
        options = self._pending_clarification
        self._pending_clarification = None

        t = text.lower().strip()

        # Match by number ("option 1", "first", "1")
        chosen_cmd = None
        for i, (label, cmd) in enumerate(options):
            num_words = ["first", "second", "third", "fourth"]
            if (str(i + 1) in t or
                f"option {i+1}" in t or
                (i < len(num_words) and num_words[i] in t) or
                any(kw in t for kw in label.lower().split()[:3])):
                chosen_cmd = cmd
                break

        if chosen_cmd is None:
            msg = f"I didn't catch that. Please say 'option 1' or 'option 2'."
            self.voice.speak(msg)
            self._pending_clarification = options  # keep waiting
            return True, msg

        if chosen_cmd == "__stop_voice__":
            msg = f"Okay, turning off voice commands."
            self.voice.speak(msg)
            # Signal main window to stop listening
            if "stop_voice" in self.actions:
                self._do("stop_voice")
            return True, msg

        # Execute the resolved command
        return self.handle(chosen_cmd)

    def _do(self, action: str, *args):
        """Safely call an action from actions dict."""
        try:
            if action in self.actions and self.actions[action]:
                self.actions[action](*args)
        except Exception as e:
            logger.error(f"[Cmd] action '{action}' failed: {e}")
