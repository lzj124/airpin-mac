"""
Global hotkey manager for macOS using pynput.

Listens for Ctrl+Alt+key combinations globally and triggers
registered callbacks. Runs in a background thread.

Replaces Win32 GetAsyncKeyState hotkey manager from Windows AirPin.
"""

import threading
import time

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

import config


class HotkeyManager:
    """pynput-based global hotkey manager for macOS."""

    def __init__(self):
        if not HAS_PYNPUT:
            raise ImportError(
                "pynput package is required. Install with: pip install pynput"
            )

        self._listener = None
        self._hotkeys = {}  # name -> (modifiers_set, key, callback)
        self._callbacks = {}  # name -> callback
        self._cooldowns = {}  # name -> last_trigger_time
        self._cooldown_sec = 0.3
        self._pressed_keys = set()
        self._running = False
        self._lock = threading.Lock()
        self._triggered = set()  # names triggered this frame

    def register(self, name, key_char, callback=None):
        """Register a hotkey.

        Args:
            name: Hotkey identifier (e.g., 'recenter')
            key_char: The character key (e.g., 'r', 't', 'q')
            callback: Function to call when hotkey is triggered
        """
        with self._lock:
            self._hotkeys[name] = key_char
            if callback:
                self._callbacks[name] = callback
            self._cooldowns[name] = 0.0

    def register_hotkeys_from_config(self, callback_map=None):
        """Register all hotkeys from config.HOTKEYS.

        Args:
            callback_map: dict of name -> callback function
        """
        if callback_map is None:
            callback_map = {}

        for name, (key_char,) in config.HOTKEYS.items():
            self.register(name, key_char, callback_map.get(name))

    def _on_press(self, key):
        """Handle key press event."""
        try:
            # Track modifiers
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._pressed_keys.add('ctrl')
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self._pressed_keys.add('alt')
            else:
                # Check if this key + modifiers matches a hotkey
                char = None
                if hasattr(key, 'char') and key.char:
                    char = key.char.lower()
                elif hasattr(key, 'name'):
                    # Special keys
                    char = key.name

                if char and 'ctrl' in self._pressed_keys and 'alt' in self._pressed_keys:
                    now = time.monotonic()
                    with self._lock:
                        for name, hk_char in self._hotkeys.items():
                            if char == hk_char:
                                cd = self._cooldowns.get(name, 0.0)
                                if now - cd >= self._cooldown_sec:
                                    self._triggered.add(name)
                                    self._cooldowns[name] = now
                                    # Fire callback if registered
                                    cb = self._callbacks.get(name)
                                    if cb:
                                        try:
                                            cb()
                                        except Exception as e:
                                            print(f"  Hotkey callback error ({name}): {e}")
        except Exception:
            pass  # Ignore key parsing errors

    def _on_release(self, key):
        """Handle key release event."""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._pressed_keys.discard('ctrl')
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self._pressed_keys.discard('alt')
        except Exception:
            pass

    def start(self):
        """Start listening for hotkeys in a background thread."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        self._running = True
        print("  Hotkeys: listening for Ctrl+Alt+... combinations")

    def poll(self):
        """Get triggered hotkey names and clear the set.

        Returns:
            set of triggered hotkey names since last poll.
        """
        with self._lock:
            triggered = self._triggered.copy()
            self._triggered.clear()
            return triggered

    def stop(self):
        """Stop the hotkey listener."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    @property
    def is_running(self) -> bool:
        return self._running


# ── Standalone test ──
if __name__ == '__main__':
    print("Hotkey Manager Test (pynput)")
    print("Press Ctrl+Alt+R, Ctrl+Alt+T, Ctrl+Alt+Q to test")
    print("(Press Ctrl+C to exit)")

    manager = HotkeyManager()

    def on_recenter():
        print(">>> RECENTER triggered!")

    def on_toggle():
        print(">>> TOGGLE TRACKING triggered!")

    def on_quit():
        print(">>> QUIT triggered!")
        manager.stop()

    manager.register('recenter', 'r', on_recenter)
    manager.register('toggle_tracking', 't', on_toggle)
    manager.register('quit', 'q', on_quit)

    manager.start()

    try:
        while manager.is_running:
            triggered = manager.poll()
            if triggered:
                print(f"  Hotkeys triggered: {triggered}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        manager.stop()
