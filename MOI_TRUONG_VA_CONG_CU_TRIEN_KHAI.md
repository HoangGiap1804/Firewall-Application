# MÔI TRƯỜNG VÀ CÔNG CỤ TRIỂN KHAI
## Hệ thống Quản lý Firewall với Giám sát Hệ thống

---

## 1. TỔNG QUAN MÔI TRƯỜNG TRIỂN KHAI

### 1.1. Kiến trúc Hệ thống

Hệ thống được triển khai theo mô hình **Client-Server** với 2 thành phần chính:

1. **Backend Service (Daemon)**
   - Chạy như một systemd service với quyền root
   - Cung cấp REST API qua Flask
   - Xử lý logic nghiệp vụ và tương tác với iptables
   - Giám sát hệ thống liên tục trong background thread

2. **Frontend GUI (Client)**
   - Giao diện đồ họa PyQt6
   - Giao tiếp với backend qua REST API
   - Hiển thị dữ liệu real-time

### 1.2. Mô hình Triển khai

```
┌─────────────────────────────────────────┐
│         Frontend GUI (PyQt6)            │
│         (main_qt_api.py)                │
│                                         │
│  - Quản lý Rules                        │
│  - Giám sát Hệ thống                    │
│  - Hiển thị Biểu đồ                     │
└──────────────┬──────────────────────────┘
               │ HTTP REST API
               │ (localhost:5000)
               ▼
┌─────────────────────────────────────────┐
│    Backend Service (Flask API)          │
│    (firewall_service.py)                │
│    [systemd service - root]             │
│                                         │
│  - REST API Endpoints                   │
│  - iptables Management                  │
│  - System Monitoring                    │
│  - Anomaly Detection                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         System Resources                │
│                                         │
│  - iptables (firewall rules)            │
│  - cgroup (container monitoring)        │
│  - psutil (system metrics)              │
│  - systemd (service management)         │
└─────────────────────────────────────────┘
```

---

## 2. YÊU CẦU MÔI TRƯỜNG HỆ THỐNG

### 2.1. Hệ điều hành

- **Hệ điều hành**: Linux (Ubuntu/Debian được khuyến nghị)
- **Kernel**: Hỗ trợ cgroup v2 (cho container monitoring)
- **Init System**: systemd (bắt buộc cho service daemon)
- **Architecture**: x86_64 hoặc ARM64

**Kiểm tra hệ thống:**
```bash
# Kiểm tra OS
lsb_release -a

# Kiểm tra kernel version
uname -r

# Kiểm tra systemd
systemctl --version

# Kiểm tra cgroup v2
mount | grep cgroup
```

### 2.2. Python Environment

- **Python Version**: Python 3.12 (hoặc Python 3.10+)
- **Virtual Environment**: venv (khuyến nghị)
- **Package Manager**: pip

**Kiểm tra Python:**
```bash
python3 --version
which python3
```

### 2.3. Quyền Truy cập

- **Root Access**: Bắt buộc để thao tác iptables
- **Sudo Privileges**: Cần để cài đặt và quản lý service
- **Network Access**: Chỉ cần localhost (127.0.0.1)

**Kiểm tra quyền:**
```bash
# Kiểm tra quyền root
sudo -v

# Kiểm tra iptables
sudo iptables -L
```

### 2.4. Dependencies Hệ thống

**Các công cụ hệ thống cần thiết:**

```bash
# Cài đặt các công cụ cơ bản
sudo apt update
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    iptables \
    systemd \
    inotify-tools \
    net-tools \
    iproute2

# Kiểm tra iptables
sudo iptables --version

# Kiểm tra systemd
systemctl --version
```

### 2.5. Container Support (Tùy chọn)

Nếu sử dụng tính năng giám sát container:

- **Container Runtime**: systemd-nspawn hoặc Docker
- **Container Name**: "ubuntu" (có thể cấu hình trong code)
- **Cgroup Path**: `/sys/fs/cgroup/machine.slice/machine-ubuntu.scope`

**Kiểm tra container:**
```bash
# Kiểm tra systemd-nspawn
machinectl list

# Kiểm tra Docker (nếu dùng)
docker ps
```

---

## 3. CÀI ĐẶT MÔI TRƯỜNG PHÁT TRIỂN

### 3.1. Chuẩn bị Môi trường

**Bước 1: Clone hoặc tải dự án**
```bash
cd /home/nqim/PBL6
```

**Bước 2: Tạo Virtual Environment**
```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate

# Kiểm tra Python trong venv
which python3
```

**Bước 3: Cài đặt Dependencies**
```bash
# Cài đặt các package Python
pip install --upgrade pip
pip install -r requirements.txt
```

**Bước 4: Kiểm tra Cài đặt**
```bash
# Kiểm tra các package đã cài
pip list

# Kiểm tra Flask
python3 -c "import flask; print(flask.__version__)"

# Kiểm tra PyQt6
python3 -c "import PyQt6; print(PyQt6.__version__)"
```

### 3.2. Cấu trúc Dependencies

**File `requirements.txt` chứa:**

```
PySide6
QtWidgets 
uic
PyQt6>=6.9.0,<6.10.0
PyQt6-Charts>=6.9.0,<6.10.0
python-dotenv
psutil
notify2
flask>=2.0.0
flask-cors>=3.0.0
requests>=2.25.0
```

**Mô tả các package chính:**

- **PyQt6 / PySide6**: Framework GUI cho giao diện đồ họa
- **PyQt6-Charts**: Thư viện vẽ biểu đồ real-time
- **Flask**: Framework REST API cho backend service
- **flask-cors**: Hỗ trợ CORS cho API
- **psutil**: Thu thập thông tin hệ thống (CPU, RAM, Network, etc.)
- **notify2**: Gửi desktop notifications
- **requests**: HTTP client để gọi API
- **python-dotenv**: Quản lý biến môi trường

---

## 4. CÔNG CỤ TRIỂN KHAI

### 4.1. Systemd Service

Hệ thống sử dụng **systemd** để quản lý backend service như một daemon.

#### 4.1.1. Service File

**File**: `service/firewall-service.service`

```ini
[Unit]
Description=Firewall Management Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/nqim/PBL6
Environment="PATH=/home/nqim/PBL6/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/nqim/PBL6/venv/bin/python3 /home/nqim/PBL6/service/firewall_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Giải thích:**
- **Type=simple**: Service chạy một process đơn giản
- **User=root**: Chạy với quyền root để thao tác iptables
- **WorkingDirectory**: Thư mục làm việc của dự án
- **Environment**: Đường dẫn Python trong venv
- **ExecStart**: Lệnh khởi chạy service
- **Restart=always**: Tự động restart khi crash
- **RestartSec=10**: Đợi 10 giây trước khi restart

#### 4.1.2. Installation Script

**File**: `service/install_service.sh`

Script bash để quản lý service:

```bash
# Cài đặt service
sudo ./install_service.sh install

# Khởi động service
sudo ./install_service.sh start

# Dừng service
sudo ./install_service.sh stop

# Restart service (load code mới)
sudo ./install_service.sh restart

# Xem trạng thái
sudo ./install_service.sh status

# Xem logs
sudo ./install_service.sh logs

# Gỡ cài đặt
sudo ./install_service.sh uninstall
```

**Các chức năng của script:**

1. **install**: Cài đặt service vào systemd
2. **uninstall**: Gỡ cài đặt service
3. **start**: Khởi động service
4. **stop**: Dừng service
5. **restart**: Restart service (quan trọng sau khi sửa code)
6. **reload**: Reload service và config
7. **status**: Xem trạng thái service
8. **logs**: Xem logs real-time

### 4.2. Flask REST API Service

#### 4.2.1. Cấu hình Service

**File**: `service/firewall_service.py`

**Cấu hình mặc định:**
- **Host**: `127.0.0.1` (localhost only - bảo mật)
- **Port**: `5000`
- **Debug**: `False` (production mode)
- **Threaded**: `True` (hỗ trợ multiple requests)

**Khởi động service:**
```python
app.run(host=SERVICE_HOST, port=SERVICE_PORT, debug=False, threaded=True)
```

#### 4.2.2. API Endpoints

**Health Check:**
```
GET /api/health
```

**Monitoring:**
```
POST /api/monitoring/start    # Bắt đầu monitoring
POST /api/monitoring/stop     # Dừng monitoring
GET  /api/monitoring/data     # Lấy dữ liệu monitoring
```

**Rules Management:**
```
GET  /api/rules/list          # Lấy danh sách rules
POST /api/rules/add           # Thêm rule mới
POST /api/rules/delete        # Xóa một rule
POST /api/rules/delete-many   # Xóa nhiều rules
GET  /api/rules/search?q=...  # Tìm kiếm rules
```

### 4.3. API Client Library

**File**: `service/api_client.py`

Thư viện Python để giao tiếp với API:

```python
from service.api_client import get_client

client = get_client()

# Health check
if client.health_check():
    print("Service is running")

# Lấy danh sách rules
rules = client.list_rules()

# Thêm rule
client.add_rule(ip="192.168.1.1", protocol="tcp", action="DROP")

# Lấy monitoring data
data = client.get_monitoring_data()
```

**Tính năng:**
- Singleton pattern
- Error handling (ConnectionError, TimeoutError)
- Timeout: 5 giây
- JSON serialization tự động

---

## 5. QUY TRÌNH TRIỂN KHAI

### 5.1. Triển khai Lần đầu

**Bước 1: Chuẩn bị Môi trường**
```bash
# Cài đặt dependencies hệ thống
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iptables systemd inotify-tools

# Tạo virtual environment
cd /home/nqim/PBL6
python3 -m venv venv
source venv/bin/activate

# Cài đặt Python packages
pip install -r requirements.txt
```

**Bước 2: Cài đặt Service**
```bash
cd service
sudo ./install_service.sh install
```

**Bước 3: Khởi động Service**
```bash
sudo ./install_service.sh start
```

**Bước 4: Kiểm tra Service**
```bash
# Kiểm tra trạng thái
sudo systemctl status firewall-service

# Kiểm tra API
curl http://127.0.0.1:5000/api/health

# Xem logs
sudo ./install_service.sh logs
```

**Bước 5: Chạy GUI**
```bash
cd /home/nqim/PBL6
source venv/bin/activate
python3 main_qt_api.py
```

### 5.2. Cập nhật Code

**Quy trình sau khi sửa code:**

1. **Sửa code** trong `backend/` hoặc `service/`
2. **Restart service** để load code mới:
   ```bash
   cd service
   sudo ./install_service.sh restart
   ```
3. **Kiểm tra logs** để đảm bảo không có lỗi:
   ```bash
   sudo ./install_service.sh logs
   ```
4. **Test** qua GUI hoặc API

**⚠️ LƯU Ý QUAN TRỌNG:**
- **PHẢI restart service** sau mỗi lần sửa code backend
- Service không tự động reload code mới
- GUI không cần restart (chỉ cần đóng và mở lại)

### 5.3. Debugging và Troubleshooting

#### 5.3.1. Kiểm tra Service Status

```bash
# Xem trạng thái chi tiết
sudo systemctl status firewall-service

# Xem logs real-time
sudo journalctl -u firewall-service -f

# Xem logs gần đây
sudo journalctl -u firewall-service -n 50
```

#### 5.3.2. Kiểm tra API

```bash
# Health check
curl http://127.0.0.1:5000/api/health

# Lấy danh sách rules
curl http://127.0.0.1:5000/api/rules/list

# Lấy monitoring data
curl http://127.0.0.1:5000/api/monitoring/data
```

#### 5.3.3. Kiểm tra Port

```bash
# Kiểm tra port 5000 có bị chiếm không
sudo netstat -tlnp | grep 5000
# hoặc
sudo ss -tlnp | grep 5000
```

#### 5.3.4. Chạy Service Thủ công (Debug Mode)

```bash
# Dừng systemd service
sudo systemctl stop firewall-service

# Chạy thủ công với output
cd /home/nqim/PBL6
source venv/bin/activate
python3 service/firewall_service.py
```

### 5.4. Gỡ Cài đặt

```bash
# Dừng service
sudo ./install_service.sh stop

# Gỡ cài đặt
sudo ./install_service.sh uninstall

# Xóa virtual environment (nếu cần)
rm -rf venv
```

---

## 6. CẤU HÌNH VÀ TÙY CHỈNH

### 6.1. Cấu hình Service

**Thay đổi Port API:**

Sửa trong `service/firewall_service.py`:
```python
SERVICE_PORT = 5000  # Đổi thành port khác
```

Sau đó restart service:
```bash
sudo ./install_service.sh restart
```

**Thay đổi Container Name:**

Sửa trong `service/firewall_service.py`:
```python
CONTAINER_NAME = "ubuntu"  # Đổi thành tên container khác
CGROUP_BASE = f"/sys/fs/cgroup/machine.slice/machine-{CONTAINER_NAME}.scope"
```

### 6.2. Cấu hình Monitoring Thresholds

**File**: `service/firewall_service.py`

```python
RAM_SPIKE_MB = 150          # Ngưỡng tăng RAM (MB)
CPU_SPIKE_PERCENT = 40      # Ngưỡng CPU spike (%)
CPU_MAX_PERCENT = 85        # Ngưỡng cảnh báo CPU (%)
SERVICE_ALERT_COOLDOWN = 60 # Thời gian giữa các cảnh báo (giây)
```

### 6.3. Cấu hình Refresh Rate

**Rules Table Refresh:**
- File: `backend/rules/core/iptables_model.py`
- Mặc định: 1.5 giây

**Monitoring Data Refresh:**
- File: `service/firewall_service.py`
- Mặc định: 2 giây (trong `monitoring_loop()`)

---

## 7. BẢO MẬT

### 7.1. Quyền Truy cập

- **Service chạy với quyền root**: Cần thiết để thao tác iptables
- **API chỉ lắng nghe localhost**: Bảo vệ khỏi truy cập từ bên ngoài
- **Không có authentication**: API chỉ accessible từ localhost

### 7.2. Network Security

- **Host**: `127.0.0.1` (localhost only)
- **Port**: `5000` (có thể thay đổi)
- **CORS**: Chỉ cho phép từ localhost

### 7.3. Best Practices

1. **Không expose API ra ngoài**: Giữ `SERVICE_HOST = "127.0.0.1"`
2. **Sử dụng firewall**: Cấu hình iptables để block port 5000 từ bên ngoài
3. **Regular updates**: Cập nhật dependencies thường xuyên
4. **Log monitoring**: Theo dõi logs để phát hiện bất thường

---

## 8. MONITORING VÀ LOGGING

### 8.1. Service Logs

**Xem logs qua systemd:**
```bash
# Logs real-time
sudo journalctl -u firewall-service -f

# Logs gần đây
sudo journalctl -u firewall-service -n 100

# Logs theo thời gian
sudo journalctl -u firewall-service --since "1 hour ago"
```

**Xem logs qua script:**
```bash
sudo ./install_service.sh logs
```

### 8.2. Application Logs

Service in logs ra stdout/stderr, được systemd journal capture:
- API requests
- Errors và exceptions
- Monitoring updates
- Rule operations

### 8.3. System Monitoring

Service tự động giám sát:
- CPU usage
- RAM usage
- Disk I/O
- Network traffic
- Temperature
- Running services

---

## 9. BACKUP VÀ RESTORE

### 9.1. Backup iptables Rules

```bash
# Backup rules hiện tại
sudo iptables-save > iptables_backup.txt

# Backup metadata
cp rules_meta.json rules_meta_backup.json
```

### 9.2. Restore iptables Rules

```bash
# Restore rules
sudo iptables-restore < iptables_backup.txt

# Restore metadata
cp rules_meta_backup.json rules_meta.json
```

### 9.3. Backup Service Configuration

```bash
# Backup service file
sudo cp /etc/systemd/system/firewall-service.service firewall-service.service.backup

# Backup toàn bộ dự án
tar -czf pbl6_backup_$(date +%Y%m%d).tar.gz /home/nqim/PBL6
```

---

## 10. TROUBLESHOOTING

### 10.1. Service không khởi động

**Nguyên nhân và giải pháp:**

1. **Lỗi Python path:**
   ```bash
   # Kiểm tra Python trong venv
   ls -la venv/bin/python3
   
   # Sửa service file nếu cần
   sudo nano /etc/systemd/system/firewall-service.service
   ```

2. **Lỗi permissions:**
   ```bash
   # Kiểm tra quyền file
   ls -la service/firewall_service.py
   
   # Đảm bảo có quyền thực thi
   chmod +x service/firewall_service.py
   ```

3. **Lỗi dependencies:**
   ```bash
   # Kiểm tra dependencies
   source venv/bin/activate
   pip list
   
   # Cài đặt lại nếu cần
   pip install -r requirements.txt
   ```

### 10.2. GUI không kết nối được Service

**Kiểm tra:**

1. **Service có đang chạy:**
   ```bash
   sudo systemctl status firewall-service
   ```

2. **Port có bị chiếm:**
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

3. **API có hoạt động:**
   ```bash
   curl http://127.0.0.1:5000/api/health
   ```

4. **Firewall block:**
   ```bash
   sudo iptables -L -n | grep 5000
   ```

### 10.3. Lỗi iptables Permission Denied

**Giải pháp:**

```bash
# Đảm bảo service chạy với root
sudo systemctl status firewall-service | grep User

# Kiểm tra quyền sudo
sudo -v

# Test iptables
sudo iptables -L
```

### 10.4. Monitoring không hoạt động

**Kiểm tra:**

1. **Container có tồn tại:**
   ```bash
   machinectl list
   ```

2. **Cgroup path đúng:**
   ```bash
   ls -la /sys/fs/cgroup/machine.slice/machine-ubuntu.scope
   ```

3. **psutil có hoạt động:**
   ```bash
   python3 -c "import psutil; print(psutil.cpu_percent())"
   ```

---

## 11. TÀI NGUYÊN VÀ THAM KHẢO

### 11.1. Tài liệu Dự án

- `README.md`: Hướng dẫn tổng quan
- `SERVICE_GUIDE.md`: Hướng dẫn sử dụng service
- `service/README.md`: Tài liệu service chi tiết
- `PHAN_TICH_YEU_CAU_HE_THONG.md`: Phân tích yêu cầu hệ thống

### 11.2. Tài liệu Công nghệ

- **Flask**: https://flask.palletsprojects.com/
- **PyQt6**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **systemd**: https://www.freedesktop.org/software/systemd/man/
- **iptables**: https://netfilter.org/documentation/

### 11.3. Scripts và Tools

- `service/install_service.sh`: Script quản lý service
- `scripts/send-to-sandbox.sh`: Script gửi file vào sandbox
- `service/api_client.py`: API client library

---

## 12. CHECKLIST TRIỂN KHAI

### 12.1. Trước khi Triển khai

- [ ] Hệ điều hành Linux với systemd
- [ ] Python 3.10+ đã cài đặt
- [ ] Quyền root/sudo
- [ ] iptables đã cài đặt
- [ ] Network interface hoạt động

### 12.2. Cài đặt

- [ ] Tạo virtual environment
- [ ] Cài đặt dependencies (`pip install -r requirements.txt`)
- [ ] Cài đặt service (`sudo ./install_service.sh install`)
- [ ] Khởi động service (`sudo ./install_service.sh start`)
- [ ] Kiểm tra service status
- [ ] Test API (`curl http://127.0.0.1:5000/api/health`)

### 12.3. Sau khi Triển khai

- [ ] Service chạy ổn định
- [ ] API trả về đúng response
- [ ] GUI kết nối được service
- [ ] Monitoring hoạt động
- [ ] Rules management hoạt động
- [ ] Logs không có lỗi

---

**Ngày tạo**: 2025-01-27  
**Phiên bản**: 1.0  
**Tác giả**: Deployment Documentation

