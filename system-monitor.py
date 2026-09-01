#!/usr/bin/env python3
import json
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import psutil

PORT = 8000
BOOT_TIME = psutil.boot_time()

metrics = {}


def format_duration(total_seconds):
    """Return a concise, human-readable representation of a duration."""
    total_seconds = max(0, int(total_seconds))
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours or parts:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return ", ".join(parts)


def get_root_filesystem_birth_time():
    """Return the root filesystem creation timestamp, when GNU stat provides it."""
    try:
        result = subprocess.run(
            ["stat", "-c", "%W", "/"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return None
    try:
        birth_time = int(result.stdout.strip())
    except ValueError:
        return None

    # GNU stat reports -1 when the filesystem does not expose a birth time.
    return birth_time if birth_time > 0 else None


ROOT_FILESYSTEM_BIRTH_TIME = get_root_filesystem_birth_time()


def get_os_age():
    """Return the OS age in whole days based on the root filesystem birth time."""
    if ROOT_FILESYSTEM_BIRTH_TIME is None:
        return None

    elapsed_seconds = max(0, int(time.time()) - ROOT_FILESYSTEM_BIRTH_TIME)
    return f"{elapsed_seconds // 86_400} days"


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
            "uptime": format_duration(uptime),
            "os_age": get_os_age(),
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
