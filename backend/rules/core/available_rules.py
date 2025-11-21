#!/usr/bin/env python3
import subprocess
import json
import os
from typing import List
from PySide6.QtCore import QObject, Slot, Signal

STATUS_FILE = "available_rules.json"
SYSCTL_BACKUP_FILE = "sysctl_backup.json"
META_FILE = "rules_meta.json"

PROTOCOL_MAP = {
    "icmp": "1",
    "tcp": "6",
    "udp": "17"
}

def make_rule_key_from_cmd(cmd):
    """
    Chuẩn hóa key dạng rút gọn: <TARGET> <PROT_NUM> -- <SRC> <DEST>
    Bỏ qua toàn bộ phần extras như --dport, --icmp-type, -m ...
    """
    try:
        target = cmd[cmd.index("-j") + 1] if "-j" in cmd else "ACCEPT"
        prot = cmd[cmd.index("-p") + 1] if "-p" in cmd else "*"
        prot_num = PROTOCOL_MAP.get(prot, prot)
        source = cmd[cmd.index("-s") + 1] if "-s" in cmd else "*"
        dest = cmd[cmd.index("-d") + 1] if "-d" in cmd else "0.0.0.0/0"
        key = f"{target} {prot_num} -- {source} {dest}"
        return key.strip()
    except Exception:
        return f"ERR_KEY_PARSE_{' '.join(cmd)}"

def normalize_rule_key(key: str) -> str:
    """
    Chuẩn hóa key rule để trùng định dạng với rule_input.py:
    <TARGET> <PROT> -- <IN> <OUT> <SRC> <DEST>
    """
    parts = key.split()
    if len(parts) < 3:
        return key.strip()

    target = parts[0]
    prot = parts[1]
    # Nếu prot đã là số thì giữ nguyên, nếu là tên thì convert
    if prot.isdigit():
        prot_num = prot
    else:
        prot_num = PROTOCOL_MAP.get(prot, prot)
    opt = "--"
    in_if = "*"
    out_if = "*"

    # Lấy source và dest
    src = "0.0.0.0/0"
    dest = "0.0.0.0/0"
    if "--" in parts:
        idx = parts.index("--")
        if len(parts) > idx + 1:
            src = parts[idx + 1]
        if len(parts) > idx + 2:
            dest = parts[idx + 2]

    # Đảm bảo đúng thứ tự 7 phần tử
    norm_key = f"{target} {prot_num} {opt} {in_if} {out_if} {src} {dest}"
    return norm_key.strip()

def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r") as f:
            return json.load(f)
    return {}

def save_meta(meta):
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=4)

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
    res = subprocess.run(["sysctl", "-n", param], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else None

def set_sysctl(param: str, value: str):
    subprocess.run(["sudo", "sysctl", f"{param}={value}"], capture_output=True, text=True)


class AvailableRules(QObject):
    ruleToggled = Signal(str, bool)

    RULE_GROUPS = {
        "ICMP Flood": {
            "group": "ICMP Flood",
            "rules": [
                ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request",
                "-m", "limit", "--limit", "5/second", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request",
                "-j", "LOG", "--log-prefix", "PING_FLOOD: "],
                ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request",
                "-j", "DROP"]
            ]
        },
        "SYN Flood": {
            "group": "SYN Flood",
            "rules": [
                # ["sudo", "iptables", "-N", "SYN_PROTECT"],
                # ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-j", "SYN_PROTECT"],
                # ["sudo", "iptables", "-A", "SYN_PROTECT", "-m", "hashlimit",
                #  "--hashlimit-name", "synflood", "--hashlimit-above", "10/sec",
                #  "--hashlimit-burst", "20", "--hashlimit-mode", "srcip",
                #  "--hashlimit-htable-expire", "300000", "-j", "DROP"],
                # ["sudo", "iptables", "-A", "SYN_PROTECT", "-j", "RETURN"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-j", "LOG", "--log-prefix", '"SYN_FLOOD: "'],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-j", "DROP"]
            ]
        },
        "Port Scan": {
            "group": "PORT_SCAN",
            "rules": [
                # 1️⃣ Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "PORT_SCAN"],
                ["sudo", "iptables", "-X", "PORT_SCAN"],
                ["sudo", "iptables", "-N", "PORT_SCAN"],

                # 2️⃣ Log giới hạn 2 lần/phút để tránh log flood
                ["sudo", "iptables", "-A", "PORT_SCAN", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "PORT_SCAN: ", "--log-level", "4"],

                # 3️⃣ Drop toàn bộ gói bị nghi ngờ
                ["sudo", "iptables", "-A", "PORT_SCAN", "-j", "DROP"],

                # 4️⃣ Gắn các rule phát hiện đặc trưng của Port Scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "PORT_SCAN"],          # NULL scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "ALL", "-j", "PORT_SCAN"],          # XMAS scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "FIN,URG,PSH", "-j", "PORT_SCAN"],  # Xmas variation
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,RST", "SYN,RST", "-j", "PORT_SCAN"],  # SYN/RST scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,FIN", "SYN,FIN", "-j", "PORT_SCAN"],  # SYN/FIN scan

                # 5️⃣ Chặn gói UDP nghi ngờ (kích thước nhỏ bất thường)
                ["sudo", "iptables", "-A", "INPUT", "-p", "udp", "-m", "length", "--length", "0:28", "-j", "DROP"],
            ]
        },
        "IP Spoofing": {
            "group": "IP Spoofing",
            "rules": [
                ["sudo", "iptables", "-A", "INPUT", "-s", "10.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "172.16.0.0/12", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "192.168.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "127.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "169.254.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "224.0.0.0/4", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-s", "240.0.0.0/5", "-j", "DROP"],
            ]
        },
        "Invalid Packet": {
            "group": "Invalid Packet",
            "rules": [
                ["sudo", "iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "INVALID",
                 "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "INVALID_PKT: "],
                ["sudo", "iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
            ]
        },
        "Broadcast Control": {
            "group": "Broadcast Control",
            "rules": [
                ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast",
                 "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast",
                 "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "BROADCAST_PKT: "],
                ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast", "-j", "DROP"],
            ]
        },
        "Outbound Protection": {
            "group": "Outbound Protection",
            "rules": [
                ["sudo", "iptables", "-A", "OUTPUT", "-s", "10.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTPUT", "-s", "172.16.0.0/12", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTPUT", "-s", "192.168.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTPUT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
            ]
        },
        "FIN/XMAS/NULL Scan": {
            "group": "FIN/XMAS/NULL Scan",
            "rules": [
                # FIN scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "FIN_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN", "-j", "DROP"],

                # XMAS scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "FIN,PSH,URG", "FIN,PSH,URG", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "XMAS_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "FIN,PSH,URG", "FIN,PSH,URG", "-j", "DROP"],

                # NULL scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "NULL_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "DROP"],

                # Tạo chain FIN_PROTECT
                ["sudo", "iptables", "-N", "FIN_PROTECT"],
                ["sudo", "iptables", "-A", "FIN_PROTECT", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN",
                "-m", "recent", "--name", "FIN_SCAN", "--set", "--rsource",
                "-j", "LOG", "--log-prefix", "FIN_SET: "],
                ["sudo", "iptables", "-A", "FIN_PROTECT", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN",
                "-m", "recent", "--name", "FIN_SCAN", "--rcheck", "--seconds", "60", "--hitcount", "5", "--rsource", "-j", "DROP"],
                ["sudo", "iptables", "-I", "INPUT", "-j", "FIN_PROTECT"],
            ]
        },
        "SSH/FTP Brute Force": {
            "group": "SSH/FTP Brute Force",
            "rules": [
                # SSH brute force
                ["sudo", "iptables", "-N", "SSH_PROTECT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "SSH_BRUTE", "--update", "--seconds", "60", "--hitcount", "5", "--rttl", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "SSH_BRUTE", "--set", "-j", "ACCEPT"],

                # FTP brute force
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "21", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "FTP_BRUTE", "--update", "--seconds", "60", "--hitcount", "10", "-j", "DROP"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "21", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "FTP_BRUTE", "--set", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "50000:51000", "-m", "conntrack", "--ctstate", "NEW", "-j", "ACCEPT"],

                # Cho phép các dịch vụ cơ bản
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "443", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "53", "-j", "ACCEPT"],
            ]
        },
    }

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
        return {k: {"enabled": False, "group": self.RULE_GROUPS[k]["group"]} for k in self.RULE_GROUPS}

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
        """Trả về trạng thái và group của từng rule."""
        return self.status

    @Slot(str, bool, result=str)
    def toggleRule(self, group_name: str, enable: bool) -> str:
        if group_name not in self.RULE_GROUPS:
            return f"Unknown rule group: {group_name}"

        cmds = self.RULE_GROUPS[group_name]["rules"]
        group_meta = self.RULE_GROUPS[group_name]["group"]
        logs = []

        meta = load_meta()

        if enable:
            for cmd in cmds:
                res = run_cmd(cmd)
                logs.append(f"ADD: {' '.join(cmd)} => {res.returncode}")
                if res.returncode == 0:
                    # Ghi thẳng vào rules_meta.json
                    rule_key = make_rule_key_from_cmd(cmd)
                    norm_key = normalize_rule_key(rule_key)
                    meta[norm_key] = group_meta

            self.status[group_name] = {"enabled": True, "group": group_meta}

        else:
            for cmd in cmds:
                if "-A" in cmd or "-I" in cmd:
                    cmd_del = cmd.copy()
                    cmd_del[cmd_del.index("-A") if "-A" in cmd_del else cmd_del.index("-I")] = "-D"
                    res = run_cmd(cmd_del)
                    logs.append(f"DEL: {' '.join(cmd_del)} => {res.returncode}")
                elif "-N" in cmd:
                    try:
                        chain = cmd[cmd.index("-N") + 1]
                        run_cmd(["sudo", "iptables", "-F", chain])
                        run_cmd(["sudo", "iptables", "-X", chain])
                        logs.append(f"FLUSH/DELETE {chain}")
                    except Exception as e:
                        logs.append(f"ERR deleting chain: {e}")

                # Xóa rule_key tương ứng trong meta
                rule_key = make_rule_key_from_cmd(cmd)
                norm_key = normalize_rule_key(rule_key)
                if norm_key in meta:
                    del meta[norm_key]

            self.status[group_name] = {"enabled": False, "group": group_meta}

        save_meta(meta)

        # --- Quản lý sysctl cho SYN Flood ---
        if group_name == "SYN Flood":
            if enable:
                for p in self.SYSCTL_PARAMS:
                    v = get_sysctl(p)
                    if v:
                        self.sysctl_backup[p] = v
                self._save_sysctl_backup()
                set_sysctl("net.ipv4.tcp_syncookies", "1")
                set_sysctl("net.ipv4.tcp_max_syn_backlog", "2048")
                set_sysctl("net.ipv4.tcp_synack_retries", "3")
                set_sysctl("net.ipv4.tcp_abort_on_overflow", "1")
                logs.append("SYSCTL: applied SYN protections")
            else:
                for p, v in self.sysctl_backup.items():
                    if v:
                        set_sysctl(p, v)
                        logs.append(f"SYSCTL: restored {p}={v}")

        self._save_status()
        self.ruleToggled.emit(group_name, enable)
        return "\n".join(logs)
