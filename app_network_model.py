import psutil
import os
import configparser
from pathlib import Path
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QByteArray


class AppNetworkModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    PidRole = Qt.UserRole + 2
    IconRole = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps = []
        self.refresh()

    def roleNames(self):
        return {
            self.NameRole: QByteArray(b"name"),
            self.PidRole: QByteArray(b"pid"),
            self.IconRole: QByteArray(b"icon"),
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._apps)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        app = self._apps[index.row()]
        if role == self.NameRole:
            return app["name"]
        if role == self.PidRole:
            return app["pid"]
        if role == self.IconRole:
            return app["icon"]
        return None

    def _find_icon_for_process(self, proc_name: str) -> str:
        """Tìm icon từ .desktop ứng với tên process."""
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications"
        ]
        for ddir in desktop_dirs:
            if ddir.exists():
                for file in ddir.glob("*.desktop"):
                    config = configparser.ConfigParser(interpolation=None)
                    try:
                        config.read(file, encoding="utf-8")
                        name = config.get("Desktop Entry", "Name", fallback="")
                        exec_cmd = config.get("Desktop Entry", "Exec", fallback="")
                        icon = config.get("Desktop Entry", "Icon", fallback="")

                        # Match theo tên process hoặc exec
                        if proc_name.lower() in exec_cmd.lower() or proc_name.lower() in file.stem.lower():
                            return icon
                    except Exception:
                        continue
        return ""  # fallback nếu không tìm thấy

    def refresh(self):
        apps = []
        seen = set()
        for proc in psutil.process_iter(attrs=["pid", "name", "environ"]):
            try:
                env = proc.info.get("environ") or {}
                # Lọc process có GUI (x11/wayland)
                if "DISPLAY" in env or "WAYLAND_DISPLAY" in env:
                    pid = proc.info["pid"]
                    name = proc.info["name"]
                    if pid not in seen:
                        icon = self._find_icon_for_process(name)
                        apps.append({
                            "name": name,
                            "pid": pid,
                            "icon": icon
                        })
                        seen.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.beginResetModel()
        self._apps = apps
        self.endResetModel()
