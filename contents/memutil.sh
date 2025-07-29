#!/bin/bash

log_file="/home/swap/memusage.log"
line_limit=1000

while true; do
    # Find the amount of free memory in kilobytes
    free_memory=$(free -k | awk 'NR==2{print $4}')

    # Append the free memory value to the log file
    echo "$free_memory" >> "$log_file"

    # Check if the file has more than the specified line limit
    line_count=$(wc -l < "$log_file")
    if [ "$line_count" -gt "$line_limit" ]; then
        # Remove the top line from the file
        sed -i '1d' "$log_file"
    fi

    # Wait before the next iteration
    sleep .1
done

