"""
IMU tracker for RayNeo Air 4 Pro — macOS port.

Reads gyro/accel via imu_reader (hidapi), fuses into yaw/pitch/roll
using complementary filter, with bias calibration and EMA smoothing.

Port of AirPin's imu_tracker.py — replaces RayNeoSDK.dll with hidapi.
"""

import threading
import numpy as np
import math
import time

import config


class ImuTracker:
    """Complementary filter IMU tracker for RayNeo Air 4 Pro."""

    def __init__(self):
        self._reader = None  # ImuReader instance
        self.connected = False
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._imu_count = 0

        # Raw integrated angles from complementary filter
        self._raw_yaw = 0.0
        self._raw_pitch = 0.0
        self._raw_roll = 0.0

        # EMA-smoothed output
        self._yaw = 0.0
        self._pitch = 0.0
        self._roll = 0.0

        # Reference (set on recenter)
        self._ref_yaw = 0.0
        self._ref_pitch = 0.0
        self._ref_roll = 0.0

        # Bias calibration
        self._gyro_bias = np.zeros(3)
        self._bias_count = 0
        self._bias_done = False
        self._last_tick = 0
        self._cf_initialized = False

        # Gyro magnitude for movement detection
        self._last_gyro_mag = 0.0

        # Raw gyro values (rad/s) for smooth follow filter
        self._raw_gyro = np.zeros(3)

        # Output deadzone state
        self._still_counter = 0

    def start(self, reader=None):
        """Start IMU tracking.

        Args:
            reader: ImuReader instance (if None, creates one)
        """
        if reader is not None:
            self._reader = reader
        else:
            from imu_reader import ImuReader
            self._reader = ImuReader()

        if not self._reader.open():
            raise RuntimeError("IMU reader failed to open. Glasses connected?")

        self.connected = True
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        import atexit
        atexit.register(self.stop)

    def _poll_loop(self):
        """Main IMU polling loop — reads HID reports, runs complementary filter."""
        while self._running:
            sample = self._reader.read_sample()
            if sample is None:
                time.sleep(0.001)  # 1ms backoff
                continue

            self._imu_count += 1
            gyro = np.array(sample['gyro_rad'], dtype=np.float64)
            accel = np.array(sample['acc'], dtype=np.float64)

            # ── Initialize orientation from accel on first sample ──
            if not self._cf_initialized:
                ax, ay, az = accel
                self._raw_pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
                self._raw_roll = math.atan2(ay, az)
                self._raw_yaw = 0.0
                with self._lock:
                    self._yaw = 0.0
                    self._pitch = self._raw_pitch
                    self._roll = self._raw_roll
                    self._ref_yaw = 0.0
                    self._ref_pitch = self._raw_pitch
                    self._ref_roll = self._raw_roll
                self._cf_initialized = True
                continue

            # ── Bias calibration (first BIAS_SAMPLES samples) ──
            if not self._bias_done:
                self._gyro_bias += gyro
                self._bias_count += 1
                if self._bias_count >= config.BIAS_SAMPLES:
                    self._gyro_bias /= self._bias_count
                    self._bias_done = True
                continue

            # ── Subtract bias ──
            gc = gyro - self._gyro_bias
            gc = np.where(np.abs(gc) > config.GYRO_DEADZONE, gc, 0.0)

            # Save gyro magnitude for movement detection
            self._last_gyro_mag = float(np.sqrt(np.sum(gc * gc)))
            self._raw_gyro = gc.copy()

            # ── Compute dt ──
            dt = 0.002  # default: 500Hz
            tick = sample.get('tick', 0)
            if self._last_tick > 0 and tick > self._last_tick:
                dt_t = (tick - self._last_tick) / 1000.0
                if 0.0001 < dt_t < 0.1:
                    dt = dt_t
            self._last_tick = tick

            gx, gy, gz = gc

            # ── Complementary filter ──
            # Pitch/Roll: 99.9% gyro integration + 0.1% accel correction
            pitch_gyro = self._raw_pitch + gx * dt
            roll_gyro = self._raw_roll + gz * dt
            yaw_gyro = self._raw_yaw + gy * dt

            ax, ay, az = accel
            g_norm = math.sqrt(ax * ax + ay * ay + az * az)
            if g_norm > 0.5:
                pitch_accel = math.atan2(-ax, math.sqrt(ay * ay + az * az))
                roll_accel = math.atan2(ay, az)
            else:
                pitch_accel = self._raw_pitch
                roll_accel = self._raw_roll

            CF_ALPHA = config.CF_ALPHA  # 0.999
            self._raw_pitch = CF_ALPHA * pitch_gyro + (1 - CF_ALPHA) * pitch_accel
            self._raw_roll = CF_ALPHA * roll_gyro + (1 - CF_ALPHA) * roll_accel
            self._raw_yaw = yaw_gyro * config.YAW_DECAY

            # ── EMA smooth output ──
            a = config.EMA_ALPHA
            with self._lock:
                self._yaw = self._raw_yaw
                self._pitch = a * self._raw_pitch + (1 - a) * self._pitch
                # Wrap-aware roll smoothing
                rd = (self._raw_roll - self._roll + math.pi) % (2 * math.pi) - math.pi
                self._roll += rd * a

    def get_orientation(self):
        """Get (yaw, pitch, roll) in radians, relative to reference."""
        with self._lock:
            dy = (self._yaw - self._ref_yaw + math.pi) % (2 * math.pi) - math.pi
            dp = self._pitch - self._ref_pitch
            dr = (self._roll - self._ref_roll + math.pi) % (2 * math.pi) - math.pi
            return (dy, dp, dr)

    def get_gyro_magnitude(self):
        """Get current gyro magnitude (rad/s) for movement detection."""
        return self._last_gyro_mag

    def get_raw_gyro(self):
        """Get raw bias-corrected gyro values (gx, gy, gz) in rad/s."""
        gx, gy, gz = self._raw_gyro
        return (float(gx), float(gy), float(gz))

    def recenter(self):
        """Set current orientation as the reference (zero) point."""
        with self._lock:
            self._ref_yaw = self._yaw
            self._ref_pitch = self._pitch
            self._ref_roll = self._roll

    @property
    def imu_count(self):
        return self._imu_count

    def stop(self):
        """Stop IMU tracking and release resources."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._reader:
            self._reader.close()
        self.connected = False

    def __del__(self):
        self._running = False
        if hasattr(self, '_reader') and self._reader:
            try:
                self._reader.close()
            except Exception:
                pass
