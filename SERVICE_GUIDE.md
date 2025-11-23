# Hướng dẫn sử dụng Firewall Service

## Tổng quan

Dự án đã được tách thành 2 phần:
1. **Service daemon** - Chạy backend logic và cung cấp REST API
2. **Giao diện GUI** - Gọi và điều khiển service qua API

## Cài đặt

### Bước 1: Cài đặt dependencies

```bash
cd /home/nqim/PBL6
source venv/bin/activate
pip install -r requirements.txt
```

### Bước 2: Cài đặt service vào systemd

```bash
cd service
sudo ./install_service.sh install
```

### Bước 3: Khởi động service

```bash
sudo systemctl start firewall-service
```

### Bước 4: Kiểm tra service đang chạy

```bash
sudo systemctl status firewall-service
```

## Sử dụng

### Chạy GUI với Service (Khuyến nghị)

```bash
cd /home/nqim/PBL6
source venv/bin/activate
python3 main_qt_api.py
```

GUI sẽ tự động kết nối đến service và sử dụng API để:
- Xem danh sách rules
- Thêm/xóa rules
- Xem monitoring data (CPU, RAM, Network, etc.)

### Chạy GUI trực tiếp (Không dùng service)

```bash
python3 main_qt.py
```

## Quản lý Service

### Các lệnh quản lý

```bash
cd service

# Khởi động service
sudo ./install_service.sh start

# Dừng service
sudo ./install_service.sh stop

# Xem trạng thái
sudo ./install_service.sh status

# Xem logs (theo dõi real-time)
sudo ./install_service.sh logs

# Gỡ cài đặt
sudo ./install_service.sh uninstall
```

### Chạy service thủ công (không dùng systemd)

```bash
cd /home/nqim/PBL6
source venv/bin/activate
python3 service/firewall_service.py
```

Service sẽ chạy trên `http://127.0.0.1:5000`

## API Endpoints

Service cung cấp các API endpoints sau:

### Health Check
- `GET /api/health` - Kiểm tra service có hoạt động không

### Monitoring
- `POST /api/monitoring/start` - Bắt đầu monitoring
- `POST /api/monitoring/stop` - Dừng monitoring
- `GET /api/monitoring/data` - Lấy dữ liệu monitoring (CPU, RAM, Network, etc.)

### Rules Management
- `GET /api/rules/list` - Lấy danh sách tất cả rules
- `POST /api/rules/add` - Thêm rule mới
- `POST /api/rules/delete` - Xóa một rule
- `POST /api/rules/delete-many` - Xóa nhiều rules
- `GET /api/rules/search?q=<query>` - Tìm kiếm rules

## Cấu trúc Files

```
PBL6/
├── service/
│   ├── firewall_service.py      # Service daemon với REST API
│   ├── api_client.py            # Client để gọi API
│   ├── install_service.sh       # Script cài đặt service
│   ├── firewall-service.service # Systemd service file
│   └── README.md                # Tài liệu chi tiết
├── backend/
│   ├── rules/handlers/
│   │   ├── rules_table_handler_api.py  # Handler sử dụng API
│   │   └── add_rule_handler_api.py     # Handler sử dụng API
│   └── monitoring/
│       └── system_monitor_api.py       # Monitor sử dụng API
├── main_qt.py                   # GUI trực tiếp (không dùng service)
└── main_qt_api.py              # GUI sử dụng API service
```

## Lưu ý

1. **Quyền root**: Service cần chạy với quyền root để thao tác iptables
2. **Tự động khởi động**: Service tự động bắt đầu monitoring khi khởi động
3. **Bảo mật**: API chỉ lắng nghe trên localhost (127.0.0.1) để bảo mật
4. **Kết nối**: Nếu GUI không kết nối được, kiểm tra service có đang chạy không:
   ```bash
   sudo systemctl status firewall-service
   ```

## Troubleshooting

### Service không khởi động được

```bash
# Xem logs chi tiết
sudo journalctl -u firewall-service -n 50

# Kiểm tra đường dẫn Python
which python3
```

### GUI không kết nối được service

1. Kiểm tra service có đang chạy:
   ```bash
   sudo systemctl status firewall-service
   ```

2. Kiểm tra port 5000 có bị chiếm không:
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

3. Test API trực tiếp:
   ```bash
   curl http://127.0.0.1:5000/api/health
   ```

### Lỗi permission denied

Đảm bảo service chạy với quyền root:
```bash
sudo systemctl start firewall-service
```

