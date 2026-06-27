#!/usr/bin/env python3
"""
Test v15 — exactly replicate main.py flow: OverlayWindow creates everything.
No pre-finishLaunching. Find what's different from v14.
"""
import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSTimer
from overlay_window import OverlayView, OverlayWindow

class Stopper(NSObject):
    def fire_(self, t):
        NSApplication.sharedApplication().stop_(None)


def main():
    # Do NOT call finishLaunching — let OverlayWindow.start() do it
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    print("Creating real OverlayWindow (no pre-finishLaunching)...")
    overlay = OverlayWindow()
    overlay.start()
    print("OverlayWindow started OK")

    # Stop after 3s
    stopper = Stopper.alloc().init()
    stoptimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False)

    print("Running app.run() for 3s...")
    try:
        app.run()
        print("SURVIVED!")
    except Exception as e:
        print(f"CRASHED: {e}")
        return

    overlay.close()


if __name__ == '__main__':
    main()
