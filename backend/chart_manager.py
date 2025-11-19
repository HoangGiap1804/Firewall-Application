"""
Module quản lý việc setup và hiển thị charts trong UI
"""

from PyQt6 import QtWidgets
from backend.system_monitor import SystemMonitor
from backend.system_chart import SystemChartsManager


def setup_charts(ui, monitor):
    """
    Thiết lập và hiển thị charts trong UI
    
    Args:
        ui: UI object từ uic.loadUi
        monitor: SystemMonitor instance
    
    Returns:
        SystemChartsManager instance
    """
    # Tạo charts manager (tự động kết nối với monitor)
    charts_manager = SystemChartsManager(monitor)
    
    # Tìm frameGraph trong UI
    frame_graph = ui.findChild(QtWidgets.QFrame, "frameGraph")
    if frame_graph:
        # Tạo layout dọc để chia 2 chart (một trên, một dưới)
        layout = frame_graph.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame_graph)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
        
        # Thêm CPU chart vào trên
        layout.addWidget(charts_manager.get_cpu_chart_view())
        
        # Thêm RAM chart vào dưới
        layout.addWidget(charts_manager.get_ram_chart_view())
        
        # Bắt đầu giám sát (cập nhật mỗi 2 giây)
        charts_manager.start_monitoring(2000)
    
    return charts_manager

