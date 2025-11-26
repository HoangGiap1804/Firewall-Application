# GIAO DIỆN HỆ THỐNG
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN GIAO DIỆN

Giao diện hệ thống được xây dựng bằng **PyQt6**, là một ứng dụng desktop với giao diện tab-based, cho phép người dùng quản lý firewall rules và giám sát hệ thống một cách trực quan.

### 1.1. Cấu trúc Giao diện

- **Main Window**: Cửa sổ chính chứa QTabWidget
- **5 Tabs chính**: Log tab, Rules, Available Rules, Sandbox, Graph
- **Real-time Updates**: Tự động cập nhật dữ liệu mỗi 1.5-2 giây
- **Responsive Design**: Giao diện thân thiện, dễ sử dụng

### 1.2. Công nghệ UI

- **Framework**: PyQt6 (Qt6 for Python)
- **Charts**: PyQt6-Charts (biểu đồ real-time)
- **UI Files**: Qt Designer (.ui files)
- **Styling**: CSS-like stylesheet

---

## 2. CẤU TRÚC MAIN WINDOW

### 2.1. Main Window Layout

```
┌─────────────────────────────────────────────────────────┐
│              Firewall Application                        │
├─────────────────────────────────────────────────────────┤
│  [Log tab] [Rules] [Available Rules] [Sandbox] [Graph] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│              Nội dung Tab được chọn                      │
│                                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**File**: `frontend/main.ui`
- **Window Title**: "Firewall Application"
- **Size**: 747x865 pixels (mặc định)
- **Layout**: QGridLayout với QTabWidget

### 2.2. Tab Styling

Giao diện sử dụng custom stylesheet cho tabs:

- **Tab không chọn**: Nền gradient xám nhạt (#f5f5f5 → #e8e8e8)
- **Tab được chọn**: Nền gradient xanh dương (#3498db → #2980b9), chữ trắng
- **Tab hover**: Nền xám đậm hơn khi di chuột
- **Border radius**: 8px cho góc bo tròn

---

## 3. CÁC TAB CHÍNH

### 3.1. Tab 1: LOG TAB

**File**: `frontend/tabs/tab_log.ui`  
**Handler**: `backend/ui/log_tab.py`

#### 3.1.1. Chức năng

- **Hiển thị Kernel Logs**: Đọc và hiển thị logs từ `/var/log/kern.log`
- **Real-time Monitoring**: Tự động cập nhật khi có log mới
- **Phân tích Logs**: Parse các trường thông tin từ log
- **Phát hiện Tấn công**: Tự động phát hiện các loại tấn công
- **Chặn IP tự động**: Tự động chặn IP khi phát hiện tấn công

#### 3.1.2. Các Trường Hiển thị

Bảng hiển thị các cột sau:

| Cột | Mô tả |
|-----|-------|
| IN | Interface vào |
| OUT | Interface ra |
| MAC | Địa chỉ MAC |
| SRC | IP nguồn |
| DST | IP đích |
| LEN | Độ dài packet |
| TOS | Type of Service |
| PREC | Precedence |
| TTL | Time To Live |
| ID | Packet ID |
| PROTO | Protocol (TCP/UDP/ICMP) |
| SPT | Source Port |
| DPT | Destination Port |
| LEN2 | Độ dài thứ 2 |

#### 3.1.3. Tính năng Đặc biệt

**Phát hiện Tấn công:**
- **ICMP Flood**: Phát hiện ping flood
- **SYN Flood**: Phát hiện SYN flood attack
- **IP Spoofing**: Phát hiện IP giả mạo
- **Port Scan**: Phát hiện quét cổng
- **Invalid Packet**: Phát hiện packet không hợp lệ
- **Broadcast Attack**: Phát hiện tấn công broadcast
- **Outbound Attack**: Phát hiện tấn công outbound
- **Stealth Scan**: Phát hiện FIN/XMAS/NULL scan

**Hành động Tự động:**
- Tự động chặn IP tấn công bằng iptables
- Gửi desktop notification cảnh báo
- Gửi email cảnh báo (nếu được cấu hình)
- Highlight dòng log tấn công màu đỏ (#db5858)

**UI Features:**
- Alternating row colors (xám trắng xen kẽ)
- Auto-scroll xuống cuối khi có log mới
- Chỉ auto-scroll nếu đang ở gần cuối bảng

---

### 3.2. Tab 2: RULES

**File**: `frontend/tabs/tab_rules.ui`  
**Handler**: `backend/rules/handlers/rules_table_handler_api.py`

#### 3.2.1. Chức năng

- **Xem danh sách Rules**: Hiển thị tất cả firewall rules từ tất cả chains
- **Tìm kiếm Rules**: Lọc rules theo chain name
- **Xóa Rules**: Xóa một hoặc nhiều rules
- **Thêm Rule mới**: Form thêm rule mới vào iptables

#### 3.2.2. Bảng Rules (tableRules)

**Các cột hiển thị:**

| Cột | Mô tả |
|-----|-------|
| num | Số thứ tự rule trong chain |
| pkts | Số lượng packets đã match |
| bytes | Tổng bytes đã match |
| target | Hành động (ACCEPT/DROP/REJECT) |
| prot | Protocol (tcp/udp/icmp/all) |
| opt | Options |
| in | Interface vào |
| out | Interface ra |
| source | IP nguồn |
| destination | IP đích |
| chain | Chain name (INPUT/OUTPUT/FORWARD) |
| detail | Chi tiết rule (các tham số khác) |
| delete | Checkbox để chọn xóa |

**Tính năng:**
- **Auto-refresh**: Tự động refresh mỗi 1.5 giây
- **Checkbox selection**: Chọn nhiều rules để xóa
- **Preserve selection**: Giữ nguyên trạng thái checkbox khi refresh
- **Multi-chain support**: Hiển thị rules từ nhiều chains
- **Read-only cells**: Các ô dữ liệu không thể chỉnh sửa trực tiếp

#### 3.2.3. Form Thêm Rule (frameAddRule)

**Các trường nhập liệu:**

| Trường | Mô tả | Bắt buộc |
|--------|-------|----------|
| IP | Source IP address | Không |
| Port | Destination port | Không |
| Protocol | Protocol (tcp/udp/icmp/all) | **Có** |
| Action | Hành động (ACCEPT/DROP/REJECT) | **Có** |
| Interface | Network interface | Không |
| State | Connection state (NEW/ESTABLISHED/RELATED) | Không |
| Group | Nhóm phân loại rule | Không |

**Nút bấm:**
- **buttonAddRuleInFrame**: Thêm rule mới vào iptables

#### 3.2.4. Tìm kiếm và Xóa

**Tìm kiếm:**
- **buttonSearch**: Lọc rules theo chain name
- **Input field**: Nhập tên chain để lọc
- Real-time filtering khi nhập

**Xóa Rules:**
- **buttonDeleteMany**: Xóa tất cả rules đã chọn (checkbox)
- Hỗ trợ xóa rules từ nhiều chains khác nhau
- Tự động sắp xếp num giảm dần để tránh lỗi khi xóa

---

### 3.3. Tab 3: AVAILABLE RULES

**File**: `frontend/tabs/tab_available_rules.ui`  
**Handler**: `backend/rules/handlers/available_rules_handler.py`

#### 3.3.1. Chức năng

- **Quản lý Rule Templates**: Hiển thị danh sách các rules có sẵn (templates)
- **Enable/Disable Rules**: Bật/tắt rules bằng checkbox
- **Lưu trạng thái**: Lưu trạng thái enable/disable vào file

#### 3.3.2. Danh sách Available Rules

**Nguồn dữ liệu**: File `available_rules.json`

**Hiển thị:**
- Danh sách các rules có sẵn
- Checkbox để enable/disable từng rule
- Mô tả rule (nếu có)

**Tính năng:**
- **Persistent state**: Lưu trạng thái checkbox vào file
- **Auto-restore**: Tự động khôi phục trạng thái khi mở lại
- **Real-time toggle**: Bật/tắt rule ngay lập tức

---

### 3.4. Tab 4: SANDBOX

**File**: `frontend/tabs/tab_sandbox.ui`

#### 3.4.1. Chức năng

- **Giám sát Sandbox/Container**: Theo dõi tài nguyên container
- **Hiển thị Metrics**: CPU, RAM, Network của sandbox
- **Charts**: Biểu đồ real-time cho sandbox

#### 3.4.2. Nội dung Tab

**Metrics hiển thị:**
- CPU usage (%)
- RAM usage (MB và %)
- Disk I/O (read/write MB)
- Network traffic (RX/TX)
- Temperature
- Network processes count
- Services count

**Charts:**
- CPU Chart: Biểu đồ CPU usage theo thời gian
- RAM Chart: Biểu đồ RAM usage theo thời gian
- Network Chart: Biểu đồ network traffic
- Temperature Chart: Biểu đồ nhiệt độ

---

### 3.5. Tab 5: GRAPH

**File**: `frontend/tabs/tab_graph.ui`  
**Handler**: `backend/monitoring/system_monitor_api.py`, `backend/monitoring/chart_manager.py`

#### 3.5.1. Chức năng

- **Giám sát Host System**: Theo dõi tài nguyên hệ thống host
- **Real-time Charts**: Biểu đồ cập nhật real-time
- **System Metrics**: Hiển thị các chỉ số hệ thống

#### 3.5.2. Biểu đồ Real-time

**Sandbox Charts:**
- **CPU Chart**: Biểu đồ CPU usage của container
- **RAM Chart**: Biểu đồ RAM usage của container
- **Network Chart**: Biểu đồ network traffic của container
- **Temperature Chart**: Biểu đồ nhiệt độ

**Host Charts:**
- **CPU Chart**: Biểu đồ CPU usage của host
- **RAM Chart**: Biểu đồ RAM usage của host
- **Network Chart**: Biểu đồ network traffic của host
- **Temperature Chart**: Biểu đồ nhiệt độ host

**Chart Features:**
- **Real-time updates**: Cập nhật mỗi 2 giây
- **Line series**: Đường line chart với màu sắc khác nhau
- **Time axis**: Trục X hiển thị thời gian
- **Value axis**: Trục Y hiển thị giá trị
- **Animation**: Hiệu ứng animation khi vẽ
- **Max points**: Giữ tối đa 100 điểm dữ liệu (scroll tự động)

#### 3.5.3. Labels Hiển thị Metrics

**Các label hiển thị giá trị hiện tại:**

| Label | Mô tả | Format |
|-------|-------|--------|
| label_cpu | CPU usage | `{value:.1f}%` |
| label_ram | RAM usage | `{mb:.1f} MB ({percent:.1f}%)` |
| label_disk | Disk I/O | `↑ {write:.1f} MB  ↓ {read:.1f} MB` |
| label_netproc | Network processes | `Net procs: {count} kết nối` |
| label_service | Services count | `{count} running services` |

**Update frequency**: Mỗi 2 giây

---

## 4. COMPONENTS VÀ WIDGETS

### 4.1. Tables (QTableWidget)

**Sử dụng trong:**
- **Log Tab**: Hiển thị kernel logs
- **Rules Tab**: Hiển thị firewall rules

**Tính năng:**
- Alternating row colors
- Read-only cells (trừ checkbox)
- Auto-resize columns
- Horizontal/vertical headers
- Checkbox selection

### 4.2. Charts (QChart, QLineSeries)

**Sử dụng trong:**
- **Sandbox Tab**: Charts cho container
- **Graph Tab**: Charts cho host và sandbox

**Loại charts:**
- **Line Chart**: Đường line cho time series data
- **Multiple series**: Nhiều đường trên cùng một chart
- **Value axis**: Trục giá trị (Y-axis)
- **Time axis**: Trục thời gian (X-axis)

**Thư viện**: PyQt6-Charts

### 4.3. Forms và Input Fields

**Sử dụng trong:**
- **Rules Tab**: Form thêm rule mới

**Widgets:**
- QLineEdit: Input text (IP, Port, etc.)
- QComboBox: Dropdown (Protocol, Action, Interface, State)
- QPushButton: Nút bấm (Add Rule, Search, Delete)

### 4.4. Labels (QLabel)

**Sử dụng trong:**
- **Graph Tab**: Hiển thị metrics hiện tại
- **Sandbox Tab**: Hiển thị metrics

**Tính năng:**
- Real-time updates
- Formatted text (số, phần trăm)
- Color coding (có thể)

---

## 5. REAL-TIME UPDATES

### 5.1. Refresh Timers

**Rules Table:**
- **Interval**: 1.5 giây (1500ms)
- **Handler**: `RulesTableHandlerAPI.refresh_rules_table()`
- **Action**: Lấy danh sách rules từ API và cập nhật bảng

**Monitoring Data:**
- **Interval**: 2 giây (2000ms)
- **Handler**: `SystemMonitorAPI.update_stats()`
- **Action**: Lấy monitoring data từ API và cập nhật labels + charts

**Log Tab:**
- **Real-time**: Sử dụng QProcess với `tail -f`
- **Action**: Đọc log mới từ `/var/log/kern.log` ngay khi có

### 5.2. Data Flow

```
Service (Backend)
    ↓ (mỗi 2s)
Monitoring Thread → monitoring_data
    ↓
API Endpoint: GET /api/monitoring/data
    ↓
API Client (requests)
    ↓
SystemMonitorAPI.update_stats()
    ↓
Update Labels + Emit Signal
    ↓
Chart Manager → Update Charts
```

---

## 6. USER INTERACTIONS

### 6.1. Mouse Interactions

- **Click checkbox**: Chọn/deselect rule để xóa
- **Click button**: Thực hiện action (Add, Search, Delete)
- **Click tab**: Chuyển đổi giữa các tab
- **Scroll table**: Cuộn xem dữ liệu

### 6.2. Keyboard Interactions

- **Enter trong search**: Tìm kiếm rules
- **Tab**: Di chuyển giữa các input fields
- **Escape**: Đóng dialog (nếu có)

### 6.3. Visual Feedback

- **Button hover**: Thay đổi màu khi di chuột
- **Tab selection**: Highlight tab được chọn
- **Table selection**: Highlight dòng được chọn
- **Alert colors**: Màu đỏ cho log tấn công

---

## 7. ERROR HANDLING VÀ NOTIFICATIONS

### 7.1. Error Dialogs

**Service Connection Error:**
- Hiển thị khi không kết nối được service
- Message: "Không thể kết nối đến Firewall Service"
- Hướng dẫn: Cách khởi động service

**API Error:**
- Hiển thị khi API request thất bại
- Message: Chi tiết lỗi từ API
- Action: Retry hoặc kiểm tra service

### 7.2. Desktop Notifications

**Sử dụng**: `notify2` library

**Các loại thông báo:**
- **Attack Alert**: Khi phát hiện tấn công
- **Malware Alert**: Khi phát hiện malware/anomaly
- **Service Alert**: Khi phát hiện service lạ

**Thông tin:**
- Title: Loại cảnh báo
- Message: Chi tiết (IP, thời gian, mức độ)
- Urgency: Low/Medium/High/Critical

### 7.3. Console Logging

**In ra console:**
- API requests/responses
- Errors và exceptions
- Debug information
- Alert messages

---

## 8. STYLING VÀ THEME

### 8.1. Tab Styling

**Custom stylesheet** trong `main.ui`:
- Gradient backgrounds
- Border radius
- Hover effects
- Selected state highlighting

### 8.2. Table Styling

- **Alternating colors**: Xám trắng xen kẽ
- **Header styling**: Bold, background color
- **Selection color**: Highlight màu xanh

### 8.3. Chart Styling

- **Line colors**: Màu khác nhau cho mỗi series
- **Grid lines**: Đường lưới mờ
- **Axis labels**: Font và màu tùy chỉnh
- **Animation**: Smooth transitions

---

## 9. RESPONSIVE DESIGN

### 9.1. Window Resizing

- **Tables**: Auto-resize columns
- **Charts**: Auto-resize với window
- **Layouts**: Flexible layouts (QVBoxLayout, QHBoxLayout, QGridLayout)

### 9.2. Scroll Areas

- **Tables**: Vertical và horizontal scrollbars
- **Auto-scroll**: Tự động cuộn khi có dữ liệu mới (Log tab)

---

## 10. ACCESSIBILITY

### 10.1. Keyboard Navigation

- Tab order: Logical flow
- Shortcuts: Có thể thêm keyboard shortcuts
- Focus indicators: Visual feedback khi focus

### 10.2. Readability

- **Font size**: Đủ lớn để đọc
- **Colors**: Contrast tốt
- **Spacing**: Padding và margin hợp lý

---

## 11. PERFORMANCE

### 11.1. Optimization

- **Lazy loading**: Chỉ load tab khi được chọn
- **Data limiting**: Giữ tối đa 100 điểm trong charts
- **Efficient updates**: Chỉ update phần thay đổi
- **Threading**: Monitoring chạy trong thread riêng

### 11.2. Memory Management

- **Timer cleanup**: Tự động cleanup khi đóng window
- **Chart data**: Giới hạn số điểm dữ liệu
- **Table rows**: Không giới hạn nhưng có thể pagination

---

## 12. TỔNG KẾT

### 12.1. Các Tab Chính

1. **Log Tab**: Kernel logs, phát hiện tấn công, chặn IP tự động
2. **Rules Tab**: Quản lý firewall rules, thêm/xóa/tìm kiếm
3. **Available Rules Tab**: Quản lý rule templates
4. **Sandbox Tab**: Giám sát container/sandbox
5. **Graph Tab**: Biểu đồ real-time cho host và sandbox

### 12.2. Tính năng Nổi bật

- ✅ Real-time updates (1.5-2 giây)
- ✅ Multi-chain firewall rules support
- ✅ Automatic attack detection và blocking
- ✅ Beautiful charts với animation
- ✅ Desktop notifications
- ✅ Error handling và user feedback
- ✅ Responsive và user-friendly

### 12.3. Công nghệ

- **PyQt6**: GUI framework
- **PyQt6-Charts**: Real-time charts
- **Qt Designer**: UI design
- **REST API**: Communication với backend
- **Threading**: Background monitoring

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**Tác giả**: UI Documentation

