"""
Global configuration for AirPin macOS.

All tunable parameters in one place.
"""

# RayNeo Air 4 Pro USB HID IDs
RAYNEO_VID = 0x1BBB
RAYNEO_PID = 0xAF50

# Display settings
TARGET_FPS = 120
CAPTURE_FPS = 120
MONITOR_INDEX = 0  # 0 = primary display

# IMU / Head tracking
IMU_RATE_HZ = 500
HEAD_TRACKING_SENSITIVITY = 1.0
INVERT_YAW = False
INVERT_PITCH = False
PITCH_ENABLED = False  # False = only track yaw (recommended)
COMPLEMENTARY_ALPHA = 0.999  # CF_ALPHA: gyro vs accel weighting

# Complementary filter
# CF_ALPHA = 0.999 means 99.9% gyro, 0.1% accel
CF_ALPHA = 0.999

# EMA smoothing alpha at 500Hz (equivalent to ~0.25 at 60Hz)
EMA_ALPHA = 0.035

# Gyro deadzone in rad/s — filters noise when head is still
GYRO_DEADZONE = 0.0

# Output deadzone on displayed yaw (degrees)
OUTPUT_DEADZONE_DEG = 0.5

# Bias calibration samples at startup
BIAS_SAMPLES = 500  # ~1 second at 500Hz

# Auto-bias: update bias ONLY when head is VERY still for a LONG time
STILL_THRESHOLD = 0.01   # rad/s — very strict stillness detection
STILL_SAMPLES = 1000     # 2 seconds at 500Hz before updating
BIAS_LEARN_RATE = 0.0002 # very slow adaptation

# Yaw decay (1.0 = no decay, <1.0 = slowly return to center)
YAW_DECAY = 1.0

# FOV settings for rendering
FOV_HORIZONTAL_DEG = 46.0
FOV_VERTICAL_DEG = 25.0

# Audio routing
AUDIO_ENABLED = True
GLASSES_AUDIO_DEVICE = "RayNeo"  # substring match for output device name
AUDIO_BUFFER_FRAMES = 1024
AUDIO_SAMPLE_RATE = 48000

# Overlay window
OVERLAY_OPACITY = 1.0  # 0.0-1.0 (1.0 = fully opaque overlay, 0.0 = invisible)
SHOW_HUD = True

# Hotkey configuration
# Uses pynput key names:
# ctrl + alt + key
HOTKEYS = {
    'recenter':        ('r',),
    'toggle_hud':      ('h',),
    'toggle_tracking': ('t',),
    'invert_yaw':      ('i',),
    'toggle_pitch':    ('p',),
    'quit':            ('q',),
    'zoom_reset':      ('0',),
}

# Zoom settings
ZOOM_DEFAULT = 1.0
ZOOM_STEP = 0.1
ZOOM_MIN = 0.5
ZOOM_MAX = 3.0

# Path to SwitchAudioSource CLI
SWITCH_AUDIO_SOURCE_PATH = None  # None = auto-detect in PATH
