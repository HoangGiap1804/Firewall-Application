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
        if not cmd or not isinstance(cmd, (list, tuple)):
            return "ERR_KEY_PARSE_INVALID_CMD"
        
        target = "ACCEPT"
        if "-j" in cmd:
            try:
                idx = cmd.index("-j")
                if idx + 1 < len(cmd):
                    target = cmd[idx + 1]
            except (ValueError, IndexError):
                pass
        
        prot = "*"
        if "-p" in cmd:
            try:
                idx = cmd.index("-p")
                if idx + 1 < len(cmd):
                    prot = cmd[idx + 1]
            except (ValueError, IndexError):
                pass
        
        prot_num = PROTOCOL_MAP.get(prot, prot)
        
        source = "*"
        if "-s" in cmd:
            try:
                idx = cmd.index("-s")
                if idx + 1 < len(cmd):
                    source = cmd[idx + 1]
            except (ValueError, IndexError):
                pass
        
        dest = "0.0.0.0/0"
        if "-d" in cmd:
            try:
                idx = cmd.index("-d")
                if idx + 1 < len(cmd):
                    dest = cmd[idx + 1]
            except (ValueError, IndexError):
                pass
        
        key = f"{target} {prot_num} -- {source} {dest}"
        return key.strip()
    except Exception as e:
        try:
            cmd_str = ' '.join(str(c) for c in cmd) if cmd else "INVALID"
            return f"ERR_KEY_PARSE_{cmd_str}"
        except Exception:
            return "ERR_KEY_PARSE_UNKNOWN"

def normalize_rule_key(key: str) -> str:
    """
    Chuẩn hóa key rule để trùng định dạng với rule_input.py:
    <TARGET> <PROT> -- <IN> <OUT> <SRC> <DEST>
    """
    try:
        if not key or not isinstance(key, str):
            return "* * -- * * 0.0.0.0/0 0.0.0.0/0"
        
        parts = key.split()
        if len(parts) < 3:
            return key.strip()

        target = parts[0] if len(parts) > 0 else "*"
        prot = parts[1] if len(parts) > 1 else "*"
        
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
            try:
                idx = parts.index("--")
                if len(parts) > idx + 1:
                    src = parts[idx + 1]
                if len(parts) > idx + 2:
                    dest = parts[idx + 2]
            except (ValueError, IndexError):
                pass

        # Đảm bảo đúng thứ tự 7 phần tử
        norm_key = f"{target} {prot_num} {opt} {in_if} {out_if} {src} {dest}"
        return norm_key.strip()
    except Exception:
        return "* * -- * * 0.0.0.0/0 0.0.0.0/0"

def load_meta():
    try:
        if os.path.exists(META_FILE):
            try:
                with open(META_FILE, "r", encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"Error loading meta file {META_FILE}: {e}")
                return {}
        return {}
    except Exception as e:
        print(f"Unexpected error in load_meta: {e}")
        return {}

def save_meta(meta):
    try:
        if not isinstance(meta, dict):
            print(f"Warning: meta is not a dict, got {type(meta)}")
            return False
        with open(META_FILE, "w", encoding='utf-8') as f:
            json.dump(meta, f, indent=4)
        return True
    except (IOError, OSError, TypeError) as e:
        print(f"Error saving meta file {META_FILE}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in save_meta: {e}")
        return False

def run_cmd(cmd: List[str], timeout: int = 10):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res
    except subprocess.TimeoutExpired:
        class _E:
            returncode = 124  # Exit code for timeout
            stdout = ""
            stderr = f"Command timeout after {timeout} seconds"
        return _E()
    except Exception as e:
        class _E:
            returncode = 255
            stdout = ""
            stderr = str(e)
        return _E()

def get_sysctl(param: str) -> str:
    try:
        if not param or not isinstance(param, str):
            return None
        res = subprocess.run(
            ["sysctl", "-n", param], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        return res.stdout.strip() if res.returncode == 0 else None
    except subprocess.TimeoutExpired:
        print(f"Timeout getting sysctl param: {param}")
        return None
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"Error getting sysctl param {param}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_sysctl: {e}")
        return None

def set_sysctl(param: str, value: str):
    try:
        if not param or not isinstance(param, str) or not isinstance(value, str):
            print(f"Invalid sysctl param or value: param={param}, value={value}")
            return False
        res = subprocess.run(
            ["sudo", "sysctl", f"{param}={value}"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        if res.returncode != 0:
            print(f"Failed to set sysctl {param}={value}: {res.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"Timeout setting sysctl param: {param}={value}")
        return False
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"Error setting sysctl param {param}={value}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in set_sysctl: {e}")
        return False

def chain_exists(chain_name: str) -> bool:
    """Kiểm tra xem chain có tồn tại trong iptables không"""
    try:
        if not chain_name or not isinstance(chain_name, str):
            return False
        res = subprocess.run(
            ["sudo", "iptables", "-L", chain_name, "-n"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Exit code 0 = chain tồn tại, 1 = chain không tồn tại
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout checking chain existence: {chain_name}")
        return False
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"Error checking chain existence {chain_name}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in chain_exists: {e}")
        return False


class AvailableRules(QObject):
    ruleToggled = Signal(str, bool)

    RULE_GROUPS = {
        "ICMP Flood": {
            "group": "ICMP Flood",
            "chain": "ICMP_FLOOD",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "ICMP_FLOOD"],
                ["sudo", "iptables", "-X", "ICMP_FLOOD"],
                ["sudo", "iptables", "-N", "ICMP_FLOOD"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "ICMP_FLOOD", "-p", "icmp", "--icmp-type", "echo-request",
                "-m", "limit", "--limit", "5/second", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "ICMP_FLOOD", "-p", "icmp", "--icmp-type", "echo-request",
                "-j", "LOG", "--log-prefix", "PING_FLOOD: "],
                ["sudo", "iptables", "-A", "ICMP_FLOOD", "-p", "icmp", "--icmp-type", "echo-request",
                "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-p", "icmp", "--icmp-type", "echo-request", "-j", "ICMP_FLOOD"]
            ]
        },
        "SYN Flood": {
            "group": "SYN Flood",
            "chain": "SYN_FLOOD",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "SYN_FLOOD"],
                ["sudo", "iptables", "-X", "SYN_FLOOD"],
                ["sudo", "iptables", "-N", "SYN_FLOOD"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "SYN_FLOOD", "-p", "tcp", "--syn", "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "SYN_FLOOD", "-p", "tcp", "--syn", "-j", "LOG", "--log-prefix", '"SYN_FLOOD: "'],
                ["sudo", "iptables", "-A", "SYN_FLOOD", "-p", "tcp", "--syn", "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--syn", "-j", "SYN_FLOOD"]
            ]
        },
        "Port Scan": {
            "group": "PORT_SCAN",
            "chain": "PORT_SCAN",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "PORT_SCAN"],
                ["sudo", "iptables", "-X", "PORT_SCAN"],
                ["sudo", "iptables", "-N", "PORT_SCAN"],
                # Log giới hạn 2 lần/phút để tránh log flood
                ["sudo", "iptables", "-A", "PORT_SCAN", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "PORT_SCAN: ", "--log-level", "4"],
                # Drop toàn bộ gói bị nghi ngờ
                ["sudo", "iptables", "-A", "PORT_SCAN", "-j", "DROP"],
                # Gắn các rule phát hiện đặc trưng của Port Scan vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "PORT_SCAN"],          # NULL scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "ALL", "-j", "PORT_SCAN"],          # XMAS scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "ALL", "FIN,URG,PSH", "-j", "PORT_SCAN"],  # Xmas variation
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,RST", "SYN,RST", "-j", "PORT_SCAN"],  # SYN/RST scan
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--tcp-flags", "SYN,FIN", "SYN,FIN", "-j", "PORT_SCAN"],  # SYN/FIN scan
                # Chặn gói UDP nghi ngờ (kích thước nhỏ bất thường)
                ["sudo", "iptables", "-A", "INPUT", "-p", "udp", "-m", "length", "--length", "0:28", "-j", "DROP"],
            ]
        },
        "IP Spoofing": {
            "group": "IP Spoofing",
            "chain": "IP_SPOOFING",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "IP_SPOOFING"],
                ["sudo", "iptables", "-X", "IP_SPOOFING"],
                ["sudo", "iptables", "-N", "IP_SPOOFING"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "10.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "172.16.0.0/12", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "192.168.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "127.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "169.254.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "224.0.0.0/4", "-j", "DROP"],
                ["sudo", "iptables", "-A", "IP_SPOOFING", "-s", "240.0.0.0/5", "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-j", "IP_SPOOFING"]
            ]
        },
        "Invalid Packet": {
            "group": "Invalid Packet",
            "chain": "INVALID_PKT",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "INVALID_PKT"],
                ["sudo", "iptables", "-X", "INVALID_PKT"],
                ["sudo", "iptables", "-N", "INVALID_PKT"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "INVALID_PKT", "-m", "conntrack", "--ctstate", "INVALID",
                 "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "INVALID_PKT: "],
                ["sudo", "iptables", "-A", "INVALID_PKT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "INVALID_PKT"]
            ]
        },
        "Broadcast Control": {
            "group": "Broadcast Control",
            "chain": "BROADCAST_CTRL",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "BROADCAST_CTRL"],
                ["sudo", "iptables", "-X", "BROADCAST_CTRL"],
                ["sudo", "iptables", "-N", "BROADCAST_CTRL"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "BROADCAST_CTRL", "-m", "pkttype", "--pkt-type", "broadcast",
                 "-m", "limit", "--limit", "10/s", "--limit-burst", "20", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "BROADCAST_CTRL", "-m", "pkttype", "--pkt-type", "broadcast",
                 "-m", "limit", "--limit", "2/min", "-j", "LOG", "--log-prefix", "BROADCAST_PKT: "],
                ["sudo", "iptables", "-A", "BROADCAST_CTRL", "-m", "pkttype", "--pkt-type", "broadcast", "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-m", "pkttype", "--pkt-type", "broadcast", "-j", "BROADCAST_CTRL"]
            ]
        },
        "Outbound Protection": {
            "group": "Outbound Protection",
            "chain": "OUTBOUND_PROTECT",
            "target_chain": "OUTPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "OUTBOUND_PROTECT"],
                ["sudo", "iptables", "-X", "OUTBOUND_PROTECT"],
                ["sudo", "iptables", "-N", "OUTBOUND_PROTECT"],
                # Rules trong chain
                ["sudo", "iptables", "-A", "OUTBOUND_PROTECT", "-s", "10.0.0.0/8", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTBOUND_PROTECT", "-s", "172.16.0.0/12", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTBOUND_PROTECT", "-s", "192.168.0.0/16", "-j", "DROP"],
                ["sudo", "iptables", "-A", "OUTBOUND_PROTECT", "-m", "conntrack", "--ctstate", "INVALID", "-j", "DROP"],
                # Gắn chain vào OUTPUT
                ["sudo", "iptables", "-A", "OUTPUT", "-j", "OUTBOUND_PROTECT"]
            ]
        },
        "FIN/XMAS/NULL Scan": {
            "group": "FIN/XMAS/NULL Scan",
            "chain": "FIN_XMAS_NULL_SCAN",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "FIN_XMAS_NULL_SCAN"],
                ["sudo", "iptables", "-X", "FIN_XMAS_NULL_SCAN"],
                ["sudo", "iptables", "-N", "FIN_XMAS_NULL_SCAN"],
                # FIN scan
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "FIN_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "FIN,SYN,RST,PSH", "FIN", "-j", "DROP"],
                # XMAS scan
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "FIN,PSH,URG", "FIN,PSH,URG", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "XMAS_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "FIN,PSH,URG", "FIN,PSH,URG", "-j", "DROP"],
                # NULL scan
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-m", "limit", "--limit", "2/min",
                "-j", "LOG", "--log-prefix", "NULL_SCAN: ", "--log-level", "4"],
                ["sudo", "iptables", "-A", "FIN_XMAS_NULL_SCAN", "-p", "tcp", "--tcp-flags", "ALL", "NONE", "-j", "DROP"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "-j", "FIN_XMAS_NULL_SCAN"]
            ]
        },
        "SSH/FTP Brute Force": {
            "group": "SSH/FTP Brute Force",
            "chain": "SSH_FTP_BRUTE",
            "target_chain": "INPUT",
            "rules": [
                # Tạo chain mới (xóa nếu đã tồn tại)
                ["sudo", "iptables", "-F", "SSH_FTP_BRUTE"],
                ["sudo", "iptables", "-X", "SSH_FTP_BRUTE"],
                ["sudo", "iptables", "-N", "SSH_FTP_BRUTE"],
                # SSH brute force
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "22", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "SSH_BRUTE", "--update", "--seconds", "60", "--hitcount", "5", "--rttl", "-j", "DROP"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "22", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "SSH_BRUTE", "--set", "-j", "ACCEPT"],
                # FTP brute force
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "21", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "FTP_BRUTE", "--update", "--seconds", "60", "--hitcount", "10", "-j", "DROP"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "21", "-m", "conntrack", "--ctstate", "NEW",
                "-m", "recent", "--name", "FTP_BRUTE", "--set", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "50000:51000", "-m", "conntrack", "--ctstate", "NEW", "-j", "ACCEPT"],
                # Cho phép các dịch vụ cơ bản
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "443", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
                ["sudo", "iptables", "-A", "SSH_FTP_BRUTE", "-p", "tcp", "--dport", "53", "-j", "ACCEPT"],
                # Gắn chain vào INPUT
                ["sudo", "iptables", "-A", "INPUT", "-j", "SSH_FTP_BRUTE"]
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
        try:
            super().__init__()
            self.status = self._load_status()
            self.sysctl_backup = self._load_sysctl_backup()
        except Exception as e:
            print(f"Error initializing AvailableRules: {e}")
            import traceback
            traceback.print_exc()
            # Initialize with safe defaults
            self.status = {}
            self.sysctl_backup = {}

    def _load_status(self):
        try:
            if os.path.exists(STATUS_FILE):
                try:
                    with open(STATUS_FILE, "r", encoding='utf-8') as f:
                        loaded_status = json.load(f)
                        # Validate loaded data
                        if not isinstance(loaded_status, dict):
                            raise ValueError("Status file does not contain a dictionary")
                        return loaded_status
                except (json.JSONDecodeError, IOError, OSError) as e:
                    print(f"Error loading status file {STATUS_FILE}: {e}")
                    # Return default status on error
                    return self._get_default_status()
            return self._get_default_status()
        except Exception as e:
            print(f"Unexpected error in _load_status: {e}")
            return self._get_default_status()
    
    def _get_default_status(self):
        """Trả về status mặc định cho tất cả rule groups"""
        try:
            return {k: {"enabled": False, "group": self.RULE_GROUPS[k].get("group", k)} 
                   for k in self.RULE_GROUPS}
        except Exception as e:
            print(f"Error creating default status: {e}")
            return {}

    def _save_status(self):
        try:
            if not isinstance(self.status, dict):
                print(f"Warning: status is not a dict, got {type(self.status)}")
                return False
            with open(STATUS_FILE, "w", encoding='utf-8') as f:
                json.dump(self.status, f, indent=4)
            return True
        except (IOError, OSError, TypeError) as e:
            print(f"Error saving status file {STATUS_FILE}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error in _save_status: {e}")
            return False

    def _load_sysctl_backup(self):
        try:
            if os.path.exists(SYSCTL_BACKUP_FILE):
                try:
                    with open(SYSCTL_BACKUP_FILE, "r", encoding='utf-8') as f:
                        loaded_backup = json.load(f)
                        # Validate loaded data
                        if not isinstance(loaded_backup, dict):
                            raise ValueError("Sysctl backup file does not contain a dictionary")
                        return loaded_backup
                except (json.JSONDecodeError, IOError, OSError) as e:
                    print(f"Error loading sysctl backup file {SYSCTL_BACKUP_FILE}: {e}")
                    return {}
            return {}
        except Exception as e:
            print(f"Unexpected error in _load_sysctl_backup: {e}")
            return {}

    def _save_sysctl_backup(self):
        try:
            if not isinstance(self.sysctl_backup, dict):
                print(f"Warning: sysctl_backup is not a dict, got {type(self.sysctl_backup)}")
                return False
            with open(SYSCTL_BACKUP_FILE, "w", encoding='utf-8') as f:
                json.dump(self.sysctl_backup, f, indent=4)
            return True
        except (IOError, OSError, TypeError) as e:
            print(f"Error saving sysctl backup file {SYSCTL_BACKUP_FILE}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error in _save_sysctl_backup: {e}")
            return False

    @Slot(result='QVariant')
    def getStatus(self):
        """Trả về trạng thái và group của từng rule."""
        try:
            if not isinstance(self.status, dict):
                print("Warning: status is not a dict, returning default")
                return self._get_default_status()
            return self.status
        except Exception as e:
            print(f"Error in getStatus: {e}")
            import traceback
            traceback.print_exc()
            try:
                return self._get_default_status()
            except Exception:
                return {}

    @Slot(str, bool, result=str)
    def toggleRule(self, group_name: str, enable: bool) -> str:
        try:
            if not group_name or not isinstance(group_name, str):
                return f"ERROR: Invalid group_name: {group_name}"
            
            if not isinstance(enable, bool):
                return f"ERROR: enable must be a boolean, got {type(enable)}"
            
            if group_name not in self.RULE_GROUPS:
                return f"ERROR: Unknown rule group: {group_name}"

            try:
                cmds = self.RULE_GROUPS[group_name]["rules"]
                group_meta = self.RULE_GROUPS[group_name]["group"]
                logs = []

                meta = load_meta()

                if enable:
                    # Kiểm tra chain có tồn tại không trước khi tạo
                    chain_name = self.RULE_GROUPS[group_name].get("chain")
                    
                    if not isinstance(cmds, list):
                        return f"ERROR: Invalid rules format for group {group_name}"
                    
                    for cmd in cmds:
                        try:
                            if not isinstance(cmd, list):
                                logs.append(f"  WARNING: Invalid command format: {cmd}")
                                continue
                            
                            # Nếu là lệnh tạo chain (-N) và chain đã tồn tại, bỏ qua
                            if "-N" in cmd and chain_name:
                                try:
                                    if chain_exists(chain_name):
                                        logs.append(f"SKIP: Chain {chain_name} đã tồn tại, bỏ qua tạo mới")
                                        continue
                                except Exception as e:
                                    logs.append(f"  WARNING checking chain existence: {str(e)}")
                            
                            res = run_cmd(cmd)
                            if res and hasattr(res, 'returncode'):
                                logs.append(f"ADD: {' '.join(str(c) for c in cmd)} => {res.returncode}")
                                if res.returncode != 0:
                                    stderr = getattr(res, 'stderr', '')
                                    stderr_lower = stderr.lower() if stderr else ""
                                    
                                    # Các trường hợp không phải lỗi nghiêm trọng
                                    is_non_error = False
                                    if "-N" in cmd and "already exists" in stderr_lower:
                                        logs.append(f"  INFO: Chain đã tồn tại (không phải lỗi)")
                                        is_non_error = True
                                    elif ("-F" in cmd or "-X" in cmd) and ("no chain" in stderr_lower or "no such chain" in stderr_lower):
                                        logs.append(f"  INFO: Chain không tồn tại, bỏ qua flush/delete (không phải lỗi)")
                                        is_non_error = True
                                    
                                    if not is_non_error:
                                        logs.append(f"  WARNING: {stderr}")
                                if res.returncode == 0:
                                    # Ghi thẳng vào rules_meta.json
                                    try:
                                        rule_key = make_rule_key_from_cmd(cmd)
                                        norm_key = normalize_rule_key(rule_key)
                                        if isinstance(meta, dict):
                                            meta[norm_key] = group_meta
                                    except Exception as e:
                                        logs.append(f"  WARNING creating rule key: {str(e)}")
                            else:
                                logs.append(f"  ERROR: Command execution returned invalid result")
                        except Exception as e:
                            logs.append(f"  EXCEPTION: {str(e)}")
                            import traceback
                            traceback.print_exc()

                    try:
                        if not isinstance(self.status, dict):
                            self.status = {}
                        self.status[group_name] = {"enabled": True, "group": group_meta}
                    except Exception as e:
                        logs.append(f"  WARNING updating status: {str(e)}")

                else:
                    # Lấy tên chain từ rule group
                    chain_name = self.RULE_GROUPS[group_name].get("chain")
                    
                    if not isinstance(cmds, list):
                        return f"ERROR: Invalid rules format for group {group_name}"
                    
                    # Bước 1: Xóa tất cả các rule gắn chain vào INPUT/OUTPUT trước
                    for cmd in cmds:
                        try:
                            if not isinstance(cmd, list):
                                logs.append(f"  WARNING: Invalid command format: {cmd}")
                                continue
                            
                            if "-A" in cmd or "-I" in cmd:
                                # Bỏ qua các lệnh tạo chain (-N) và flush chain (-F, -X)
                                if "-N" not in cmd and "-F" not in cmd and "-X" not in cmd:
                                    try:
                                        cmd_del = cmd.copy()
                                        try:
                                            if "-A" in cmd_del:
                                                idx = cmd_del.index("-A")
                                                cmd_del[idx] = "-D"
                                            elif "-I" in cmd_del:
                                                idx = cmd_del.index("-I")
                                                cmd_del[idx] = "-D"
                                            else:
                                                continue
                                        except (ValueError, IndexError) as e:
                                            logs.append(f"  WARNING: Cannot find -A/-I in command: {str(e)}")
                                            continue
                                        
                                        res = run_cmd(cmd_del)
                                        if res and hasattr(res, 'returncode'):
                                            logs.append(f"DEL: {' '.join(str(c) for c in cmd_del)} => {res.returncode}")
                                            if res.returncode != 0:
                                                # Nếu rule không tồn tại, không coi là lỗi nghiêm trọng - bỏ qua
                                                stderr = getattr(res, 'stderr', '')
                                                stderr_lower = stderr.lower() if stderr else ""
                                                if stderr and ("bad rule" in stderr_lower or "no such rule" in stderr_lower or "does not exist" in stderr_lower):
                                                    # Rule không tồn tại, bỏ qua không xử lý gì thêm
                                                    logs.append(f"  INFO: Rule không tồn tại, bỏ qua")
                                                    continue
                                                else:
                                                    logs.append(f"  WARNING: {stderr}")
                                            
                                            # Xóa rule_key tương ứng trong meta (chỉ khi rule đã được xóa thành công)
                                            if res.returncode == 0:
                                                try:
                                                    rule_key = make_rule_key_from_cmd(cmd)
                                                    norm_key = normalize_rule_key(rule_key)
                                                    if isinstance(meta, dict) and norm_key in meta:
                                                        del meta[norm_key]
                                                except Exception as e:
                                                    logs.append(f"  WARNING deleting rule key: {str(e)}")
                                        else:
                                            logs.append(f"  ERROR: Command execution returned invalid result")
                                    except Exception as e:
                                        # Nếu có exception khi xóa rule, kiểm tra xem có phải do rule không tồn tại không
                                        error_str = str(e).lower()
                                        if "bad rule" in error_str or "no such rule" in error_str or "does not exist" in error_str:
                                            logs.append(f"  INFO: Rule không tồn tại, bỏ qua exception")
                                        else:
                                            logs.append(f"  EXCEPTION deleting rule: {str(e)}")
                                            import traceback
                                            traceback.print_exc()
                        except Exception as e:
                            logs.append(f"  EXCEPTION processing command: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    
                    # Bước 2: Xóa chain sau khi đã xóa tất cả các rule tham chiếu đến nó
                    if chain_name:
                        try:
                            # Chỉ flush và delete nếu chain tồn tại
                            try:
                                if chain_exists(chain_name):
                                    res1 = run_cmd(["sudo", "iptables", "-F", chain_name])
                                    res2 = run_cmd(["sudo", "iptables", "-X", chain_name])
                                    if res1 and hasattr(res1, 'returncode') and res2 and hasattr(res2, 'returncode'):
                                        logs.append(f"FLUSH/DELETE chain: {chain_name} => {res1.returncode}, {res2.returncode}")
                                        if res1.returncode != 0:
                                            stderr1 = getattr(res1, 'stderr', '')
                                            stderr1_lower = stderr1.lower() if stderr1 else ""
                                            if "no chain" in stderr1_lower or "no such chain" in stderr1_lower:
                                                logs.append(f"  INFO flush: Chain không tồn tại (không phải lỗi)")
                                            else:
                                                logs.append(f"  WARNING flush: {stderr1}")
                                        if res2.returncode != 0:
                                            stderr2 = getattr(res2, 'stderr', '')
                                            stderr2_lower = stderr2.lower() if stderr2 else ""
                                            if "no chain" in stderr2_lower or "no such chain" in stderr2_lower:
                                                logs.append(f"  INFO delete: Chain không tồn tại (không phải lỗi)")
                                            else:
                                                logs.append(f"  WARNING delete: {stderr2}")
                                    else:
                                        logs.append(f"  ERROR: Invalid result from chain deletion commands")
                                else:
                                    logs.append(f"Chain {chain_name} không tồn tại, bỏ qua flush/delete")
                            except Exception as e:
                                logs.append(f"  WARNING checking/deleting chain {chain_name}: {str(e)}")
                        except Exception as e:
                            logs.append(f"WARNING deleting chain {chain_name}: {e}")
                            import traceback
                            traceback.print_exc()

                    try:
                        if not isinstance(self.status, dict):
                            self.status = {}
                        self.status[group_name] = {"enabled": False, "group": group_meta}
                    except Exception as e:
                        logs.append(f"  WARNING updating status: {str(e)}")

                try:
                    save_meta(meta)
                except Exception as e:
                    logs.append(f"  WARNING saving meta: {str(e)}")

                # --- Quản lý sysctl cho SYN Flood ---
                if group_name == "SYN Flood":
                    try:
                        if enable:
                            try:
                                if not isinstance(self.sysctl_backup, dict):
                                    self.sysctl_backup = {}
                                for p in self.SYSCTL_PARAMS:
                                    try:
                                        v = get_sysctl(p)
                                        if v:
                                            self.sysctl_backup[p] = v
                                    except Exception as e:
                                        logs.append(f"  WARNING getting sysctl {p}: {str(e)}")
                                self._save_sysctl_backup()
                                set_sysctl("net.ipv4.tcp_syncookies", "1")
                                set_sysctl("net.ipv4.tcp_max_syn_backlog", "2048")
                                set_sysctl("net.ipv4.tcp_synack_retries", "3")
                                set_sysctl("net.ipv4.tcp_abort_on_overflow", "1")
                                logs.append("SYSCTL: applied SYN protections")
                            except Exception as e:
                                logs.append(f"SYSCTL ERROR applying: {str(e)}")
                        else:
                            try:
                                if isinstance(self.sysctl_backup, dict):
                                    for p, v in self.sysctl_backup.items():
                                        try:
                                            if v and isinstance(v, str):
                                                set_sysctl(p, v)
                                                logs.append(f"SYSCTL: restored {p}={v}")
                                        except Exception as e:
                                            logs.append(f"  WARNING restoring sysctl {p}={v}: {str(e)}")
                            except Exception as e:
                                logs.append(f"SYSCTL ERROR restoring: {str(e)}")
                    except Exception as e:
                        logs.append(f"SYSCTL ERROR: {str(e)}")
                        import traceback
                        traceback.print_exc()

                try:
                    self._save_status()
                except Exception as e:
                    logs.append(f"  WARNING saving status: {str(e)}")
                
                try:
                    self.ruleToggled.emit(group_name, enable)
                except Exception as e:
                    logs.append(f"  WARNING emitting signal: {str(e)}")
                
                return "\n".join(logs)
            except Exception as e:
                import traceback
                error_msg = f"ERROR in toggleRule inner try: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                return error_msg
        except Exception as e:
            import traceback
            error_msg = f"ERROR in toggleRule: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return error_msg
