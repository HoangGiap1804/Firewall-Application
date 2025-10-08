#!/usr/bin/env python3
"""
main.py
QML + Python (PySide6) GUI to enable/disable preset iptables rule groups.

Run as root (sudo). Edit WAN_IFACE if needed (default 'eth0').
"""
import sys
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Slot, QUrl, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

# --- Configuration ---
WAN_IFACE = "eth0"  # <- chỉnh tên interface WAN nếu cần
CHAIN_NAME = "MYFW"  # custom chain to hold our mitigation rules

# Utility to run iptables commands safely (no shell)
def run_cmd(args):
    try:
        res = subprocess.run(args, check=False, capture_output=True, text=True)
        return (res.returncode, res.stdout.strip(), res.stderr.strip())
    except Exception as e:
        return (255, "", str(e))


# Predefined groups of rules to mitigate common network attacks.
# Each entry is a list of iptables commands (each command is a list of args).
RULE_SETS = {
    "syn_flood": [
        # allow established first (should normally exist)
        ["iptables", "-C", "INPUT", "-m", "conntrack", "--ctstate", "ESTABLISHED,RELATED", "-j", "ACCEPT"],
        # limit NEW SYN rate to 10/s, burst 20 as example (we will try -C first)
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--syn", "-m", "conntrack", "--ctstate", "NEW",
         "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
        # drop others (log then drop is possible; here we drop)
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--syn", "-m", "conntrack", "--ctstate", "NEW", "-j", "DROP"],
    ],
    "icmp_limit": [
        # allow limited ping
        ["iptables", "-A", CHAIN_NAME, "-p", "icmp", "--icmp-type", "8/0", "-m", "limit", "--limit", "5/second", "--limit-burst", "10", "-j", "ACCEPT"],
        ["iptables", "-A", CHAIN_NAME, "-p", "icmp", "--icmp-type", "8/0", "-j", "DROP"],
    ],
    "ssh_rate": [
        # simple recent-based SSH brute-force mitigation
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--dport", "22", "-m", "state", "--state", "NEW", "-m", "recent", "--set", "--name", "SSH"],
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--dport", "22", "-m", "state", "--state", "NEW", "-m", "recent", "--update", "--seconds", "60", "--hitcount", "4", "--name", "SSH", "-j", "DROP"],
    ],
    "null_xmas": [
        # Drop suspicious scans
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "DROP"],
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--tcp-flags", "ALL", "FIN,PSH,URG", "-j", "DROP"],
        ["iptables", "-A", CHAIN_NAME, "-p", "tcp", "--tcp-flags", "ALL", "FIN", "-j", "DROP"],
    ],
    "spoof_block": [
        # Block RFC1918 private source addresses arriving on WAN iface
        ["iptables", "-A", CHAIN_NAME, "-i", WAN_IFACE, "-s", "10.0.0.0/8", "-j", "DROP"],
        ["iptables", "-A", CHAIN_NAME, "-i", WAN_IFACE, "-s", "172.16.0.0/12", "-j", "DROP"],
        ["iptables", "-A", CHAIN_NAME, "-i", WAN_IFACE, "-s", "192.168.0.0/16", "-j", "DROP"],
        ["iptables", "-A", CHAIN_NAME, "-i", WAN_IFACE, "-s", "127.0.0.0/8", "-j", "DROP"],
    ],
}


class FirewallController(QObject):
    def __init__(self):
        super().__init__()
        # ensure iptables is present
        if not shutil.which("iptables"):
            print("iptables not found in PATH. Exiting.", file=sys.stderr)
            sys.exit(1)
        # ensure our chain exists
        self._ensure_chain()

    def _ensure_chain(self):
        # create chain if not exists
        code, out, err = run_cmd(["iptables", "-L", CHAIN_NAME])
        if code != 0:
            run_cmd(["iptables", "-N", CHAIN_NAME])
        # ensure there is a jump from INPUT to CHAIN_NAME (only one)
        # check with -C
        code, out, err = run_cmd(["iptables", "-C", "INPUT", "-j", CHAIN_NAME])
        if code != 0:
            run_cmd(["iptables", "-I", "INPUT", "-j", CHAIN_NAME])

    @Slot(str)
    def apply_rule_set(self, name="all"):
        print(f"Applying rule set: {name}")
        """Apply a named rule set (add commands to chain)."""
        if name not in RULE_SETS:
            return f"Unknown ruleset: {name}"
        logs = []
        for cmd in RULE_SETS[name]:
            # Try to add the specific command. We first attempt to check -C for exact match when reasonable.
            # Some commands might not be checkable; we just try to add.
            code, out, err = run_cmd(cmd)
            if code == 0:
                logs.append(f"OK: {' '.join(cmd)}")
            else:
                # if -C attempted earlier and failed, many commands are -A; show info
                # If it fails because rule exists, iptables returns non-zero; still continue.
                logs.append(f"ERR({code}): {' '.join(cmd)}; {err}")
        return "\n".join(logs)

    @Slot(result=str)
    def flush_myfw(self) -> str:
        """Flush (remove) all rules from our chain MYFW but keep chain and INPUT jump."""
        code, out, err = run_cmd(["iptables", "-F", CHAIN_NAME])
        if code == 0:
            return f"Flushed {CHAIN_NAME}."
        else:
            return f"Failed flush: {err}"

    @Slot(result=str)
    def delete_myfw_chain(self) -> str:
        """Remove jump and delete chain entirely (dangerous - use with care)."""
        logs = []
        # delete jump from INPUT if exists
        code, out, err = run_cmd(["iptables", "-D", "INPUT", "-j", CHAIN_NAME])
        if code == 0:
            logs.append("Removed INPUT -> MYFW jump")
        else:
            logs.append(f"Could not remove jump (maybe not present): {err}")
        # try to delete chain (must be empty)
        code, out, err = run_cmd(["iptables", "-X", CHAIN_NAME])
        if code == 0:
            logs.append("Deleted chain MYFW")
        else:
            logs.append(f"Could not delete chain (maybe not empty): {err}")
        return "\n".join(logs)

    @Slot(result=str)
    def status(self) -> str:
        """Return iptables -nvL for INPUT and the MYFW chain summary."""
        out_lines = []
        c1 = run_cmd(["iptables", "-vnL", "INPUT", "--line-numbers"])
        if c1[0] == 0:
            out_lines.append("=== INPUT ===")
            out_lines.append(c1[1])
        else:
            out_lines.append("Failed to list INPUT: " + c1[2])
        c2 = run_cmd(["iptables", "-vnL", CHAIN_NAME, "--line-numbers"])
        if c2[0] == 0:
            out_lines.append(f"=== {CHAIN_NAME} ===")
            out_lines.append(c2[1])
        else:
            out_lines.append(f"Failed to list {CHAIN_NAME}: " + c2[2])
        return "\n".join(out_lines)

    @Slot(result=str)
    def apply_all(self) -> str:
        """Apply all configured rule sets (order matters)."""
        msgs = []
        for key in RULE_SETS.keys():
            msgs.append(f"Applying {key} ...")
            msgs.append(self.apply_rule_set(key))
        return "\n".join(msgs)