#!/usr/bin/env python3
"""
Overlay test v4 — capture the ObjC exception that causes SIGTRAP.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSLog
from PyObjCTools import AppHelper
import traceback


class TestView(NSView):
    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        try:
            c = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.2, 0.2, 0.5)
            c.set()
            NSRectFill(self.bounds())
        except Exception as e:
            print(f"drawRect EXCEPTION: {e}")
            traceback.print_exc()


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        print(">> applicationDidFinishLaunching called!")
        NSLog(">> didFinishLaunching")

        screen = NSScreen.mainScreen()
        frame = screen.frame()

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
        self.window.display()
        print(">> Window should be visible now!")

    def applicationWillTerminate_(self, notification):
        print(">> terminating")


def main():
    print("Starting v4...")
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    print("Calling runConsoleEventLoop...")
    try:
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()

    print("Done.")


if __name__ == '__main__':
    main()
