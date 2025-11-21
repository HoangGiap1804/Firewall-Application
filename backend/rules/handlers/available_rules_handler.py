"""
Handler xử lý logic cho Available Rules Tab
"""

from backend.rules.core import AvailableRules


class AvailableRulesHandler:
    """Xử lý logic cho tab Available Rules"""
    
    def __init__(self, ui):
        """
        Args:
            ui: UI object từ uic.loadUi
        """
        self.ui = ui
        self.available_rules = AvailableRules()
        self.available_rule_map = self._build_rule_map()
    
    def _build_rule_map(self):
        """Tạo map checkbox -> group name"""
        return {
            self.ui.checkBoxICMPFlood: "ICMP Flood",
            self.ui.checkBoxSYNFlood: "SYN Flood",
            self.ui.checkBoxPortScan: "Port Scan",
            self.ui.checkBoxIpSpoofing: "IP Spoofing",
            self.ui.checkBoxInvalidPacket: "Invalid Packet",
            self.ui.checkBoxBroadcast: "Broadcast Control",
            self.ui.checkBoxOutbound: "Outbound Protection",
            self.ui.checkBoxFinXmasNullScan: "FIN/XMAS/NULL Scan",
            self.ui.checkBoxSSH_FTP: "SSH/FTP Brute Force",
        }
    
    def connect_checkboxes(self, toggle_callback):
        """
        Kết nối event handlers cho các checkboxes
        
        Args:
            toggle_callback: Function được gọi khi checkbox thay đổi state
        """
        for checkbox, group_name in self.available_rule_map.items():
            checkbox.stateChanged.connect(lambda state, g=group_name: toggle_callback(g, state))
    
    def on_available_rule_toggled(self, group_name, state):
        """Khi bật/tắt checkbox => gọi toggleRule trong backend."""
        enable = bool(state)
        print(f"Toggling {group_name}: {'ON' if enable else 'OFF'}")
        try:
            result = self.available_rules.toggleRule(group_name, enable)
            print(result)
        except Exception as e:
            print(f"Error toggling {group_name}: {e}")
    
    def load_available_rules_status(self):
        """Cập nhật trạng thái checkbox theo available_rules.json"""
        status_data = self.available_rules.getStatus()

        if not isinstance(status_data, dict):
            print("Warning: available_rules.getStatus() did not return dict.")
            return

        for checkbox, group_name in self.available_rule_map.items():
            info = status_data.get(group_name, {})
            enabled = info.get("enabled", False) if isinstance(info, dict) else bool(info)
            checkbox.blockSignals(True)
            checkbox.setChecked(enabled)
            checkbox.blockSignals(False)

