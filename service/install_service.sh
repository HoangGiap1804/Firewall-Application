#!/bin/bash
# Script cài đặt và quản lý Firewall Service

SERVICE_NAME="firewall-service"
SERVICE_FILE="firewall-service.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

case "$1" in
    install)
        echo "Cài đặt Firewall Service..."
        
        # Kiểm tra quyền root
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 install"
            exit 1
        fi
        
        # Tạo service file với đường dẫn đúng
        cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Firewall Management Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/service/firewall_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        
        # Reload systemd
        systemctl daemon-reload
        
        # Enable service
        systemctl enable "$SERVICE_NAME"
        
        echo "✅ Đã cài đặt service. Sử dụng:"
        echo "   sudo systemctl start $SERVICE_NAME    # Khởi động service"
        echo "   sudo systemctl stop $SERVICE_NAME     # Dừng service"
        echo "   sudo systemctl status $SERVICE_NAME   # Xem trạng thái"
        echo "   sudo journalctl -u $SERVICE_NAME -f   # Xem logs"
        ;;
    
    uninstall)
        echo "Gỡ cài đặt Firewall Service..."
        
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 uninstall"
            exit 1
        fi
        
        systemctl stop "$SERVICE_NAME" 2>/dev/null
        systemctl disable "$SERVICE_NAME" 2>/dev/null
        rm -f "$SERVICE_PATH"
        systemctl daemon-reload
        
        echo "✅ Đã gỡ cài đặt service"
        ;;
    
    start)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 start"
            exit 1
        fi
        systemctl start "$SERVICE_NAME"
        systemctl status "$SERVICE_NAME"
        ;;
    
    stop)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 stop"
            exit 1
        fi
        systemctl stop "$SERVICE_NAME"
        ;;
    
    restart)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 restart"
            exit 1
        fi
        echo "🔄 Đang restart service để load code mới..."
        systemctl restart "$SERVICE_NAME"
        sleep 1
        systemctl status "$SERVICE_NAME"
        echo ""
        echo "✅ Service đã được restart. Code mới đã được load."
        echo "📋 Xem logs: sudo $0 logs"
        ;;
    
    reload)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 reload"
            exit 1
        fi
        echo "🔄 Đang reload service (graceful restart)..."
        systemctl daemon-reload
        systemctl restart "$SERVICE_NAME"
        sleep 1
        systemctl status "$SERVICE_NAME"
        echo ""
        echo "✅ Service đã được reload."
        ;;
    
    status)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 status"
            exit 1
        fi
        systemctl status "$SERVICE_NAME"
        ;;
    
    logs)
        if [ "$EUID" -ne 0 ]; then 
            echo "Vui lòng chạy với quyền sudo: sudo $0 logs"
            exit 1
        fi
        journalctl -u "$SERVICE_NAME" -f
        ;;
    
    *)
        echo "Usage: $0 {install|uninstall|start|stop|restart|reload|status|logs}"
        echo ""
        echo "Commands:"
        echo "  install   - Cài đặt service vào systemd"
        echo "  uninstall - Gỡ cài đặt service"
        echo "  start     - Khởi động service"
        echo "  stop      - Dừng service"
        echo "  restart   - Restart service (load code mới) ⭐"
        echo "  reload    - Reload service và systemd config"
        echo "  status    - Xem trạng thái service"
        echo "  logs      - Xem logs của service (theo dõi real-time)"
        echo ""
        echo "💡 Sau khi sửa code backend, chạy: sudo $0 restart"
        exit 1
        ;;
esac

