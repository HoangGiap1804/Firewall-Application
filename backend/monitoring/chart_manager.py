"""
Module quản lý việc setup và hiển thị charts trong UI
"""

from PyQt6 import QtWidgets
from .system_monitor import SystemMonitor
from .host_monitor import HostSystemMonitor
from .system_chart import SystemChartsManager


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
    
    # Tạo host monitor và charts manager cho máy thật
    host_monitor = HostSystemMonitor(interval=1000)  # Cập nhật mỗi 1 giây
    host_charts_manager = SystemChartsManager(host_monitor)
    
    # Tìm các frame trong tab Graph (máy thật)
    frame_cpu = ui.findChild(QtWidgets.QFrame, "frameGraphCPU")
    frame_ram = ui.findChild(QtWidgets.QFrame, "frameGraphRAM")
    frame_temp = ui.findChild(QtWidgets.QFrame, "frameGraphTemperature")
    frame_network = ui.findChild(QtWidgets.QFrame, "frameGraphNetwork")
    
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
    
    # Bắt đầu giám sát
    sandbox_charts_manager.start_monitoring(2000)  # Sandbox: 2 giây
    host_charts_manager.start_monitoring(1000)  # Host: 1 giây
    
    return sandbox_charts_manager, host_charts_manager

