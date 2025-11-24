# Diagrams - Use Case và Sequence Diagrams

Thư mục này chứa các file PlantUML để vẽ Use Case Diagram và Sequence Diagrams của hệ thống.

## Cài đặt PlantUML

### Cài đặt Graphviz (BẮT BUỘC)
PlantUML cần Graphviz để render diagrams. Cài đặt bằng lệnh:
```bash
sudo apt-get update
sudo apt-get install graphviz
```

### Cách 1: Sử dụng PlantUML JAR
```bash
# Tải PlantUML JAR
wget http://sourceforge.net/projects/plantuml/files/plantuml.jar/download -O plantuml.jar

# Render diagram
java -jar plantuml.jar use_case_diagram.puml
```

### Cách 2: Sử dụng VS Code Extension
1. Cài đặt extension "PlantUML" trong VS Code
2. Mở file `.puml`
3. Nhấn `Alt+D` để preview hoặc `Ctrl+Shift+P` > "PlantUML: Export Current Diagram"

### Cách 3: Sử dụng Online
- Truy cập: http://www.plantuml.com/plantuml/uml/
- Copy nội dung file `.puml` và paste vào

## Danh sách Diagrams

### Use Case Diagrams (đã chia thành nhiều diagram)

1. **use_case_overview.puml**
   - Tổng quan hệ thống với các module chính
   - Hiển thị mối quan hệ giữa các module

2. **use_case_firewall_rules.puml**
   - Use cases cho quản lý Firewall Rules
   - UC-01 đến UC-05

3. **use_case_system_monitoring.puml**
   - Use cases cho giám sát hệ thống
   - UC-06 đến UC-09

4. **use_case_log_management.puml**
   - Use cases cho quản lý Logs
   - UC-10

5. **use_case_diagram.puml** (tổng hợp)
   - Tất cả use cases trong một diagram
   - Dùng để xem tổng quan đầy đủ

### Sequence Diagrams

1. **sequence_add_rule.puml**
   - Luồng thêm firewall rule mới
   - UC-02: Thêm Rule mới

2. **sequence_list_rules.puml**
   - Luồng xem danh sách rules (auto-refresh)
   - UC-01: Xem danh sách Rules

3. **sequence_delete_many_rules.puml**
   - Luồng xóa nhiều rules cùng lúc
   - UC-03: Xóa Rule

4. **sequence_search_rules.puml**
   - Luồng tìm kiếm rules
   - UC-04: Tìm kiếm Rules

5. **sequence_monitoring.puml**
   - Luồng giám sát hệ thống và phát hiện anomaly
   - UC-08: Phát hiện Anomaly
   - UC-09: Nhận cảnh báo

6. **sequence_startup.puml**
   - Luồng khởi động hệ thống
   - Kết nối GUI với Backend Service

## Render tất cả diagrams

```bash
# Nếu có PlantUML JAR
java -jar plantuml.jar *.puml

# Hoặc render từng nhóm
java -jar plantuml.jar use_case_*.puml
java -jar plantuml.jar sequence_*.puml

# Hoặc render từng file cụ thể
java -jar plantuml.jar use_case_overview.puml
java -jar plantuml.jar use_case_firewall_rules.puml
java -jar plantuml.jar use_case_system_monitoring.puml
java -jar plantuml.jar use_case_log_management.puml
```

## Output

Các file sẽ được render thành:
- PNG: `*.png`
- SVG: `*.svg` (nếu cấu hình)
- PDF: `*.pdf` (nếu cấu hình)

## Xem chi tiết

Xem file `PHAN_TICH_USE_CASE_VA_SEQUENCE_DIAGRAM.md` ở thư mục gốc để biết chi tiết về các use cases và sequence diagrams.

