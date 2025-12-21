import subprocess
import os
import pwd

def send_notification(title: str, message: str):
    """
    Sends a desktop notification using notify-send.
    Handles the case where the script is running as root (SUDO) by detecting 
    the actual user and setting the correct DBus environment variables.
    """
    try:
        user = os.environ.get('SUDO_USER')
        if not user:
            # Check for pkexec user
            pkexec_uid = os.environ.get('PKEXEC_UID')
            if pkexec_uid:
                try:
                    user = pwd.getpwuid(int(pkexec_uid)).pw_name
                except Exception:
                    pass

        if user:
            # Running as root via sudo
            try:
                pw = pwd.getpwnam(user)
                uid = pw.pw_uid
                
                # Use 'env' to strictly set environment variables for the user command
                # This was verified to work in test_proof.py
                cmd = [
                    "sudo", "-u", user,
                    "env",
                    "DISPLAY=:0",
                    f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
                    "notify-send",
                    "--icon=dialog-warning",
                    "--urgency=critical",
                    "--expire-time=10000",
                    title,
                    message
                ]
                
                # Use subprocess.Popen to avoid blocking, but we trust this works based on tests
                subprocess.Popen(cmd)
                print(f"📢 Notification sent (as {user}): {title}")
                return
            except Exception as e:
                print(f"⚠️ Failed to send as user {user}: {e}")

        # Fallback for normal user execution
        subprocess.Popen([
            "notify-send",
            "--icon=dialog-warning",
            "--urgency=critical",
            "--expire-time=10000",
            title,
            message
        ])
        print(f"📢 Notification sent: {title}")
    except Exception as e:
        print("❌ Failed to send notification:", e)

