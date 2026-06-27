#!/usr/bin/env python3
"""
Test v10 — test the OverlayView itself, WITHOUT OverlayWindow.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSMakeRect, NSObject, NSTimer

# Import the REAL OverlayView from overlay_window
from overlay_window import OverlayView

print("OverlayView imported OK")


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # Test A: OverlayView in an OPAQUE window
    print("\n[A] OverlayView in opaque window...")
    win_a = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(100, 100, 400, 300),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win_a.setOpaque_(True)
    win_a.setBackgroundColor_(NSColor.blueColor())
    win_a.setLevel_(NSFloatingWindowLevel)

    view_a = OverlayView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 300))
    win_a.setContentView_(view_a)
    win_a.makeKeyAndOrderFront_(None)

    # Timer to stop after 3s
    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)

    stopper = Stopper.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False
    )
    print("  Running app.run() for 3s...")
    try:
        app.run()
        print("  [A] SURVIVED")
        win_a.orderOut_(None)
    except Exception as e:
        print(f"  [A] CRASHED: {e}")
        return


if __name__ == '__main__':
    main()
