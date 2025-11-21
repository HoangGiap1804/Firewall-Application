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

