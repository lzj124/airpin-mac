# AirPin macOS

**Single-screen 3DoF spatial head tracking for RayNeo Air 4 Pro AR glasses on macOS.**

Put on the glasses. See your desktop floating in front of you. Turn your head — the screen shifts to stay in place, like a virtual monitor pinned to the wall.

Port of [AirPin (Windows)](https://github.com/arigandores/AirPin) and [AirPin Extended](https://github.com/peterradzisz/Air4-Pro-Gyro-PC) to macOS.

## Features

- **3DoF Head Tracking**: Yaw (left/right) + optional pitch (up/down) using IMU data
- **Smooth Follow Filter**: 1:1 tracking when moving, freeze when still, silent drift correction
- **Complementary Filter**: 99.9% gyro + 0.1% accelerometer fusion with bias calibration
- **Transparent Overlay**: Floating AppKit window that ignores mouse events
- **Audio Routing**: Switch system audio output to glasses via SwitchAudioSource
- **Global Hotkeys**: Ctrl+Alt combinations for recenter, toggle tracking, etc.
- **Direct HID Reading**: Reads IMU data via hidapi — no proprietary SDK required

## Requirements

- **Hardware**: RayNeo Air 4 Pro glasses
- **Connection**: USB-C (for IMU data + audio) + HDMI/DP (for display)
- **OS**: macOS 12+ (Monterey or later)
- **Python**: 3.10+
- **Display**: Glasses as extended/secondary display

## Quick Start

### 1. Install Dependencies

```bash
# Clone the repo
git clone https://github.com/lzj124/airpin-mac.git
cd airpin-mac

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install SwitchAudioSource for audio routing (optional)
brew install switchaudio-osx
```

### 2. Connect the Glasses

1. Connect glasses to your Mac via USB-C (provides IMU data + audio)
2. Connect glasses to your Mac via HDMI (provides display)
3. Go to **System Settings > Displays** and set glasses to **Extended Desktop**

### 3. Run

```bash
python main.py
```

For best results, make sure the glasses are set as a secondary display in Extended mode (mirrored mode can cause capture issues).

### 4. Controls

All hotkeys: hold **Ctrl+Alt** then press the key:

| Key | Action |
|-----|--------|
| **R** | Recenter (reset head position) |
| **T** | Toggle head tracking on/off |
| **P** | Toggle pitch tracking |
| **I** | Invert yaw direction |
| **H** | Toggle HUD overlay |
| **0** | Reset zoom |
| **Q** | Quit |

### 5. HID Permissions

On macOS, you may need to grant HID access permissions:

1. If you get "device not found", check **System Settings > Privacy & Security > Input Monitoring**
2. Add Terminal (or your terminal app) to the allowed list
3. Restart your terminal

## Architecture

```
airpin-mac/
├── main.py              # Entry point — wires all modules together
├── config.py            # Configuration (VID/PID, tuning params)
├── imu_reader.py        # HID IMU reading via hidapi (replaces RayNeoSDK.dll)
├── imu_tracker.py       # Complementary filter + bias calibration
├── smooth_follow.py     # Drift correction filter (direct port from AirPin)
├── screen_capture.py    # macOS screen capture via mss
├── overlay_window.py    # Transparent AppKit floating overlay
├── hotkey_manager.py    # Global hotkeys via pynput
├── audio_router.py      # Audio routing to glasses speaker
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── SPEC.md              # Full architecture spec
```

### macOS ↔ Windows Replacements

| Component | Windows (AirPin) | macOS (AirPin Mac) |
|-----------|-----------------|-------------------|
| IMU Reading | RayNeoSDK.dll | hidapi (direct USB HID) |
| Screen Capture | DXGI (dxcam) | mss library |
| Overlay Window | Win32 (pygame) | AppKit (NSWindow) |
| Audio Routing | WASAPI (sounddevice) | SwitchAudioSource CLI |
| Hotkeys | GetAsyncKeyState | pynput |
| Virtual Displays | Parsec VDD | Not supported (macOS limitation) |

## Key Differences from Windows AirPin

1. **Single screen only**: macOS doesn't support virtual displays via VDD
2. **Direct HID access**: No proprietary DLL — reads IMU reports directly from USB
3. **Native overlay**: Uses AppKit instead of pygame/Win32 for lower latency
4. **No spatial renderer**: Simpler rendering without OpenGL 3D pipeline
5. **Audio via CLI**: Uses SwitchAudioSource instead of WASAPI loopback

## Configuration

Edit `config.py` to tune:

- `RAYNEO_VID` / `RAYNEO_PID`: USB device IDs (default: 0x1BBB/0xAF50)
- `CF_ALPHA`: Complementary filter weighting (0.999 = 99.9% gyro)
- `TARGET_FPS` / `CAPTURE_FPS`: Frame rate for capture and rendering
- `HEAD_TRACKING_SENSITIVITY`: Yaw sensitivity multiplier
- `PITCH_ENABLED`: Enable/disable pitch tracking
- `BIAS_SAMPLES`: Number of samples for gyro bias calibration
- `GLASSES_AUDIO_DEVICE`: Substring to match audio device name

## CLI Options

```
python main.py [OPTIONS]

Options:
  --no-imu          Run without IMU head tracking
  --no-audio        Don't route audio to glasses
  --monitor N       Capture monitor N (default: 0 = primary)
  --sensitivity F   Head tracking sensitivity (default: 1.0)
  --fps N           Capture FPS (default: from config)
```

## Troubleshooting

### "No RayNeo device found"
- Ensure glasses are connected via USB-C
- Check System Settings > Privacy & Security > Input Monitoring
- Try a different USB-C cable (some cables are charge-only)

### "Screen capture failed"
- Ensure glasses are set to Extended Desktop (not Mirrored)
- Check System Settings > Displays

### "Audio not routing to glasses"
- Install SwitchAudioSource: `brew install switchaudio-osx`
- Check that glasses appear as an audio output device in System Settings > Sound

### "Overlay not appearing"
- Ensure `pyobjc-framework-Cocoa` and `pyobjc-framework-Quartz` are installed
- Check that the app has Accessibility permissions

## Credits

- [AirPin](https://github.com/arigandores/AirPin) — Original Windows version
- [AirPin Extended](https://github.com/peterradzisz/Air4-Pro-Gyro-PC) — Extended fork
- [verncat RayNeo SDK](https://github.com/verncat/RayNeo-Air-3S-Pro-OpenVR) — HID protocol reference

## License

MIT License — see [AirPin](https://github.com/arigandores/AirPin) for original license.
