import subprocess
from PyQt6.QtCore import QObject, pyqtSlot


class IptablesHandler(QObject):
    """Xử lý thêm rule iptables"""

    @pyqtSlot(str, str, str, str, str, str, str)
    def addRule(self, ip, port, protocol, action, interface, state, chain="OUTPUT"):
        if not protocol or not action:
            print("Protocol và Action là bắt buộc!")
            return

        import os
        chain = chain.strip()
        cmd = ["iptables", "-A", chain, "-p", protocol]
        if os.geteuid() != 0:
            cmd.insert(0, "sudo")

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
        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi thêm rule: {e}")
