import subprocess
import json
import os
from PyQt6.QtCore import QAbstractListModel, Qt, QModelIndex, QTimer, pyqtSlot

META_FILE = "rules_meta.json"

PROTOCOL_MAP = {
    "icmp": "1",
    "tcp": "6",
    "udp": "17"
}


def normalize_rule_key(rule_key: str) -> str:
    """
    Chuẩn hóa key rule để trùng định dạng với available_rules.py:
    <TARGET> <PROT_NUM> -- <IN> <OUT> <SRC> <DEST>
    
    Input: rule_key từ iptables output (format: target prot opt in out source destination ...)
    Output: normalized key (format: target prot_num -- in out source destination)
    
    Logic này phải match chính xác với normalize_rule_key() trong available_rules.py
    """
    parts = rule_key.split()
    if len(parts) < 3:
        return rule_key.strip()
    
    target = parts[0]
    prot = parts[1]
    
    # Chuyển protocol name thành number (icmp -> 1, tcp -> 6, udp -> 17)
    # Nếu đã là số thì giữ nguyên
    if prot.isdigit():
        prot_num = prot
    else:
        prot_num = PROTOCOL_MAP.get(prot.lower(), prot)
    
    opt = "--"
    in_if = "*"
    out_if = "*"
    
    # Parse source và dest
    # Format từ iptables output: target prot opt in out source destination ...
    # opt thường là "--", nếu có "--" thì tìm nó, nếu không thì lấy từ vị trí cố định
    source = "0.0.0.0/0"
    dest = "0.0.0.0/0"
    
    if "--" in parts:
        # Format: target prot -- in out source destination
        idx = parts.index("--")
        # Phần tử sau "--" là: in, out, source, destination
        if len(parts) > idx + 1:
            in_if = parts[idx + 1]
        if len(parts) > idx + 2:
            out_if = parts[idx + 2]
        if len(parts) > idx + 3:
            source = parts[idx + 3]
        if len(parts) > idx + 4:
            dest = parts[idx + 4]
    else:
        # Format: target prot opt in out source destination (không có "--")
        # Lấy từ vị trí cố định
        if len(parts) >= 7:
            in_if = parts[3] if len(parts) > 3 else "*"
            out_if = parts[4] if len(parts) > 4 else "*"
            source = parts[5] if len(parts) > 5 else "0.0.0.0/0"
            dest = parts[6] if len(parts) > 6 else "0.0.0.0/0"
    
    # Tạo normalized key với format: target prot_num -- in out source dest
    # Match chính xác với format trong available_rules.py normalize_rule_key()
    # Lưu ý: source và dest giữ nguyên "*" hoặc "0.0.0.0/0" tùy theo input
    norm_key = f"{target} {prot_num} {opt} {in_if} {out_if} {source} {dest}"
    return norm_key.strip()


def get_group_map():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r") as f:
            return json.load(f)
    return {}


def get_input_rules():
    try:
        result = subprocess.run(
            ["sudo", "iptables", "-L", "INPUT", "-v", "-n", "--line-numbers"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        rules = []
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            rule_key = " ".join(parts[3:])
            rule = {
                "num": parts[0],
                "pkts": parts[1],
                "bytes": parts[2],
                "target": parts[3],
                "prot": parts[4],
                "opt": parts[5],
                "in_": parts[6],
                "out": parts[7],
                "source": parts[8],
                "destination": parts[9],
                "rule_key": rule_key
            }
            rules.append(rule)
        return rules
    except subprocess.CalledProcessError as e:
        print("Lỗi lấy danh sách rule:", e)
        return []


class IptablesModel(QAbstractListModel):
    """Model quản lý rule INPUT chain."""

    NumRole = Qt.ItemDataRole.UserRole + 1
    PktsRole = Qt.ItemDataRole.UserRole + 2
    BytesRole = Qt.ItemDataRole.UserRole + 3
    TargetRole = Qt.ItemDataRole.UserRole + 4
    ProtRole = Qt.ItemDataRole.UserRole + 5
    OptRole = Qt.ItemDataRole.UserRole + 6
    InRole = Qt.ItemDataRole.UserRole + 7
    OutRole = Qt.ItemDataRole.UserRole + 8
    SourceRole = Qt.ItemDataRole.UserRole + 9
    DestinationRole = Qt.ItemDataRole.UserRole + 10
    GroupRole = Qt.ItemDataRole.UserRole + 11

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = get_input_rules()
        self.group_map = get_group_map()
        self.filter_group = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refreshRules)
        self.timer.start(1500)

    def rowCount(self, parent=QModelIndex()):
        return len(self.rules)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        rule = self.rules[index.row()]
        role_map = {
            self.NumRole: "num",
            self.PktsRole: "pkts",
            self.BytesRole: "bytes",
            self.TargetRole: "target",
            self.ProtRole: "prot",
            self.OptRole: "opt",
            self.InRole: "in_",
            self.OutRole: "out",
            self.SourceRole: "source",
            self.DestinationRole: "destination"
        }
        if role == self.GroupRole:
            key = rule["rule_key"]
            # Normalize key để match với format trong rules_meta.json
            norm_key = normalize_rule_key(key)
            
            # Thử lookup với normalized key trước
            group = self.group_map.get(norm_key)
            if group:
                return group
            
            # Thử với key gốc
            group = self.group_map.get(key)
            if group:
                return group
            
            # Thử với các biến thể của source/dest (* vs 0.0.0.0/0)
            # Vì available_rules.py có thể dùng "*" cho source, nhưng iptables output dùng "0.0.0.0/0"
            parts = norm_key.split()
            if len(parts) >= 7:
                # Thử thay source "*" thành "0.0.0.0/0" và ngược lại
                if parts[5] == "*":
                    alt_key = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]} 0.0.0.0/0 {parts[6]}"
                    group = self.group_map.get(alt_key)
                    if group:
                        return group
                elif parts[5] == "0.0.0.0/0":
                    alt_key = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]} * {parts[6]}"
                    group = self.group_map.get(alt_key)
                    if group:
                        return group
            
            return "None"
        if role in role_map:
            return rule[role_map[role]]
        return None

    def roleNames(self):
        return {
            self.NumRole: b"num",
            self.PktsRole: b"pkts",
            self.BytesRole: b"bytes",
            self.TargetRole: b"target",
            self.ProtRole: b"prot",
            self.OptRole: b"opt",
            self.InRole: b"in",
            self.OutRole: b"out",
            self.SourceRole: b"source",
            self.DestinationRole: b"destination",
            self.GroupRole: b"group",
        }

    def refreshRules(self):
        """Làm mới danh sách rule."""
        self.group_map = get_group_map()
        all_rules = get_input_rules()

        if self.filter_group:
            new_rules = [
                r for r in all_rules
                if self.group_map.get(normalize_rule_key(r["rule_key"]), self.group_map.get(r["rule_key"], "None")) == self.filter_group
            ]
        else:
            new_rules = all_rules

        if new_rules != self.rules:
            self.beginResetModel()
            self.rules = new_rules
            self.endResetModel()
            print("Rules updated.")

    @pyqtSlot(str)
    def deleteRule(self, num):
        if not num.isdigit():
            print("Num phải là số!")
            return
        cmd = ["sudo", "iptables", "-D", "INPUT", num]
        try:
            subprocess.run(cmd, check=True)
            print(f"Đã xóa rule số {num}")
            self.refreshRules()
        except subprocess.CalledProcessError as e:
            print(f"Lỗi xóa rule: {e}")

    @pyqtSlot(str)
    def setFilterGroup(self, group):
        self.filter_group = group.strip()
        self.refreshRules()

    @pyqtSlot(str)
    def deleteGroupRule(self, group):
        group = group.strip()
        if not group:
            print("Group rỗng.")
            return

        meta = get_group_map()
        keys_to_delete = [k for k, v in meta.items() if v == group]
        if not keys_to_delete:
            print(f"Không tìm thấy rule nào trong group '{group}'")
            return

        all_rules = get_input_rules()
        # Normalize rule_key để match với keys trong meta
        rules_to_delete = [
            r for r in all_rules 
            if normalize_rule_key(r["rule_key"]) in keys_to_delete or r["rule_key"] in keys_to_delete
        ]

        for r in sorted(rules_to_delete, key=lambda x: int(x["num"]), reverse=True):
            try:
                subprocess.run(["sudo", "iptables", "-D", "INPUT", r["num"]], check=True)
                print(f"Đã xoá rule {r['num']} trong group {group}")
            except subprocess.CalledProcessError as e:
                print(f"Lỗi xoá rule: {e}")

        for k in keys_to_delete:
            meta.pop(k, None)
        with open(META_FILE, "w") as f:
            json.dump(meta, f, indent=4)

        self.refreshRules()
