#!/usr/bin/env python3
"""
AirPin macOS — Single-Screen 3DoF Spatial Head Tracking
for RayNeo Air 4 Pro AR Glasses.

Pins your desktop in 3D space: turn your head and the screen
shifts to stay in place, like a virtual monitor pinned to the wall.

Usage:
    python main.py
    python main.py --no-imu         # Run without head tracking
    python main.py --no-audio       # Don't route audio
    python main.py --monitor 1      # Capture monitor 1 instead of primary
    python main.py --sensitivity 1.5
    python main.py --fps 60         # Lower capture FPS

Hotkeys (Ctrl+Alt+...):
    R   Recenter             T   Toggle tracking
    P   Toggle pitch         I   Invert yaw
    H   Toggle HUD           0   Reset zoom
    Q   Quit
"""

import sys
import os
import time
import math
import argparse
import threading
import signal

import numpy as np

import config
from smooth_follow import SmoothFollow
from imu_tracker import ImuTracker
from imu_reader import ImuReader
from screen_capture import ScreenCapture
from overlay_window import OverlayWindow
from hotkey_manager import HotkeyManager
from audio_router import AudioRouter


def parse_args():
    parser = argparse.ArgumentParser(
        description="AirPin macOS — 3DoF head tracking for RayNeo Air 4 Pro"
    )
    parser.add_argument("--no-imu", action="store_true",
                        help="Run without IMU head tracking")
    parser.add_argument("--no-audio", action="store_true",
                        help="Don't route audio to glasses")
    parser.add_argument("--monitor", type=int, default=config.MONITOR_INDEX,
                        help=f"Monitor index to capture (default: {config.MONITOR_INDEX})")
    parser.add_argument("--sensitivity", type=float,
                        default=config.HEAD_TRACKING_SENSITIVITY,
                        help="Head tracking sensitivity multiplier")
    parser.add_argument("--fps", type=int, default=None,
                        help="Capture FPS (default: from config)")
    return parser.parse_args()


class AirPinApp:
    """Main application that wires all modules together."""

    def __init__(self, args):
        self.args = args
        self.running = False
        self.last_time = time.time()
        self.frame_count = 0

        # Modules
        self.imu_reader = None
        self.imu_tracker = None
        self.screen_capture = None
        self.overlay = None
        self.hotkeys = None
        self.audio = None
        self.smooth_follow = None

        # State
        self.tracking_enabled = True
        self.show_hud = config.SHOW_HUD
        self.zoom = config.ZOOM_DEFAULT

        # Callback map for hotkeys
        self._hotkey_callbacks = {
            'recenter': self._on_recenter,
            'toggle_hud': self._on_toggle_hud,
            'toggle_tracking': self._on_toggle_tracking,
            'invert_yaw': self._on_invert_yaw,
            'toggle_pitch': self._on_toggle_pitch,
            'quit': self._on_quit,
            'zoom_reset': self._on_zoom_reset,
        }

    def setup(self):
        """Initialize all modules."""
        print("=" * 50)
        print("AirPin macOS — RayNeo Air 4 Pro")
        print("=" * 50)

        # ── Screen Capture ──
        print("\n[1/6] Starting screen capture...")
        capture_fps = self.args.fps or config.CAPTURE_FPS
        self.screen_capture = ScreenCapture(
            monitor_index=self.args.monitor,
            capture_fps=capture_fps,
        )
        if not self.screen_capture.start():
            print("ERROR: Screen capture failed.")
            return False

        # Wait for first frame
        print("  Waiting for first frame...")
        for _ in range(50):
            if self.screen_capture.frame_available:
                break
            time.sleep(0.1)
        if self.screen_capture.frame_available:
            w, h = self.screen_capture.width, self.screen_capture.height
            print(f"  Got first frame: {w}x{h}")
        else:
            print("  WARNING: No frame yet, continuing...")

        # ── Overlay Window ──
        print("\n[2/6] Creating overlay window...")
        self.overlay = OverlayWindow()
        self.overlay.start()

        # ── IMU Tracker ──
        print("\n[3/6] Connecting to RayNeo glasses...")
        if not self.args.no_imu:
            try:
                self.imu_reader = ImuReader()
                if not self.imu_reader.open():
                    print("  WARNING: Glasses not found. "
                          "Connect via USB-C and ensure HID permissions.")
                    print("  Running without head tracking.")
                else:
                    self.imu_tracker = ImuTracker()
                    self.imu_tracker.start(reader=self.imu_reader)
                    time.sleep(0.1)
                    self.imu_tracker.recenter()
                    self.smooth_follow = SmoothFollow()
                    self.smooth_follow.reset()
                    print("  IMU tracker: connected and recentered")
            except Exception as e:
                print(f"  WARNING: IMU failed: {e}")
                print("  Running without head tracking.")
        else:
            print("  IMU disabled (--no-imu)")

        # ── Hotkeys ──
        print("\n[4/6] Setting up hotkeys...")
        self.hotkeys = HotkeyManager()
        self.hotkeys.register_hotkeys_from_config(self._hotkey_callbacks)
        self.hotkeys.start()

        # ── Audio ──
        print("\n[5/6] Setting up audio routing...")
        if not self.args.no_audio and config.AUDIO_ENABLED:
            self.audio = AudioRouter()
            if not self.audio.start():
                print("  Audio routing not available.")
        else:
            print("  Audio disabled.")

        print("\n[6/6] Starting main loop...")
        print("\n" + "=" * 50)
        print("AirPin Running")
        print("=" * 50)
        print("Hotkeys (Ctrl+Alt+...):")
        print("  R   Recenter          T   Toggle tracking")
        print("  P   Toggle pitch      I   Invert yaw")
        print("  H   Toggle HUD        0   Reset zoom")
        print("  Q   Quit")
        print()

        return True

    def run(self):
        """Main loop: capture → apply head offset → render overlay."""
        self.running = True

        try:
            while self.running:
                # Check hotkeys
                triggered = self.hotkeys.poll()
                if 'quit' in triggered:
                    self.running = False
                    break

                # Compute dt
                now = time.time()
                dt_ms = (now - self.last_time) * 1000.0
                self.last_time = now

                # ── Get head orientation ──
                pixel_offset_x = 0.0
                pixel_offset_y = 0.0

                if (self.imu_tracker and self.tracking_enabled
                        and self.imu_tracker.imu_count > 0):
                    dy, dp, dr = self.imu_tracker.get_orientation()
                    gyro_mag = self.imu_tracker.get_gyro_magnitude()

                    # Apply sensitivity
                    dy *= self.args.sensitivity

                    # Apply smooth follow filter
                    if self.smooth_follow:
                        yaw_offset = self.smooth_follow.update(
                            dy, dt_ms, gyro_mag
                        )
                    else:
                        yaw_offset = dy

                    # Convert radians to pixels
                    # Approximate pixels-per-radian from FOV
                    ppd = self.screen_capture.width / math.radians(
                        config.FOV_HORIZONTAL_DEG
                    )
                    pixel_offset_x = yaw_offset * ppd

                    if config.INVERT_YAW:
                        pixel_offset_x *= -1

                    if config.PITCH_ENABLED:
                        ppd_v = self.screen_capture.height / math.radians(
                            config.FOV_VERTICAL_DEG
                        )
                        pixel_offset_y = dp * ppd_v
                        if config.INVERT_PITCH:
                            pixel_offset_y *= -1

                # ── Render frame ──
                self._render_frame(pixel_offset_x, pixel_offset_y)

                self.frame_count += 1

                # Periodic status
                if self.frame_count % 600 == 0:
                    imu_status = 'OK' if (self.imu_tracker and
                                          self.imu_tracker.connected) else 'NONE'
                    print(f"  Frame {self.frame_count}: "
                          f"offset=({pixel_offset_x:.0f},{pixel_offset_y:.0f})px "
                          f"zoom={self.zoom:.1f}x "
                          f"tracking={'ON' if self.tracking_enabled else 'OFF'} "
                          f"imu={imu_status}")

        except KeyboardInterrupt:
            print("\nInterrupted.")
        finally:
            self.shutdown()

    def _render_frame(self, offset_x, offset_y):
        """Render the captured frame with head offset to the overlay."""
        # Get latest captured frame
        info = self.screen_capture.get_frame_info()
        frame = info['frame']

        if frame is None:
            return

        # Pass frame + transforms to the overlay for rendering
        self.overlay.render_frame(frame, offset_x, offset_y, self.zoom)

        # Process Cocoa events to flush the draw
        self.overlay.process_events()

    # ── Hotkey callbacks ──

    def _on_recenter(self):
        if self.imu_tracker:
            self.imu_tracker.recenter()
            if self.smooth_follow:
                self.smooth_follow.reset()
            print("  ▶ Recentered!")

    def _on_toggle_hud(self):
        self.show_hud = not self.show_hud
        print(f"  ▶ HUD: {'ON' if self.show_hud else 'OFF'}")

    def _on_toggle_tracking(self):
        self.tracking_enabled = not self.tracking_enabled
        if self.tracking_enabled and self.imu_tracker:
            self.imu_tracker.recenter()
            if self.smooth_follow:
                self.smooth_follow.reset()
        print(f"  ▶ Tracking: {'ON' if self.tracking_enabled else 'OFF'}")

    def _on_invert_yaw(self):
        config.INVERT_YAW = not config.INVERT_YAW
        print(f"  ▶ Yaw invert: {'ON' if config.INVERT_YAW else 'OFF'}")

    def _on_toggle_pitch(self):
        config.PITCH_ENABLED = not config.PITCH_ENABLED
        print(f"  ▶ Pitch: {'ON' if config.PITCH_ENABLED else 'OFF'}")

    def _on_zoom_reset(self):
        self.zoom = config.ZOOM_DEFAULT
        print(f"  ▶ Zoom reset: {self.zoom:.1f}x")

    def _on_quit(self):
        print("  ▶ Quit requested")
        self.running = False

    def shutdown(self):
        """Graceful shutdown of all modules."""
        print("\nShutting down...")

        self.running = False

        if self.hotkeys:
            self.hotkeys.stop()

        if self.audio:
            self.audio.stop()

        if self.imu_tracker:
            self.imu_tracker.stop()

        if self.screen_capture:
            self.screen_capture.stop()

        if self.overlay:
            self.overlay.close()

        print("Done.")


def main():
    args = parse_args()
    app = AirPinApp(args)

    if not app.setup():
        print("Setup failed. Exiting.")
        sys.exit(1)

    app.run()


if __name__ == '__main__':
    main()
