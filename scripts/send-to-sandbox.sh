#!/bin/bash

SANDBOX_NAME="ubuntu"
SANDBOX_ROOT="/var/sandbox/ubuntu"
SANDBOX_HOME="$SANDBOX_ROOT/home/giap/downloads"
DOWNLOADS="$HOME/Downloads"

while true; do
    FILE=$(inotifywait -e close_write --format "%f" "$DOWNLOADS")  
    echo "Detected new file: $FILE"

    # copy file
    sudo cp "$DOWNLOADS/$FILE" "$SANDBOX_HOME"
    echo "Copied into sandbox!"

    # chạy file bên trong sandbox
    echo "Executing file inside sandbox..."
    sudo systemd-nspawn -M "$SANDBOX_NAME" -D "$SANDBOX_ROOT" \
        -- /bin/bash -c "cd /home/giap/downloads; chmod +x '$FILE'; ./'$FILE'"

    echo "Execution done for: $FILE"
done
