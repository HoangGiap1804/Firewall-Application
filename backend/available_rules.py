#!/usr/bin/env python3
import subprocess
import json
import os
from typing import List
from PySide6.QtCore import QObject, Slot, Signal

STATUS_FILE = "available_rules.json"
SYSCTL_BACKUP_FILE = "sysctl_backup.json"


def run_cmd(cmd: List[str]):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res
    except Exception as e:
        class _E:
            returncode = 255
            stdout = ""
            stderr = str(e)
        return _E()

def get_sysctl(param: str) -> str:
    """Lấy giá trị sysctl hiện tại"""
    res = subprocess.run(["sysctl", "-n", param], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else None


def set_sysctl(param: str, value: str):
    """Set sysctl (dùng sudo)"""
    subprocess.run(["sudo", "sysctl", f"{param}={value}"], capture_output=True, text=True)


class AvailableRules(QObject):
    ruleToggled = Signal(str, bool)  # group_name, enabled

    # Các nhóm luật đã nâng cấp
    RULE_GROUPS = {
        # Giới hạn ICMP theo từng IP (hashlimit) + drop còn lại + log giới hạn
        "ICMP Flood": [
            ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request",
             "-m", "hashlimit", "--hashlimit-name", "icmp_flood", "--hashlimit", "5/sec",
             "--hashlimit-burst", "10", "--hashlimit-mode", "srcip", "-j", "ACCEPT"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request",
             "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "ICMP_FLOOD: "],
            ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request", "-j", "DROP"],
        ],

        # SYN Flood: chain riêng + hashlimit theo srcip + RETURN cho hợp lí
        "SYN Flood": [
            ["sudo", "iptables", "-N", "SYN_PROTECT"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-j", "SYN_PROTECT"],
            ["sudo", "iptables", "-A", "SYN_PROTECT", "-m", "hashlimit",
             "--hashlimit-name", "synflood", "--hashlimit-above", "10/sec",
             "--hashlimit-burst", "20", "--hashlimit-mode", "srcip",
             "--hashlimit-htable-expire", "300000", "-j", "DROP"],
            ["sudo", "iptables", "-A", "SYN_PROTECT", "-j", "RETURN"],
        ],

        # Port scan: chain riêng, nhiều flag detect, log giới hạn
        "Port Scan": [
            ["sudo", "iptables", "-N", "PORT_SCAN"],
            ["sudo", "iptables", "-A", "PORT_SCAN", "-m", "limit", "--limit", "2/min",
             "-j", "LOG", "--log-prefix", "PORTSCAN: "],
            ["sudo", "iptables", "-A", "PORT_SCAN", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "PORT_SCAN"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "ALL", "-j", "PORT_SCAN"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "FIN,URG,PSH", "-j", "PORT_SCAN"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,RST", "SYN,RST", "-j", "PORT_SCAN"],
            ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,FIN", "SYN,FIN", "-j", "PORT_SCAN"],
            # optional: small UDP scan mitigation
            ["sudo", "iptables", "-A", "INPUT", "-p", "udp", "-m", "length", "--length", "0:28", "-j", "DROP"],
        ],

        # IP spoofing: chặn thêm multicast, link-local, reserved
        "IP Spoofing": [
            ["sudo", "iptables", "-A", "INPUT", "-s", "10.0.0.0/8", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "172.16.0.0/12", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "192.168.0.0/16", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "127.0.0.0/8", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "169.254.0.0/16", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "224.0.0.0/4", "-j", "DROP"],
            ["sudo", "iptables", "-A", "INPUT", "-s", "240.0.0.0/5", "-j", "DROP"],
        ],

        # Invalid packet: dùng conntrack, log giới hạn rồi drop
        "Invalid Packet": [
            ["sudo", "iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "INVALID",
             "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "INVALID_PKT: "],
            ["sudo", "iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
        ],

        # Broadcast control: limit + log
        "Broadcast Control": [
            ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast",
             "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
            ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast",
             "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "BROADCAST_PKT: "],
            ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast", "-j", "DROP"],
        ],

        # Outbound protection: ngăn outbound spoof / invalid
        "Outbound Protection": [
            ["sudo", "iptables", "-A", "OUTPUT", "-s", "10.0.0.0/8", "-j", "DROP"],
            ["sudo", "iptables", "-A", "OUTPUT", "-s", "172.16.0.0/12", "-j", "DROP"],
            ["sudo", "iptables", "-A", "OUTPUT", "-s", "192.168.0.0/16", "-j", "DROP"],
            ["sudo", "iptables", "-A", "OUTPUT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
        ],
    }

    # sysctl params cần backup cho SYN Flood
    SYSCTL_PARAMS = [
        "net.ipv4.tcp_syncookies",
        "net.ipv4.tcp_max_syn_backlog",
        "net.ipv4.tcp_synack_retries",
        "net.ipv4.tcp_abort_on_overflow",
    ]

    def __init__(self):
        super().__init__()
        self.status = self._load_status()
        self.sysctl_backup = self._load_sysctl_backup()

    def _load_status(self):
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        return {k: False for k in self.RULE_GROUPS}

    def _save_status(self):
        with open(STATUS_FILE, "w") as f:
            json.dump(self.status, f, indent=4)

    def _load_sysctl_backup(self):
        if os.path.exists(SYSCTL_BACKUP_FILE):
            with open(SYSCTL_BACKUP_FILE, "r") as f:
                return json.load(f)
        return {}

    def _save_sysctl_backup(self):
        with open(SYSCTL_BACKUP_FILE, "w") as f:
            json.dump(self.sysctl_backup, f, indent=4)

    @Slot(result='QVariant')
    def getStatus(self):
        """Trả về trạng thái bật/tắt hiện tại."""
        return self.status

    @Slot(str, bool, result=str)
    def toggleRule(self, group_name: str, enable: bool) -> str:
        """Bật/tắt nhóm luật. Có xử lý sysctl cho SYN Flood và rollback."""
        if group_name not in self.RULE_GROUPS:
            return f"Unknown rule group: {group_name}"

        cmds = self.RULE_GROUPS[group_name]
        logs = []

        # --- Thêm hoặc xóa iptables ---
        if enable:
            for cmd in cmds:
                res = run_cmd(cmd)
                logs.append(f"ADD: {' '.join(cmd)} => {res.returncode}")
            self.status[group_name] = True
        else:
            # Xóa: với -A/-I -> thay bằng -D; với -N -> flush & delete chain
            for cmd in cmds:
                if "-A" in cmd or "-I" in cmd:
                    # đổi -A/-I thành -D
                    cmd_del = cmd.copy()
                    if "-A" in cmd_del:
                        idx = cmd_del.index("-A")
                    else:
                        idx = cmd_del.index("-I")
                    cmd_del[idx] = "-D"
                    res = run_cmd(cmd_del)
                    logs.append(f"DEL: {' '.join(cmd_del)} => {res.returncode}")
                elif "-N" in cmd:
                    # nếu tạo chain: flush & delete chain
                    try:
                        idx = cmd.index("-N")
                        chain = cmd[idx + 1]
                        resf = run_cmd(["sudo", "iptables", "-F", chain])
                        resx = run_cmd(["sudo", "iptables", "-X", chain])
                        logs.append(f"FLUSH {chain} => {resf.returncode}; DELETE {chain} => {resx.returncode}")
                    except Exception as e:
                        logs.append(f"ERR deleting chain: {str(e)}")
            self.status[group_name] = False

        # --- Xử lý sysctl cho SYN Flood ---
        if group_name == "SYN Flood":
            if enable:
                # backup sysctl trước khi thay đổi
                for p in self.SYSCTL_PARAMS:
                    v = get_sysctl(p)
                    if v is not None:
                        self.sysctl_backup[p] = v
                self._save_sysctl_backup()
                # áp dụng giá trị bảo vệ
                set_sysctl("net.ipv4.tcp_syncookies", "1")
                set_sysctl("net.ipv4.tcp_max_syn_backlog", "2048")
                set_sysctl("net.ipv4.tcp_synack_retries", "3")
                set_sysctl("net.ipv4.tcp_abort_on_overflow", "1")
                logs.append("SYSCTL: applied SYN protections")
            else:
                # khôi phục sysctl đã backup
                for p, v in self.sysctl_backup.items():
                    if v is not None:
                        set_sysctl(p, v)
                        logs.append(f"SYSCTL: restored {p}={v}")
                # optional: clear backup
                # self.sysctl_backup = {}
                # self._save_sysctl_backup()

        self._save_status()
        self._save_sysctl_backup()
        self.ruleToggled.emit(group_name, enable)
        return "\n".join(logs)
