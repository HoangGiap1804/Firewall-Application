import subprocess
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QTimer, Signal, QObject, Slot

def get_input_rules():
    try:
        result = subprocess.run(
            ['sudo', 'iptables', '-L', 'INPUT', '-v', '-n', '--line-numbers'],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        rules = []

        # Bỏ 2 dòng header
        for line in lines[2:]:
            if line.strip() == "":
                continue
            parts = line.split()
            rule = {
                "num": parts[0] if len(parts) > 0 else "",
                "pkts": parts[1] if len(parts) > 1 else "",
                "bytes": parts[2] if len(parts) > 2 else "",
                "target": parts[3] if len(parts) > 3 else "",
                "prot": parts[4] if len(parts) > 4 else "",
                "opt": parts[5] if len(parts) > 5 else "",
                "in_": parts[6] if len(parts) > 6 else "",
                "out": parts[7] if len(parts) > 7 else "",
                "source": parts[8] if len(parts) > 8 else "",
                "destination": parts[9] if len(parts) > 9 else ""
            }
            rules.append(rule)
        return rules
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        return []

# Model cho Repeater / TableView
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = get_input_rules()

        # Timer refresh mỗi 2 giây
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
            self.DestinationRole: b"destination"
        }

    def refreshRules(self):
        new_rules = get_input_rules()
        if new_rules != self.rules:  # nếu có thay đổi
            self.beginResetModel()
            self.rules = new_rules
            self.endResetModel()
            print("Rules updated!")  # bạn có thể emit signal để QML biết
    @Slot(str)
    def deleteRule(self, num):
        """
        Xóa rule INPUT theo số thứ tự (num)
        """
        if not num.isdigit():
            print("Num phải là số nguyên!")
            return

        cmd = ["sudo", "iptables", "-D", "INPUT", num]
        try:
            subprocess.run(cmd, check=True)
            print(f"Đã xóa rule số {num}")
        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi xóa rule: {e}")