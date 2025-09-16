import subprocess
from PySide6.QtCore import QObject, Slot

class IptablesHandler(QObject):
    @Slot(str, str, str, str, str, str)
    def addRule(self, ip, port, protocol, action, interface, state):
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
        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi thêm rule: {e}")
