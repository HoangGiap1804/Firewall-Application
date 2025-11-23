# Firewall Service

Service daemon chạy backend logic và cung cấp REST API để giao diện điều khiển.

## Cài đặt

### 1. Cài đặt dependencies

```bash
cd /home/nqim/PBL6
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Cài đặt service vào systemd

```bash
cd service
sudo ./install_service.sh install
```

### 3. Khởi động service

```bash
sudo systemctl start firewall-service
```

### 4. Kiểm tra trạng thái

```bash
sudo systemctl status firewall-service
```

## Sử dụng

### Quản lý service

```bash
# Khởi động
sudo ./install_service.sh start

# Dừng
sudo ./install_service.sh stop

# Xem trạng thái
sudo ./install_service.sh status

# Xem logs
sudo ./install_service.sh logs

# Gỡ cài đặt
sudo ./install_service.sh uninstall
```

### Chạy thủ công (không dùng systemd)

```bash
cd /home/nqim/PBL6
source venv/bin/activate
python3 service/firewall_service.py
```

## API Endpoints

Service chạy trên `http://127.0.0.1:5000`

### Health Check
```
GET /api/health
```

### Monitoring
```
POST /api/monitoring/start    # Bắt đầu monitoring
POST /api/monitoring/stop     # Dừng monitoring
GET  /api/monitoring/data     # Lấy dữ liệu monitoring
```

### Rules Management
```
GET  /api/rules/list          # Lấy danh sách rules
POST /api/rules/add           # Thêm rule mới
POST /api/rules/delete        # Xóa rule
POST /api/rules/delete-many   # Xóa nhiều rules
GET  /api/rules/search        # Tìm kiếm rules
```

## Sử dụng với GUI

### Chạy GUI với API Service

```bash
cd /home/nqim/PBL6
source venv/bin/activate
python3 main_qt_api.py
```

GUI sẽ tự động kết nối đến service và sử dụng API để điều khiển.

### Chạy GUI trực tiếp (không dùng service)

```bash
python3 main_qt.py
```

## Cấu trúc

- `firewall_service.py` - Service daemon với REST API
- `api_client.py` - Client để gọi API từ Python
- `install_service.sh` - Script cài đặt và quản lý service
- `firewall-service.service` - Systemd service file

## Lưu ý

- Service cần chạy với quyền root để thao tác iptables
- Service tự động bắt đầu monitoring khi khởi động
- API chỉ lắng nghe trên localhost (127.0.0.1) để bảo mật

