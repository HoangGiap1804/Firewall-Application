"""
Script để tách file main.ui thành các file tab riêng biệt
"""
import xml.etree.ElementTree as ET
from pathlib import Path

def split_ui_file():
    """Tách file main.ui thành các file tab riêng biệt"""
    main_ui = Path(__file__).parent / "main.ui"
    tabs_dir = Path(__file__).parent / "tabs"
    tabs_dir.mkdir(exist_ok=True)
    
    # Parse file main.ui
    tree = ET.parse(main_ui)
    root = tree.getroot()
    
    # Tìm QTabWidget
    tab_widget = root.find(".//widget[@class='QTabWidget']")
    if tab_widget is None:
        print("Không tìm thấy QTabWidget")
        return
    
    # Lấy styleSheet của QTabWidget
    style_sheet_elem = tab_widget.find(".//property[@name='styleSheet']")
    style_sheet = style_sheet_elem.find("string").text if style_sheet_elem is not None else None
    
    # Tạo file main.ui mới chỉ chứa QTabWidget
    new_main = ET.Element("ui", version="4.0")
    new_main_class = ET.SubElement(new_main, "class")
    new_main_class.text = "Dialog"
    new_main_widget = ET.SubElement(new_main, "widget", attrib={"class": "QDialog", "name": "Dialog"})
    
    # Copy geometry và windowTitle
    for prop in root.findall(".//property[@name='geometry']"):
        new_main_widget.append(prop)
    for prop in root.findall(".//property[@name='windowTitle']"):
        new_main_widget.append(prop)
    
    # Tạo layout và QTabWidget
    layout = ET.SubElement(new_main_widget, "layout", attrib={"class": "QGridLayout", "name": "gridLayout_2"})
    item = ET.SubElement(layout, "item", attrib={"row": "0", "column": "0"})
    new_tab_widget = ET.SubElement(item, "widget", attrib={"class": "QTabWidget", "name": "tabWidget"})
    
    # Copy styleSheet
    if style_sheet:
        style_prop = ET.SubElement(new_tab_widget, "property", attrib={"name": "styleSheet"})
        style_string = ET.SubElement(style_prop, "string", attrib={"notr": "true"})
        style_string.text = style_sheet
    
    # Copy currentIndex
    current_index = tab_widget.find(".//property[@name='currentIndex']")
    if current_index is not None:
        new_tab_widget.append(current_index)
    
    # Thêm resources và connections
    ET.SubElement(new_main, "resources")
    ET.SubElement(new_main, "connections")
    
    # Lưu file main.ui mới
    new_tree = ET.ElementTree(new_main)
    ET.indent(new_tree, space=" ")
    new_tree.write(main_ui, encoding="utf-8", xml_declaration=True)
    
    # Tách các tab
    tab_mapping = {
        "tabLog": "tab_log",
        "tabRules": "tab_rules",
        "tabAddRule": "tab_add_rule",
        "tabAvailableRules": "tab_available_rules",
        "tab": "tab_sandbox",
        "tab_2": "tab_graph",
    }
    
    for tab_widget_elem in tab_widget.findall("widget"):
        tab_name = tab_widget_elem.get("name")
        if tab_name in tab_mapping:
            # Tạo file tab mới
            tab_file = tabs_dir / f"{tab_mapping[tab_name]}.ui"
            tab_root = ET.Element("ui", version="4.0")
            tab_class = ET.SubElement(tab_root, "class")
            tab_class.text = tab_widget_elem.get("name", "Tab")
            tab_root.append(tab_widget_elem)
            ET.SubElement(tab_root, "resources")
            ET.SubElement(tab_root, "connections")
            
            tab_tree = ET.ElementTree(tab_root)
            ET.indent(tab_tree, space=" ")
            tab_tree.write(tab_file, encoding="utf-8", xml_declaration=True)
            print(f"Đã tạo: {tab_file}")
    
    print("Hoàn thành tách file UI!")

if __name__ == "__main__":
    split_ui_file()

