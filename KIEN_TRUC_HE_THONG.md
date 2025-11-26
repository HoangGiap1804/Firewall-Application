# KIẾN TRÚC HỆ THỐNG
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN KIẾN TRÚC

### 1.1. Mô hình Kiến trúc

Hệ thống được thiết kế theo mô hình **Client-Server** với kiến trúc 3 tầng:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│                  (Frontend - PyQt6 GUI)                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Log Tab  │  │ Rules Tab│  │Available │  │ Sandbox  │   │
│  │          │  │          │  │ Rules Tab│  │   Tab    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Graph Tab (Monitoring)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST API
                           │ (localhost:5000)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│              (Backend Service - Flask API)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              REST API Endpoints                       │   │
│  │  - /api/health                                        │   │
│  │  - /api/monitoring/*                                  │   │
│  │  - /api/rules/*                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Business Logic Layer                          │   │
│  │  - Rules Management                                   │   │
│  │  - System Monitoring                                  │   │
│  │  - Anomaly Detection                                  │   │
│  │  - Notifications                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Background Threads                            │   │
│  │  - Monitoring Thread (update mỗi 2s)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│                  (System Resources)                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ iptables │  │  cgroup  │  │  psutil  │  │ systemd  │   │
│  │          │  │  files   │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  JSON    │  │  Logs    │  │ Thermal  │                 │
│  │  Files   │  │  Files   │  │  Zones   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 1.2. Các Thành phần Chính

1. **Frontend (Client)**: PyQt6 GUI Application
2. **Backend (Server)**: Flask REST API Service (systemd daemon)
3. **API Client**: Thư viện Python để giao tiếp với API
4. **System Resources**: iptables, cgroup, psutil, systemd

---

## 2. KIẾN TRÚC CHI TIẾT

### 2.1. PRESENTATION LAYER (Frontend)

#### 2.1.1. Main Application (`main_qt_api.py`)

**Vai trò**: Entry point của ứng dụng GUI

**Cấu trúc**:
```python
MainWindow
├── UI Loading (main.ui)
├── Service Connection Check
├── Tab Initialization
│   ├── Log Tab
│   ├── Rules Tab
│   ├── Available Rules Tab
│   ├── Sandbox Tab
│   └── Graph Tab
└── Component Initialization
    ├── System Monitor
    ├── Charts Manager
    ├── Rules Table Handler
    ├── Add Rule Handler
    └── Available Rules Handler
```

**Luồng khởi động**:
1. Load UI từ `main.ui`
2. Kiểm tra kết nối service (`health_check()`)
3. Load các tab UI
4. Khởi tạo các handlers
5. Bắt đầu monitoring
6. Hiển thị main window

#### 2.1.2. UI Components (`frontend/`)

**Cấu trúc thư mục**:
```
frontend/
├── main.ui                    # Main window UI
├── ui_loader.py               # Utility để load tabs
└── tabs/
    ├── tab_log.ui             # Log tab UI
    ├── tab_rules.ui           # Rules tab UI
    ├── tab_available_rules.ui # Available rules tab UI
    ├── tab_sandbox.ui         # Sandbox tab UI
    └── tab_graph.ui           # Graph tab UI
```

**Tính năng**:
- 5 tabs chính với giao diện riêng biệt
- Real-time updates qua QTimer
- Responsive design với PyQt6

#### 2.1.3. Tab Handlers

**Log Tab** (`backend/ui/log_tab.py`):
- Đọc kernel logs từ `/var/log/kern.log`
- Phân tích và phát hiện tấn công
- Tự động chặn IP tấn công
- Highlight dòng log tấn công

**Rules Tab** (`backend/rules/handlers/rules_table_handler_api.py`):
- Hiển thị danh sách rules từ API
- Tự động refresh mỗi 1.5 giây
- Tìm kiếm và lọc rules
- Xóa rules (một hoặc nhiều)

**Add Rule Handler** (`backend/rules/handlers/add_rule_handler_api.py`):
- Form thêm rule mới
- Validate input
- Gọi API để thêm rule

**Available Rules Handler** (`backend/rules/handlers/available_rules_handler.py`):
- Quản lý rule templates
- Enable/disable rules
- Lưu trạng thái vào JSON

**System Monitor** (`backend/monitoring/system_monitor_api.py`):
- Cập nhật metrics từ API mỗi 2 giây
- Cập nhật labels (CPU, RAM, Disk, Network, Services)
- Emit signals cho charts

**Charts Manager** (`backend/monitoring/chart_manager.py`):
- Quản lý biểu đồ real-time
- Sandbox charts (container)
- Host charts (system)
- Cập nhật charts từ monitoring data

---

### 2.2. APPLICATION LAYER (Backend Service)

#### 2.2.1. Flask REST API Service (`service/firewall_service.py`)

**Vai trò**: Backend service cung cấp REST API và xử lý business logic

**Cấu trúc**:
```python
Flask App
├── Global State
│   ├── monitoring_active (bool)
│   ├── monitoring_thread (Thread)
│   └── monitoring_data (dict)
│
├── REST API Endpoints
│   ├── GET  /api/health
│   ├── POST /api/monitoring/start
│   ├── POST /api/monitoring/stop
│   ├── GET  /api/monitoring/data
│   ├── GET  /api/rules/list
│   ├── POST /api/rules/add
│   ├── POST /api/rules/delete
│   ├── POST /api/rules/delete-many
│   └── GET  /api/rules/search
│
├── Background Threads
│   └── monitoring_loop() - Update mỗi 2 giây
│
└── Business Logic
    ├── update_monitoring() - Thu thập metrics
    ├── Anomaly Detection
    └── Notification System
```

**Monitoring Thread**:
- Chạy độc lập trong background
- Cập nhật dữ liệu mỗi 2 giây
- Thu thập từ: cgroup, psutil, systemctl, thermal zones
- Phát hiện anomaly và gửi alerts

**Metrics được thu thập**:
- CPU usage (%)
- RAM usage (% và MB)
- Disk I/O (read/write MB)
- Network traffic (RX/TX bytes/s)
- Temperature (°C)
- Network processes count
- Services count

**Anomaly Detection**:
- CPU spike: > 85%
- RAM spike: > 150MB tăng đột biến
- Service alert: > 10 services (với cooldown 60s)

#### 2.2.2. API Client (`service/api_client.py`)

**Vai trò**: Thư viện Python để giao tiếp với API

**Cấu trúc**:
```python
FirewallServiceClient
├── _request() - HTTP request wrapper
├── health_check()
├── start_monitoring()
├── stop_monitoring()
├── get_monitoring_data()
├── list_rules()
├── add_rule()
├── delete_rule()
├── delete_many_rules()
└── search_rules()
```

**Tính năng**:
- Singleton pattern
- Error handling (ConnectionError, TimeoutError)
- Timeout: 5 giây
- JSON serialization tự động

#### 2.2.3. Business Logic Modules

**Rules Management** (`backend/rules/core/`):

`rule_input.py`:
- `get_input_rules()` - Lấy rules từ INPUT chain
- `get_all_chains_rules()` - Lấy rules từ tất cả chains
- `get_group_map()` - Lấy metadata groups
- `normalize_rule_key()` - Chuẩn hóa rule key

`add_rule.py`:
- `IptablesHandler` - Xử lý thêm rule
- `load_meta()` / `save_meta()` - Quản lý metadata
- `make_rule_key()` - Tạo key cho rule

`available_rules.py`:
- Quản lý rule templates
- Enable/disable rules

**Monitoring** (`backend/monitoring/`):

`system_monitor_api.py`:
- `SystemMonitorAPI` - Monitor sử dụng API
- Cập nhật stats từ API
- Emit signals cho charts

`system_chart.py`:
- `SystemChartsManager` - Quản lý charts
- CPU, RAM, Network, Temperature charts
- Real-time updates

`host_monitor.py`:
- `HostSystemMonitor` - Monitor host system
- Thu thập metrics từ psutil

**Notifications** (`backend/notifications/`):

`notification.py`:
- `send_notification()` - Desktop notification
- Sử dụng `notify-send`

`mailer.py`:
- Email alerts (nếu được cấu hình)

---

### 2.3. DATA LAYER (System Resources)

#### 2.3.1. iptables

**Vai trò**: Quản lý firewall rules

**Tương tác**:
- Đọc rules: `iptables -L -v -n --line-numbers`
- Thêm rule: `iptables -A INPUT ...`
- Xóa rule: `iptables -D <chain> <num>`
- Thực thi qua subprocess

**Chains hỗ trợ**:
- INPUT, OUTPUT, FORWARD
- Custom chains

#### 2.3.2. cgroup (Container Monitoring)

**Vai trò**: Giám sát tài nguyên container

**Files được đọc**:
- `/sys/fs/cgroup/.../cpu.stat` - CPU usage
- `/sys/fs/cgroup/.../memory.current` - RAM usage
- `/sys/fs/cgroup/.../io.stat` - Disk I/O

**Container**: systemd-nspawn container (tên: "ubuntu")

#### 2.3.3. psutil

**Vai trò**: Thu thập system metrics

**Metrics**:
- Network I/O counters
- Network connections
- Temperature (sensors)

#### 2.3.4. systemd

**Vai trò**: Service management

**Tương tác**:
- Service chạy như systemd daemon
- `systemctl list-units` - Đếm services
- `machinectl shell` - Truy cập container

#### 2.3.5. File Storage

**JSON Files**:
- `rules_meta.json` - Metadata của rules (groups)
- `available_rules.json` - Rule templates

**Log Files**:
- `/var/log/kern.log` - Kernel logs

---

## 3. LUỒNG DỮ LIỆU (Data Flow)

### 3.1. Luồng Quản lý Rules

```
User Action (GUI)
    ↓
Handler (rules_table_handler_api.py)
    ↓
API Client (api_client.py)
    ↓ HTTP Request
Flask Service (firewall_service.py)
    ↓
Backend Logic (rule_input.py, add_rule.py)
    ↓ subprocess
iptables Command
    ↓
Response → API → GUI Update
```

**Ví dụ: Thêm Rule**:
1. User nhập thông tin rule trong GUI
2. `AddRuleHandlerAPI` validate input
3. Gọi `client.add_rule()` với JSON data
4. API Client gửi POST request đến `/api/rules/add`
5. Flask service nhận request, build iptables command
6. Thực thi `iptables -A INPUT ...`
7. Lưu metadata vào `rules_meta.json`
8. Trả về success response
9. GUI refresh rules table

### 3.2. Luồng Giám sát Hệ thống

```
Monitoring Thread (firewall_service.py)
    ↓ (mỗi 2 giây)
update_monitoring()
    ↓
Thu thập dữ liệu:
  - CPU: cgroup/cpu.stat
  - RAM: cgroup/memory.current
  - Disk I/O: cgroup/io.stat
  - Network: psutil.net_io_counters()
  - Temperature: thermal zones
  - Services: systemctl list-units
    ↓
Phát hiện Anomaly
    ↓
Gửi Alert (notification/mailer)
    ↓
Lưu vào monitoring_data (dict)
    ↓
GUI Request → GET /api/monitoring/data
    ↓
API Response (JSON)
    ↓
SystemMonitorAPI.update_stats()
    ↓
Update Labels + Charts
```

### 3.3. Luồng Phát hiện Tấn công (Log Tab)

```
QProcess (tail -f /var/log/kern.log)
    ↓
read_log() - Parse log line
    ↓
Phát hiện Attack Patterns:
  - ICMP Flood
  - SYN Flood
  - IP Spoofing
  - Port Scan
  - Invalid Packet
  - Broadcast Attack
  - Outbound Attack
  - Stealth Scan
    ↓
block_ip() - iptables -I INPUT 1 -s <IP> -j DROP
    ↓
send_attack_alert() - Desktop notification
    ↓
Highlight dòng log (màu đỏ)
```

---

## 4. KIẾN TRÚC MODULE

### 4.1. Cấu trúc Thư mục

```
PBL6/
├── main_qt_api.py              # Entry point GUI
├── main_qt.py                  # GUI direct mode (legacy)
│
├── frontend/                   # UI Files
│   ├── main.ui
│   ├── ui_loader.py
│   └── tabs/
│       ├── tab_log.ui
│       ├── tab_rules.ui
│       ├── tab_available_rules.ui
│       ├── tab_sandbox.ui
│       └── tab_graph.ui
│
├── backend/                    # Business Logic
│   ├── rules/
│   │   ├── core/
│   │   │   ├── rule_input.py      # Parse iptables rules
│   │   │   ├── add_rule.py        # Add/delete rules
│   │   │   └── available_rules.py # Rule templates
│   │   └── handlers/
│   │       ├── rules_table_handler_api.py  # Rules table UI handler
│   │       ├── add_rule_handler_api.py     # Add rule UI handler
│   │       └── available_rules_handler.py  # Available rules handler
│   │
│   ├── monitoring/
│   │   ├── system_monitor_api.py  # Monitor sử dụng API
│   │   ├── system_monitor.py      # Monitor direct mode
│   │   ├── host_monitor.py        # Host system monitor
│   │   ├── system_chart.py        # Charts manager
│   │   └── chart_manager.py       # Chart setup utility
│   │
│   ├── notifications/
│   │   ├── notification.py        # Desktop notifications
│   │   └── mailer.py              # Email alerts
│   │
│   └── ui/
│       └── log_tab.py             # Log tab handler
│
├── service/                    # Backend Service
│   ├── firewall_service.py       # Flask REST API daemon
│   ├── api_client.py             # API client library
│   ├── firewall-service.service  # Systemd service file
│   └── install_service.sh        # Service installation script
│
├── diagrams/                   # Documentation diagrams
│   ├── *.puml                   # PlantUML source files
│   └── *.png                    # Generated diagrams
│
└── Data Files
    ├── rules_meta.json          # Rules metadata
    ├── available_rules.json     # Rule templates
    └── sysctl_backup.json       # System config backup
```

### 4.2. Module Dependencies

```
main_qt_api.py
    ├── frontend.ui_loader
    ├── backend.ui.LogTab
    ├── backend.monitoring.system_monitor_api
    ├── backend.monitoring.chart_manager
    ├── backend.rules.handlers.rules_table_handler_api
    ├── backend.rules.handlers.add_rule_handler_api
    ├── backend.rules.handlers.available_rules_handler
    └── service.api_client

firewall_service.py
    ├── backend.rules.core.rule_input
    ├── backend.rules.core.add_rule
    └── backend.notifications

api_client.py
    └── requests (external)

Handlers
    └── service.api_client
```

---

## 5. KIẾN TRÚC GIAO TIẾP (Communication Architecture)

### 5.1. Client-Server Communication

**Protocol**: HTTP REST API

**Base URL**: `http://127.0.0.1:5000/api`

**Request/Response Format**: JSON

**Timeout**: 5 giây

### 5.2. API Endpoints

#### Health Check
- `GET /api/health` → `{status: "ok", service: "firewall-service"}`

#### Monitoring
- `POST /api/monitoring/start` → `{status: "started"}`
- `POST /api/monitoring/stop` → `{status: "stopped"}`
- `GET /api/monitoring/data` → `{cpu_percent, ram_percent, ...}`

#### Rules Management
- `GET /api/rules/list` → `{rules: [...]}`
- `POST /api/rules/add` → `{status: "success", message: "..."}`
- `POST /api/rules/delete` → `{status: "success"}`
- `POST /api/rules/delete-many` → `{status: "success", deleted: [...], failed: [...]}`
- `GET /api/rules/search?q=<query>` → `{rules: [...]}`

### 5.3. Error Handling

**Connection Errors**:
- GUI hiển thị dialog lỗi
- Hướng dẫn khởi động service

**API Errors**:
- Trả về HTTP status code
- Error message trong JSON response

**System Errors**:
- Catch exceptions
- Log errors
- Graceful degradation

---

## 6. KIẾN TRÚC THỜI GIAN THỰC (Real-time Architecture)

### 6.1. Refresh Timers

**Rules Table**: 1.5 giây
- QTimer trong `RulesTableHandlerAPI`
- Gọi `refresh_rules_table()`
- Lấy rules từ API

**Monitoring Data**: 2 giây
- QTimer trong `SystemMonitorAPI`
- Gọi `update_stats()`
- Lấy monitoring data từ API

**Monitoring Thread**: 2 giây
- Background thread trong `firewall_service.py`
- Gọi `update_monitoring()`
- Thu thập metrics từ system

**Charts**: 1-2 giây
- Tự động cập nhật khi nhận signal từ monitor
- Giữ tối đa 100 điểm dữ liệu

### 6.2. Event-Driven Updates

**Signals và Slots**:
- `SystemMonitorAPI.stats_updated` signal
- Charts tự động cập nhật khi nhận signal

**QProcess**:
- Log tab sử dụng QProcess với `tail -f`
- Real-time log reading

---

## 7. KIẾN TRÚC BẢO MẬT

### 7.1. Network Security

- API chỉ lắng nghe trên `127.0.0.1:5000` (localhost)
- CORS chỉ cho phép từ localhost
- Không expose ra ngoài

### 7.2. Permission Model

- Service chạy với quyền root (cần thiết cho iptables)
- GUI chạy với quyền user thường
- API không có authentication (chỉ localhost)

### 7.3. Input Validation

- Validate input trước khi thực thi iptables
- Protocol và Action là bắt buộc
- Sanitize user input

---

## 8. KIẾN TRÚC TRIỂN KHAI (Deployment Architecture)

### 8.1. Systemd Service

**Service File**: `service/firewall-service.service`

**Cấu hình**:
- Type: simple
- User: root
- Restart: always
- RestartSec: 10

**Lifecycle**:
- Install: `sudo ./install_service.sh install`
- Start: `sudo systemctl start firewall-service`
- Stop: `sudo systemctl stop firewall-service`
- Restart: `sudo systemctl restart firewall-service`

### 8.2. Virtual Environment

- Python 3.12
- Dependencies trong `requirements.txt`
- Isolated environment

### 8.3. File Permissions

- Service files: executable
- JSON files: read/write
- Log files: read-only (GUI)

---

## 9. KIẾN TRÚC MỞ RỘNG (Scalability Architecture)

### 9.1. Modular Design

- Tách biệt frontend và backend
- Module hóa business logic
- Dễ dàng thêm tính năng mới

### 9.2. API-Based

- REST API cho phép nhiều clients
- Có thể thêm web dashboard
- Có thể thêm mobile app

### 9.3. Threading

- Monitoring chạy trong thread riêng
- Không block main thread
- Non-blocking I/O

---

## 10. TỔNG KẾT KIẾN TRÚC

### 10.1. Điểm Mạnh

✅ **Tách biệt rõ ràng**: Frontend và Backend độc lập
✅ **API-based**: Dễ mở rộng và tích hợp
✅ **Real-time**: Cập nhật dữ liệu real-time
✅ **Modular**: Code được tổ chức tốt, dễ bảo trì
✅ **Threading**: Background processing không block UI
✅ **Error handling**: Xử lý lỗi graceful

### 10.2. Điểm Cần Cải thiện

⚠️ **Authentication**: Chưa có user authentication
⚠️ **Persistence**: Rules không tự động lưu persistent
⚠️ **Database**: Chưa có database để lưu trữ lịch sử
⚠️ **Testing**: Chưa có unit tests và integration tests
⚠️ **Documentation**: API documentation chưa đầy đủ

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**Tác giả**: System Architecture Documentation

