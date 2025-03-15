#!/bin/bash

# Define the output devices
DEVICE1="alsa_output.usb-Blue_Microphones_Yeti_Stereo_Microphone_REV8-00.iec958-stereo"
DEVICE2="alsa_output.pci-0000_00_1b.0.analog-stereo"

# Get the current active sink (output device)
current_sink=$(pactl get-default-sink)

# Check which device is currently set and toggle
if [ "$current_sink" == "$DEVICE1" ]; then
    pactl set-default-sink "$DEVICE2"
else
    pactl set-default-sink "$DEVICE1"
fi
echo "$current_sink -> $(pactl get-default-sink)"
