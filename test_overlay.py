#!/usr/bin/env python3
"""
Test v7 — overlay + pynput = does pynput cause the crash?
"""
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSMakeRect, NSObject, NSTimer
import time, traceback

# Test WITH pynput
try:
    from pynput import keyboard
    HAS_PYNPUT = True
    print("pynput imported OK")
except ImportError:
    HAS_PYNPUT = False
    print("pynput NOT available")


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

    screen = NSScreen.mainScreen()
    frame = screen.frame()

    # Create window (same as test v5 — works fine)
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

    # ── NOW add pynput ──
    if HAS_PYNPUT:
        print("Starting pynput keyboard listener...")
        pressed = set()

        def on_press(key):
            pressed.add(key)

        def on_release(key):
            pressed.discard(key)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        try:
            listener.start()
            print("pynput listener started OK")
        except Exception as e:
            print(f"pynput FAILED: {e}")
            traceback.print_exc()

    # Run app.run() for 5 seconds
    print("Running app.run() for 5s...")
    class Stopper(NSObject):
        def fire_(self, t):
            NSApplication.sharedApplication().stop_(None)
    stopper = Stopper.alloc().init()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        5.0, stopper, b'fire:', None, False
    )
    try:
        app.run()
        print("SURVIVED with pynput!")
    except Exception as e:
        print(f"CRASHED: {e}")
        traceback.print_exc()

    if HAS_PYNPUT:
        listener.stop()


if __name__ == '__main__':
    main()
