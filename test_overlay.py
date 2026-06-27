#!/usr/bin/env python3
"""
Test v16 — THE missing piece. Pass ACTUAL frame data to OverlayView.drawRect_.
"""
import objc, threading, time
import numpy as np
from AppKit import (
    NSApplication, NSWindow, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSMakeRect, NSObject, NSTimer

from overlay_window import OverlayView

class Stopper(NSObject):
    def fire_(self, t):
        NSApplication.sharedApplication().stop_(None)


class FakeOverlay:
    """Holds real frame data like OverlayWindow does."""
    _frame_lock = threading.Lock()
    _current_frame = None
    _offset_x = 0.0
    _offset_y = 0.0
    _zoom = 1.0


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # Create a fake frame (BGRA, same shape as mss capture)
    print("Creating fake frame data...")
    fake_frame = np.zeros((956, 1470, 4), dtype=np.uint8)
    fake_frame[:, :, 0] = 255  # Blue channel
    print(f"  Frame shape: {fake_frame.shape}, dtype: {fake_frame.dtype}")

    # Set up overlay
    overlay = FakeOverlay()
    overlay._current_frame = fake_frame

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)

    view = OverlayView.alloc().initWithFrame_(frame)
    view._overlay_window = overlay
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)

    # Timer to trigger redraw every frame
    class Ticker(NSObject):
        def init(self):
            self = objc.super(Ticker, self).init()
            return self
        def tick_(self, t):
            view.setNeedsDisplay_(True)

    ticker = Ticker.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0/60.0, ticker, b'tick:', None, True)

    stopper = Stopper.alloc().init()
    stoptimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False)

    print("Running 3s with REAL frame data in drawRect_...")
    try:
        app.run()
        print("SURVIVED! drawRect_ with real data works!")
    except Exception as e:
        print(f"CRASHED: {e}")


if __name__ == '__main__':
    main()
