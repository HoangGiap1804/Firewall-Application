"""
Module để load các tab UI riêng biệt
"""
from PyQt6 import QtWidgets, uic
from pathlib import Path

# Đường dẫn đến thư mục tabs
TABS_DIR = Path(__file__).parent / "tabs"


def load_tab_ui(tab_name: str) -> QtWidgets.QWidget:
    """
    Load một tab UI từ file riêng biệt
    
    Args:
        tab_name: Tên file tab (không cần .ui)
    
    Returns:
        QWidget: Widget của tab đã load
    """
    ui_file = TABS_DIR / f"{tab_name}.ui"
    if not ui_file.exists():
        raise FileNotFoundError(f"Tab UI file not found: {ui_file}")
    
    widget = QtWidgets.QWidget()
    uic.loadUi(str(ui_file), widget)
    return widget


def load_all_tabs(tab_widget: QtWidgets.QTabWidget):
    """
    Load tất cả các tab vào QTabWidget
    
    Args:
        tab_widget: QTabWidget để thêm các tab vào
    """
    tabs_config = [
        ("tab_log", "Log tab"),
        ("tab_rules", "Rules"),
        ("tab_available_rules", "Available Rules"),
        ("tab_sandbox", "Sandbox"),
        ("tab_graph", "Graph"),
        ("tab_setting", "Settings"),
        ("tab_blacklist", "Blacklist"),
        ("tab_test", "Test"),
    ]
    
    for tab_file, tab_title in tabs_config:
        try:
            tab = load_tab_ui(tab_file)
            tab_widget.addTab(tab, tab_title)
        except FileNotFoundError as e:
            print(f"Warning: {e}")

