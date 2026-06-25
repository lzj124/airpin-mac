"""
Transparent floating overlay window for macOS using PyObjC (AppKit).

Creates a borderless, transparent, floating window that covers the
primary display. The window ignores mouse events (clicks pass through),
sits above all normal windows but below the screensaver.

Key properties:
  - NSFloatingWindowLevel (above all apps, below screensaver)
  - ignoresMouseEvents = True (clicks pass through to underlying windows)
  - opaque = False, backgroundColor = NSColor.clearColor
  - Borderless, full-screen on primary display

Replaces Win32 transparent overlay from Windows AirPin.
"""

import threading
import time
import sys

try:
    from AppKit import (
        NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
        NSScreen, NSBorderlessWindowMask, NSFloatingWindowLevel,
        NSApplicationActivationPolicyAccessory, NSEvent,
    )
    from Quartz import (
        CGDisplayBounds, CGMainDisplayID,
        kCGNullWindowID, kCGWindowListOptionOnScreenOnly,
        CGWindowListCopyWindowInfo,
    )
    from Foundation import NSMakeRect, NSPoint, NSZeroRect
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

import config


class OverlayView(NSView):
    """Custom NSView for rendering the overlay content.

    Subclasses override drawRect_ or use OpenGL/Metal for rendering.
    For simplicity, we use a callback-based approach: the main loop
    provides a render function that gets called on each frame.
    """

    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
        if self is not None:
            self._render_callback = None
        return self

    def setRenderCallback_(self, callback):
        self._render_callback = callback

    def drawRect_(self, rect):
        if self._render_callback:
            self._render_callback(self, rect)

    def isOpaque(self):
        return False


class OverlayWindow:
    """Transparent floating overlay window on the primary display."""

    def __init__(self):
        if not HAS_APPKIT:
            raise ImportError(
                "PyObjC is required. Install with: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa"
            )

        self._app = None
        self._window = None
        self._view = None
        self._running = False
        self._thread = None

        # Get primary display bounds
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self._get_display_bounds()

    def _get_display_bounds(self):
        """Get primary display bounds in points (not pixels)."""
        main_display_id = CGMainDisplayID()
        bounds = CGDisplayBounds(main_display_id)
        self.x = int(bounds.origin.x)
        self.y = int(bounds.origin.y)
        self.width = int(bounds.size.width)
        self.height = int(bounds.size.height)

    def start(self):
        """Create and show the overlay window. Must be called from main thread."""
        if not NSApplication.sharedApplication().isRunning():
            self._app = NSApplication.sharedApplication()
            self._app.setActivationPolicy_(
                NSApplicationActivationPolicyAccessory
            )

        # Create window
        frame = NSMakeRect(self.x, self.y, self.width, self.height)
        style_mask = NSBorderlessWindowMask

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            NSBackingStoreBuffered,
            False,  # defer = NO
        )

        # Configure as transparent floating overlay
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setIgnoresMouseEvents_(True)
        self._window.setHasShadow_(False)
        self._window.setReleasedWhenClosed_(False)

        # Make it cover the full screen
        self._window.setFrame_display_(frame, True)

        # Create content view
        self._view = OverlayView.alloc().initWithFrame_(frame)
        self._window.setContentView_(self._view)

        # Show window
        self._window.makeKeyAndOrderFront_(None)
        self._running = True

        print(f"  Overlay: {self.width}x{self.height} "
              f"({self.width}x{self.height} pts) on primary display")

    def set_render_callback(self, callback):
        """Set the render callback for the overlay view."""
        if self._view:
            self._view.setRenderCallback_(callback)

    def refresh(self):
        """Force the overlay to redraw."""
        if self._view:
            self._view.setNeedsDisplay_(True)

    def run_event_loop(self):
        """Run the Cocoa event loop (blocking)."""
        if self._app:
            self._app.run()

    def stop_event_loop(self):
        """Stop the Cocoa event loop."""
        if self._app:
            self._app.stop_(None)

    def process_events(self, until_date=None):
        """Process pending events. Use for non-blocking main loops."""
        if self._app:
            if until_date:
                self._app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                    0xFFFFFFFF, until_date, 'kCFRunLoopDefaultMode', True
                )
            else:
                # Process all pending events without blocking
                while True:
                    event = self._app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                        0xFFFFFFFF, None, 'kCFRunLoopDefaultMode', True
                    )
                    if event is None:
                        break
                    self._app.sendEvent_(event)

    def hide(self):
        """Hide the overlay window."""
        if self._window:
            self._window.orderOut_(None)

    def show(self):
        """Show the overlay window."""
        if self._window:
            self._window.makeKeyAndOrderFront_(None)

    def toggle_mouse_events(self, ignore: bool):
        """Toggle whether mouse events pass through the overlay."""
        if self._window:
            self._window.setIgnoresMouseEvents_(ignore)

    def close(self):
        """Close and destroy the overlay window."""
        self._running = False
        if self._window:
            self._window.orderOut_(None)
            self._window.close()
            self._window = None
        self._view = None

    @property
    def is_running(self) -> bool:
        return self._running
