#!/usr/bin/env python3
"""
Firewall Service Daemon
Service chạy backend logic và cung cấp REST API để giao diện điều khiển
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

from backend.rules.core import get_input_rules, get_group_map, normalize_rule_key
from backend.rules.core.add_rule import IptablesHandler, load_meta, save_meta, make_rule_key
from backend.notifications import send_malware_alert

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
prev_ram = 0

RAM_SPIKE_MB = 150
CPU_SPIKE_PERCENT = 40
CPU_MAX_PERCENT = 85
SERVICE_ALERT_COOLDOWN = 60
last_service_alert_time = 0


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
    global prev_cpu_usage, prev_time, prev_net_rx, prev_net_tx, prev_ram
    global last_service_alert_time
    
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
                send_malware_alert(malware_type="Trojan.Generic", severity="high")
        
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
            
            if prev_ram > 0:
                diff_mb = (used_bytes - prev_ram) / (1024 ** 2)
                if diff_mb > RAM_SPIKE_MB:
                    monitoring_data["alerts"].append({
                        "type": "RAM",
                        "message": f"RAM tăng đột biến: +{diff_mb:.1f} MB",
                        "severity": "high",
                        "timestamp": time.time()
                    })
                    send_malware_alert(malware_type="Trojan.Generic", severity="high")
            prev_ram = used_bytes
        
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
                capture_output=True, text=True
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
    """Lấy danh sách rules"""
    try:
        rules = get_input_rules()
        group_map = get_group_map()
        # Thêm group vào mỗi rule
        for rule in rules:
            rule_key = rule.get("rule_key", "")
            normalized_key = normalize_rule_key(rule_key)
            rule["group"] = group_map.get(normalized_key, "None")
        return jsonify({"rules": rules})
    except Exception as e:
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
        group = data.get("group", "")
        
        if not protocol or not action:
            return jsonify({"error": "Protocol và Action là bắt buộc"}), 400
        
        cmd = ["sudo", "iptables", "-A", "INPUT", "-p", protocol]
        if ip:
            cmd += ["-s", ip]
        if port:
            cmd += ["--dport", port]
        if interface:
            cmd += ["-i", interface]
        if state:
            cmd += ["-m", "state", "--state", state]
        cmd += ["-j", action]
        
        subprocess.run(cmd, check=True)
        
        # Lưu metadata
        result = subprocess.run(
            ["sudo", "iptables", "-L", "INPUT", "-v", "-n", "--line-numbers"],
            capture_output=True, text=True, check=True
        )
        lines = [l for l in result.stdout.splitlines()[2:] if l.strip()]
        if lines:
            last_rule = lines[-1]
            parts = last_rule.split()
            key = make_rule_key(parts)
            meta = load_meta()
            meta[key] = group.strip() if group.strip() else "None"
            save_meta(meta)
        
        return jsonify({"status": "success", "message": f"Đã thêm rule: {' '.join(cmd)}"})
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
        if not num or not num.isdigit():
            return jsonify({"error": "Num phải là số"}), 400
        
        cmd = ["sudo", "iptables", "-D", "INPUT", num]
        subprocess.run(cmd, check=True)
        return jsonify({"status": "success", "message": f"Đã xóa rule số {num}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Lỗi khi xóa rule: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rules/delete-many', methods=['POST'])
def delete_many_rules():
    """Xóa nhiều rules"""
    try:
        data = request.json
        nums = data.get("nums", [])
        if not nums:
            return jsonify({"error": "Danh sách nums rỗng"}), 400
        
        deleted = []
        failed = []
        for num in sorted(nums, reverse=True):
            try:
                cmd = ["sudo", "iptables", "-D", "INPUT", str(num)]
                subprocess.run(cmd, check=True)
                deleted.append(num)
            except:
                failed.append(num)
        
        return jsonify({
            "status": "success",
            "deleted": deleted,
            "failed": failed
        })
    except Exception as e:
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

