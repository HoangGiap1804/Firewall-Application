"""
Handler xử lý logic thêm rule mới
"""

from backend.rules.core import IptablesHandler


class AddRuleHandler:
    """Xử lý logic thêm rule mới vào iptables"""
    
    def __init__(self, ui):
        """
        Args:
            ui: UI object từ uic.loadUi
        """
        self.ui = ui
        self.ip_handler = IptablesHandler()
    
    def on_add_rule_clicked(self, refresh_callback):
        """
        Lấy dữ liệu từ tab Add Rule và gọi IptablesHandler.addRule(...)
        Sau khi thêm, gọi refresh_callback để refresh tableRules.
        
        Args:
            refresh_callback: Function để refresh rules table sau khi thêm
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
        refresh_callback()
    
    def on_add_rule_in_frame_clicked(self, refresh_callback):
        """
        Lấy dữ liệu từ frameAddRule và gọi IptablesHandler.addRule(...)
        Sau khi thêm, gọi refresh_callback để refresh tableRules.
        
        Args:
            refresh_callback: Function để refresh rules table sau khi thêm
        """
        # Receive inputs from frameAddRule
        state = self.ui.editAddRuleState.text().strip() if hasattr(self.ui, "editAddRuleState") else ""
        interface_in = self.ui.editAddRuleIn.text().strip() if hasattr(self.ui, "editAddRuleIn") else ""
        interface_out = self.ui.editAddRuleOut.text().strip() if hasattr(self.ui, "editAddRuleOut") else ""
        # Sử dụng interface_in nếu có, nếu không thì dùng interface_out
        interface = interface_in if interface_in else interface_out
        protocol = ""
        if hasattr(self.ui, "comboAddRuleProtocol"):
            protocol = self.ui.comboAddRuleProtocol.currentText().strip()
        action = ""
        if hasattr(self.ui, "comboAddRuleAction"):
            action = self.ui.comboAddRuleAction.currentText().strip()
        port = self.ui.editAddRulePort.text().strip() if hasattr(self.ui, "editAddRulePort") else ""
        source = self.ui.editAddRuleSource.text().strip() if hasattr(self.ui, "editAddRuleSource") else ""
        destination = self.ui.editAddRuleDestination.text().strip() if hasattr(self.ui, "editAddRuleDestination") else ""
        opt = self.ui.editAddRuleOpt.text().strip() if hasattr(self.ui, "editAddRuleOpt") else ""
        # Group không có trong frameAddRule, để trống
        group = ""

        # Lowercase for protocols
        protocol_map = {"TCP": "tcp", "UDP": "udp", "ICMP": "icmp", "": ""}
        protocol_normalized = protocol_map.get(protocol.upper(), protocol.lower())

        # Uppercase for actions
        action_normalized = action.upper() if action else ""

        # Validate required fields
        if not protocol_normalized or not action_normalized:
            print("Protocol và Action là bắt buộc!")
            return

        # Call backend method: addRule(ip, port, protocol, action, interface, state, group="")
        # Note: destination, opt, in, out sẽ được xử lý trong backend sau
        try:
            self.ip_handler.addRule(source, port, protocol_normalized, action_normalized, interface, state, group)
            print("✅ Đã thêm rule từ frameAddRule")
            if destination:
                print(f"   Destination: {destination}")
            if opt:
                print(f"   Options: {opt}")
            
            # Clear form after successful add
            if hasattr(self.ui, "editAddRuleState"):
                self.ui.editAddRuleState.clear()
            if hasattr(self.ui, "editAddRuleIn"):
                self.ui.editAddRuleIn.clear()
            if hasattr(self.ui, "editAddRuleOut"):
                self.ui.editAddRuleOut.clear()
            if hasattr(self.ui, "editAddRulePort"):
                self.ui.editAddRulePort.clear()
            if hasattr(self.ui, "editAddRuleSource"):
                self.ui.editAddRuleSource.clear()
            if hasattr(self.ui, "editAddRuleDestination"):
                self.ui.editAddRuleDestination.clear()
            if hasattr(self.ui, "editAddRuleOpt"):
                self.ui.editAddRuleOpt.clear()
        except Exception as e:
            print(f"❌ Lỗi khi thêm rule: {e}")

        # Refresh rules table
        refresh_callback()

