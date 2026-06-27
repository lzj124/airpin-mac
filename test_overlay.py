#!/usr/bin/env python3
"""
Test v12 — systematically replicate OverlayWindow.start() inline.
Binary search which property causes the crash.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSBorderlessWindowMask,
    NSFloatingWindowLevel, NSApplicationActivationPolicyAccessory,
)
from Foundation import NSMakeRect, NSObject, NSTimer
from overlay_window import OverlayView


def test(label, setup_fn, with_timer=False):
    """Run a window test for 3 seconds."""
    app = NSApplication.sharedApplication()

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    print(f"\n[{label}]")
    win, view = setup_fn(frame)

    if with_timer:
        class Ticker(NSObject):
            def tick_(self, t):
                view.setNeedsDisplay_(True)
        ticker = Ticker.alloc().init()
        timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0/60.0, ticker, b'tick:', None, True
        )

    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    stoptimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False
    )

    print("  running 3s...")
    try:
        app.run()
        print(f"  [{label}] SURVIVED")
        win.orderOut_(None)
        return True
    except Exception as e:
        print(f"  [{label}] EXCEPTION: {e}")
        return False


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    # A: baseline (same as v11 — known to work)
    def setup_a(frame):
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setLevel_(NSFloatingWindowLevel)
        win.setIgnoresMouseEvents_(True)
        win.setHasShadow_(False)
        view = OverlayView.alloc().initWithFrame_(frame)
        win.setContentView_(view)
        win.makeKeyAndOrderFront_(None)
        return win, view

    if not test("A baseline", setup_a):
        print("Baseline failed?!"); return

    # B: add setReleasedWhenClosed + setFrame_display
    def setup_b(frame):
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setLevel_(NSFloatingWindowLevel)
        win.setIgnoresMouseEvents_(True)
        win.setHasShadow_(False)
        win.setReleasedWhenClosed_(False)       # NEW
        win.setFrame_display_(frame, True)       # NEW
        view = OverlayView.alloc().initWithFrame_(frame)
        view._overlay_window = True  # set _overlay_window to truthy
        win.setContentView_(view)
        win.makeKeyAndOrderFront_(None)
        return win, view

    if not test("B +releasedWhenClosed +setFrame_display +timer", setup_b, with_timer=True):
        print("=> Found it in B!"); return

    print("\n=== All survived ===")


if __name__ == '__main__':
    main()
