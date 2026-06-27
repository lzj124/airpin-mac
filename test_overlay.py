#!/usr/bin/env python3
"""
Test v14 — isolate setFrame_display vs setReleasedWhenClosed.
Use proper fake overlay to avoid test bug from v13.
"""
import objc, threading
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

class Ticker(NSObject):
    def init(self):
        self = objc.super(Ticker, self).init()
        return self
    def tick_(self, t):
        if hasattr(self, '_view'):
            self._view.setNeedsDisplay_(True)


class FakeOverlay:
    """Mimics OverlayWindow attributes used by drawRect_."""
    _frame_lock = threading.Lock()
    _current_frame = None
    _offset_x = 0.0
    _offset_y = 0.0
    _zoom = 1.0


def run_test(label, frame, add_released=False, add_setframe=False):
    app = NSApplication.sharedApplication()

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)

    if add_released:
        win.setReleasedWhenClosed_(False)
    if add_setframe:
        win.setFrame_display_(frame, True)

    view = OverlayView.alloc().initWithFrame_(frame)
    view._overlay_window = FakeOverlay()  # proper fake overlay
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)

    # Timer to trigger redraws
    ticker = Ticker.alloc().init()
    ticker._view = view
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0/60.0, ticker, b'tick:', None, True)

    # Stop after 3s
    stopper = Stopper.alloc().init()
    stoptimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False)

    print(f"  running 3s...")
    try:
        app.run()
        print(f"  [{label}] SURVIVED")
        win.orderOut_(None)
        return True
    except Exception as e:
        print(f"  [{label}] CRASHED: {e}")
        return False


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # 1: baseline — no extras, just FakeOverlay + timer
    print("\n[1] baseline (FakeOverlay + timer)")
    if not run_test("1", frame): print("=> baseline failed!"); return

    # 2: + setReleasedWhenClosed only
    print("\n[2] + setReleasedWhenClosed")
    if not run_test("2", frame, add_released=True): print("=> setReleasedWhenClosed is the problem!"); return

    # 3: + setFrame_display only
    print("\n[3] + setFrame_display")
    if not run_test("3", frame, add_setframe=True): print("=> setFrame_display is the problem!"); return

    # 4: both
    print("\n[4] + both")
    if not run_test("4", frame, add_released=True, add_setframe=True): print("=> combination is the problem!"); return

    print("\n=== All survived ===")


if __name__ == '__main__':
    main()
