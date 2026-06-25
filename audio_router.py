"""
Audio router for macOS.

Routes system audio output to RayNeo glasses using SwitchAudioSource CLI
or CoreAudio via PyObjC.

Two approaches:
  1. SwitchAudioSource CLI (simplest, recommended)
     - brew install switchaudio-osx
     - SwitchAudioSource -s "RayNeo Air 4 Pro"

  2. CoreAudio via PyObjC (fallback)
     - Uses AudioHardwareServiceSetPropertyData

RayNeo glasses appear as a USB audio output device when connected via USB-C.
"""

import subprocess
import shutil
import sys
import os

try:
    from CoreAudio import (
        AudioHardwareServiceSetPropertyData,
        AudioObjectGetPropertyData,
        AudioObjectPropertyAddress,
        kAudioHardwarePropertyDefaultOutputDevice,
        kAudioObjectSystemObject,
        kAudioDevicePropertyDeviceNameCFString,
    )
    from Foundation import NSAppleEventManager, NSObject
    HAS_COREAUDIO = True
except ImportError:
    HAS_COREAUDIO = False

import config


class AudioRouter:
    """Routes system audio output to RayNeo glasses on macOS."""

    def __init__(self):
        self._switch_audio_path = config.SWITCH_AUDIO_SOURCE_PATH
        self._original_device = None  # Original output device name
        self._glasses_device = None
        self.active = False
        self._method = None  # 'switchaudio' or 'coreaudio'

    def start(self) -> bool:
        """Route audio to RayNeo glasses. Returns True on success."""
        # Try SwitchAudioSource first
        self._find_switchaudio()

        if self._switch_audio_path:
            success = self._start_with_switchaudio()
            if success:
                self._method = 'switchaudio'
                self.active = True
                return True

        # Fallback to CoreAudio
        if HAS_COREAUDIO:
            success = self._start_with_coreaudio()
            if success:
                self._method = 'coreaudio'
                self.active = True
                return True

        print("  Audio: Could not route to glasses.")
        print("  Install SwitchAudioSource: brew install switchaudio-osx")
        print("  Available audio devices:")
        self._list_devices()
        return False

    def _find_switchaudio(self):
        """Find the SwitchAudioSource binary."""
        if self._switch_audio_path and os.path.exists(self._switch_audio_path):
            return

        # Check common locations
        candidates = [
            'SwitchAudioSource',
            '/usr/local/bin/SwitchAudioSource',
            '/opt/homebrew/bin/SwitchAudioSource',
        ]
        for path in candidates:
            found = shutil.which(path)
            if found:
                self._switch_audio_path = found
                return
            if os.path.exists(path):
                self._switch_audio_path = path
                return

    def _start_with_switchaudio(self) -> bool:
        """Use SwitchAudioSource CLI to switch output."""
        if not self._switch_audio_path:
            return False
        try:
            # Get current output device
            result = subprocess.run(
                [self._switch_audio_path, '-c'],
                capture_output=True, text=True, timeout=5
            )
            self._original_device = result.stdout.strip()
            print(f"  Audio: current output = '{self._original_device}'")

            # Find glasses device by name
            result = subprocess.run(
                [self._switch_audio_path, '-a'],
                capture_output=True, text=True, timeout=5
            )
            available = result.stdout.strip().split('\n')

            glasses_dev = None
            for dev in available:
                if config.GLASSES_AUDIO_DEVICE.lower() in dev.lower():
                    glasses_dev = dev.strip()
                    break

            if not glasses_dev:
                print(f"  Audio: Glasses device matching "
                      f"'{config.GLASSES_AUDIO_DEVICE}' not found")
                return False

            # Switch to glasses
            result = subprocess.run(
                [self._switch_audio_path, '-s', glasses_dev],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self._glasses_device = glasses_dev
                print(f"  Audio: Switched output → '{glasses_dev}'")
                return True
            else:
                print(f"  Audio: Switch failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("  Audio: SwitchAudioSource not found")
            return False
        except Exception as e:
            print(f"  Audio: SwitchAudioSource error: {e}")
            return False

    def _start_with_coreaudio(self) -> bool:
        """Use CoreAudio to switch output device."""
        try:
            # Get the default output device
            addr = AudioObjectPropertyAddress(
                mSelector=kAudioHardwarePropertyDefaultOutputDevice,
                mScope=0,  # kAudioObjectPropertyScopeGlobal
                mElement=0,  # kAudioObjectPropertyElementMain
            )

            result, default_device_id = AudioObjectGetPropertyData(
                kAudioObjectSystemObject,
                addr,
                0, None,
                None, None
            )

            print(f"  Audio: CoreAudio default device ID = {default_device_id}")

            # List all output devices
            devices = self._list_coreaudio_devices()
            for dev_id, dev_name in devices:
                if config.GLASSES_AUDIO_DEVICE.lower() in dev_name.lower():
                    # Switch to this device
                    self._original_device = default_device_id
                    self._glasses_device = dev_name
                    result = AudioHardwareServiceSetPropertyData(
                        kAudioObjectSystemObject,
                        addr,
                        0, None,
                        dev_id
                    )
                    print(f"  Audio: CoreAudio switched to '{dev_name}'")
                    return True

            print(f"  Audio: No device matching '{config.GLASSES_AUDIO_DEVICE}'")
            return False

        except Exception as e:
            print(f"  Audio: CoreAudio error: {e}")
            return False

    def _list_coreaudio_devices(self):
        """List CoreAudio output devices. Returns [(id, name), ...]."""
        # This is a simplified version — full implementation requires
        # AudioObjectGetPropertyDataSize + enumerate
        return []

    def _list_devices(self):
        """List available audio output devices."""
        if self._switch_audio_path:
            try:
                result = subprocess.run(
                    [self._switch_audio_path, '-a'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        marker = ' (output)' if 'output' not in line.lower() else ''
                        print(f"    {line.strip()}{marker}")
            except Exception:
                pass

    def restore(self):
        """Restore original audio output device."""
        if not self.active:
            return

        if self._method == 'switchaudio' and self._switch_audio_path:
            if self._original_device:
                try:
                    subprocess.run(
                        [self._switch_audio_path, '-s', self._original_device],
                        capture_output=True, timeout=5
                    )
                    print(f"  Audio: Restored output → '{self._original_device}'")
                except Exception as e:
                    print(f"  Audio: Restore failed: {e}")

        elif self._method == 'coreaudio' and HAS_COREAUDIO:
            try:
                addr = AudioObjectPropertyAddress(
                    mSelector=kAudioHardwarePropertyDefaultOutputDevice,
                    mScope=0,
                    mElement=0,
                )
                AudioHardwareServiceSetPropertyData(
                    kAudioObjectSystemObject,
                    addr,
                    0, None,
                    self._original_device
                )
                print(f"  Audio: CoreAudio restored output")
            except Exception as e:
                print(f"  Audio: Restore failed: {e}")

        self.active = False

    def stop(self):
        """Stop audio routing and restore original device."""
        self.restore()

    def __del__(self):
        self.restore()


# ── Standalone test ──
if __name__ == '__main__':
    print("Audio Router Test (SwitchAudioSource)")
    router = AudioRouter()
    if router.start():
        print("Routing to glasses... (press Enter to restore)")
        input()
        router.stop()
    else:
        print("Failed to route audio.")
