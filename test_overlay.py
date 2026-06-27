#!/usr/bin/env python3
"""
Minimal transparent overlay test.
If THIS crashes, the problem is fundamental to PyObjC + transparent windows on this macOS.
If it works, the problem is in AirPin's code.
"""
import sys
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSLog
from PyObjCTools import AppHelper


class TestView(NSView):
    """Bare minimum view — does nothing in drawRect."""

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        # Draw a translucent red rect so we can see if the window appears
        c = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.2, 0.2, 0.3)
        c.set()
        NSRectFill(self.bounds())


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        NSLog("App did finish launching")

        screen = NSScreen.mainScreen()
        frame = screen.frame()
        NSLog(f"Screen frame: {frame}")

        try:
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            )
            self.window.setOpaque_(False)
            self.window.setBackgroundColor_(NSColor.clearColor())
            self.window.setLevel_(NSFloatingWindowLevel)
            self.window.setIgnoresMouseEvents_(True)
            self.window.setHasShadow_(False)
            self.window.setReleasedWhenClosed_(False)

            view = TestView.alloc().initWithFrame_(frame)
            self.window.setContentView_(view)

            self.window.makeKeyAndOrderFront_(None)
            NSLog("Window shown OK!")
            print("Window shown OK!")
        except Exception as e:
            NSLog(f"WINDOW ERROR: {e}")
            print(f"WINDOW ERROR: {e}")
            import traceback
            traceback.print_exc()
            AppHelper.stopEventLoop()


def main():
    print("Minimal overlay test starting...")
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    print("Entering event loop (Ctrl+C to quit)...")
    try:
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    except Exception as e:
        print(f"EVENT LOOP ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("Done.")


if __name__ == '__main__':
    main()
