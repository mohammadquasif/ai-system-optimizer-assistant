"""
Idle Watcher Service
---------------------
Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
License: Personal Use Only (Non-Commercial)

Monitors user inactivity. If no interaction detected for the configured
idle_minutes, a countdown is shown and the app closes cleanly, freeing RAM.

On next Windows startup → app auto-launches, greets, then enters idle watch.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class IdleWatcher:
    """
    Tracks the last user-interaction timestamp.
    After idle_minutes of no interaction, fires the close callback.

    Usage:
        watcher = IdleWatcher(idle_minutes=5, countdown_seconds=60,
                              countdown_cb=..., close_cb=...)
        watcher.start()
        # On any UI interaction:
        watcher.reset()
        # To cancel shutdown:
        watcher.cancel_close()
    """

    def __init__(
        self,
        idle_minutes: int = 5,
        countdown_seconds: int = 60,
        countdown_cb: Optional[Callable[[int], None]] = None,  # receives seconds left
        close_cb:     Optional[Callable[[], None]]    = None,  # fires when time is up
        warn_cb:      Optional[Callable[[], None]]    = None,  # fires when countdown starts
    ):
        self.idle_minutes      = idle_minutes
        self.countdown_seconds = countdown_seconds
        self.countdown_cb      = countdown_cb or (lambda s: None)
        self.close_cb          = close_cb or (lambda: None)
        self.warn_cb           = warn_cb or (lambda: None)

        self._last_active      = datetime.now()
        self._running          = False
        self._in_countdown     = False
        self._cancel_flag      = False
        self._thread: Optional[threading.Thread] = None

    # ─── Public API ─────────────────────────────────────────────────

    def start(self):
        """Start the idle watcher background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="IdleWatcher")
        self._thread.start()
        logger.info(f"IdleWatcher started — idle timeout: {self.idle_minutes} min")

    def stop(self):
        """Stop the watcher (e.g. on manual close)."""
        self._running = False

    def reset(self):
        """Call this on every user interaction (mouse click, key press, etc.)."""
        self._last_active  = datetime.now()
        self._cancel_flag  = True   # cancels any active countdown
        self._in_countdown = False

    def cancel_close(self):
        """Cancel a pending shutdown countdown."""
        self._cancel_flag  = True
        self._in_countdown = False
        self._last_active  = datetime.now()
        logger.info("IdleWatcher: countdown cancelled by user.")

    @property
    def idle_since(self) -> float:
        """Seconds since last activity."""
        return (datetime.now() - self._last_active).total_seconds()

    # ─── Internal loop ───────────────────────────────────────────────

    def _loop(self):
        idle_threshold = self.idle_minutes * 60
        while self._running:
            time.sleep(10)  # check every 10 seconds
            if not self._running:
                break

            elapsed = self.idle_since

            if elapsed >= idle_threshold and not self._in_countdown:
                # Start countdown
                self._in_countdown = True
                self._cancel_flag  = False
                logger.info(f"IdleWatcher: idle for {elapsed:.0f}s, starting countdown.")
                self.warn_cb()
                self._run_countdown()

    def _run_countdown(self):
        """Count down to zero. If not cancelled, fires close_cb."""
        for secs_left in range(self.countdown_seconds, 0, -1):
            if self._cancel_flag or not self._running:
                logger.info("IdleWatcher: countdown cancelled.")
                self._in_countdown = False
                return
            self.countdown_cb(secs_left)
            time.sleep(1)

        if not self._cancel_flag and self._running:
            logger.info("IdleWatcher: closing app to free RAM.")
            self._in_countdown = False
            self.close_cb()
