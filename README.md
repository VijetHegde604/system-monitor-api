# System Monitor API

A lightweight Python HTTP service that exposes basic host system metrics as JSON. It samples CPU, memory, disk, temperature, uptime, load average, and network throughput once per second, then serves the latest snapshot from a single `/info` endpoint.

## Features

- JSON API for current system status
- CPU usage and core count
- Memory and disk usage in percentages and GiB
- Hostname, formatted uptime and OS age in days, load average, and Unix timestamp
- Optional temperature reporting when supported by the host
- Per-second upload and download throughput for the first active non-loopback network interface

## Requirements

- Python 3.8 or newer
- [`psutil`](https://pypi.org/project/psutil/)
- A Linux/macOS/Unix-like environment is recommended for full metric support

> Temperature sensor data depends on operating system and hardware support. If no sensors are available, `temperature_c` is returned as `null`.

## Installation

Clone the repository and install the Python dependency:

```bash
git clone <repository-url>
cd system-monitor-api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install psutil
```

## Usage

Start the API server:

```bash
python system-monitor.py
```

By default, the service listens on all interfaces on port `8000` and exposes metrics at:

```text
http://localhost:8000/info
```

Query the endpoint with `curl`:

```bash
curl http://localhost:8000/info
```

## Example Response

```json
{
  "hostname": "monitor-host",
  "cpu_percent": 12.5,
  "cpu_cores": 8,
  "memory_percent": 43.2,
  "memory_used_gb": 6.91,
  "memory_total_gb": 16.0,
  "disk_percent": 58.7,
  "disk_used_gb": 137.4,
  "disk_total_gb": 234.1,
  "temperature_c": 48.5,
  "load_avg": 0.76,
  "uptime_seconds": 123456,
  "uptime": "1 day, 10 hours, 17 minutes, 36 seconds",
  "os_age": "142 days",
  "download_speed_mbps": 1.23,
  "upload_speed_mbps": 0.45,
  "timestamp": 1797715200
}
```

## API Reference

### `GET /info`

Returns the latest sampled host metrics.

| Field | Type | Description |
| --- | --- | --- |
| `hostname` | string | Hostname reported by the operating system. |
| `cpu_percent` | number | CPU utilization percentage. |
| `cpu_cores` | integer | Number of logical CPU cores. |
| `memory_percent` | number | Percentage of memory currently used. |
| `memory_used_gb` | number | Used memory in GiB. |
| `memory_total_gb` | number | Total memory in GiB. |
| `disk_percent` | number | Percentage of root filesystem storage used. |
| `disk_used_gb` | number | Used root filesystem storage in GiB. |
| `disk_total_gb` | number | Total root filesystem storage in GiB. |
| `temperature_c` | number or null | First available sensor temperature in Celsius, or `null` when unavailable. |
| `load_avg` | number | One-minute system load average. |
| `uptime_seconds` | integer | Seconds since the system booted. |
| `uptime` | string | Human-readable time since the system booted. |
| `os_age` | string or null | Whole days since the root filesystem was created. `null` when the filesystem does not expose a creation time. |
| `download_speed_mbps` | number | Approximate inbound network throughput in megabits per second. |
| `upload_speed_mbps` | number | Approximate outbound network throughput in megabits per second. |
| `timestamp` | integer | Unix timestamp for the sample. |

Unknown routes return `404`.

## Configuration

Runtime configuration is currently defined in `system-monitor.py`:

- `PORT` controls the HTTP port and defaults to `8000`.
- The monitored network interface is auto-detected as the first active non-loopback interface. If none is found, the script falls back to `eth0`.

## Development

There is no formal test suite in this repository yet. For a quick syntax check, run:

```bash
python -m py_compile system-monitor.py
```

For a manual smoke test, start the server and query `/info` from another terminal:

```bash
python system-monitor.py
curl http://localhost:8000/info
```

## Notes

- The first network speed sample may be `0` or near `0` because speeds are calculated from the difference between consecutive one-second samples.
- OS age is derived from `stat -c %W /` (the root filesystem creation timestamp), rather than the most recent boot. Filesystems without a creation timestamp return `null` for `os_age`.
- The API is intentionally minimal and does not provide authentication. Avoid exposing it directly to untrusted networks without adding access controls or placing it behind a trusted reverse proxy.
