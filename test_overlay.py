#!/usr/bin/env python3
"""
Test v8 — overlay + pynput + mss capture thread + app.run()
This replicates the full AirPin stack.
"""
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSMakeRect, NSObject, NSTimer
import time, traceback, threading
import numpy as np

try:
    import mss
    print("mss imported OK")
except ImportError:
    print("mss NOT available")
    import sys; sys.exit(1)

from pynput import keyboard


class FillView(NSView):
    def isOpaque(self):
        return True
    def drawRect_(self, rect):
        NSColor.whiteColor().set()
        NSRectFill(self.bounds())


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    # ── mss capture thread (same as AirPin) ──
    print("Starting mss capture thread...")
    sct = mss.mss()
    monitor = sct.monitors[1]
    print(f"  Monitor: {monitor['width']}x{monitor['height']}")

    capture_running = True
    frame_holder = [None]
    frame_lock = threading.Lock()

    def capture_loop():
        while capture_running:
            try:
                img = sct.grab(monitor)
                frame = np.frombuffer(img.bgra, dtype=np.uint8).reshape(
                    img.height, img.width, 4
                )
                with frame_lock:
                    frame_holder[0] = frame
            except Exception as e:
                print(f"  Capture error: {e}")
            time.sleep(1.0 / 120)

    cap_thread = threading.Thread(target=capture_loop, daemon=True)
    cap_thread.start()
    time.sleep(0.5)
    print(f"  Capture OK, frame shape: {frame_holder[0].shape if frame_holder[0] is not None else 'None'}")

    # ── Window ──
    screen = NSScreen.mainScreen()
    frame = screen.frame()
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(100, 100, 400, 300),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win.setOpaque_(True)
    win.setBackgroundColor_(NSColor.blueColor())
    win.setLevel_(NSFloatingWindowLevel)
    view = FillView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 300))
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)

    # ── pynput ──
    listener = keyboard.Listener(on_press=lambda k: None, on_release=lambda k: None)
    listener.start()
    print("pynput listener started")

    # ── NSTimer that reads frame + setNeedsDisplay (like AirPin _tick) ──
    class TickTarget(NSObject):
        def init(self):
            self = objc.super(TickTarget, self).init()
            return self
        def tick_(self, timer):
            # Read latest frame (like AirPin does)
            with frame_lock:
                f = frame_holder[0]
            # Trigger redraw
            view.setNeedsDisplay_(True)

    import objc
    target = TickTarget.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0 / 120.0, target, b'tick:', None, True
    )

    # Stop after 5s
    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    stop_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        5.0, stopper, b'fire:', None, False
    )

    print("Running app.run() for 5s with full stack...")
    try:
        app.run()
        print("SURVIVED full stack!")
    except Exception as e:
        print(f"CRASHED: {e}")
        traceback.print_exc()

    capture_running = False
    listener.stop()
    sct.close()


if __name__ == '__main__':
    main()
