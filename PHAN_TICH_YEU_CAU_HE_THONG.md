# PHÂN TÍCH YÊU CẦU HỆ THỐNG
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Mục đích
Hệ thống quản lý firewall (iptables) với giao diện đồ họa (GUI) và khả năng giám sát hệ thống real-time, phát hiện các hoạt động bất thường và cảnh báo malware.

### 1.2. Kiến trúc hệ thống
Hệ thống được thiết kế theo mô hình **Client-Server** với 2 thành phần chính:

1. **Backend Service (Daemon)**
   - Chạy như một systemd service
   - Cung cấp REST API (Flask)
   - Xử lý logic nghiệp vụ và tương tác với iptables
   - Giám sát hệ thống liên tục

2. **Frontend GUI (Client)**
   - Giao diện PyQt6
   - Giao tiếp với backend qua REST API
   - Hiển thị dữ liệu real-time

---

## 2. YÊU CẦU CHỨC NĂNG (Functional Requirements)

### 2.1. Quản lý Firewall Rules

#### 2.1.1. Xem danh sách Rules
- **Mô tả**: Hiển thị tất cả các rules từ tất cả các chains (INPUT, OUTPUT, FORWARD, etc.)
- **Chi tiết**:
  - Hiển thị các thông tin: num, pkts, bytes, target, prot, opt, in, out, source, destination, chain, detail
  - Tự động refresh mỗi 1.5 giây
  - Hỗ trợ lọc theo chain name
  - Lưu trạng thái checkbox khi refresh

#### 2.1.2. Thêm Rule mới
- **Mô tả**: Thêm rule mới vào iptables
- **Tham số**:
  - IP (source IP)
  - Port (destination port)
  - Protocol (tcp, udp, icmp, etc.)
  - Action (ACCEPT, DROP, REJECT, etc.)
  - Interface (network interface)
  - State (NEW, ESTABLISHED, RELATED, etc.)
  - Group (phân loại rule)
- **Xử lý**: 
  - Validate input
  - Thực thi lệnh iptables
  - Lưu metadata (group) vào file

#### 2.1.3. Xóa Rules
- **Xóa một rule**: Xóa rule theo số thứ tự (num) trong chain
- **Xóa nhiều rules**: 
  - Xóa các rules đã được chọn (checkbox)
  - Xóa tất cả rules trong một chain
  - Hỗ trợ xóa rules từ nhiều chains khác nhau
  - Sắp xếp num giảm dần để tránh lỗi khi xóa

#### 2.1.4. Tìm kiếm Rules
- **Mô tả**: Tìm kiếm rules theo chain name
- **Chức năng**: Filter real-time khi nhập tên chain

#### 2.1.5. Available Rules
- **Mô tả**: Quản lý danh sách các rules có sẵn (templates)
- **Chức năng**:
  - Hiển thị danh sách rules từ file JSON
  - Cho phép enable/disable rules
  - Lưu trạng thái vào file

### 2.2. Giám sát Hệ thống (System Monitoring)

#### 2.2.1. Giám sát Tài nguyên
- **CPU**: 
  - Theo dõi % sử dụng CPU
  - Phát hiện spike CPU (> 40%)
  - Cảnh báo khi CPU > 85%
  
- **RAM**:
  - Theo dõi % sử dụng RAM
  - Theo dõi RAM sử dụng (MB)
  - Phát hiện tăng đột biến RAM (> 150 MB)
  
- **Disk I/O**:
  - Theo dõi disk read (MB)
  - Theo dõi disk write (MB)
  
- **Network**:
  - Theo dõi network RX (bytes/s)
  - Theo dõi network TX (bytes/s)
  - Đếm số lượng network processes (kết nối established)
  
- **Temperature**: Theo dõi nhiệt độ CPU/hệ thống

- **Services**: Đếm số lượng services đang chạy

#### 2.2.2. Biểu đồ Real-time
- **Sandbox Charts**: Biểu đồ giám sát container/sandbox
- **Host Charts**: Biểu đồ giám sát host system
- **Metrics**: CPU, RAM, Network, Temperature
- **Update**: Real-time mỗi 2 giây

#### 2.2.3. Phát hiện Anomaly
- **CPU Spike**: Cảnh báo khi CPU vượt ngưỡng
- **RAM Spike**: Cảnh báo khi RAM tăng đột biến
- **Service Alert**: Cảnh báo khi phát hiện service lạ (> 10 services)
- **Cooldown**: 60 giây giữa các cảnh báo cùng loại

### 2.3. Cảnh báo và Thông báo (Notifications)

#### 2.3.1. Desktop Notifications
- **Mô tả**: Gửi thông báo desktop khi phát hiện malware/anomaly
- **Loại cảnh báo**:
  - Trojan.Generic (khi phát hiện CPU/RAM spike)
  - Service alerts
- **Thông tin**: Title, message, urgency level

#### 2.3.2. Email Alerts (Mailer)
- **Mô tả**: Gửi email cảnh báo (nếu được cấu hình)
- **Chức năng**: Gửi thông báo malware alert qua email

### 2.4. Log Management

#### 2.4.1. Log Tab
- **Mô tả**: Hiển thị logs hệ thống
- **Chức năng**: Xem và theo dõi logs

---

## 3. YÊU CẦU PHI CHỨC NĂNG (Non-Functional Requirements)

### 3.1. Hiệu năng (Performance)
- **Refresh rate**: 
  - Rules table: 1.5 giây
  - Monitoring data: 2 giây
- **Response time**: API response < 5 giây
- **Timeout**: Request timeout 5 giây

### 3.2. Bảo mật (Security)
- **Quyền truy cập**: Service cần quyền root để thao tác iptables
- **Network**: API chỉ lắng nghe trên localhost (127.0.0.1:5000)
- **CORS**: Chỉ cho phép CORS từ localhost

### 3.3. Độ tin cậy (Reliability)
- **Service daemon**: Chạy như systemd service, tự động restart khi crash
- **Error handling**: Xử lý lỗi gracefully, không crash ứng dụng
- **Validation**: Validate input trước khi thực thi lệnh

### 3.4. Khả năng mở rộng (Scalability)
- **Modular design**: Tách biệt frontend và backend
- **API-based**: Dễ dàng mở rộng thêm clients khác
- **Threading**: Monitoring chạy trong thread riêng

### 3.5. Khả năng bảo trì (Maintainability)
- **Code structure**: Tổ chức code theo modules
- **Documentation**: Có README và hướng dẫn sử dụng
- **Logging**: In log để debug

### 3.6. Khả năng sử dụng (Usability)
- **GUI**: Giao diện đồ họa trực quan với PyQt6
- **Real-time updates**: Cập nhật dữ liệu real-time
- **Error messages**: Thông báo lỗi rõ ràng

---

## 4. CẤU TRÚC HỆ THỐNG

### 4.1. Thư mục và Modules

```
PBL6/
├── service/                    # Backend Service
│   ├── firewall_service.py     # Flask REST API daemon
│   ├── api_client.py           # API client library
│   ├── install_service.sh      # Service installation script
│   └── firewall-service.service # Systemd service file
│
├── backend/                    # Backend Logic
│   ├── rules/                  # Firewall rules management
│   │   ├── core/               # Core logic
│   │   │   ├── rule_input.py   # Parse iptables rules
│   │   │   ├── add_rule.py     # Add/delete rules
│   │   │   └── available_rules.py # Available rules templates
│   │   └── handlers/           # UI handlers
│   │       ├── rules_table_handler_api.py
│   │       ├── add_rule_handler_api.py
│   │       └── available_rules_handler.py
│   │
│   ├── monitoring/             # System monitoring
│   │   ├── system_monitor_api.py
│   │   ├── system_chart.py
│   │   └── chart_manager.py
│   │
│   ├── notifications/          # Notifications
│   │   ├── notification.py     # Desktop notifications
│   │   └── mailer.py           # Email alerts
│   │
│   └── ui/                     # UI components
│       └── log_tab.py
│
├── frontend/                   # Frontend UI
│   ├── main.ui                 # Main window UI
│   ├── tabs/                   # Tab UIs
│   │   ├── tab_rules.ui
│   │   ├── tab_graph.ui
│   │   ├── tab_log.ui
│   │   └── tab_sandbox.ui
│   └── ui_loader.py            # UI loader
│
├── main_qt.py                  # GUI (direct mode)
├── main_qt_api.py             # GUI (API mode - recommended)
└── requirements.txt            # Dependencies
```

### 4.2. API Endpoints

#### Health Check
- `GET /api/health` - Kiểm tra service status

#### Monitoring
- `POST /api/monitoring/start` - Bắt đầu monitoring
- `POST /api/monitoring/stop` - Dừng monitoring
- `GET /api/monitoring/data` - Lấy dữ liệu monitoring

#### Rules Management
- `GET /api/rules/list` - Lấy danh sách tất cả rules
- `POST /api/rules/add` - Thêm rule mới
- `POST /api/rules/delete` - Xóa một rule
- `POST /api/rules/delete-many` - Xóa nhiều rules
- `GET /api/rules/search?q=<query>` - Tìm kiếm rules

---

## 5. LUỒNG XỬ LÝ CHÍNH

### 5.1. Luồng Quản lý Rules

```
User Action (GUI)
    ↓
Handler (rules_table_handler_api.py)
    ↓
API Client (api_client.py)
    ↓
HTTP Request → Flask Service (firewall_service.py)
    ↓
Backend Logic (rule_input.py, add_rule.py)
    ↓
iptables Command (subprocess)
    ↓
Response → GUI Update
```

### 5.2. Luồng Giám sát Hệ thống

```
Monitoring Thread (firewall_service.py)
    ↓
update_monitoring() - Mỗi 2 giây
    ↓
Thu thập dữ liệu:
  - CPU (cgroup)
  - RAM (cgroup)
  - Disk I/O (cgroup)
  - Network (psutil)
  - Temperature (thermal zone)
  - Services (systemctl)
    ↓
Phát hiện Anomaly
    ↓
Gửi Alert (notification/mailer)
    ↓
Lưu vào monitoring_data
    ↓
GUI Request → API Response
    ↓
Update Charts & Labels
```

### 5.3. Luồng Cảnh báo Malware

```
Anomaly Detection
    ↓
CPU > 85% OR RAM spike > 150MB OR Services > 10
    ↓
send_malware_alert()
    ↓
Desktop Notification (notify-send)
    ↓
Email Alert (nếu được cấu hình)
```

---

## 6. CÔNG NGHỆ SỬ DỤNG

### 6.1. Backend
- **Python 3.12**
- **Flask**: REST API framework
- **psutil**: System monitoring
- **subprocess**: Execute iptables commands
- **threading**: Background monitoring

### 6.2. Frontend
- **PyQt6**: GUI framework
- **PyQt6-Charts**: Real-time charts
- **QTimer**: Auto-refresh

### 6.3. System Integration
- **systemd**: Service daemon
- **iptables**: Firewall management
- **cgroup**: Container resource monitoring
- **notify-send**: Desktop notifications

### 6.4. Dependencies
- flask >= 2.0.0
- flask-cors >= 3.0.0

- requests >= 2.25.0
- psutil
- PyQt6 >= 6.9.0
- PyQt6-Charts >= 6.9.0
- python-dotenv
- notify2

---

## 7. YÊU CẦU MÔI TRƯỜNG

### 7.1. Hệ điều hành
- **Linux** (Ubuntu/Debian recommended)
- Kernel hỗ trợ cgroup v2
- systemd

### 7.2. Quyền truy cập
- **Root**: Để thao tác iptables
- **sudo**: Để chạy service

### 7.3. Container (Optional)
- **systemd-nspawn** hoặc **Docker**
- Container name: "ubuntu" (có thể cấu hình)

### 7.4. Network
- Localhost (127.0.0.1:5000) cho API
- Không cần internet (trừ khi gửi email)

---

## 8. CÁC TÍNH NĂNG ĐẶC BIỆT

### 8.1. Multi-Chain Support
- Hỗ trợ quản lý rules từ nhiều chains (INPUT, OUTPUT, FORWARD, etc.)
- Xử lý đúng khi xóa rules từ nhiều chains

### 8.2. Rule Grouping
- Phân loại rules theo group
- Lưu metadata vào file JSON

### 8.3. Real-time Monitoring
- Giám sát liên tục không cần user interaction
- Tự động phát hiện và cảnh báo

### 8.4. Container Monitoring
- Giám sát tài nguyên container qua cgroup
- Hỗ trợ systemd-nspawn containers

### 8.5. Service Management
- Cài đặt như systemd service
- Tự động khởi động khi boot
- Dễ dàng quản lý (start/stop/restart)

---

## 9. HẠN CHẾ VÀ RÀNG BUỘC

### 9.1. Hạn chế
- Chỉ hỗ trợ IPv4 (iptables)
- API chỉ accessible từ localhost
- Cần quyền root để hoạt động
- Container monitoring chỉ hoạt động với systemd-nspawn

### 9.2. Ràng buộc
- Phải restart service sau khi sửa code backend
- Rules được lưu trong memory (iptables), cần lưu lại nếu muốn persistent
- Monitoring data không được lưu trữ lâu dài (chỉ trong memory)

---

## 10. KẾ HOẠCH PHÁT TRIỂN TƯƠNG LAI

### 10.1. Tính năng có thể thêm
- IPv6 support (ip6tables)
- Persistent rules (iptables-save/restore)
- Rule templates và presets
- Logging và audit trail
- User authentication cho API
- Web dashboard
- Database để lưu trữ lịch sử
- Export/Import rules
- Rule validation và testing

### 10.2. Cải thiện
- Performance optimization
- Better error handling
- Unit tests
- Integration tests
- Documentation improvements
- UI/UX enhancements

---

## 11. TÀI LIỆU THAM KHẢO

- `SERVICE_GUIDE.md`: Hướng dẫn sử dụng service
- `service/README.md`: Tài liệu service
- `requirements.txt`: Dependencies
- Code comments trong các file Python

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**Tác giả**: System Analysis

