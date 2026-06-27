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

Renders screen capture frames as CGImages with head-tracking offset
and zoom transforms applied via CoreGraphics context.

Replaces Win32 transparent overlay from Windows AirPin.
"""

import ctypes
import threading
import time
import sys

import numpy as np

try:
    import objc
    from AppKit import (
        NSApplication, NSWindow, NSView, NSColor, NSBackingStoreBuffered,
        NSScreen, NSBorderlessWindowMask, NSFloatingWindowLevel,
        NSApplicationActivationPolicyAccessory, NSEvent,
        NSGraphicsContext,
    )
    from Quartz import (
        CGRectMake,
        CGDisplayBounds, CGMainDisplayID,
        CGImageCreate, CGDataProviderCreateWithData,
        CGColorSpaceCreateDeviceRGB,
        kCGImageAlphaNoneSkipFirst, kCGBitmapByteOrder32Little,
        kCGRenderingIntentDefault,
        kCGNullWindowID, kCGWindowListOptionOnScreenOnly,
        CGWindowListCopyWindowInfo,
        CGContextSaveGState, CGContextRestoreGState,
        CGContextTranslateCTM, CGContextScaleCTM,
        CGContextDrawImage,
    )
    from Foundation import NSMakeRect, NSPoint, NSZeroRect
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

import config


class OverlayView(NSView):
    """Custom NSView for rendering captured frames with head-tracking offset."""

    def initWithFrame_(self, frame):
        self = objc.super(OverlayView, self).initWithFrame_(frame)
        if self is not None:
            self._overlay_window = None  # back-reference to OverlayWindow
        return self

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        """Draw the current frame with head-tracking offset + zoom."""
        overlay = self._overlay_window
        if overlay is None:
            return

        # Get current frame under lock — keep reference alive!
        with overlay._frame_lock:
            frame = overlay._current_frame
            ox = overlay._offset_x
            oy = overlay._offset_y
            zoom = overlay._zoom
            if frame is not None:
                frame = np.ascontiguousarray(frame)

        if frame is None:
            return

        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return

        # Keep data alive — store on self so GC doesn't collect it mid-draw
        self._draw_data = bytes(frame)
        data = self._draw_data

        provider = CGDataProviderCreateWithData(None, data, len(data), None)
        color_space = CGColorSpaceCreateDeviceRGB()
        bitmap_info = kCGImageAlphaNoneSkipFirst | kCGBitmapByteOrder32Little

        cg_image = CGImageCreate(
            w, h, 8, 32, w * 4,
            color_space, bitmap_info, provider,
            None, False, kCGRenderingIntentDefault
        )

        if cg_image is None:
            return

        # Get CGContext from current NSGraphicsContext
        ns_ctx = NSGraphicsContext.currentContext()
        if ns_ctx is None:
            return
        ctx = ns_ctx.CGContext()

        CGContextSaveGState(ctx)

        # No Y flip — draw in natural orientation
        CGContextDrawImage(ctx, CGRectMake(ox, oy, w, h), cg_image)

        CGContextRestoreGState(ctx)



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

        # Frame data (protected by lock)
        self._frame_lock = threading.Lock()
        self._current_frame = None  # numpy array (H,W,4) BGRA
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._zoom = 1.0

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
            self._app.finishLaunching()

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

        # Store window number for capture exclusion
        self._window_id = self._window.windowNumber()

        # Create content view with back-reference
        self._view = OverlayView.alloc().initWithFrame_(frame)
        self._view._overlay_window = self
        self._window.setContentView_(self._view)

        # Show window
        self._window.makeKeyAndOrderFront_(None)
        self._running = True

        print(f"  Overlay: {self.width}x{self.height} "
              f"({self.width}x{self.height} pts) on primary display")

    def render_frame(self, frame, offset_x=0.0, offset_y=0.0, zoom=1.0):
        """Queue a captured frame for rendering.

        Args:
            frame: numpy array (H, W, 4) BGRA from screen capture
            offset_x: horizontal pixel offset from head tracking
            offset_y: vertical pixel offset
            zoom: zoom factor (1.0 = native)
        """
        if frame is None:
            return

        with self._frame_lock:
            self._current_frame = frame
            self._offset_x = offset_x
            self._offset_y = offset_y
            self._zoom = zoom

        # Trigger Cocoa redraw (NSApp.run() loop will handle display)
        if self._view:
            self._view.setNeedsDisplay_(True)

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

    @property
    def window_id(self):
        """Return CG window ID for capture exclusion."""
        return getattr(self, '_window_id', 0)
