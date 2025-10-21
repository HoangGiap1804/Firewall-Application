from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

class LogModel(QAbstractListModel):
    Roles = ["in", "out", "mac", "src", "dst", "len", "tos", "prec",
             "ttl", "id", "proto", "spt", "dpt", "len2"]

    def __init__(self):
        super().__init__()
        self.logs = []

    def rowCount(self, parent=QModelIndex()):
        return len(self.logs)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.logs):
            return None
        key = self.Roles[role - Qt.UserRole - 1]
        return self.logs[index.row()].get(key, "")

    def roleNames(self):
        return {Qt.UserRole + i + 1: key.encode() for i, key in enumerate(self.Roles)}

    def addLog(self, line):
        log_dict = {}
        for part in line.split():
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.lower()
                if key == "len" and "len" in log_dict:
                    key = "len2"
                if key in self.Roles:
                    log_dict[key] = value
        if log_dict:
            self.beginInsertRows(QModelIndex(), len(self.logs), len(self.logs))
            self.logs.append(log_dict)
            self.endInsertRows()

    # ✅ Thêm hàm trả về list JSON
    @Slot(result="QVariantList")
    def toList(self):
        return self.logs
