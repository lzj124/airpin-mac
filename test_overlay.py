#!/usr/bin/env python3
"""
Test v6 — narrow down: transparency? fullscreen? app.run()?
"""
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSMakeRect
import time, traceback


class FillView(NSView):
    def isOpaque(self):
        return True

    def drawRect_(self, rect):
        NSColor.whiteColor().set()
        NSRectFill(self.bounds())


def pump_events(app, seconds, label):
    """Manual event pump for N seconds."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                0xFFFFFFFF, None, 'kCFRunLoopDefaultMode', True
            )
            if event:
                app.sendEvent_(event)
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"  {label} EXCEPTION: {e}")
            traceback.print_exc()
            return False
    print(f"  {label}: survived")
    return True


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    screen = NSScreen.mainScreen()
    sf = screen.frame()

    # ── Phase A: transparent small window ──
    print("\n[A] Transparent small window (400x300)...")
    win_a = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(100, 100, 400, 300),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win_a.setOpaque_(False)
    win_a.setBackgroundColor_(NSColor.clearColor())
    win_a.setLevel_(NSFloatingWindowLevel)
    win_a.setHasShadow_(False)
    va = FillView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 300))
    win_a.setContentView_(va)
    win_a.makeKeyAndOrderFront_(None)
    ok = pump_events(app, 3, "[A]")
    win_a.orderOut_(None)
    if not ok:
        print("=> Transparency is the problem!")
        return

    # ── Phase B: transparent FULLSCREEN window ──
    print("\n[B] Transparent fullscreen window...")
    win_b = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        sf,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win_b.setOpaque_(False)
    win_b.setBackgroundColor_(NSColor.clearColor())
    win_b.setLevel_(NSFloatingWindowLevel)
    win_b.setHasShadow_(False)
    win_b.setIgnoresMouseEvents_(True)
    vb = FillView.alloc().initWithFrame_(sf)
    win_b.setContentView_(vb)
    win_b.makeKeyAndOrderFront_(None)
    ok = pump_events(app, 3, "[B]")
    win_b.orderOut_(None)
    if not ok:
        print("=> Fullscreen transparent is the problem!")
        return

    # ── Phase C: app.run() with opaque small window ──
    print("\n[C] Opaque small window + app.run() for 3s...")
    win_c = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(100, 100, 400, 300),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False,
    )
    win_c.setOpaque_(True)
    win_c.setBackgroundColor_(NSColor.blueColor())
    win_c.setLevel_(NSFloatingWindowLevel)
    vc = FillView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 300))
    win_c.setContentView_(vc)
    win_c.makeKeyAndOrderFront_(None)

    # Schedule stop after 3s
    from Foundation import NSTimer, NSObject
    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        3.0, stopper, b'fire:', None, False
    )
    print("  Calling app.run()...")
    try:
        app.run()
        print("  [C]: survived")
    except Exception as e:
        print(f"  [C] EXCEPTION: {e}")
        traceback.print_exc()
        print("=> app.run() is the problem!")
        return

    print("\n=== All phases passed ===")


if __name__ == '__main__':
    main()
