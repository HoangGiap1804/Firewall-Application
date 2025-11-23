#!/bin/bash

SANDBOX_PATH="/var/sandbox/ubuntu/home/giap/downloads"
DOWNLOADS="$HOME/Downloads"

# theo dõi sự kiện moved_to (rename file vào thư mục)
inotifywait -m -e moved_to --format "%f" "$DOWNLOADS" | while read FILE
do
    echo "Detected completed file: $FILE"
    
    # Copy file vào sandbox
    sudo cp "$DOWNLOADS/$FILE" "$SANDBOX_PATH"
    echo "Copied into sandbox!"
    
    # Cấp quyền thực thi cho file trong sandbox (chmod trên host filesystem)
    SANDBOX_FILE="$SANDBOX_PATH/$FILE"
    if [ -f "$SANDBOX_FILE" ]; then
        sudo chmod +x "$SANDBOX_FILE"
        echo "Set executable permission for: $FILE"
    else
        echo "File not found in sandbox: $SANDBOX_FILE"
        continue
    fi

    # Chạy file trong sandbox (không cần sudo trong container vì đã chmod rồi)
    echo "Running file in sandbox: $FILE"
    sudo systemd-nspawn -M ubuntu -D /var/sandbox/ubuntu \
        -- /bin/bash -c "cd /home/giap/downloads && ./'$FILE'"

    echo "Execution done for: $FILE"
done
