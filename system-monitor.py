#!/usr/bin/env python3
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import psutil

PORT = 8000
BOOT_TIME = psutil.boot_time()

metrics = {}


# ---------------------------
# Detect active interface
# ---------------------------
def get_active_interface():
    stats = psutil.net_if_stats()
    for iface, data in stats.items():
        if data.isup and iface != "lo":
            return iface
    return "eth0"


INTERFACE = get_active_interface()
print("Monitoring Interface:", INTERFACE)


# ---------------------------
# Temperature
# ---------------------------
def get_temperature():
    temps = psutil.sensors_temperatures()
    if not temps:
        return None

    for name in temps:
        if temps[name]:
            return round(temps[name][0].current, 1)

    return None


# ---------------------------
# Background sampler (1s)
# ---------------------------
previous_net = psutil.net_io_counters(pernic=True)


def sampler():
    global metrics, previous_net

    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        uptime = int(time.time() - BOOT_TIME)

        # ---- Network speed ----
        net = psutil.net_io_counters(pernic=True)

        if INTERFACE in net:
            rx_diff = net[INTERFACE].bytes_recv - previous_net[INTERFACE].bytes_recv
            tx_diff = net[INTERFACE].bytes_sent - previous_net[INTERFACE].bytes_sent

            download = (rx_diff * 8) / (1024 * 1024)
            upload = (tx_diff * 8) / (1024 * 1024)
        else:
            download = upload = 0

        previous_net = net

        metrics = {
            "hostname": socket.gethostname(),
            "cpu_percent": cpu,
            "cpu_cores": psutil.cpu_count(),
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "temperature_c": get_temperature(),
            "load_avg": round(psutil.getloadavg()[0], 2),
            "uptime_seconds": uptime,
            "download_speed_mbps": round(download, 2),
            "upload_speed_mbps": round(upload, 2),
            "timestamp": int(time.time()),
        }

        time.sleep(1)


# ---------------------------
# HTTP Handler
# ---------------------------
class InfoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps(metrics).encode())
        else:
            self.send_response(404)
            self.end_headers()


# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    threading.Thread(target=sampler, daemon=True).start()

    server = HTTPServer(("", PORT), InfoHandler)
    print(f"Serving on :{PORT}/info")
    server.serve_forever()
