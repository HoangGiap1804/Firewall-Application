"""
Module quản lý việc setup và hiển thị charts trong UI
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from .system_monitor import SystemMonitor
from .host_monitor import HostSystemMonitor
from .system_chart import SystemChartsManager



class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


def setup_charts(ui, monitor):
    """
    Thiết lập và hiển thị charts trong UI
    
    Args:
        ui: UI object từ uic.loadUi
        monitor: SystemMonitor instance (cho container/sandbox)
    
    Returns:
        tuple: (sandbox_charts_manager, host_charts_manager)
    """
    # Tạo charts manager cho sandbox (tự động kết nối với monitor)
    sandbox_charts_manager = SystemChartsManager(monitor)
    
    # Tìm frameGraph trong UI (Sandbox tab)
    frame_graph = ui.findChild(QtWidgets.QFrame, "frameGraph")
    if frame_graph:
        # Tạo layout dọc để chia 2 chart (một trên, một dưới)
        layout = frame_graph.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame_graph)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
        
        # Thêm CPU chart vào trên
        layout.addWidget(sandbox_charts_manager.get_cpu_chart_view())
        
        # Thêm RAM chart vào dưới
        layout.addWidget(sandbox_charts_manager.get_ram_chart_view())

        # Thêm Network chart
        layout.addWidget(sandbox_charts_manager.get_network_chart_view())
    
    # Tìm các frame trong tab Graph (máy thật)
    frame_cpu = ui.findChild(QtWidgets.QFrame, "frameGraphCPU")
    frame_ram = ui.findChild(QtWidgets.QFrame, "frameGraphRAM")
    frame_temp = ui.findChild(QtWidgets.QFrame, "frameGraphTemperature")
    frame_network = ui.findChild(QtWidgets.QFrame, "frameGraphNetwork")
    frame_services = ui.findChild(QtWidgets.QFrame, "frameGraphServices")
    frame_disk = ui.findChild(QtWidgets.QFrame, "frameGraphDisk")
    
    # Tạo Labels cho Stats
    # Sử dụng ClickableLabel cho Services để hiển thị popup
    lbl_services = ClickableLabel("Active Services: 0")
    lbl_services.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    lbl_services.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
    lbl_services.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    
    lbl_free_disk = QtWidgets.QLabel("Free Disk: 0 GB")
    lbl_free_disk.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
    lbl_free_disk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    # Tạo host monitor và charts manager cho máy thật
    host_monitor = HostSystemMonitor(interval=1000)  # Cập nhật mỗi 1 giây
    host_charts_manager = SystemChartsManager(host_monitor, label_services=lbl_services, label_free_disk=lbl_free_disk)
    
    # Kết nối sự kiện click cho service label
    def show_services_popup():
        service_list = host_monitor.get_service_list()
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Active Services")
        dialog.resize(600, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(service_list)
        # Set font monospace cho dễ nhìn
        font = text_edit.font()
        font.setFamily("Monospace")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        text_edit.setFont(font)
        
        layout.addWidget(text_edit)
        
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        dialog.exec()

    lbl_services.clicked.connect(show_services_popup)
    
    if frame_cpu:
        layout_cpu = frame_cpu.layout()
        if layout_cpu is None:
            layout_cpu = QtWidgets.QVBoxLayout(frame_cpu)
            layout_cpu.setContentsMargins(5, 5, 5, 5)
        layout_cpu.addWidget(host_charts_manager.get_cpu_chart_view())
    
    if frame_ram:
        layout_ram = frame_ram.layout()
        if layout_ram is None:
            layout_ram = QtWidgets.QVBoxLayout(frame_ram)
            layout_ram.setContentsMargins(5, 5, 5, 5)
        layout_ram.addWidget(host_charts_manager.get_ram_chart_view())
    
    if frame_temp:
        layout_temp = frame_temp.layout()
        if layout_temp is None:
            layout_temp = QtWidgets.QVBoxLayout(frame_temp)
            layout_temp.setContentsMargins(5, 5, 5, 5)
        layout_temp.addWidget(host_charts_manager.get_temperature_chart_view())
    
    if frame_network:
        layout_network = frame_network.layout()
        if layout_network is None:
            layout_network = QtWidgets.QVBoxLayout(frame_network)
            layout_network.setContentsMargins(5, 5, 5, 5)
        layout_network.addWidget(host_charts_manager.get_network_chart_view())

    if frame_services:
        layout_services = frame_services.layout()
        if layout_services is None:
            layout_services = QtWidgets.QVBoxLayout(frame_services)
            layout_services.setContentsMargins(10, 10, 10, 10)
        layout_services.addWidget(lbl_services)

    if frame_disk:
        layout_disk = frame_disk.layout()
        if layout_disk is None:
            layout_disk = QtWidgets.QVBoxLayout(frame_disk)
            layout_disk.setContentsMargins(10, 10, 10, 10)
        layout_disk.addWidget(lbl_free_disk)
    
    # Bắt đầu giám sát
    sandbox_charts_manager.start_monitoring(2000)  # Sandbox: 2 giây
    host_charts_manager.start_monitoring(1000)  # Host: 1 giây
    
    return sandbox_charts_manager, host_charts_manager

