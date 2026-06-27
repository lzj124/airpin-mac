#!/usr/bin/env python3
"""
Test v11 — isolate: is it OverlayView(isOpaque=False) + transparent window?
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSMakeRect, NSObject, NSTimer

from overlay_window import OverlayView


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # ── Transparent fullscreen + OverlayView(isOpaque=False) ──
    print("[A] Transparent fullscreen + OverlayView...")
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)

    view = OverlayView.alloc().initWithFrame_(frame)
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)

    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False
    )

    print("  Running 3s...")
    try:
        app.run()
        print("  [A] SURVIVED")
    except Exception as e:
        print(f"  [A] CRASHED: {e}")
        return


if __name__ == '__main__':
    main()
