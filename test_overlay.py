#!/usr/bin/env python3
"""
Test v9 — use the REAL OverlayWindow from overlay_window.py.
"""
import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSTimer
from PyObjCTools import AppHelper

# Import the ACTUAL AirPin overlay module
from overlay_window import OverlayWindow
import config

print("OverlayWindow imported OK")


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    # Use the REAL OverlayWindow — exactly like main.py does
    print("Creating real OverlayWindow...")
    overlay = OverlayWindow()
    overlay.start()
    print("OverlayWindow started OK")

    # NSTimer that calls render_frame (like main.py _tick)
    class TickTarget(NSObject):
        def init(self):
            self = objc.super(TickTarget, self).init()
            return self
        def tick_(self, timer):
            # Just trigger redraw, no actual frame data
            overlay.refresh()

    target = TickTarget.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0 / 60.0, target, b'tick:', None, True
    )

    # Stop after 5s
    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    stop_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        5.0, stopper, b'fire:', None, False
    )

    print("Running app.run() for 5s with real OverlayWindow...")
    try:
        app.run()
        print("SURVIVED with real OverlayWindow!")
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

    overlay.close()


if __name__ == '__main__':
    main()
