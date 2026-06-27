#!/usr/bin/env python3
"""
Overlay test v5 — isolate the crash systematically.
Try 3 things: empty drawRect, opaque window, proper exception handler.
"""
import objc
from AppKit import (
    NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
    NSScreen, NSWindowStyleMaskBorderless, NSFloatingWindowLevel,
    NSApplicationActivationPolicyAccessory, NSRectFill,
)
from Foundation import NSObject, NSLog
from PyObjCTools import AppHelper
import traceback
import sys

# Install ObjC uncaught exception handler
class ExcHandler(NSObject):
    def handleException_(self, exc):
        print(f">>> OBJC EXCEPTION CAUGHT: {exc}")
        print(f">>> reason: {exc.reason()}")
        traceback.print_exc()

from Foundation import NSException, NSSetUncaughtExceptionHandler

handler = ExcHandler.alloc().init()

def setup_handler():
    try:
        NSSetUncaughtExceptionHandler_(handler.handleException_)
        print("Exception handler installed")
    except:
        print("Could not install exception handler")


class EmptyView(NSView):
    """View that does literally nothing in drawRect."""
    def isOpaque(self):
        return True  # opaque = no transparency issues

    def drawRect_(self, rect):
        # Fill solid white — use the imported NSRectFill
        NSColor.whiteColor().set()
        NSRectFill(self.bounds())


def main():
    print("=== Test v5 ===")
    setup_handler()

    print("1. Creating NSApp...")
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app.finishLaunching()

    print("2. Getting screen...")
    screen = NSScreen.mainScreen()
    frame = screen.frame()
    print(f"   {frame.size.width}x{frame.size.height}")

    print("3. Creating OPAQUE window...")
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(100, 100, 400, 300),  # small window, not fullscreen
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    win.setOpaque_(True)  # OPAQUE — no transparency
    win.setBackgroundColor_(NSColor.blueColor())  # solid blue bg
    win.setLevel_(NSFloatingWindowLevel)
    win.setHasShadow_(True)

    print("4. Creating view...")
    view = EmptyView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 300))
    win.setContentView_(view)

    print("5. Showing window...")
    win.makeKeyAndOrderFront_(None)

    print("6. Running event loop for 5 seconds...")
    print("   You should see a small white window with blue background.")

    import time
    deadline = time.time() + 5

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
            print(f"EVENT LOOP EXCEPTION: {e}")
            traceback.print_exc()
            break

    print("7. Done! Survived 5 seconds.")


if __name__ == '__main__':
    from Foundation import NSMakeRect
    main()
