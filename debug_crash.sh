#!/bin/bash
# Run AirPin under lldb to get the exact crash frame
cd "$(dirname "$0")"
echo "Starting lldb..."
echo "When it crashes, type: bt"
echo ""
lldb -- python3 main.py --no-imu --no-audio
