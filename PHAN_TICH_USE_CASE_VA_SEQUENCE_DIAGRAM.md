# PHÂN TÍCH USE CASE VÀ SEQUENCE DIAGRAM
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN

Tài liệu này phân tích chi tiết các Use Case và Sequence Diagram của hệ thống quản lý firewall với giám sát hệ thống real-time.

**Kiến trúc hệ thống**: Client-Server
- **Backend**: Flask REST API Service (chạy như systemd daemon)
- **Frontend**: PyQt6 GUI Application

---

## 2. USE CASE DIAGRAM

### 2.1. Tổng quan Use Cases

Hệ thống có các Actor chính:
- **User (Người dùng)**: Sử dụng GUI để quản lý firewall và xem monitoring
- **System Monitor**: Hệ thống tự động giám sát và phát hiện anomaly
- **Firewall Service**: Backend service xử lý logic nghiệp vụ

### 2.2. Danh sách Use Cases

#### 2.2.1. Quản lý Firewall Rules

| Use Case ID | Use Case Name | Mô tả | Actor |
|------------|---------------|-------|-------|
| UC-01 | Xem danh sách Rules | Hiển thị tất cả firewall rules từ các chains | User |
| UC-02 | Thêm Rule mới | Thêm rule mới vào iptables | User |
| UC-03 | Xóa Rule | Xóa một hoặc nhiều rules | User |
| UC-04 | Tìm kiếm Rules | Tìm kiếm rules theo chain name | User |
| UC-05 | Quản lý Available Rules | Enable/disable các rule templates | User |

#### 2.2.2. Giám sát Hệ thống

| Use Case ID | Use Case Name | Mô tả | Actor |
|------------|---------------|-------|-------|
| UC-06 | Xem biểu đồ Monitoring | Hiển thị biểu đồ real-time về CPU, RAM, Network, Temperature | User |
| UC-07 | Xem thống kê tài nguyên | Hiển thị số liệu chi tiết về tài nguyên hệ thống | User |
| UC-08 | Phát hiện Anomaly | Tự động phát hiện CPU spike, RAM spike, service lạ | System Monitor |
| UC-09 | Nhận cảnh báo | Nhận desktop notification và email alert | User |

#### 2.2.3. Quản lý Logs

| Use Case ID | Use Case Name | Mô tả | Actor |
|------------|---------------|-------|-------|
| UC-10 | Xem Logs | Hiển thị logs hệ thống | User |

### 2.3. Use Case Diagram (PlantUML)

```plantuml
@startuml UseCaseDiagram
!theme plain
skinparam actorStyle awesome

actor User as user
actor "System Monitor" as monitor
actor "Firewall Service" as service

rectangle "Firewall Management System" {
  package "Firewall Rules Management" {
    usecase "UC-01: Xem danh sách Rules" as UC01
    usecase "UC-02: Thêm Rule mới" as UC02
    usecase "UC-03: Xóa Rule" as UC03
    usecase "UC-04: Tìm kiếm Rules" as UC04
    usecase "UC-05: Quản lý Available Rules" as UC05
  }
  
  package "System Monitoring" {
    usecase "UC-06: Xem biểu đồ Monitoring" as UC06
    usecase "UC-07: Xem thống kê tài nguyên" as UC07
    usecase "UC-08: Phát hiện Anomaly" as UC08
    usecase "UC-09: Nhận cảnh báo" as UC09
  }
  
  package "Log Management" {
    usecase "UC-10: Xem Logs" as UC10
  }
}

user --> UC01
user --> UC02
user --> UC03
user --> UC04
user --> UC05
user --> UC06
user --> UC07
user --> UC09
user --> UC10

monitor --> UC08
monitor --> UC09

service --> UC01
service --> UC02
service --> UC03
service --> UC04
service --> UC06
service --> UC07
service --> UC08

UC08 ..> UC09 : <<triggers>>

@enduml
```

---

## 3. SEQUENCE DIAGRAMS

### 3.1. Sequence Diagram: Thêm Firewall Rule (UC-02)

**Mô tả**: User nhập thông tin rule mới qua GUI, hệ thống validate và thêm vào iptables.

```plantuml
@startuml AddRuleSequence
!theme plain
autonumber

actor User
participant "GUI\n(main_qt_api.py)" as GUI
participant "AddRuleHandlerAPI" as Handler
participant "API Client\n(api_client.py)" as Client
participant "Flask Service\n(firewall_service.py)" as Service
participant "iptables\n(subprocess)" as Iptables
participant "Metadata File\n(JSON)" as Meta

User -> GUI: Nhập thông tin rule\n(IP, Port, Protocol, Action, ...)
User -> GUI: Click "Add Rule"

GUI -> Handler: on_add_rule_in_frame_clicked()
Handler -> Handler: Validate input\n(Protocol, Action required)

alt Validation thành công
    Handler -> Client: add_rule(ip, port, protocol, action, ...)
    Client -> Service: POST /api/rules/add\n{JSON data}
    
    Service -> Service: Validate data
    Service -> Service: Build iptables command
    
    Service -> Iptables: sudo iptables -A INPUT ...
    Iptables --> Service: Success
    
    Service -> Iptables: sudo iptables -L INPUT -v -n --line-numbers
    Iptables --> Service: Rule list
    
    Service -> Service: Extract last rule\n(make_rule_key)
    Service -> Meta: load_meta()
    Meta --> Service: Current metadata
    Service -> Service: Add group to metadata
    Service -> Meta: save_meta(updated_meta)
    
    Service --> Client: {status: "success", message: "..."}
    Client --> Handler: Success response
    
    Handler -> GUI: Clear form fields
    Handler -> GUI: refresh_rules_table()
    GUI -> Client: GET /api/rules/list
    Client -> Service: GET /api/rules/list
    Service -> Iptables: sudo iptables -L -v -n --line-numbers
    Iptables --> Service: All rules
    Service --> Client: {rules: [...]}
    Client --> GUI: Rules list
    GUI -> GUI: Update rules table
    
    GUI --> User: Hiển thị rule mới trong table
else Validation thất bại
    Handler -> GUI: Show error message
    GUI --> User: "Protocol và Action là bắt buộc!"
end

@enduml
```

### 3.2. Sequence Diagram: Xem danh sách Rules (UC-01)

**Mô tả**: GUI tự động refresh danh sách rules mỗi 1.5 giây.

```plantuml
@startuml ListRulesSequence
!theme plain
autonumber

participant "QTimer\n(1.5s interval)" as Timer
participant "GUI\n(main_qt_api.py)" as GUI
participant "RulesTableHandlerAPI" as Handler
participant "API Client" as Client
participant "Flask Service" as Service
participant "iptables" as Iptables
participant "Metadata File" as Meta

loop Mỗi 1.5 giây
    Timer -> GUI: timeout signal
    GUI -> Handler: refresh_rules_table()
    
    Handler -> Client: list_rules()
    Client -> Service: GET /api/rules/list
    
    Service -> Iptables: sudo iptables -L -v -n --line-numbers\n(all chains)
    Iptables --> Service: Rules output
    
    Service -> Service: Parse rules\n(get_all_chains_rules())
    Service -> Meta: get_group_map()
    Meta --> Service: Group mapping
    
    Service -> Service: Add group to each rule
    Service --> Client: {rules: [rule1, rule2, ...]}
    Client --> Handler: Rules list
    
    Handler -> Handler: Preserve checkbox states
    Handler -> GUI: Update tableRules widget
    GUI -> GUI: Display rules with groups
end

@enduml
```

### 3.3. Sequence Diagram: Xóa nhiều Rules (UC-03)

**Mô tả**: User chọn nhiều rules và xóa cùng lúc, hệ thống xử lý đúng với nhiều chains.

```plantuml
@startuml DeleteManyRulesSequence
!theme plain
autonumber

actor User
participant "GUI" as GUI
participant "RulesTableHandlerAPI" as Handler
participant "API Client" as Client
participant "Flask Service" as Service
participant "iptables" as Iptables

User -> GUI: Chọn nhiều rules (checkboxes)
User -> GUI: Click "Delete Selected"

GUI -> Handler: on_delete_many_clicked()
Handler -> Handler: Get selected rule numbers\n(nums = ["1", "3", "5"])

Handler -> Client: delete_many_rules(nums)
Client -> Service: POST /api/rules/delete-many\n{nums: ["1", "3", "5"]}

Service -> Service: get_all_chains_rules()
Service -> iptables: sudo iptables -L -v -n --line-numbers
iptables --> Service: All rules

Service -> Service: Build rule_map\n{(chain, num) -> rule}

Service -> Service: Group rules by chain\n{INPUT: [1, 3], OUTPUT: [5]}

loop For each chain
    Service -> Service: Sort nums descending\n([3, 1] for INPUT)
    
    loop For each num in chain
        Service -> iptables: sudo iptables -D <chain> <num>
        iptables --> Service: Success/Failure
        Service -> Service: Track deleted/failed
    end
end

Service --> Client: {status: "success", deleted: [...], failed: [...]}
Client --> Handler: Response

alt Có rules bị xóa thành công
    Handler -> GUI: refresh_rules_table()
    GUI -> Client: GET /api/rules/list
    Client -> Service: GET /api/rules/list
    Service -> iptables: sudo iptables -L -v -n --line-numbers
    iptables --> Service: Updated rules
    Service --> Client: {rules: [...]}
    Client --> GUI: Updated rules list
    GUI -> GUI: Update table
    GUI --> User: Hiển thị rules đã cập nhật
end

alt Có rules xóa thất bại
    Handler -> GUI: Show error message
    GUI --> User: "Một số rules không thể xóa"
end

@enduml
```

### 3.4. Sequence Diagram: Giám sát Hệ thống và Phát hiện Anomaly (UC-08, UC-09)

**Mô tả**: Hệ thống tự động giám sát tài nguyên và phát hiện anomaly, gửi cảnh báo.

```plantuml
@startuml MonitoringSequence
!theme plain
autonumber

participant "Monitoring Thread" as Thread
participant "update_monitoring()" as Update
participant "cgroup files" as Cgroup
participant "psutil" as Psutil
participant "systemctl" as Systemctl
participant "Anomaly Detection" as Detection
participant "Notification System" as Notify
participant "Email Service" as Email
participant "GUI" as GUI
participant "API Client" as Client
participant "Flask Service" as Service

loop Mỗi 2 giây
    Thread -> Update: update_monitoring()
    
    == Thu thập dữ liệu CPU ==
    Update -> Cgroup: Read /sys/fs/cgroup/.../cpu.stat
    Cgroup --> Update: usage_usec
    Update -> Update: Calculate CPU %
    
    == Thu thập dữ liệu RAM ==
    Update -> Cgroup: Read /sys/fs/cgroup/.../memory.current
    Cgroup --> Update: used_bytes
    Update -> Update: Calculate RAM % và MB
    
    == Thu thập dữ liệu Disk I/O ==
    Update -> Cgroup: Read /sys/fs/cgroup/.../io.stat
    Cgroup --> Update: rbytes, wbytes
    
    == Thu thập dữ liệu Network ==
    Update -> Psutil: net_io_counters()
    Psutil --> Update: bytes_recv, bytes_sent
    Update -> Update: Calculate RX/TX rate
    
    == Thu thập Temperature ==
    Update -> Cgroup: Read /sys/class/thermal/thermal_zone*/temp
    Cgroup --> Update: temperature
    
    == Thu thập Services ==
    Update -> Systemctl: machinectl shell ... systemctl list-units
    Systemctl --> Update: Running services count
    
    Update -> Update: Store in monitoring_data
    
    == Phát hiện Anomaly ==
    Update -> Detection: Check thresholds
    
    alt CPU > 85%
        Detection -> Update: Create alert\n{type: "CPU", severity: "high"}
        Update -> Notify: send_malware_alert("Trojan.Generic", "high")
        Notify -> Notify: Desktop notification\n(notify-send)
        Notify -> Email: Send email alert (if configured)
        Notify --> User: Desktop popup
    end
    
    alt RAM spike > 150MB
        Detection -> Update: Create alert\n{type: "RAM", severity: "high"}
        Update -> Notify: send_malware_alert("Trojan.Generic", "high")
        Notify -> Notify: Desktop notification
        Notify -> Email: Send email alert
        Notify --> User: Desktop popup
    end
    
    alt Services > 10
        Detection -> Update: Check cooldown (60s)
        alt Cooldown expired
            Detection -> Update: Create alert\n{type: "Service", severity: "high"}
            Update -> Notify: send_malware_alert("Service", "high")
            Notify -> Notify: Desktop notification
            Notify -> Email: Send email alert
            Notify --> User: Desktop popup
        end
    end
    
    Update -> Update: Keep max 100 alerts
end

== GUI Request Monitoring Data ==
loop Mỗi 2 giây (GUI timer)
    GUI -> Client: get_monitoring_data()
    Client -> Service: GET /api/monitoring/data
    Service --> Client: monitoring_data\n{CPU, RAM, Network, ...}
    Client --> GUI: Monitoring data
    
    GUI -> GUI: Update charts\n(CPU, RAM, Network, Temperature)
    GUI -> GUI: Update labels\n(CPU %, RAM %, etc.)
end

@enduml
```

### 3.5. Sequence Diagram: Khởi động hệ thống

**Mô tả**: Luồng khởi động GUI và kết nối với Backend Service.

```plantuml
@startuml StartupSequence
!theme plain
autonumber

actor User
participant "main_qt_api.py" as Main
participant "MainWindow" as Window
participant "API Client" as Client
participant "Flask Service" as Service
participant "System Monitor" as Monitor
participant "Charts Manager" as Charts

User -> Main: python main_qt_api.py
Main -> Window: __init__()

Window -> Window: Load UI (main.ui)
Window -> Window: load_all_tabs()

Window -> Client: get_client()
Client -> Client: Create FirewallServiceClient

Window -> Client: health_check()
Client -> Service: GET /api/health
Service --> Client: {status: "ok"}
Client --> Window: True

alt Service không khả dụng
    Window -> Window: Show error dialog
    Window --> User: "Không thể kết nối đến service"
    Window -> Window: Exit
end

Window -> Window: _init_log_tab()
Window -> Window: _init_system_monitor()
Window -> Monitor: SystemMonitorAPI(ui)
Monitor -> Monitor: Setup QTimer (2s interval)

Window -> Charts: setup_charts(ui, monitor)
Charts -> Charts: Create sandbox charts
Charts -> Charts: Create host charts

Window -> Window: _init_rules_table()
Window -> Window: _init_add_rule()
Window -> Window: _init_available_rules()

Window -> Client: start_monitoring()
Client -> Service: POST /api/monitoring/start
Service -> Service: Start monitoring thread
Service --> Client: {status: "started"}

Window -> Window: show()
Window --> User: Display main window

== Background Operations ==
par Monitoring thread starts
    Service -> Service: monitoring_loop()
    Service -> Service: update_monitoring() every 2s
end

par GUI refresh timers
    Monitor -> Monitor: Update stats every 2s
    Monitor -> Client: get_monitoring_data()
    Client -> Service: GET /api/monitoring/data
    Service --> Client: monitoring_data
    Client --> Monitor: Data
    Monitor -> Charts: Update charts
end

@enduml
```

### 3.6. Sequence Diagram: Tìm kiếm Rules (UC-04)

**Mô tả**: User tìm kiếm rules theo chain name.

```plantuml
@startuml SearchRulesSequence
!theme plain
autonumber

actor User
participant "GUI" as GUI
participant "RulesTableHandlerAPI" as Handler
participant "API Client" as Client
participant "Flask Service" as Service
participant "iptables" as Iptables

User -> GUI: Nhập chain name vào search box
User -> GUI: Click "Search" hoặc Enter

GUI -> Handler: on_search_clicked()
Handler -> Handler: Get search query\n(query = "INPUT")

Handler -> Client: search_rules(query)
Client -> Service: GET /api/rules/search?q=INPUT

Service -> iptables: sudo iptables -L INPUT -v -n --line-numbers
iptables --> Service: INPUT chain rules

Service -> Service: get_input_rules()
Service -> Service: Filter by chain name\n(if query provided)

Service --> Client: {rules: [filtered_rules]}
Client --> Handler: Filtered rules

Handler -> GUI: Update tableRules widget
GUI -> GUI: Display only matching rules
GUI --> User: Hiển thị kết quả tìm kiếm

@enduml
```

---

## 4. CHI TIẾT CÁC USE CASES

### 4.1. UC-01: Xem danh sách Rules

**Preconditions**:
- Firewall Service đang chạy
- GUI đã kết nối thành công với service

**Main Flow**:
1. GUI tự động gọi API `/api/rules/list` mỗi 1.5 giây
2. Service thực thi `iptables -L -v -n --line-numbers` cho tất cả chains
3. Service parse output và thêm group từ metadata
4. Service trả về JSON với danh sách rules
5. GUI cập nhật bảng rules, giữ nguyên trạng thái checkbox

**Postconditions**:
- Bảng rules hiển thị đầy đủ thông tin
- Rules được tự động refresh

**Alternative Flows**:
- Nếu service không khả dụng: Hiển thị lỗi kết nối
- Nếu không có rules: Hiển thị bảng trống

### 4.2. UC-02: Thêm Rule mới

**Preconditions**:
- User có quyền root (service chạy với sudo)
- Protocol và Action đã được nhập

**Main Flow**:
1. User nhập thông tin rule (IP, Port, Protocol, Action, Interface, State, Group)
2. User click "Add Rule"
3. Handler validate input (Protocol và Action bắt buộc)
4. Handler gọi API `/api/rules/add` với JSON data
5. Service build iptables command
6. Service thực thi `iptables -A INPUT ...`
7. Service lấy rule vừa thêm và lưu group vào metadata
8. Service trả về success
9. GUI refresh rules table
10. GUI clear form

**Postconditions**:
- Rule mới được thêm vào iptables
- Metadata được cập nhật
- Rules table được refresh

**Alternative Flows**:
- Validation thất bại: Hiển thị warning "Protocol và Action là bắt buộc!"
- iptables command thất bại: Trả về error message

### 4.3. UC-08: Phát hiện Anomaly

**Preconditions**:
- Monitoring thread đang chạy
- Cgroup files có thể truy cập

**Main Flow**:
1. Monitoring thread gọi `update_monitoring()` mỗi 2 giây
2. Thu thập dữ liệu từ cgroup, psutil, systemctl
3. Kiểm tra các ngưỡng:
   - CPU > 85%
   - RAM spike > 150MB
   - Services > 10 (với cooldown 60s)
4. Nếu phát hiện anomaly:
   - Tạo alert object
   - Gọi `send_malware_alert()`
   - Gửi desktop notification
   - Gửi email (nếu được cấu hình)
5. Lưu alert vào monitoring_data (tối đa 100 alerts)

**Postconditions**:
- Alert được ghi nhận
- User nhận được notification

**Alternative Flows**:
- Cooldown chưa hết: Bỏ qua alert
- Email không được cấu hình: Chỉ gửi desktop notification

---

## 5. TƯƠNG TÁC GIỮA CÁC COMPONENTS

### 5.1. Frontend Components

```
MainWindow (main_qt_api.py)
├── RulesTableHandlerAPI
│   └── API Client
├── AddRuleHandlerAPI
│   └── API Client
├── SystemMonitorAPI
│   └── API Client
├── AvailableRulesHandler
│   └── File I/O (available_rules.json)
└── LogTab
    └── File I/O (logs)
```

### 5.2. Backend Components

```
Flask Service (firewall_service.py)
├── REST API Endpoints
│   ├── /api/health
│   ├── /api/monitoring/*
│   └── /api/rules/*
├── Monitoring Thread
│   └── update_monitoring()
├── Anomaly Detection
│   └── send_malware_alert()
└── iptables Integration
    └── subprocess calls
```

### 5.3. Data Flow

```
GUI Request
    ↓
API Client (HTTP)
    ↓
Flask Service (REST API)
    ↓
Backend Logic (rules/monitoring)
    ↓
System Resources (iptables/cgroup/psutil)
    ↓
Response (JSON)
    ↓
GUI Update
```

---

## 6. CÁC ĐIỂM QUAN TRỌNG TRONG THIẾT KẾ

### 6.1. Separation of Concerns
- **Frontend**: Chỉ xử lý UI và gọi API
- **Backend**: Xử lý logic nghiệp vụ và tương tác với system
- **API Client**: Lớp trung gian để giao tiếp

### 6.2. Asynchronous Operations
- **Monitoring**: Chạy trong thread riêng, không block main thread
- **GUI Refresh**: Sử dụng QTimer để refresh định kỳ
- **Email**: Gửi trong thread riêng để không block

### 6.3. Error Handling
- **Connection Errors**: GUI hiển thị dialog lỗi
- **API Errors**: Trả về error message trong JSON response
- **iptables Errors**: Catch subprocess exceptions

### 6.4. State Management
- **Checkbox States**: Được preserve khi refresh rules table
- **Monitoring Data**: Lưu trong global dictionary
- **Metadata**: Lưu trong JSON file

---

## 7. KẾT LUẬN

Hệ thống được thiết kế theo mô hình Client-Server với các đặc điểm:

1. **Modular Architecture**: Tách biệt rõ ràng giữa frontend và backend
2. **RESTful API**: Giao tiếp qua HTTP/JSON, dễ mở rộng
3. **Real-time Updates**: Monitoring và rules table tự động refresh
4. **Anomaly Detection**: Tự động phát hiện và cảnh báo
5. **Error Resilience**: Xử lý lỗi gracefully, không crash ứng dụng

Các Sequence Diagrams trên mô tả chi tiết luồng xử lý của các use case chính, giúp hiểu rõ cách các components tương tác với nhau.

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**Tác giả**: System Analysis

