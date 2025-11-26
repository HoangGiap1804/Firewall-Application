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
        rule_map = {}
        checkbox_names = {
            "checkBoxICMPFlood": "ICMP Flood",
            "checkBoxSYNFlood": "SYN Flood",
            "checkBoxPortScan": "Port Scan",
            "checkBoxIpSpoofing": "IP Spoofing",
            "checkBoxInvalidPacket": "Invalid Packet",
            "checkBoxBroadcast": "Broadcast Control",
            "checkBoxOutbound": "Outbound Protection",
            "checkBoxFinXmasNullScan": "FIN/XMAS/NULL Scan",
            "checkBoxSSH_FTP": "SSH/FTP Brute Force",
        }
        
        for checkbox_name, group_name in checkbox_names.items():
            if hasattr(self.ui, checkbox_name):
                checkbox = getattr(self.ui, checkbox_name)
                rule_map[checkbox] = group_name
            else:
                print(f"Warning: Checkbox {checkbox_name} không tồn tại trong UI")
        
        return rule_map
    
    def connect_checkboxes(self, toggle_callback):
        """
        Kết nối event handlers cho các checkboxes
        
        Args:
            toggle_callback: Function được gọi khi checkbox thay đổi state
        """
        for checkbox, group_name in self.available_rule_map.items():
            try:
                checkbox.stateChanged.connect(lambda state, g=group_name: toggle_callback(g, state))
            except Exception as e:
                print(f"Error connecting checkbox for {group_name}: {e}")
    
    def on_available_rule_toggled(self, group_name, state):
        """Khi bật/tắt checkbox => gọi toggleRule trong backend."""
        enable = bool(state)
        print(f"Toggling {group_name}: {'ON' if enable else 'OFF'}")
        try:
            result = self.available_rules.toggleRule(group_name, enable)
            print(result)
            if "error" in result.lower() or "err" in result.lower():
                print(f"⚠️ Có lỗi khi toggle {group_name}: {result}")
        except Exception as e:
            import traceback
            print(f"❌ Error toggling {group_name}: {e}")
            traceback.print_exc()
            # Khôi phục lại trạng thái checkbox nếu có lỗi
            try:
                checkbox = None
                for cb, name in self.available_rule_map.items():
                    if name == group_name:
                        checkbox = cb
                        break
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(not enable)  # Đảo ngược lại
                    checkbox.blockSignals(False)
            except:
                pass
    
    def load_available_rules_status(self):
        """Cập nhật trạng thái checkbox theo available_rules.json"""
        try:
            status_data = self.available_rules.getStatus()

            if not isinstance(status_data, dict):
                print("Warning: available_rules.getStatus() did not return dict.")
                return

            for checkbox, group_name in self.available_rule_map.items():
                try:
                    info = status_data.get(group_name, {})
                    enabled = info.get("enabled", False) if isinstance(info, dict) else bool(info)
                    checkbox.blockSignals(True)
                    checkbox.setChecked(enabled)
                    checkbox.blockSignals(False)
                except Exception as e:
                    print(f"Error loading status for {group_name}: {e}")
        except Exception as e:
            import traceback
            print(f"Error in load_available_rules_status: {e}")
            traceback.print_exc()

