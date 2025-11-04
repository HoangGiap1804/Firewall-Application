import subprocess
import json
import os
from PyQt6.QtCore import QObject, pyqtSlot

META_FILE = "rules_meta.json"


def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r") as f:
            return json.load(f)
    return {}


def save_meta(data):
    with open(META_FILE, "w") as f:
        json.dump(data, f, indent=4)


def make_rule_key(parts):
    """Tạo key duy nhất cho rule, bỏ qua num, pkts, bytes."""
    return " ".join(parts[3:])


class IptablesHandler(QObject):
    """Xử lý thêm rule iptables và quản lý metadata nhóm."""

    @pyqtSlot(str, str, str, str, str, str, str)
    def addRule(self, ip, port, protocol, action, interface, state, group=""):
        if not protocol or not action:
            print("Protocol và Action là bắt buộc!")
            return

        cmd = ["sudo", "iptables", "-A", "INPUT", "-p", protocol]

        if ip:
            cmd += ["-s", ip]
        if port:
            cmd += ["--dport", port]
        if interface:
            cmd += ["-i", interface]
        if state:
            cmd += ["-m", "state", "--state", state]

        cmd += ["-j", action]

        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Đã thêm rule: {' '.join(cmd)}")

            # Lấy rule vừa thêm
            result = subprocess.run(
                ["sudo", "iptables", "-L", "INPUT", "-v", "-n", "--line-numbers"],
                capture_output=True, text=True, check=True
            )
            lines = [l for l in result.stdout.splitlines()[2:] if l.strip()]
            if not lines:
                return
            last_rule = lines[-1]
            parts = last_rule.split()
            key = make_rule_key(parts)

            meta = load_meta()
            meta[key] = group.strip() if group.strip() else "None"
            save_meta(meta)

        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi thêm rule: {e}")
