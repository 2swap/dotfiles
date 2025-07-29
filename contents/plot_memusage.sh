#!/bin/bash

log_file="/home/swap/memusage.log"
output_plot="/home/swap/memusage_plot.png"

gnuplot -persist <<PLOT
    set terminal png size 800,600
    set output "$output_plot"

    set title "Memory Usage Over Time"
    set xlabel "Time"
    set ylabel "Free Memory (KB)"

    plot "$log_file" with lines title "Free Memory"
PLOT

