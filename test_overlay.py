#!/usr/bin/env python3
"""
Overlay test v3 — direct approach, no AppDelegate.
Create window BEFORE entering event loop.
"""
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject
from PyObjCTools import AppHelper


class TestView(NSView):
    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        c = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.2, 0.2, 0.5)
        c.set()
        NSRectFill(self.bounds())


def main():
    print("1. Creating NSApp...")
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    print("2. Getting screen...")
    screen = NSScreen.mainScreen()
    frame = screen.frame()
    print(f"   Screen: {frame.size.width}x{frame.size.height}")

    print("3. Creating window...")
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    win.setTitle_("AirPin Test")
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSFloatingWindowLevel)
    win.setIgnoresMouseEvents_(True)
    win.setHasShadow_(False)
    win.setReleasedWhenClosed_(False)

    print("4. Creating view...")
    view = TestView.alloc().initWithFrame_(frame)
    win.setContentView_(view)

    print("5. Ordering front...")
    win.makeKeyAndOrderFront_(None)
    win.display()

    print("6. Entering event loop. Ctrl+C to quit.")
    print("   You should see a RED tint over the whole screen now.")

    try:
        app.run()
    except KeyboardInterrupt:
        print("Interrupted.")

    print("Done.")


if __name__ == '__main__':
    main()
