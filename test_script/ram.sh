#!/bin/bash

echo "Gradually consuming RAM..."
block=$(printf '0%.0s' {1..10000000})  # tạo block 10MB

RAM=()

while true; do
    RAM+=("$block")
    echo "Added 10MB block. Current blocks: ${#RAM[@]}"
    sleep 0.5
done
