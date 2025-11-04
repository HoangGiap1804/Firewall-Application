from PyQt6 import QtWidgets, uic
from backend.log_tab import LogTab

from backend.rule_input import IptablesModel, get_input_rules, get_group_map, normalize_rule_key

from backend.add_rule import IptablesHandler

from backend.available_rules import AvailableRules

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")

        ## Log Tab
        self.log_tab = LogTab(self.ui.tabLogTable)

        ## Rule input Tab
        self.iptables_model = IptablesModel()
        
        # Current filter state (editRules)
        self.current_filter = ""
        self.refresh_rules_table()

        self.ui.buttonSearch.clicked.connect(self.on_search_clicked)
        self.ui.buttonDeleteMany.clicked.connect(self.on_delete_many_clicked)
        
        # Refresh rules table periodically
        self.iptables_model.timer.timeout.connect(self.refresh_rules_table)

        ## Add rule Tab
        self.ip_handler = IptablesHandler()
        self.ui.buttonAddRule.clicked.connect(self.on_add_rule_clicked)
        
        ## Available Rules Tab
        self.available_rules = AvailableRules()
        
        # Map checkbox -> group name trong available_rules.py
        self.available_rule_map = {
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
        
        # Event handlers for checkboxes
        for checkbox, group_name in self.available_rule_map.items():
            checkbox.stateChanged.connect(lambda state, g=group_name: self.on_available_rule_toggled(g, state))

        # Restore checkbox states based on current iptables rules checkbox status, use QTimer to delay execution for UI load
        QTimer.singleShot(0, self.load_available_rules_status)

        # Show the main window
        self.ui.show()

    # Rule input Tab handlers
    def refresh_rules_table(self):
        """Lấy danh sách rule từ model và hiển thị trên tableRules"""
        rules = get_input_rules()
        group_map = get_group_map()
        filter_text = self.current_filter.lower().strip()
        table = self.ui.tableRules
        
        # Save the state of checked checkboxes
        checked_nums = set()
        delete_col = table.columnCount() - 1  
        for row in range(table.rowCount()):
            chk_item = table.item(row, delete_col)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                num_item = table.item(row, 0)
                if num_item:
                    checked_nums.add(num_item.text())
        
        table.setRowCount(0)
        table.setColumnCount(12)
        headers = [
            "num", "pkts", "bytes", "target", "prot", "opt",
            "in", "out", "source", "destination", "group", "delete"
        ]
        table.setHorizontalHeaderLabels(headers)

        for row_index, rule in enumerate(rules):
            # Group filtering - normalize key để match với format trong rules_meta.json
            norm_key = normalize_rule_key(rule["rule_key"])
            
            # Thử lookup với normalized key trước
            group = group_map.get(norm_key)
            if not group:
                # Thử với key gốc
                group = group_map.get(rule["rule_key"])
            if not group:
                # Thử với các biến thể của source/dest (* vs 0.0.0.0/0)
                parts = norm_key.split()
                if len(parts) >= 7:
                    if parts[5] == "*":
                        alt_key = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]} 0.0.0.0/0 {parts[6]}"
                        group = group_map.get(alt_key)
                    elif parts[5] == "0.0.0.0/0":
                        alt_key = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]} * {parts[6]}"
                        group = group_map.get(alt_key)
            if not group:
                group = "None"
            
            if filter_text and filter_text not in group.lower():
                continue
            
            table.insertRow(row_index)
            values = [
                rule["num"], rule["pkts"], rule["bytes"], rule["target"],
                rule["prot"], rule["opt"], rule["in_"], rule["out"], 
                rule["source"], rule["destination"], group
            ]
            
            # Set items in the table read-only
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, col_index, item)

            # Add checkbox for deletion
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)

            # Restore checked state if previously checked
            if rule["num"] in checked_nums:
                chk_item.setCheckState(Qt.CheckState.Checked)
            else:
                chk_item.setCheckState(Qt.CheckState.Unchecked)
            table.setItem(row_index, 11, chk_item)

        table.resizeColumnsToContents()
    
    # Search and Delete handlers
    def on_search_clicked(self):
        """Lọc theo group"""
        group_name = self.ui.editRules.text().strip()
        self.current_filter = group_name
        self.iptables_model.setFilterGroup(group_name)
        print(f"Filter applied: {group_name if group_name else 'All rules shown'}")

    def on_delete_many_clicked(self):
        """
        Xoá rule đã tick. Nếu không tick => xoá theo group trong editRules.
        """
        table = self.ui.tableRules
        selected_nums = []

        delete_col = table.columnCount() - 1  # cột delete checkbox

        # Lấy danh sách rule đã tick
        for row in range(table.rowCount()):
            chk_item = table.item(row, delete_col)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                num_item = table.item(row, 0)
                if num_item:
                    selected_nums.append(num_item.text())

        if selected_nums:
            print(f"Deleting {len(selected_nums)} chosen rule(s)...")
            for num in sorted(selected_nums, key=lambda x: int(x), reverse=True):
                try:
                    self.iptables_model.deleteRule(num)
                except Exception as e:
                    print(f"Error deleting rule {num}: {e}")
        else:
            group_name = self.ui.editRules.text().strip()
            if group_name:
                print(f"No chosen rule, deleting by group: {group_name}")
                self.iptables_model.deleteGroupRule(group_name)
            else:
                print("No chosen rule and no group name provided.")

        self.refresh_rules_table()
        
    # Add Rule Tab handler
    def on_add_rule_clicked(self):
        """
        Lấy dữ liệu từ tab Add Rule và gọi IptablesHandler.addRule(...)
        Sau khi thêm, refresh tableRules.
        """
        # Receive inputs
        state = self.ui.editState.text().strip() if hasattr(self.ui, "editState") else ""
        interface = self.ui.editInterface.text().strip() if hasattr(self.ui, "editInterface") else ""
        protocol = ""
        if hasattr(self.ui, "comboProtocol"):
            protocol = self.ui.comboProtocol.currentText().strip()
        action = ""
        if hasattr(self.ui, "comboAction"):
            action = self.ui.comboAction.currentText().strip()
        port = self.ui.editPort.text().strip() if hasattr(self.ui, "editPort") else ""
        source = self.ui.editSource.text().strip() if hasattr(self.ui, "editSource") else ""
        group = self.ui.editGroup.text().strip() if hasattr(self.ui, "editGroup") else ""

        # Lowercase for protocols
        protocol_map = {"TCP": "tcp", "UDP": "udp", "ICMP": "icmp", "": ""}
        protocol_normalized = protocol_map.get(protocol.upper(), protocol.lower())

        # Uppercase for actions
        action_normalized = action.upper() if action else ""

        # Call backend method: addRule(ip, port, protocol, action, interface, state, group="")
        try:
            self.ip_handler.addRule(source, port, protocol_normalized, action_normalized, interface, state, group)
            print("Adding rule, please wait...")
        except Exception as e:
            print("Error calling addRule():", e)

        # Refresh rules table
        self.refresh_rules_table()
    
    # Available Rules Tab handlers
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
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())
