"""
IMU Reader for RayNeo Air 4 Pro on macOS.

Reads IMU data (gyro, accel, magnet, temperature) directly from
the USB HID device using hidapi — replaces RayNeoSDK.dll on Windows.

HID Report Layout (64 bytes, per verncat's XRPacket.h):

  XrHidSensorEvent (XrDataPacket):
    Bytes 0-3:   Header (magic, type, length)
    Bytes 4-15:  acc[3] (float32 x3) — accelerometer m/s^2
    Bytes 16-27: gyro[3] (float32 x3) — gyroscope rad/s
    Bytes 28-31: temperature (float32)
    Bytes 32-39: magnet[2] (float32 x2)
    Bytes 40-43: tick (uint32) — timestamp in ms
    Bytes 44-47: psensor (float32)
    Bytes 48-51: lsensor (float32)
    Bytes 52-55: magnet_2 (float32) — 3rd magnet axis
    Bytes 56-59: count (uint32) — sample counter
    Bytes 60-61: reserved[2]
    Byte 62:     checksum (uint8)
    Byte 63:     flag (uint8)

  XrHidCommand (for sending commands):
    Byte 0:      magic (0xAA)
    Byte 1:      type (command type)
    Byte 2:      value
    Bytes 3-54:  data (52 bytes)
    Bytes 55-63: reserved (9 bytes)

Reference:
  https://github.com/verncat/RayNeo-Air-3S-Pro-OpenVR
  (rayneoSDKHeaders/device/usb/XRPacket.h)
"""

import struct
import threading
import time
import sys

try:
    import hid
    HAS_HIDAPI = True
except ImportError:
    HAS_HIDAPI = False

import config


# HID report magic byte
HID_MAGIC = 0xAA

# Report types
REPORT_TYPE_SENSOR = 0x01   # IMU sensor data
REPORT_TYPE_DEVINFO = 0xC8  # Device info response

# Command types
CMD_ENABLE_IMU = 0x01
CMD_DISABLE_IMU = 0x02


class ImuReader:
    """Reads IMU data from RayNeo glasses via USB HID on macOS."""

    def __init__(self, vid=None, pid=None):
        self._vid = vid or config.RAYNEO_VID
        self._pid = pid or config.RAYNEO_PID
        self._device = None
        self._opened = False
        self._lock = threading.Lock()
        self._sample_count = 0
        self._last_tick = 0

    def open(self) -> bool:
        """Open the HID device. Returns True on success."""
        if not HAS_HIDAPI:
            raise ImportError(
                "hidapi package is required. Install with: pip install hidapi"
            )

        # Enumerate all HID devices to find the glasses
        glasses_path = None
        for dev_dict in hid.enumerate(self._vid, self._pid):
            # On macOS, check that this is the right device
            # Glasses typically report as a generic HID device
            p = dev_dict['path']
            if p:
                glasses_path = p
                print(f"  Found RayNeo glasses: "
                      f"VID=0x{dev_dict['vendor_id']:04X} "
                      f"PID=0x{dev_dict['product_id']:04X} "
                      f"'{dev_dict.get('product_string', '')}' "
                      f"at {p}")
                break

        if not glasses_path:
            print(f"  No RayNeo device found (VID=0x{self._vid:04X}, PID=0x{self._pid:04X})")
            return False

        try:
            self._device = hid.device()
            self._device.open_path(glasses_path)
            self._device.set_nonblocking(True)  # Don't block on read
            self._opened = True
            print(f"  IMU reader: device opened successfully")
            return True
        except Exception as e:
            print(f"  IMU reader: failed to open device: {e}")
            return False

    def close(self):
        """Close the HID device."""
        with self._lock:
            if self._device:
                try:
                    self._device.close()
                except Exception:
                    pass
                self._device = None
            self._opened = False

    def read_sample(self):
        """Read a single IMU sample from the HID device.

        Returns:
            dict with keys: acc, gyro_rad, gyro_dps, magnet, temperature,
            psensor, lsensor, tick, count, flag, checksum
            OR None if no data available.
        """
        if not self._opened or self._device is None:
            return None

        try:
            with self._lock:
                # Read up to 64 bytes (one HID report)
                data = self._device.read(64, timeout_ms=5)
        except Exception:
            return None

        if not data or len(data) < 64:
            return None

        return self._parse_report(bytes(data))

    def read_sample_blocking(self, timeout_ms=100):
        """Read a single IMU sample, blocking until data arrives.

        Returns dict or None on timeout.
        """
        if not self._opened or self._device is None:
            return None

        try:
            with self._lock:
                data = self._device.read(64, timeout_ms=timeout_ms)
        except Exception:
            return None

        if not data or len(data) < 64:
            return None

        return self._parse_report(bytes(data))

    def _parse_report(self, data: bytes):
        """Parse a 64-byte HID report into a sample dict.

        Layout (XrHidSensorEvent / XrDataPacket):
          [0]     magic        uint8
          [1]     type         uint8
          [2-3]   length       uint16 LE
          [4-15]  acc[3]       3x float32 LE  (m/s^2)
          [16-27] gyro[3]      3x float32 LE  (rad/s)
          [28-31] temperature  float32 LE
          [32-39] magnet[2]    2x float32 LE
          [40-43] tick         uint32 LE (ms)
          [44-47] psensor      float32 LE
          [48-51] lsensor      float32 LE
          [52-55] magnet_2     float32 LE (3rd axis)
          [56-59] count        uint32 LE
          [60-61] reserved     uint8[2]
          [62]    checksum     uint8
          [63]    flag         uint8
        """
        try:
            magic = data[0]
            report_type = data[1]

            # Parse sensor data from the fixed layout
            acc = struct.unpack_from('<fff', data, 4)
            gyro_rad = struct.unpack_from('<fff', data, 16)
            temperature = struct.unpack_from('<f', data, 28)[0]
            magnet_xy = struct.unpack_from('<ff', data, 32)
            tick = struct.unpack_from('<I', data, 40)[0]
            psensor = struct.unpack_from('<f', data, 44)[0]
            lsensor = struct.unpack_from('<f', data, 48)[0]
            magnet_z = struct.unpack_from('<f', data, 52)[0]
            count = struct.unpack_from('<I', data, 56)[0]
            checksum = data[62]
            flag = data[63]

            # Convert gyro from rad/s to deg/s
            gyro_dps = tuple(g * 180.0 / 3.141592653589793 for g in gyro_rad)

            self._sample_count += 1
            self._last_tick = tick

            return {
                'acc': list(acc),            # m/s^2
                'gyro_rad': list(gyro_rad),  # rad/s
                'gyro_dps': list(gyro_dps), # deg/s
                'magnet': [magnet_xy[0], magnet_xy[1], magnet_z],
                'temperature': temperature,
                'psensor': psensor,
                'lsensor': lsensor,
                'tick': tick,
                'count': count,
                'flag': flag,
                'checksum': checksum,
                'type': report_type,
            }
        except struct.error as e:
            # Malformed report — skip
            return None

    def send_command(self, command_type: int, value: int = 0,
                     payload: bytes = b'') -> bool:
        """Send a command to the glasses via HID.

        Command format (XrHidCommand, 64 bytes):
          [0]     magic   uint8  (0xAA)
          [1]     type    uint8  (command type)
          [2]     value   uint8
          [3-54]  data    uint8[52]
          [55-63] reserved uint8[9]
        """
        if not self._opened or self._device is None:
            return False

        buf = bytearray(64)
        buf[0] = HID_MAGIC
        buf[1] = command_type & 0xFF
        buf[2] = value & 0xFF

        # Copy payload (max 52 bytes)
        payload_len = min(len(payload), 52)
        buf[3:3 + payload_len] = payload[:payload_len]

        try:
            with self._lock:
                written = self._device.write(bytes(buf))
            return written == 64
        except Exception as e:
            print(f"  IMU command failed: {e}")
            return False

    def enable_imu(self) -> bool:
        """Send IMU enable command to the glasses."""
        return self.send_command(CMD_ENABLE_IMU, 0x01)

    def disable_imu(self) -> bool:
        """Send IMU disable command to the glasses."""
        return self.send_command(CMD_DISABLE_IMU, 0x00)

    @property
    def is_open(self) -> bool:
        return self._opened

    @property
    def sample_count(self) -> int:
        return self._sample_count


# ── Standalone test ──
if __name__ == '__main__':
    print("RayNeo Air 4 Pro — IMU Reader Test")
    print(f"  VID: 0x{config.RAYNEO_VID:04X}, PID: 0x{config.RAYNEO_PID:04X}")
    print()

    reader = ImuReader()
    if not reader.open():
        print("No device found. Make sure glasses are connected via USB-C.")
        sys.exit(1)

    print("Reading IMU samples (Ctrl+C to stop)...")
    print(f"{'Tick':>8} {'Gyro X':>10} {'Gyro Y':>10} {'Gyro Z':>10} "
          f"{'Acc X':>10} {'Acc Y':>10} {'Acc Z':>10}")

    try:
        while True:
            sample = reader.read_sample()
            if sample:
                g = sample['gyro_rad']
                a = sample['acc']
                print(f"{sample['tick']:>8} "
                      f"{g[0]:>10.4f} {g[1]:>10.4f} {g[2]:>10.4f} "
                      f"{a[0]:>10.2f} {a[1]:>10.2f} {a[2]:>10.2f}")
            else:
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        reader.close()
