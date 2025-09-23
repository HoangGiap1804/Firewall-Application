import subprocess
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QTimer, Slot
import os
import json

META_FILE = "rules_meta.json"

def get_group_map():
    if os.path.exists("rules_meta.json"):
        with open("rules_meta.json", "r") as f:
            return json.load(f)
    return {}

def get_input_rules():
    try:
        result = subprocess.run(
            ['sudo', 'iptables', '-L', 'INPUT', '-v', '-n', '--line-numbers'],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        rules = []
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            rule_key = " ".join(parts[3:])  # key duy nhất, bỏ num/pkts/bytes
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
        print("Error:", e)
        return []

class IptablesModel(QAbstractListModel):
    NumRole = Qt.UserRole + 1
    PktsRole = Qt.UserRole + 2
    BytesRole = Qt.UserRole + 3
    TargetRole = Qt.UserRole + 4
    ProtRole = Qt.UserRole + 5
    OptRole = Qt.UserRole + 6
    InRole = Qt.UserRole + 7
    OutRole = Qt.UserRole + 8
    SourceRole = Qt.UserRole + 9
    DestinationRole = Qt.UserRole + 10
    GroupRole = Qt.UserRole + 11

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = get_input_rules()
        self.group_map = get_group_map()
        self.filter_group = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refreshRules)
        self.timer.start(1000)

    def rowCount(self, parent=QModelIndex()):
        return len(self.rules)

    def data(self, index, role=Qt.DisplayRole):
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
            rule_key = rule["rule_key"]
            return self.group_map.get(rule_key, "None")
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
            self.GroupRole: b"group"
        }

    def refreshRules(self):
        self.group_map = get_group_map()
        all_rules = get_input_rules()

        if self.filter_group:
            filtered = []
            for r in all_rules:
                g = self.group_map.get(r["rule_key"], "None")
                if g == self.filter_group:
                    filtered.append(r)
            new_rules = filtered
        else:
            new_rules = all_rules

        if new_rules != self.rules:
            self.beginResetModel()
            self.rules = new_rules
            self.endResetModel()
            print("Rules updated!")

    @Slot(str)
    def deleteRule(self, num):
        if not num.isdigit():
            print("Num phải là số nguyên!")
            return

        # lấy rule_key trước khi xoá
        rule_to_delete = None
        for r in self.rules:
            if r["num"] == num:
                rule_to_delete = r["rule_key"]
                break

        cmd = ["sudo", "iptables", "-D", "INPUT", num]
        try:
            subprocess.run(cmd, check=True)
            print(f"Đã xóa rule số {num}")

            # Cập nhật JSON
            meta = get_group_map()
            if rule_to_delete and rule_to_delete in meta:
                del meta[rule_to_delete]
                with open(META_FILE, "w") as f:
                    json.dump(meta, f, indent=4)

            self.refreshRules()

        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi xóa rule: {e}")

    @Slot(str)
    def setFilterGroup(self, group_name):
        self.filter_group = group_name.strip()
        self.refreshRules()
        
    @Slot(str)
    def deleteGroupRule(self, group_name):
        """
        Xóa tất cả rule thuộc group_name
        """
        group_name = group_name.strip()
        if not group_name:
            print("Group rỗng, không thể xoá")
            return

        meta = get_group_map()
        keys_to_delete = [k for k, v in meta.items() if v == group_name]

        if not keys_to_delete:
            print(f"Không tìm thấy rule nào trong group '{group_name}'")
            return

        # Lấy danh sách rule hiện tại
        all_rules = get_input_rules()

        # Tìm các rule có rule_key nằm trong keys_to_delete
        rules_to_delete = [r for r in all_rules if r["rule_key"] in keys_to_delete]

        # Xóa lần lượt theo số thứ tự (num)
        # Lưu ý: iptables đánh lại số sau mỗi lần xoá,
        # nên phải xoá từ rule cuối cùng về đầu tiên để không lệch num
        for r in sorted(rules_to_delete, key=lambda x: int(x["num"]), reverse=True):
            num = r["num"]
            try:
                subprocess.run(["sudo", "iptables", "-D", "INPUT", num], check=True)
                print(f"Đã xoá rule số {num} trong group '{group_name}'")
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi xoá rule số {num}: {e}")

        # Xoá metadata
        for k in keys_to_delete:
            if k in meta:
                del meta[k]
        with open("rules_meta.json", "w") as f:
            json.dump(meta, f, indent=4)

        self.refreshRules()

