"""
Voice Assistant Service - pyttsx3 (TTS) + SpeechRecognition (STT)
Runs in a dedicated background thread to avoid blocking the UI.
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
            # Clear queue and prioritize
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except queue.Empty:
                    break
        self._tts_queue.put(text)
        logger.debug(f"TTS queued: {text[:60]}")

    def greet(self, name: str = "Quasif"):
        """Speak a context-aware startup greeting."""
        hour = datetime.now().hour
        if hour < 12:
            period = "Morning"
        elif hour < 17:
            period = "Afternoon"
        else:
            period = "Evening"
        self.speak(f"Good {period} {name}. Your AI System Optimizer is ready. System monitoring is active.", priority=True)

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
            # Configure voice
            voices = engine.getProperty("voices")
            preferred_voice = get_setting("voice_name", "default")
            if voices:
                # Try to find an English voice
                for v in voices:
                    if "english" in v.name.lower() or "en" in v.id.lower():
                        engine.setProperty("voice", v.id)
                        break
            engine.setProperty("rate", 175)   # Speed
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
        """STT listener loop — handles missing pyaudio/microphone gracefully."""
        try:
            import speech_recognition as sr
        except ImportError:
            logger.warning("speech_recognition not installed. STT disabled.")
            self._listening = False
            return

        try:
            import pyaudio  # noqa — just test if it's available
        except ImportError:
            logger.warning("PyAudio not installed. STT disabled. Run: pip install pipwin && pipwin install pyaudio")
            self._listening = False
            return

        try:
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True

            with sr.Microphone() as source:
                logger.info("[STT] Calibrating ambient noise (1s)...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                except Exception:
                    pass
                logger.info("[STT] Listening for voice commands...")

                while self._listening:
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        try:
                            text = recognizer.recognize_google(audio, language="en-US")
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError:
                            # Offline fallback — try sphinx if available
                            try:
                                text = recognizer.recognize_sphinx(audio)
                            except Exception:
                                continue
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


class VoiceCommandHandler:
    """
    Maps voice commands to application actions with conversational AI responses.
    Responds naturally: "Sure Quasif, cleaning your system now!"
    """

    def __init__(self, voice: VoiceAssistant, actions: dict, user_name: str = ""):
        self.voice = voice
        self.actions = actions
        self.user_name = user_name or "there"

    def handle(self, text: str):
        t = text.lower().strip()
        logger.info(f"[VoiceCmd] '{t}'")
        name = self.user_name

        if any(kw in t for kw in ["clean", "cleanup", "optimize", "speed up", "boost"]):
            self.voice.speak(f"Sure {name}! Running a full system cleanup for you right now.")
            if "cleanup" in self.actions:
                self.actions["cleanup"]()

        elif any(kw in t for kw in ["status", "health", "how is my", "system performance"]):
            if "status" in self.actions:
                self.actions["status"]()  # Will speak status inside

        elif any(kw in t for kw in ["stop", "exit", "quit", "close", "minimize", "goodbye"]):
            self.voice.speak(f"Goodbye {name}! I'll minimize to the system tray. Call me anytime.")
            if "minimize" in self.actions:
                self.actions["minimize"]()

        elif any(kw in t for kw in ["help", "what can you do", "commands"]):
            self.voice.speak(
                f"Sure {name}! You can say: clean my system, check status, "
                "minimize, or ask me any question about your PC."
            )

        elif any(kw in t for kw in ["hello", "hi", "hey", "good morning", "good evening"]):
            self.voice.speak(f"Hello {name}! I'm here and your system is being monitored. How can I help?")

        else:
            # Pass to AI for conversational response
            self.voice.speak(f"Let me check that for you, {name}.")
            if "ai_chat" in self.actions:
                self.actions["ai_chat"](text)

