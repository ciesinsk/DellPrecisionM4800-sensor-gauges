#!/usr/bin/env bash
set -euo pipefail
monitor_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
monitor_python="${CPU_MONITOR_PYTHON:-$monitor_dir/.venv/bin/python}"
if [[ ! -x "$monitor_python" ]]; then
    printf 'Python-Umgebung fehlt. Bitte zuerst im Repository ausführen:\n  python3 -m venv .venv\n' >&2
    exit 1
fi
exec "$monitor_python" "$monitor_dir/cpu_monitor.py" "$@"
