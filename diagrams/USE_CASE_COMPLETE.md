# USE CASE DIAGRAM - TỔNG HỢP ĐẦY ĐỦ
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN

Tài liệu này mô tả đầy đủ tất cả các Use Case của hệ thống quản lý firewall với giám sát hệ thống real-time.

**File PlantUML**: `use_case_complete.puml`

---

## 2. ACTORS (Các tác nhân)

### 2.1. User (Người dùng)
- **Mô tả**: Người dùng cuối sử dụng GUI để quản lý firewall và xem monitoring
- **Vai trò**: 
  - Quản lý firewall rules
  - Xem monitoring và thống kê
  - Nhận cảnh báo
  - Xem logs

### 2.2. System Monitor (Hệ thống giám sát)
- **Mô tả**: Hệ thống tự động giám sát và phát hiện anomaly
- **Vai trò**:
  - Tự động phát hiện các hoạt động bất thường
  - Gửi cảnh báo khi phát hiện anomaly

### 2.3. Firewall Service (Backend Service)
- **Mô tả**: Backend service xử lý logic nghiệp vụ
- **Vai trò**:
  - Xử lý các yêu cầu từ GUI
  - Tương tác với iptables
  - Thu thập dữ liệu monitoring
  - Quản lý monitoring thread

### 2.4. Email Service (Dịch vụ email)
- **Mô tả**: Dịch vụ gửi email cảnh báo
- **Vai trò**:
  - Gửi email alert khi phát hiện malware/anomaly

---

## 3. USE CASES CHI TIẾT

### 3.1. QUẢN LÝ FIREWALL RULES

#### UC-01: Xem danh sách Rules

**Actor**: User, Firewall Service

**Mô tả**: Hiển thị tất cả firewall rules từ các chains (INPUT, OUTPUT, FORWARD, etc.)

**Preconditions**:
- Firewall Service đang chạy
- GUI đã kết nối thành công với service

**Main Flow**:
1. GUI tự động gọi API `/api/rules/list` mỗi 1.5 giây
2. Service thực thi `iptables -L -v -n --line-numbers` cho tất cả chains
3. Service parse output và thêm group từ metadata
4. Service trả về JSON với danh sách rules
5. GUI cập nhật bảng rules, giữ nguyên trạng thái checkbox

**Thông tin hiển thị**:
- num (số thứ tự)
- pkts (số packets)
- bytes
- target (ACCEPT, DROP, REJECT, etc.)
- prot (protocol: tcp, udp, icmp, etc.)
- opt (options)
- in (input interface)
- out (output interface)
- source (source IP)
- destination (destination IP)
- chain (chain name)
- detail (chi tiết rule)
- group (phân loại rule)

**Postconditions**:
- Bảng rules hiển thị đầy đủ thông tin
- Rules được tự động refresh

**Alternative Flows**:
- Nếu service không khả dụng: Hiển thị lỗi kết nối
- Nếu không có rules: Hiển thị bảng trống

---

#### UC-02: Thêm Rule mới

**Actor**: User, Firewall Service

**Mô tả**: Thêm rule mới vào iptables

**Preconditions**:
- User có quyền root (service chạy với sudo)
- Protocol và Action đã được nhập

**Main Flow**:
1. User nhập thông tin rule:
   - IP (source IP)
   - Port (destination port)
   - Protocol (tcp, udp, icmp, etc.) - **Bắt buộc**
   - Action (ACCEPT, DROP, REJECT, etc.) - **Bắt buộc**
   - Interface (network interface)
   - State (NEW, ESTABLISHED, RELATED, etc.)
   - Group (phân loại rule)
2. User click "Add Rule"
3. Handler validate input (Protocol và Action bắt buộc)
4. Handler gọi API `/api/rules/add` với JSON data
5. Service build iptables command
6. Service thực thi `iptables -A INPUT ...`
7. Service lấy rule vừa thêm và lưu group vào metadata
8. Service trả về success
9. GUI refresh rules table (UC-01)
10. GUI clear form

**Postconditions**:
- Rule mới được thêm vào iptables
- Metadata được cập nhật
- Rules table được refresh

**Alternative Flows**:
- Validation thất bại: Hiển thị warning "Protocol và Action là bắt buộc!"
- iptables command thất bại: Trả về error message

**Relationships**:
- `UC-02 ..> UC-01 : <<updates>>` - Cập nhật danh sách rules

---

#### UC-03: Xóa Rule

**Actor**: User, Firewall Service

**Mô tả**: Xóa một hoặc nhiều rules từ iptables

**Preconditions**:
- User có quyền root
- Có ít nhất một rule được chọn (nếu xóa nhiều)

**Main Flow**:
1. User chọn rule(s) cần xóa (checkbox)
2. User click "Delete Selected"
3. Handler lấy danh sách rule numbers đã chọn
4. Handler gọi API `/api/rules/delete-many` với danh sách numbers
5. Service lấy tất cả rules từ tất cả chains
6. Service nhóm rules theo chain
7. Service sắp xếp numbers giảm dần để tránh lỗi khi xóa
8. Service thực thi `iptables -D <chain> <num>` cho mỗi rule
9. Service trả về kết quả (deleted, failed)
10. GUI refresh rules table (UC-01)

**Postconditions**:
- Rule(s) đã được xóa khỏi iptables
- Rules table được refresh

**Alternative Flows**:
- Nếu một số rules xóa thất bại: Hiển thị thông báo lỗi
- Nếu không có rule nào được chọn: Không thực hiện gì

**Relationships**:
- `UC-03 ..> UC-01 : <<updates>>` - Cập nhật danh sách rules

---

#### UC-04: Tìm kiếm Rules

**Actor**: User, Firewall Service

**Mô tả**: Tìm kiếm rules theo chain name

**Preconditions**:
- Firewall Service đang chạy

**Main Flow**:
1. User nhập chain name vào search box (ví dụ: "INPUT")
2. User click "Search" hoặc nhấn Enter
3. Handler gọi API `/api/rules/search?q=<query>`
4. Service thực thi `iptables -L <chain> -v -n --line-numbers`
5. Service parse và filter rules theo chain name
6. Service trả về danh sách rules đã lọc
7. GUI cập nhật bảng với kết quả tìm kiếm

**Postconditions**:
- Bảng chỉ hiển thị rules khớp với tìm kiếm

**Alternative Flows**:
- Nếu không tìm thấy: Hiển thị bảng trống
- Nếu query rỗng: Hiển thị tất cả rules

---

#### UC-05: Quản lý Available Rules

**Actor**: User

**Mô tả**: Quản lý danh sách các rules có sẵn (templates)

**Preconditions**:
- File `available_rules.json` tồn tại

**Main Flow**:
1. User mở tab "Available Rules"
2. GUI load danh sách rules từ file JSON
3. User enable/disable các rules bằng checkbox
4. GUI lưu trạng thái vào file JSON

**Postconditions**:
- Trạng thái enable/disable được lưu vào file

---

### 3.2. GIÁM SÁT HỆ THỐNG

#### UC-06: Xem biểu đồ Monitoring

**Actor**: User, Firewall Service

**Mô tả**: Hiển thị biểu đồ real-time về CPU, RAM, Network, Temperature

**Preconditions**:
- Monitoring đã được khởi động (UC-11)
- Firewall Service đang chạy

**Main Flow**:
1. GUI tự động gọi API `/api/monitoring/data` mỗi 2 giây
2. Service trả về dữ liệu monitoring:
   - CPU (%)
   - RAM (% và MB)
   - Network (RX/TX bytes/s)
   - Temperature
   - Disk I/O
   - Services count
3. GUI cập nhật các biểu đồ:
   - Sandbox Charts (container monitoring)
   - Host Charts (host system monitoring)
4. Biểu đồ tự động cập nhật real-time

**Postconditions**:
- Biểu đồ hiển thị dữ liệu real-time
- Dữ liệu được cập nhật mỗi 2 giây

**Metrics hiển thị**:
- CPU usage (%)
- RAM usage (% và MB)
- Network RX/TX (bytes/s)
- Temperature (°C)
- Disk Read/Write (MB)

---

#### UC-07: Xem thống kê tài nguyên

**Actor**: User, Firewall Service

**Mô tả**: Hiển thị số liệu chi tiết về tài nguyên hệ thống

**Preconditions**:
- Monitoring đã được khởi động

**Main Flow**:
1. GUI gọi API `/api/monitoring/data`
2. Service trả về dữ liệu chi tiết
3. GUI hiển thị các thống kê:
   - CPU % và usage
   - RAM % và MB
   - Disk I/O (read/write MB)
   - Network RX/TX (bytes/s)
   - Services count
   - Network processes count

**Postconditions**:
- Thống kê được hiển thị chi tiết

---

#### UC-08: Phát hiện Anomaly

**Actor**: System Monitor, Firewall Service

**Mô tả**: Tự động phát hiện CPU spike, RAM spike, service lạ

**Preconditions**:
- Monitoring thread đang chạy
- Cgroup files có thể truy cập

**Main Flow**:
1. Monitoring thread gọi `update_monitoring()` mỗi 2 giây
2. Thu thập dữ liệu từ:
   - cgroup (CPU, RAM, Disk I/O)
   - psutil (Network)
   - thermal zone (Temperature)
   - systemctl (Services)
3. Kiểm tra các ngưỡng:
   - **CPU > 85%**: Phát hiện CPU spike
   - **RAM spike > 150MB**: Phát hiện RAM tăng đột biến
   - **Services > 10**: Phát hiện service lạ (với cooldown 60s)
4. Nếu phát hiện anomaly:
   - Tạo alert object
   - Kích hoạt UC-09 (Nhận cảnh báo)
5. Lưu alert vào monitoring_data (tối đa 100 alerts)

**Postconditions**:
- Alert được ghi nhận
- UC-09 được kích hoạt

**Alternative Flows**:
- Cooldown chưa hết: Bỏ qua alert
- Ngưỡng không vượt quá: Tiếp tục giám sát

**Relationships**:
- `UC-08 ..> UC-09 : <<triggers>>` - Kích hoạt cảnh báo
- `UC-11 ..> UC-08 : <<enables>>` - Bật giám sát
- `UC-12 ..> UC-08 : <<disables>>` - Tắt giám sát

---

#### UC-09: Nhận cảnh báo

**Actor**: User, System Monitor, Email Service

**Mô tả**: Nhận desktop notification và email alert khi phát hiện malware/anomaly

**Preconditions**:
- UC-08 đã phát hiện anomaly

**Main Flow**:
1. System Monitor gọi `send_malware_alert()`
2. Gửi desktop notification:
   - Sử dụng `notify-send`
   - Title: "Malware Alert"
   - Message: Mô tả anomaly (Trojan.Generic, Service alert, etc.)
   - Urgency: High
3. Nếu email được cấu hình:
   - Gửi email alert qua Email Service
   - Subject: "Malware Alert"
   - Body: Chi tiết anomaly
4. User nhận được cảnh báo

**Postconditions**:
- User đã nhận được cảnh báo
- Alert được lưu trong monitoring_data

**Loại cảnh báo**:
- **Trojan.Generic**: Khi phát hiện CPU/RAM spike
- **Service Alert**: Khi phát hiện service lạ (> 10 services)

**Alternative Flows**:
- Email không được cấu hình: Chỉ gửi desktop notification

---

### 3.3. QUẢN LÝ LOGS

#### UC-10: Xem Logs

**Actor**: User

**Mô tả**: Hiển thị logs hệ thống

**Preconditions**:
- File logs tồn tại

**Main Flow**:
1. User mở tab "Logs"
2. GUI load và hiển thị logs từ file
3. User có thể xem và theo dõi logs

**Postconditions**:
- Logs được hiển thị

---

### 3.4. QUẢN LÝ SERVICE

#### UC-11: Khởi động Monitoring

**Actor**: User, Firewall Service

**Mô tả**: Bắt đầu monitoring thread để giám sát hệ thống

**Preconditions**:
- Firewall Service đang chạy
- Monitoring chưa được khởi động

**Main Flow**:
1. User click "Start Monitoring" hoặc GUI tự động gọi khi khởi động
2. GUI gọi API `POST /api/monitoring/start`
3. Service khởi động monitoring thread
4. Monitoring thread bắt đầu thu thập dữ liệu mỗi 2 giây
5. Service trả về success

**Postconditions**:
- Monitoring thread đang chạy
- UC-08 được kích hoạt

**Relationships**:
- `UC-11 ..> UC-08 : <<enables>>` - Bật giám sát

---

#### UC-12: Dừng Monitoring

**Actor**: User, Firewall Service

**Mô tả**: Dừng monitoring thread

**Preconditions**:
- Monitoring đang chạy

**Main Flow**:
1. User click "Stop Monitoring"
2. GUI gọi API `POST /api/monitoring/stop`
3. Service dừng monitoring thread
4. Service trả về success

**Postconditions**:
- Monitoring thread đã dừng
- UC-08 bị vô hiệu hóa

**Relationships**:
- `UC-12 ..> UC-08 : <<disables>>` - Tắt giám sát

---

#### UC-13: Kiểm tra trạng thái Service

**Actor**: User, Firewall Service

**Mô tả**: Kiểm tra service có đang hoạt động không

**Preconditions**:
- Service đã được cài đặt

**Main Flow**:
1. GUI gọi API `GET /api/health` khi khởi động
2. Service trả về `{status: "ok"}`
3. GUI hiển thị trạng thái kết nối

**Postconditions**:
- Trạng thái service được xác định

**Alternative Flows**:
- Nếu service không khả dụng: Hiển thị lỗi kết nối và thoát

---

## 4. QUAN HỆ GIỮA CÁC USE CASES

### 4.1. Include/Extend Relationships

- `UC-02 ..> UC-01 : <<updates>>` - Thêm rule cập nhật danh sách
- `UC-03 ..> UC-01 : <<updates>>` - Xóa rule cập nhật danh sách
- `UC-08 ..> UC-09 : <<triggers>>` - Phát hiện anomaly kích hoạt cảnh báo
- `UC-11 ..> UC-08 : <<enables>>` - Khởi động monitoring bật giám sát
- `UC-12 ..> UC-08 : <<disables>>` - Dừng monitoring tắt giám sát

### 4.2. Actor-Use Case Relationships

**User** tương tác với:
- UC-01 đến UC-07, UC-09 đến UC-13

**System Monitor** tương tác với:
- UC-08, UC-09

**Firewall Service** tương tác với:
- UC-01 đến UC-04, UC-06 đến UC-08, UC-11, UC-12

**Email Service** tương tác với:
- UC-09

---

## 5. TỔNG KẾT

### 5.1. Số lượng Use Cases

- **Quản lý Firewall Rules**: 5 use cases (UC-01 đến UC-05)
- **Giám sát Hệ thống**: 4 use cases (UC-06 đến UC-09)
- **Quản lý Logs**: 1 use case (UC-10)
- **Quản lý Service**: 3 use cases (UC-11 đến UC-13)

**Tổng cộng**: 13 use cases

### 5.2. Actors

- **User**: 10 use cases
- **System Monitor**: 2 use cases
- **Firewall Service**: 10 use cases
- **Email Service**: 1 use case

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**File PlantUML**: `diagrams/use_case_complete.puml`

