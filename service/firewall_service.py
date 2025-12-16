#!/usr/bin/env python3
"""
Firewall Service Daemon
Service chạy backend logic và cung cấp REST API để giao diện điều khiển

LƯU Ý: 
- Service phải chạy với quyền root (User=root trong systemd service file)
- Tất cả lệnh iptables trong service đều sử dụng "sudo" để đảm bảo quyền thực thi
- Khi chạy với root, sudo sẽ tự động nhận ra và không yêu cầu password
"""

import os
import sys
import time
import json
import subprocess
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import psutil
import re

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rules.core.rule_input import get_input_rules, get_all_chains_rules, get_group_map, normalize_rule_key
from backend.notifications import send_malware_alert, send_performance_alert

app = Flask(__name__)
CORS(app)  # Cho phép CORS để GUI có thể gọi API

# Cấu hình
CONTAINER_NAME = "ubuntu"
CGROUP_BASE = f"/sys/fs/cgroup/machine.slice/machine-{CONTAINER_NAME}.scope"
SERVICE_PORT = 5000
SERVICE_HOST = "127.0.0.1"

# Global state
monitoring_active = False
monitoring_thread = None
monitoring_data = {
    "cpu_percent": 0,
    "ram_percent": 0,
    "ram_mb": 0,
    "temperature": 0,
    "network_rx": 0,
    "network_tx": 0,
    "disk_read_mb": 0,
    "disk_write_mb": 0,
    "network_procs": 0,
    "services_count": 0,
    "alerts": []
}

# Monitoring state
prev_cpu_usage = 0
prev_time = time.time()
prev_net_rx = 0
prev_net_tx = 0

CPU_MAX_PERCENT = 85
SERVICE_ALERT_COOLDOWN = 60
last_service_alert_time = 0
last_ram_alert_time = 0


def find_veth():
    """Tìm interface veth tương ứng với container"""
    try:
        out = subprocess.check_output(["ip", "link"], text=True)
        for line in out.splitlines():
            if f"veth{CONTAINER_NAME}" in line:
                return line.split(":")[1].strip()
    except:
        pass
    return None


def update_monitoring():
    """Cập nhật dữ liệu monitoring"""
    global prev_cpu_usage, prev_time, prev_net_rx, prev_net_tx
    global last_service_alert_time, last_ram_alert_time
    
    try:
        # CPU
        cpu_file = os.path.join(CGROUP_BASE, "cpu.stat")
        if os.path.exists(cpu_file):
            with open(cpu_file) as f:
                data = dict(line.strip().split() for line in f.readlines())
            usage_usec = int(data.get("usage_usec", 0))
            now = time.time()
            delta_time = now - prev_time
            delta_usage = usage_usec - prev_cpu_usage
            cpu_percent = (delta_usage / 1e6) / delta_time * 100 / os.cpu_count()
            monitoring_data["cpu_percent"] = cpu_percent
            prev_cpu_usage = usage_usec
            prev_time = now
            
            # Check CPU spike
            if cpu_percent > CPU_MAX_PERCENT:
                monitoring_data["alerts"].append({
                    "type": "CPU",
                    "message": f"CPU vượt ngưỡng: {cpu_percent:.1f}%",
                    "severity": "high",
                    "timestamp": time.time()
                })
                send_performance_alert(resource_type="CPU", usage_value=f"{cpu_percent:.1f}%", severity="high")
        
        # RAM
        mem_file = os.path.join(CGROUP_BASE, "memory.current")
        if os.path.exists(mem_file):
            with open(mem_file) as f:
                used_bytes = int(f.read().strip())
            with open("/proc/meminfo") as f:
                total_kb = int([l.split()[1] for l in f if l.startswith("MemTotal:")][0])
            total_bytes = total_kb * 1024
            used_mb = used_bytes / (1024 ** 2)
            percent = used_bytes / total_bytes * 100
            monitoring_data["ram_percent"] = percent
            monitoring_data["ram_mb"] = used_mb
            
            # Check RAM > 90%
            if percent > 90:
                now = time.time()
                if now - last_ram_alert_time >= SERVICE_ALERT_COOLDOWN:
                    monitoring_data["alerts"].append({
                        "type": "RAM",
                        "message": f"Cảnh báo RAM cao: {percent:.1f}% (>90%)",
                        "severity": "high",
                        "timestamp": now
                    })
                    last_ram_alert_time = now
                    send_performance_alert(resource_type="RAM", usage_value=f"{percent:.1f}% (>90%)", severity="high")
            

        
        # Disk
        io_file = os.path.join(CGROUP_BASE, "io.stat")
        if os.path.exists(io_file):
            read_bytes = 0
            write_bytes = 0
            with open(io_file) as f:
                for line in f:
                    parts = line.strip().split()
                    for p in parts:
                        if p.startswith("rbytes="):
                            read_bytes += int(p.split("=")[1])
                        elif p.startswith("wbytes="):
                            write_bytes += int(p.split("=")[1])
            monitoring_data["disk_read_mb"] = read_bytes / 1e6
            monitoring_data["disk_write_mb"] = write_bytes / 1e6
        
        # Network traffic
        net_io = psutil.net_io_counters()
        current_rx = net_io.bytes_recv
        current_tx = net_io.bytes_sent
        now = time.time()
        delta_time = now - prev_time
        if delta_time > 0 and prev_net_rx > 0:
            monitoring_data["network_rx"] = (current_rx - prev_net_rx) / delta_time
            monitoring_data["network_tx"] = (current_tx - prev_net_tx) / delta_time
        prev_net_rx = current_rx
        prev_net_tx = current_tx
        
        # Network processes
        count = 0
        try:
            cmd = ["sudo", "machinectl", "shell", f"root@{CONTAINER_NAME}",
                   "/bin/ss", "-tunp", "state", "established"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            out = proc.stdout or ""
            if out:
                pids = set(re.findall(r"pid=(\d+),", out))
                count = len(pids)
        except:
            try:
                conns = psutil.net_connections(kind='inet')
                pids = set()
                for c in conns:
                    if getattr(c, "status", "").upper() == "ESTABLISHED" and c.pid:
                        pids.add(c.pid)
                count = len(pids)
            except:
                count = 0
        monitoring_data["network_procs"] = count
        
        # Temperature
        temp_celsius = None
        for i in range(10):
            try:
                temp_file = f"/sys/class/thermal/thermal_zone{i}/temp"
                if os.path.exists(temp_file):
                    with open(temp_file) as f:
                        temp_millidegrees = int(f.read().strip())
                        temp_celsius = temp_millidegrees / 1000.0
                        break
            except:
                continue
        if temp_celsius is None:
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            temp_celsius = entries[0].current
                            break
            except:
                pass
        monitoring_data["temperature"] = temp_celsius or 0
        
        # Services
        try:
            result = subprocess.run(
                ["sudo", "machinectl", "shell", f"root@{CONTAINER_NAME}",
                 "/bin/systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
                capture_output=True, text=True, timeout=5
            )
            running = len([l for l in result.stdout.splitlines() if ".service" in l])
            monitoring_data["services_count"] = running
            
            now = time.time()
            if running > 10:
                if now - last_service_alert_time >= SERVICE_ALERT_COOLDOWN:
                    monitoring_data["alerts"].append({
                        "type": "Service",
                        "message": "Service lạ phát hiện",
                        "severity": "high",
                        "timestamp": time.time()
                    })
                    last_service_alert_time = now
                    send_malware_alert(malware_type="Service", severity="high")
        except:
            pass
        
        # Giữ lại tối đa 100 alerts gần nhất
        if len(monitoring_data["alerts"]) > 100:
            monitoring_data["alerts"] = monitoring_data["alerts"][-100:]
            
    except Exception as e:
        print(f"Error in monitoring: {e}")


def monitoring_loop():
    """Vòng lặp monitoring chạy trong thread riêng"""
    global monitoring_active
    while monitoring_active:
        update_monitoring()
        time.sleep(2)  # Update mỗi 2 giây


# ==================== REST API ENDPOINTS ====================

@app.route('/api/health', methods=['GET'])
def health():
    """Kiểm tra service có hoạt động không"""
    return jsonify({"status": "ok", "service": "firewall-service"})


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """Bắt đầu monitoring"""
    global monitoring_active, monitoring_thread
    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"})


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Dừng monitoring"""
    global monitoring_active
    monitoring_active = False
    return jsonify({"status": "stopped"})


@app.route('/api/monitoring/data', methods=['GET'])
def get_monitoring_data():
    """Lấy dữ liệu monitoring hiện tại"""
    return jsonify(monitoring_data)


@app.route('/api/rules/list', methods=['GET'])
def list_rules():
    """Lấy danh sách rules từ tất cả các chains"""
    try:
        rules = get_all_chains_rules()
        group_map = get_group_map()
        # Thêm group vào mỗi rule
        for rule in rules:
            rule_key = rule.get("rule_key", "")
            normalized_key = normalize_rule_key(rule_key)
            rule["group"] = group_map.get(normalized_key, "None")
        
        # Debug: in số lượng rules và chains
        if rules:
            chains = set(r.get("chain", "INPUT") for r in rules)
            print(f"[API] Trả về {len(rules)} rule(s) từ {len(chains)} chain(s): {', '.join(sorted(chains))}")
        
        return jsonify({"rules": rules})
    except Exception as e:
        import traceback
        print(f"[API] Lỗi khi lấy rules: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/rules/add', methods=['POST'])
def add_rule():
    """Thêm rule mới"""
    try:
        data = request.json
        ip = data.get("ip", "")
        port = data.get("port", "")
        protocol = data.get("protocol", "")
        action = data.get("action", "")
        interface = data.get("interface", "")
        state = data.get("state", "")
        
        # Lấy chain từ request, default về INPUT nếu không có
        chain = data.get("chain")
        print(f"🔍 DEBUG Service: chain from data.get('chain'): '{chain}' (type: {type(chain)})")
        
        if chain is None:
            chain = "INPUT"
            print(f"🔍 DEBUG Service: chain is None, defaulting to INPUT")
        elif isinstance(chain, str):
            chain = chain.strip()
            if not chain:
                chain = "INPUT"
                print(f"🔍 DEBUG Service: chain is empty after strip, defaulting to INPUT")
            else:
                print(f"🔍 DEBUG Service: Using chain value: '{chain}'")
        else:
            chain = str(chain).strip() if chain else "INPUT"
            print(f"🔍 DEBUG Service: Converted chain to: '{chain}'")
        
        if not protocol or not action:
            return jsonify({"error": "Protocol và Action là bắt buộc"}), 400
            
        # Luôn thử tạo chain trước (như yêu cầu của user: iptables -N & iptables -A)
        # Bỏ qua built-in chains của filter table
        if chain not in ["INPUT", "OUTPUT", "FORWARD"]:
            try:
                # Thử tạo chain, nếu tồn tại thì bỏ qua lỗi
                subprocess.run(["sudo", "iptables", "-N", chain], 
                               check=True, capture_output=True, text=True)
                print(f"✅ Created chain '{chain}'")
            except subprocess.CalledProcessError as e:
                # Chỉ bỏ qua lỗi nếu chain đã tồn tại
                err = getattr(e, 'stderr', '') or str(e)
                if "already exists" not in err.lower():
                    print(f"⚠️ Error creating chain '{chain}': {err}")
                    # Không return error ở đây, cứ thử add rule xem sao (có thể là lỗi khác non-critical)

        # Tạo iptables command
        print(f"🔍 DEBUG Service: Final chain value before command: '{chain}'")
        cmd = ["sudo", "iptables", "-A", chain, "-p", protocol]
        print(f"🔍 DEBUG Service: Command: {' '.join(cmd)}")
        if ip:
            cmd += ["-s", ip]
        if port:
            cmd += ["--dport", port]
        if interface:
            cmd += ["-i", interface]
        if state:
            cmd += ["-m", "state", "--state", state]
        cmd += ["-j", action]
        
        try:
             subprocess.run(cmd, check=True, timeout=10, capture_output=True, text=True)
             return jsonify({"status": "success", "message": f"Đã thêm rule: {' '.join(cmd)}"})
        except subprocess.CalledProcessError as e:
            stderr = getattr(e, 'stderr', '') or str(e)
            return jsonify({"error": f"Lỗi khi thêm rule: {stderr}"}), 500

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Lỗi khi thêm rule: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rules/delete', methods=['POST'])
def delete_rule():
    """Xóa rule"""
    try:
        data = request.json
        num = data.get("num")
        chain = data.get("chain", "INPUT") # Default to INPUT if not provided
        
        if not num or not str(num).isdigit():
             return jsonify({"error": "Num phải là số"}), 400
        
        # Valid chain check (basic)
        if not chain or not isinstance(chain, str):
            chain = "INPUT"

        cmd = ["sudo", "iptables", "-D", chain, str(num)]
        subprocess.run(cmd, check=True, timeout=5)
        return jsonify({"status": "success", "message": f"Đã xóa rule số {num} khỏi chain {chain}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Lỗi khi xóa rule: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rules/delete-many', methods=['POST'])
def delete_many_rules():
    """Xóa nhiều rules từ các chains khác nhau"""
    try:
        data = request.json
        nums = data.get("nums", [])
        if not nums:
            return jsonify({"error": "Danh sách nums rỗng"}), 400
        
        # Lấy danh sách tất cả rules để tìm chain của mỗi rule
        # Sửa bug: map (chain, num) -> rule thay vì num -> chain để tránh ghi đè
        all_rules = get_all_chains_rules()
        rule_map = {}  # Map (chain, num) -> rule
        for rule in all_rules:
            chain = rule.get("chain", "INPUT")
            num = rule["num"]
            rule_map[(chain, num)] = rule
        
        deleted = []
        failed = []
        
        # Group rules by chain để xóa hiệu quả hơn
        rules_by_chain = {}
        for num in nums:
            # Tìm rule có num này (có thể có nhiều rules cùng num ở các chains khác nhau)
            found = False
            for (chain, rule_num), rule in rule_map.items():
                if rule_num == num:
                    if chain not in rules_by_chain:
                        rules_by_chain[chain] = []
                    rules_by_chain[chain].append(num)
                    found = True
                    break
            if not found:
                # Nếu không tìm thấy, thử với INPUT chain (fallback)
                if "INPUT" not in rules_by_chain:
                    rules_by_chain["INPUT"] = []
                rules_by_chain["INPUT"].append(num)
        
        # Xóa rules theo từng chain, sắp xếp num giảm dần
        for chain, chain_nums in rules_by_chain.items():
            # Loại bỏ duplicate và sắp xếp
            unique_nums = sorted(set(chain_nums), key=lambda x: int(x), reverse=True)
            for num in unique_nums:
                try:
                    cmd = ["sudo", "iptables", "-D", chain, str(num)]
                    # Thêm timeout để tránh đơ
                    result = subprocess.run(cmd, check=True, timeout=5, capture_output=True, text=True)
                    deleted.append(num)
                except subprocess.TimeoutExpired:
                    print(f"Timeout khi xóa rule {num} từ chain {chain}")
                    failed.append(num)
                except subprocess.CalledProcessError as e:
                    print(f"Lỗi xóa rule {num} từ chain {chain}: {e}")
                    failed.append(num)
                except Exception as e:
                    print(f"Lỗi không xác định khi xóa rule {num} từ chain {chain}: {e}")
                    failed.append(num)
        
        return jsonify({
            "status": "success",
            "deleted": deleted,
            "failed": failed
        })
    except Exception as e:
        import traceback
        print(f"Lỗi trong delete_many_rules: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/rules/search', methods=['GET'])
def search_rules():
    """Tìm kiếm rules"""
    try:
        query = request.args.get("q", "").lower()
        rules = get_input_rules()
        if query:
            filtered = [r for r in rules if query in r.get("chain", "INPUT").lower()]
        else:
            filtered = rules
        return jsonify({"rules": filtered})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    """Main function để chạy service"""
    print(f"Starting Firewall Service on {SERVICE_HOST}:{SERVICE_PORT}")
    print("API endpoints:")
    print("  GET  /api/health")
    print("  POST /api/monitoring/start")
    print("  POST /api/monitoring/stop")
    print("  GET  /api/monitoring/data")
    print("  GET  /api/rules/list")
    print("  POST /api/rules/add")
    print("  POST /api/rules/delete")
    print("  POST /api/rules/delete-many")
    print("  GET  /api/rules/search")
    
    # Bắt đầu monitoring tự động
    global monitoring_active, monitoring_thread
    monitoring_active = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    # Chạy Flask app
    app.run(host=SERVICE_HOST, port=SERVICE_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()

