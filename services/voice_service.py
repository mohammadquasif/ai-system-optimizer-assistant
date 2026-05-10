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
        if not self._enabled:
            logger.info("Voice assistant disabled in settings.")
            return
        self._running = True
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True)
        self._tts_thread.start()
        logger.info("VoiceAssistant TTS thread started.")

    def stop(self):
        self._running = False
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
        logger.debug(f"TTS queued: {text[:60]}")

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
        """Start STT listening in background thread."""
        if self._listening:
            return
        cb = callback or self._on_command
        self._stt_thread = threading.Thread(target=self._stt_loop, args=(cb,), daemon=True)
        self._stt_thread.start()
        self._listening = True

    def stop_listening(self):
        self._listening = False

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
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 0.9)
            return engine
        except Exception as e:
            logger.error(f"TTS engine init failed: {e}")
            return None

    def _tts_loop(self):
        """TTS worker loop."""
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
        """STT listener loop."""
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

            with sr.Microphone() as source:
                logger.info("[STT] Calibrating ambient noise...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass
                logger.info("[STT] Listening for voice commands...")
                
                # Signal that we are ready to listen
                self.listening_ready = True 

                while self._listening:
                    try:
                        # Use a shorter timeout and phrase_time_limit
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=8)
                        try:
                            text = recognizer.recognize_google(audio, language="en-US")
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError:
                            # Fallback to sphinx if offline
                            try:
                                text = recognizer.recognize_sphinx(audio)
                            except Exception:
                                continue
                        
                        if text:
                            logger.info(f"[STT] Recognized: {text}")
                            if callback:
                                callback(text)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"[STT] listen error: {e}")
                        time.sleep(1)
        except OSError as e:
            logger.warning(f"[STT] Microphone not available: {e}")
        except Exception as e:
            logger.error(f"[STT] Loop error: {e}")
        finally:
            self._listening = False


# ─────────────────────────────────────────────────────────────────
# COMMAND INTERPRETER
# ─────────────────────────────────────────────────────────────────

class VoiceCommandHandler:
    """
    Full command interpreter for both voice AND typed chat commands.

    When user says/types:
      "cleanup my system"   → speaks "Sure {name}…" → navigates to Cleanup → runs it → speaks done
      "browser cleanup"     → navigates to Browser → runs optimization
      "how is my system"    → speaks live stats
      "help / what can you" → lists commands
      confused input        → asks for clarification with options
    """

    def __init__(self, voice: VoiceAssistant, actions: dict, user_name: str = ""):
        self.voice = voice
        self.user_name = user_name or "there"
        # actions dict (all optional):
        #   navigate(page_key)          - switch to a page
        #   cleanup()                   - run system cleanup
        #   browser_cleanup()           - run browser optimization
        #   status()                    - speak system status
        #   minimize()                  - minimize window
        #   ai_chat(text)               - send text to AI chat
        self.actions = actions

    # Public entry points (used by voice STT and chat input)

    def handle(self, text: str):
        """Process a command from voice recognition or chat input."""
        t = text.lower().strip()
        logger.info(f"[Cmd] '{t}'")
        name = self.user_name

        # ── CLEANUP ───────────────────────────────────────────────
        if any(kw in t for kw in [
            "clean my system", "cleanup my system", "clean the system",
            "system cleanup", "optimize my pc", "speed up my pc",
            "clean up pc", "clean pc", "run cleanup", "quick clean",
        ]):
            self.voice.speak(f"Sure {name}! I'm starting a full system cleanup now. You can see the progress in the Cleanup tab.")
            self._do("navigate", "cleanup")
            # Small delay so navigation completes before running
            threading.Timer(0.8, lambda: self._do("cleanup")).start()
            return True

        # ── BROWSER CLEANUP ───────────────────────────────────────
        if any(kw in t for kw in [
            "browser", "browser cache", "clean browser", "browser cleanup",
            "clear browser", "chrome", "edge cache", "firefox cache",
        ]):
            self.voice.speak(f"Sure {name}! Opening the browser optimization tool now.")
            self._do("navigate", "browser")
            threading.Timer(0.8, lambda: self._do("browser_cleanup")).start()
            return True

        # ── STATUS / HEALTH ───────────────────────────────────────
        if any(kw in t for kw in [
            "status", "health", "how is my system", "how is my pc",
            "system performance", "ram usage", "cpu usage",
            "how are you", "check my system",
        ]):
            self._do("status")
            return True

        # ── PERFORMANCE PAGE ──────────────────────────────────────
        if any(kw in t for kw in ["performance", "tips", "performance tips", "startup apps"]):
            self.voice.speak(f"Opening performance page, {name}.")
            self._do("navigate", "performance")
            return

        # ── DASHBOARD ─────────────────────────────────────────────
        if any(kw in t for kw in ["dashboard", "home", "overview", "main"]):
            self.voice.speak(f"Taking you to the dashboard, {name}.")
            self._do("navigate", "dashboard")
            return

        # ── AI CHAT ───────────────────────────────────────────────
        if any(kw in t for kw in ["chat", "ask ai", "open ai", "ai assistant"]):
            self.voice.speak(f"Opening AI assistant, {name}. Ask me anything!")
            self._do("navigate", "ai_chat")
            return

        # ── MINIMIZE / CLOSE ──────────────────────────────────────
        if any(kw in t for kw in ["minimize", "hide", "close", "goodbye", "bye", "exit"]):
            self.voice.speak(f"Minimizing for you, {name}. I'll be here when you need me.")
            self._do("minimize")
            return

        # ── GREETINGS ─────────────────────────────────────────────
        if any(kw in t for kw in ["hello", "hi", "hey", "good morning", "good evening"]):
            self.voice.speak(
                f"Hello {name}! I'm here and your system is being monitored. "
                "Say 'clean my system', 'browser cleanup', or 'check status' to get started."
            )
            return

        # ── HELP ─────────────────────────────────────────────────
        if any(kw in t for kw in ["help", "what can you do", "commands", "what to say"]):
            self.voice.speak(
                f"Sure {name}! Here's what I can do. "
                "Say: clean my system, browser cleanup, check status, "
                "performance tips, open dashboard, or minimize."
            )
            return

        # ── CONFUSED — ask for clarification ─────────────────────
        return False

    def handle_chat(self, text: str, speak_response: bool = True):
        """
        Process command from the AI chat box.
        If it maps to a direct action, execute it.
        Otherwise pass to AI for a conversational response.
        Returns True if command was handled locally, False if should go to AI.
        """
        t = text.lower().strip()

        # Check if any known command matches
        local_commands = [
            (["clean", "cleanup", "optimize", "speed up"], None),
            (["browser", "chrome", "edge", "firefox"], None),
            (["help", "commands", "what can you"], None),
            (["minimize", "hide", "close", "exit"], None),
        ]
        for keywords, _ in local_commands:
            if any(kw in t for kw in keywords):
                self.handle(text)
                return True
        return False

    # ── Internal helper ──────────────────────────────────────────

    def _do(self, action: str, *args):
        """Safely call an action from actions dict."""
        try:
            if action in self.actions and self.actions[action]:
                self.actions[action](*args)
        except Exception as e:
            logger.error(f"[Cmd] action '{action}' failed: {e}")
