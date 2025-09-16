# log_model.py
import subprocess
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal, Slot, Property

class LogAttackModel(QAbstractListModel):
    TimestampRole = Qt.UserRole + 1
    PrefixRole = Qt.UserRole + 2
    MessageRole = Qt.UserRole + 3

    def __init__(self):
        super().__init__()
        self._logs = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._logs)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        log = self._logs[row]
        if role == self.TimestampRole:
            return log["time"]
        if role == self.PrefixRole:
            return log["prefix"]
        if role == self.MessageRole:
            return log["msg"]
        return None

    def roleNames(self):
        return {
            self.TimestampRole: b"time",
            self.PrefixRole: b"prefix",
            self.MessageRole: b"msg"
        }

    def addLog(self, time, prefix, msg):
        self.beginInsertRows(QModelIndex(), len(self._logs), len(self._logs))
        self._logs.append({"time": time, "prefix": prefix, "msg": msg})
        self.endInsertRows()

    def startMonitor(self):
        # Dùng journalctl -k -f để theo dõi log kernel realtime
        process = subprocess.Popen(
            ["journalctl", "-k", "-f", "-n", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        import threading, re
        regex = re.compile(r"(\w{3}\s+\d+\s+\d+:\d+:\d+).* (PING_FLOOD|SYN_FLOOD|SSH_BRUTEFORCE|PORT_SCAN|BLOCKED_IP): (.*)")

        def reader():
            for line in process.stdout:
                m = regex.search(line)
                if m:
                    self.addLog(m.group(1), m.group(2), m.group(3))

        threading.Thread(target=reader, daemon=True).start()
