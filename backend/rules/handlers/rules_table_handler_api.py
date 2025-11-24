"""
Handler xử lý logic cho Rules Table sử dụng API Service
"""

from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from service.api_client import get_client


class RulesTableHandlerAPI:
    """Xử lý logic cho bảng hiển thị rules sử dụng API"""
    
    def __init__(self, ui, parent=None):
        """
        Args:
            ui: UI object từ uic.loadUi
            parent: Parent QObject cho timer (thường là MainWindow instance)
        """
        self.ui = ui
        self.client = get_client()
        self.current_filter = ""
        # Timer cần parent để không bị garbage collected
        # Nếu không có parent, dùng ui làm parent
        timer_parent = parent if parent else ui
        self.refresh_timer = QTimer(timer_parent)
        self.refresh_timer.timeout.connect(self.refresh_rules_table)
        self.refresh_timer.start(1500)  # Refresh mỗi 1.5 giây
    
    def refresh_rules_table(self):
        """Lấy danh sách rule từ API và hiển thị trên tableRules"""
        try:
            rules = self.client.list_rules()
            # Debug: in số lượng rules và chains
            if rules:
                chains = set(r.get("chain", "INPUT") for r in rules)
                print(f"Đã lấy {len(rules)} rule(s) từ {len(chains)} chain(s): {', '.join(sorted(chains))}")
        except Exception as e:
            print(f"Lỗi khi lấy danh sách rules: {e}")
            import traceback
            traceback.print_exc()
            return
        
        filter_text = self.current_filter.lower().strip()
        table = self.ui.tableRules
        
        # Save the state of checked checkboxes (lưu theo chain+num vì num có thể trùng nhau giữa các chains)
        checked_rules = set()
        delete_col = table.columnCount() - 1 if table.columnCount() > 0 else 12
        chain_col = 10  # Cột chain
        for row in range(table.rowCount()):
            chk_item = table.item(row, delete_col)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                num_item = table.item(row, 0)
                chain_item = table.item(row, chain_col)
                if num_item and chain_item:
                    # Lưu theo format "chain:num" để tránh trùng lặp
                    checked_rules.add(f"{chain_item.text()}:{num_item.text()}")
        
        table.setRowCount(0)
        table.setColumnCount(13)
        headers = [
            "num", "pkts", "bytes", "target", "prot", "opt",
            "in", "out", "source", "destination", "chain", "detail", "delete"
        ]
        table.setHorizontalHeaderLabels(headers)

        row_index = 0
        for rule in rules:
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

            # Restore checked state if previously checked (kiểm tra theo chain:num)
            rule_key = f"{chain}:{rule['num']}"
            if rule_key in checked_rules:
                chk_item.setCheckState(Qt.CheckState.Checked)
            else:
                chk_item.setCheckState(Qt.CheckState.Unchecked)
            table.setItem(row_index, 12, chk_item)
            
            row_index += 1

        table.resizeColumnsToContents()
    
    def on_search_clicked(self):
        """Lọc theo chain"""
        chain_name = self.ui.editRules.text().strip()
        self.current_filter = chain_name
        print(f"Filter applied: {chain_name if chain_name else 'All rules shown'}")
        self.refresh_rules_table()
    
    def on_delete_many_clicked(self):
        """Xoá rule đã tick hoặc theo chain"""
        # Tạm dừng refresh timer để tránh race condition
        self.refresh_timer.stop()
        
        try:
            table = self.ui.tableRules
            selected_nums = []

            delete_col = table.columnCount() - 1

            # Lấy danh sách rule đã tick (lưu cả chain và num)
            chain_col = 10  # Cột chain
            selected_rules = []  # List of (chain, num) tuples
            for row in range(table.rowCount()):
                chk_item = table.item(row, delete_col)
                if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                    num_item = table.item(row, 0)
                    chain_item = table.item(row, chain_col)
                    if num_item and chain_item:
                        selected_rules.append((chain_item.text(), num_item.text()))

            if selected_rules:
                # Lấy tất cả rules từ API để map chain+num thành num thực tế
                try:
                    all_rules = self.client.list_rules()
                    rule_map = {}  # Map (chain, num) -> actual rule
                    for r in all_rules:
                        rule_map[(r.get("chain", "INPUT"), r["num"])] = r
                    
                    # Lấy nums từ selected_rules
                    selected_nums = []
                    for chain, num in selected_rules:
                        if (chain, num) in rule_map:
                            selected_nums.append(num)
                    
                    if selected_nums:
                        print(f"Deleting {len(selected_nums)} chosen rule(s)...")
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

            # Refresh sau khi xóa xong
            self.refresh_rules_table()
        finally:
            # Khởi động lại timer
            self.refresh_timer.start(1500)

