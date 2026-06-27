"""
Screen capture for macOS using ScreenCaptureKit / CGWindowList.

Captures the primary display's framebuffer at native Retina resolution.
Excludes the overlay window from capture to prevent feedback loops.

Uses CGWindowListCreateImage for reliable, overlay-excluded capture.
"""

import time
import threading
import numpy as np

try:
    from Quartz import (
        CGWindowListCreateImage,
        CGRectNull,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False

try:
    from Quartz import (
        CGWindowListCreateImage, CGRectNull,
        kCGWindowListOption, kCGNullWindowID,
    )
except ImportError:
    pass

import config


class ScreenCapture:
    """Captures a display using CGWindowListCreateImage.

    This excludes the overlay window (set via set_exclude_window_id)
    to prevent feedback loops, and captures at native Retina resolution.
    """

    def __init__(self, monitor_index=None, capture_fps=None):
        if not HAS_QUARTZ:
            raise ImportError(
                "Quartz framework is required (pyobjc-framework-Quartz)"
            )

        self._monitor_index = monitor_index or config.MONITOR_INDEX
        self._capture_fps = capture_fps or config.CAPTURE_FPS
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Latest captured frame
        self._frame = None  # numpy array (height, width, 4) BGRA
        self._frame_time = 0.0
        self._frame_count = 0

        # Monitor info
        self.width = 0
        self.height = 0

        # Window ID to exclude from capture (the overlay window)
        self._exclude_window_id = kCGNullWindowID

        # CGImage → numpy buffer
        from Quartz import (
            CGImageGetBitsPerPixel, CGImageGetBytesPerRow,
            CGImageGetWidth, CGImageGetHeight,
            CGImageGetDataProvider, CGDataProviderCopyData,
            CGImageGetBitmapInfo,
        )
        self._CGImageGetWidth = CGImageGetWidth
        self._CGImageGetHeight = CGImageGetHeight
        self._CGImageGetBytesPerRow = CGImageGetBytesPerRow
        self._CGImageGetDataProvider = CGImageGetDataProvider
        self._CGDataProviderCopyData = CGDataProviderCopyData

    def set_exclude_window_id(self, window_id):
        """Set the window ID to exclude from capture (overlay window)."""
        self._exclude_window_id = window_id

    def start(self) -> bool:
        """Start capturing in background thread."""
        print(f"  Capture: monitor {self._monitor_index} "
              f"@ {self._capture_fps} FPS (CGWindowList)")

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
                # Capture screen excluding the overlay window
                # kCGWindowListOptionOnScreenOnly captures all on-screen windows
                # except the one we pass as the "to exclude" parameter
                cg_image = CGWindowListCreateImage(
                    CGRectNull,
                    kCGWindowListOptionOnScreenOnly,
                    self._exclude_window_id,  # exclude overlay
                    0,  # no image options
                )

                if cg_image is None:
                    time.sleep(0.001)
                    continue

                w = self._CGImageGetWidth(cg_image)
                h = self._CGImageGetHeight(cg_image)
                bpr = self._CGImageGetBytesPerRow(cg_image)

                # Copy pixel data
                provider = self._CGImageGetDataProvider(cg_image)
                raw_data = self._CGDataProviderCopyData(provider)

                # Create numpy array (pad rows to bytesPerRow if needed)
                arr = np.frombuffer(raw_data, dtype=np.uint8)
                if bpr == w * 4:
                    frame = arr.reshape(h, w, 4)
                else:
                    # Bytes per row may include padding
                    frame = arr[:h * bpr].reshape(h, bpr)[:, :w * 4].reshape(h, w, 4)

                with self._lock:
                    self._frame = np.ascontiguousarray(frame)
                    self._frame_time = now
                    self._frame_count += 1

                if self.width == 0:
                    self.width = w
                    self.height = h
                    print(f"  First capture: {w}x{h} (native res)")

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

    def __del__(self):
        self.stop()
