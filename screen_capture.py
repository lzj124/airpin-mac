"""
Screen capture for macOS using mss (MSS: Multiple Screen Shots).

Captures the primary display's framebuffer at configurable FPS.
Returns numpy arrays of pixel data suitable for OpenGL texture upload.

Replaces DXGI-based capture on Windows.
"""

import time
import threading
import numpy as np

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

import config


class ScreenCapture:
    """Captures a display using mss at a target FPS in a background thread."""

    def __init__(self, monitor_index=None, capture_fps=None):
        if not HAS_MSS:
            raise ImportError(
                "mss package is required. Install with: pip install mss"
            )

        self._monitor_index = monitor_index or config.MONITOR_INDEX
        self._capture_fps = capture_fps or config.CAPTURE_FPS
        self._running = False
        self._thread = None
        self._sct = None
        self._lock = threading.Lock()

        # Latest captured frame
        self._frame = None  # numpy array (height, width, 4) BGRA
        self._frame_time = 0.0
        self._frame_count = 0

        # Monitor info
        self._monitor = None
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0

    def start(self) -> bool:
        """Start capturing in background thread. Returns True on success."""
        self._sct = mss.mss()

        # Enumerate monitors
        monitors = self._sct.monitors
        # mss monitors: [0] = all monitors combined, [1] = primary, [2+] = others
        idx = self._monitor_index + 1  # offset for the "all monitors" entry
        if idx >= len(monitors):
            print(f"  Monitor {self._monitor_index} not found, using primary")
            idx = 1

        self._monitor = monitors[idx]
        self.x = self._monitor['left']
        self.y = self._monitor['top']
        self.width = self._monitor['width']
        self.height = self._monitor['height']

        print(f"  Capture: monitor {self._monitor_index} "
              f"({self.width}x{self.height} at +{self.x}+{self.y}) "
              f"@ {self._capture_fps} FPS")

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _capture_loop(self):
        """Background capture loop."""
        frame_interval = 1.0 / max(self._capture_fps, 1)
        last_capture = 0.0

        while self._running:
            now = time.monotonic()
            elapsed = now - last_capture

            if elapsed < frame_interval:
                time.sleep(max(0.001, frame_interval - elapsed))
                continue

            try:
                # Grab the monitor region
                sct_img = self._sct.grab(self._monitor)
                # mss returns BGRA bytes; convert to numpy array
                frame = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape(
                    sct_img.height, sct_img.width, 4
                )

                with self._lock:
                    self._frame = frame
                    self._frame_time = now
                    self._frame_count += 1

                last_capture = now
            except Exception as e:
                print(f"  Capture error: {e}")
                time.sleep(0.01)

    def get_frame(self):
        """Get the latest captured frame as a numpy array (H,W,4) BGRA."""
        with self._lock:
            if self._frame is not None:
                return self._frame.copy()
            return None

    def get_frame_info(self):
        """Get latest frame and metadata."""
        with self._lock:
            return {
                'frame': self._frame.copy() if self._frame is not None else None,
                'time': self._frame_time,
                'count': self._frame_count,
                'width': self.width,
                'height': self.height,
            }

    @property
    def frame_available(self) -> bool:
        with self._lock:
            return self._frame is not None

    @property
    def frame_count(self) -> int:
        with self._lock:
            return self._frame_count

    def stop(self):
        """Stop the capture thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._sct:
            self._sct.close()
            self._sct = None

    def __del__(self):
        self.stop()


# ── Standalone test ──
if __name__ == '__main__':
    import sys

    print("Screen Capture Test (mss)")
    cap = ScreenCapture(monitor_index=0, capture_fps=30)
    cap.start()

    print("Capturing 10 frames...")
    for i in range(10):
        time.sleep(0.05)
        info = cap.get_frame_info()
        if info['frame'] is not None:
            print(f"  Frame {info['count']}: {info['width']}x{info['height']} "
                  f"avg={info['frame'].mean():.0f}")
        else:
            print(f"  Frame {info['count']}: waiting...")

    cap.stop()
    print("Done.")
