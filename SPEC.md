# AirPin macOS — Build Spec

## Goal
Port AirPin's single-screen 3DoF spatial head tracking to macOS for RayNeo Air 4 Pro glasses.

## What AirPin (Windows) Does
1. Reads IMU data from RayNeo Air glasses via RayNeoSDK.dll (USB HID)
2. Complementary filter: gyro (99.9%) + accel (0.1%) → yaw/pitch/roll
3. Smooth Follow: detects movement hysteresis, freezes output when still, silently corrects drift
4. Screen capture → renders on transparent overlay → output to glasses (duplicate mode)
5. Audio routing to glasses speaker
6. Global hotkeys (Ctrl+Alt+R recenter, Ctrl+Alt+T toggle yaw, etc.)

## macOS Architecture

### Module 1: IMU Reader (`imu_reader.py`)
- **Approach**: Use verncat/RayNeo-Air-3S-Pro-OpenVR SDK approach — direct USB HID via IOKit
- On macOS, use `hidapi` Python package (`pip install hidapi`) to read HID reports
- RayNeo glasses appear as a USB HID device (VID: 0x27C8, PID varies by model)
- IMU data arrives as 64-byte HID reports containing: accel (3x float), gyro (3x float), magnet (3x float), temperature, timestamp
- Research verncat's HID report parser to understand byte layout
- Poll at 500Hz in background thread
- Expose: get_orientation() → (yaw, pitch, roll) in radians

### Module 2: IMU Tracker (`imu_tracker.py`)
- Direct port from AirPin's airpin/imu_tracker.py
- Complementary filter: CF_ALPHA=0.999 for pitch/roll, yaw is pure integration
- EMA smoothing: alpha=0.035
- Bias calibration: first 500 samples at startup
- Output deadzone: 0.5°
- Angle normalization: keep all angles in [-π, π]

### Module 3: Smooth Follow (`smooth_follow.py`)
- Direct port from AirPin's airpin/smooth_follow.py — ZERO changes to algorithm
- Hysteresis: start tracking at >3°/s, stop at <0.9°/s after 15 frames
- Output freeze when still
- Invisible drift correction: after 2s stillness, correct at 0.5°/s

### Module 4: Screen Capture (`screen_capture.py`)
- Use `CGDisplayCreateImage` via PyObjC or `pyobjc-framework-Quartz`
- Alternative: `mss` library for simple approach
- Capture primary display at configurable FPS (default 120)
- Return numpy array of pixel data

### Module 5: Overlay Window (`overlay_window.py`)
- Use PyObjC + AppKit to create a borderless, transparent, floating window
- Key properties:
  - `NSFloatingWindowLevel` (above all apps, below screensaver)
  - `ignoresMouseEvents = True` (clicks pass through)
  - `opaque = False`, `backgroundColor = NSColor.clearColor`
  - `level = CGShieldingWindowLevel() + 1` or `NSFloatingWindowLevel`
- Fullscreen overlay on primary display
- Render captured framebuffer with yaw/pitch offset applied
- Custom cursor drawn on overlay

### Module 6: Audio Router (`audio_router.py`)
- Use CoreAudio to switch system output to RayNeo glasses
- RayNeo appears as a USB audio device
- Use `SwitchAudioSource` CLI tool OR `AudioHardwareServiceSetPropertyData` via PyObjC
- Simplest approach: use `SwitchAudioSource` (brew install switchaudio-osx)

### Module 7: Hotkey Manager (`hotkey_manager.py`)
- Global hotkeys via Carbon `RegisterEventHotKey` (via PyObjC)
- OR use `pynput` library for cross-platform approach
- Same hotkeys as AirPin:
  - Ctrl+Alt+R: Recenter
  - Ctrl+Alt+T: Toggle yaw tracking
  - Ctrl+Alt+P: Toggle pitch tracking
  - Ctrl+Alt+I: Invert yaw
  - Ctrl+Alt+H: Toggle HUD overlay
  - Ctrl+Alt+Q: Quit
  - Ctrl+Alt+0: Reset zoom

### Module 8: Main (`main.py`)
- Wire everything together
- CLI args: --no-imu, --no-audio, --monitor N, --sensitivity F, --fps N
- Main loop: capture frame → apply head offset → render overlay
- Graceful cleanup on Ctrl+C

## Key Differences from Windows AirPin
1. **IMU**: hidapi instead of ctypes.DLL
2. **Screen capture**: mss / CGDisplay instead of DXGI
3. **Overlay**: NSWindow/AppKit instead of Win32
4. **Audio**: CoreAudio/SwitchAudioSource instead of WASAPI
5. **Hotkeys**: pynput/Carbon instead of Win32 RegisterHotKey
6. **No virtual displays**: macOS limitation, single-screen only

## Dependencies
```
hidapi>=0.14.0
numpy>=1.24.0
mss>=9.0.0
pynput>=1.7.0
PyObjC>=10.0  # for AppKit, Quartz, CoreAudio
```

## Project Structure
```
airpin-mac/
├── README.md
├── requirements.txt
├── main.py
├── config.py
├── imu_reader.py        # HID IMU reading via hidapi
├── imu_tracker.py       # Complementary filter + bias cal
├── smooth_follow.py     # Drift correction (direct port)
├── screen_capture.py    # macOS screen capture
├── overlay_window.py    # Transparent overlay AppKit window
├── audio_router.py      # CoreAudio switching
├── hotkey_manager.py    # Global hotkeys
└── SPEC.md              # This file
```

## Build Order
1. Clone this repo
2. Set up venv + install dependencies
3. Implement smooth_follow.py (pure algorithm, no macOS deps)
4. Implement imu_tracker.py (depends on smooth_follow)
5. Implement imu_reader.py (hidapi-based, research verncat's approach)
6. Implement screen_capture.py (mss first, CGDisplay as fallback)
7. Implement overlay_window.py (PyObjC)
8. Implement hotkey_manager.py (pynput)
9. Implement audio_router.py
10. Implement main.py (wire everything)
11. Implement config.py
12. Write README.md
13. Test each module individually
14. Push to GitHub

## Reference Repos
- AirPin (Windows): https://github.com/arigandores/AirPin
- Air4-Pro-Gyro-PC: https://github.com/peterradzisz/Air4-Pro-Gyro-PC
- verncat RayNeo SDK (IMU protocol): https://github.com/verncat/RayNeo-Air-3S-Pro-OpenVR
