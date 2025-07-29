#!/bin/bash

# Define the output devices
# Can be found with `pactl list short sinks`
DEVICE1="alsa_output.usb-Blue_Microphones_Yeti_Stereo_Microphone_REV8-00.analog-stereo"
DEVICE2="alsa_output.pci-0000_00_1f.3.analog-stereo"

# Get the current active sink (output device)
current_sink=$(pactl get-default-sink)

# Check which device is currently set and toggle
if [ "$current_sink" == "$DEVICE1" ]; then
    pactl set-default-sink "$DEVICE2"
else
    pactl set-default-sink "$DEVICE1"
fi
echo "$current_sink -> $(pactl get-default-sink)"
