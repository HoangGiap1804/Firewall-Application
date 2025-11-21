"""
Handler xử lý logic cho Rules Table (hiển thị, tìm kiếm, xóa rules)
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt
from backend.rules.core import get_input_rules, get_group_map, normalize_rule_key


class RulesTableHandler:
    """Xử lý logic cho bảng hiển thị rules"""
    
    def __init__(self, ui, iptables_model):
        """
        Args:
            ui: UI object từ uic.loadUi
            iptables_model: IptablesModel instance
        """
        self.ui = ui
        self.iptables_model = iptables_model
        self.current_filter = ""
    
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

