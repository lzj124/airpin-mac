#!/usr/bin/env python3
"""
Test v13 — fix ObjC class reuse, test each OverlayWindow difference.
v11 works, OverlayWindow.start() doesn't. Find the exact difference.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSBorderlessWindowMask,
    NSFloatingWindowLevel, NSApplicationActivationPolicyAccessory,
)
from Foundation import NSMakeRect, NSObject, NSTimer
from overlay_window import OverlayView

# Define ObjC classes ONCE at module level
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


def run_test(label, win, view, use_timer=False):
    app = NSApplication.sharedApplication()

    stopper = Stopper.alloc().init()
    stoptimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False
    )

    if use_timer:
        ticker = Ticker.alloc().init()
        ticker._view = view
        timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0/60.0, ticker, b'tick:', None, True
        )

    print(f"  running 3s...")
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

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # ── Test 1: NSBorderlessWindowMask (old name) vs NSWindowStyleMaskBorderless ──
    print("\n[1] NSBorderlessWindowMask + timer")
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSBorderlessWindowMask, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)
    view = OverlayView.alloc().initWithFrame_(frame)
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)
    if not run_test("1", win, view, use_timer=True):
        print("=> NSBorderlessWindowMask is the problem!"); return

    # ── Test 2: setReleasedWhenClosed + setFrame_display ──
    print("\n[2] + setReleasedWhenClosed + setFrame_display + timer")
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)
    win.setReleasedWhenClosed_(False)
    win.setFrame_display_(frame, True)
    view = OverlayView.alloc().initWithFrame_(frame)
    view._overlay_window = True  # truthy, like OverlayWindow sets it
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)
    if not run_test("2", win, view, use_timer=True):
        print("=> setReleasedWhenClosed/setFrame_display is the problem!"); return

    # ── Test 3: view._overlay_window = actual object with _frame_lock ──
    print("\n[3] view._overlay_window = fake overlay with _frame_lock + timer")
    import threading
    class FakeOverlay:
        _frame_lock = threading.Lock()
        _current_frame = None
        _offset_x = 0.0
        _offset_y = 0.0
        _zoom = 1.0

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)
    view = OverlayView.alloc().initWithFrame_(frame)
    view._overlay_window = FakeOverlay()
    win.setContentView_(view)
    win.makeKeyAndOrderFront_(None)
    if not run_test("3", win, view, use_timer=True):
        print("=> _overlay_window back-reference is the problem!"); return

    print("\n=== All survived ===")


if __name__ == '__main__':
    main()
