"""
Handler xử lý logic cho Rules Table sử dụng API Service
"""

from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from service.api_client import get_client


class RulesTableHandlerAPI:
    """Xử lý logic cho bảng hiển thị rules sử dụng API"""
    
    def __init__(self, ui):
        """
        Args:
            ui: UI object từ uic.loadUi
        """
        self.ui = ui
        self.client = get_client()
        self.current_filter = ""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_rules_table)
        self.refresh_timer.start(1500)  # Refresh mỗi 1.5 giây
    
    def refresh_rules_table(self):
        """Lấy danh sách rule từ API và hiển thị trên tableRules"""
        try:
            rules = self.client.list_rules()
        except Exception as e:
            print(f"Lỗi khi lấy danh sách rules: {e}")
            return
        
        filter_text = self.current_filter.lower().strip()
        table = self.ui.tableRules
        
        # Save the state of checked checkboxes
        checked_nums = set()
        delete_col = table.columnCount() - 1 if table.columnCount() > 0 else 12
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
            # Chain filtering
            chain = rule.get("chain", "INPUT")
            
            if filter_text and filter_text not in chain.lower():
                continue
            
            # Lấy detail từ rule_key
            rule_key = rule.get("rule_key", "")
            detail = ""
            if rule_key:
                parts = rule_key.split()
                if len(parts) > 7:
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
        print(f"Filter applied: {chain_name if chain_name else 'All rules shown'}")
        self.refresh_rules_table()
    
    def on_delete_many_clicked(self):
        """Xoá rule đã tick hoặc theo chain"""
        table = self.ui.tableRules
        selected_nums = []

        delete_col = table.columnCount() - 1

        # Lấy danh sách rule đã tick
        for row in range(table.rowCount()):
            chk_item = table.item(row, delete_col)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                num_item = table.item(row, 0)
                if num_item:
                    selected_nums.append(num_item.text())

        if selected_nums:
            print(f"Deleting {len(selected_nums)} chosen rule(s)...")
            try:
                result = self.client.delete_many_rules(selected_nums)
                print(f"✅ Đã xóa {len(result.get('deleted', []))} rule(s)")
                if result.get('failed'):
                    print(f"❌ Không thể xóa {len(result['failed'])} rule(s)")
            except Exception as e:
                QMessageBox.warning(None, "Lỗi", f"Không thể xóa rules: {e}")
        else:
            chain_name = self.ui.editRules.text().strip()
            if chain_name:
                print(f"No chosen rule, deleting by chain: {chain_name}")
                # Lấy tất cả rules của chain và xóa
                try:
                    rules = self.client.list_rules()
                    chain_rules = [r["num"] for r in rules if r.get("chain", "INPUT").upper() == chain_name.upper()]
                    if chain_rules:
                        result = self.client.delete_many_rules(chain_rules)
                        print(f"✅ Đã xóa {len(result.get('deleted', []))} rule(s) từ chain {chain_name}")
                except Exception as e:
                    QMessageBox.warning(None, "Lỗi", f"Không thể xóa rules theo chain: {e}")
            else:
                print("No chosen rule and no chain name provided.")

        self.refresh_rules_table()

