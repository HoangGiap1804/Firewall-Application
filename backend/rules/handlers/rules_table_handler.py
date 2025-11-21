"""
Handler xử lý logic cho Rules Table (hiển thị, tìm kiếm, xóa rules)
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt
from backend.rules.core import get_input_rules, normalize_rule_key


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
        table.setColumnCount(13)
        headers = [
            "num", "pkts", "bytes", "target", "prot", "opt",
            "in", "out", "source", "destination", "chain", "detail", "delete"
        ]
        table.setHorizontalHeaderLabels(headers)

        for row_index, rule in enumerate(rules):
            # Chain filtering - lấy chain từ rule (mặc định là "INPUT" vì get_input_rules() chỉ lấy INPUT chain)
            chain = rule.get("chain", "INPUT")
            
            if filter_text and filter_text not in chain.lower():
                continue
            
            # Lấy detail từ rule_key - phần sau destination
            rule_key = rule.get("rule_key", "")
            detail = ""
            if rule_key:
                # rule_key format: target prot opt in out source destination [extra...]
                # rule_key được tạo từ parts[3:], nên format là: target prot opt in out source destination [extra...]
                # destination ở index 6, detail là từ index 7 trở đi
                parts = rule_key.split()
                if len(parts) > 7:
                    # Có thông tin bổ sung sau destination
                    detail = " ".join(parts[7:])
            
            table.insertRow(row_index)
            values = [
                rule["num"], rule["pkts"], rule["bytes"], rule["target"],
                rule["prot"], rule["opt"], rule["in_"], rule["out"], 
                rule["source"], rule["destination"], chain, detail
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
            table.setItem(row_index, 12, chk_item)

        table.resizeColumnsToContents()
    
    def on_search_clicked(self):
        """Lọc theo chain"""
        chain_name = self.ui.editRules.text().strip()
        self.current_filter = chain_name
        self.iptables_model.setFilterChain(chain_name)
        print(f"Filter applied: {chain_name if chain_name else 'All rules shown'}")
    
    def on_delete_many_clicked(self):
        """
        Xoá rule đã tick. Nếu không tick => xoá theo chain trong editRules.
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
            chain_name = self.ui.editRules.text().strip()
            if chain_name:
                print(f"No chosen rule, deleting by chain: {chain_name}")
                self.iptables_model.deleteChainRule(chain_name)
            else:
                print("No chosen rule and no chain name provided.")

        self.refresh_rules_table()

