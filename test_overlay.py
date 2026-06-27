#!/usr/bin/env python3
"""
Minimal overlay test v2 — with AppDelegate pattern + actual window visibility.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSLog, NSMakeRect
from PyObjCTools import AppHelper


class TestView(NSView):

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        c = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.2, 0.2, 0.5)
        c.set()
        NSRectFill(self.bounds())


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        NSLog("App did finish launching")

        screen = NSScreen.mainScreen()
        frame = screen.frame()
        NSLog(f"Screen frame: {frame}")

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("AirPin Test")
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setIgnoresMouseEvents_(True)
        self.window.setHasShadow_(False)
        self.window.setReleasedWhenClosed_(False)

        view = TestView.alloc().initWithFrame_(frame)
        self.window.setContentView_(view)

        self.window.makeKeyAndOrderFront_(None)
        NSLog("Window orderFront done")
        print("Window shown OK! You should see a red tint. Ctrl+C to quit.")


def main():
    print("Minimal overlay test v2...")
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    try:
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    except KeyboardInterrupt:
        print("Interrupted.")
    print("Done.")


if __name__ == '__main__':
    main()
