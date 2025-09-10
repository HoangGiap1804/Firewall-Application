from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class LogModel(QAbstractListModel):
    # khai báo role
    Roles = ["in", "out", "mac", "src", "dst", "len", "tos", "prec",
             "ttl", "id", "proto", "spt", "dpt", "len2"]

    def __init__(self):
        super().__init__()
        self._logs = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._logs)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._logs):
            return None
        key = self.Roles[role - Qt.UserRole - 1] if role >= Qt.UserRole + 1 else None
        if key:
            return self._logs[index.row()].get(key, "")
        return None

    def roleNames(self):
        roles = {}
        for i, key in enumerate(self.Roles):
            roles[Qt.UserRole + i + 1] = key.encode()
        return roles

    def addLog(self, line):
        log_dict = {}
        for part in line.split():
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.lower()
                if key == "len":
                    # có 2 trường LEN trong log, map cái thứ 2 thành len2
                    if "len" in log_dict:
                        key = "len2"
                if key in self.Roles:
                    log_dict[key] = value
        if log_dict:
            self.beginInsertRows(QModelIndex(), len(self._logs), len(self._logs))
            self._logs.append(log_dict)
            self.endInsertRows()
