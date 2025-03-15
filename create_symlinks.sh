#!/bin/bash

# Check if the script is being run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo."
    exit 1
fi

CONFIG_FILE="config.tsv"

# Display a warning message
echo "WARNING: This script will overwrite any existing files or symbolic links at the destination paths."
echo "Press Ctrl+C to cancel or any other key to continue."
read -n 1 -s -r

echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found!"
    exit 1
fi

# Read each line of the config file
while IFS=$'\t' read -r source dest; do
    # Skip empty lines or lines without a tab character
    if [ -z "$source" ] || [ -z "$dest" ]; then
        continue
    fi

    # Check if source file exists
    if [ ! -f "$source" ]; then
        echo "Source file $source not found, skipping..."
        continue
    fi

    # Remove the destination file or link if it exists
    if [ -f "$dest" ] || [ -L "$dest" ]; then
        echo "Removing existing file or symlink at $dest"
        rm -f "$dest"
    fi

    # Create the parent directory of the destination if it doesn't exist
    mkdir -p "$(dirname "$dest")"

    # Create a symbolic link
    ln -sf "$(pwd)/$source" "$dest"
    echo "Created symlink for $source at $dest"
done < "$CONFIG_FILE"

