import subprocess
from PySide6.QtCore import QObject, Slot
import json
import os

META_FILE = "rules_meta.json"

def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r") as f:
            return json.load(f)
    return {}

def save_meta(data):
    with open(META_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
class IptablesHandler(QObject):
    @Slot(str, str, str, str, str, str, str)
    def addRule(self, ip, port, protocol, action, interface, state, group=""):
        """
        Sinh lệnh iptables dựa trên input:
        - ip: nguồn (source IP)
        - port: port đích
        - protocol: tcp/udp/icmp
        - action: ACCEPT/DROP/REJECT
        - interface: tên interface (eth0, wlan0...) hoặc để trống
        - state: NEW, ESTABLISHED, RELATED hoặc để trống
        """

        if not protocol or not action:
            print("Protocol và action là bắt buộc!")
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
            print(f"Đã thêm rule: {' '.join(cmd)}")
            
            meta = load_meta()
            result = subprocess.run(
                ['sudo', 'iptables', '-L', 'INPUT', '--line-numbers'],
                capture_output=True, text=True, check=True
            )
            lines = [l for l in result.stdout.splitlines()[2:] if l.strip() != ""]
            new_num = str(len(lines))
            meta[new_num] = group if group.strip()!= "" else "None"
            save_meta(meta)
            
        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi thêm rule: {e}")
