#!/usr/bin/env bash
set -euo pipefail
monitor_script="$(readlink -f -- "${BASH_SOURCE[0]}")"
monitor_dir="$(dirname -- "$monitor_script")"
if [[ -n "${CPU_MONITOR_PYTHON:-}" ]]; then
    monitor_python="$CPU_MONITOR_PYTHON"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
    monitor_python="$VIRTUAL_ENV/bin/python"
else
    monitor_python="$monitor_dir/.venv/bin/python"
fi
if [[ ! -x "$monitor_python" ]]; then
    printf 'Python-Interpreter nicht ausführbar: %s\nAktiviere eine vorhandene venv oder erstelle im Repository eine neue:\n  python3 -m venv .venv\n' "$monitor_python" >&2
    exit 1
fi
exec "$monitor_python" "$monitor_dir/cpu_monitor.py" "$@"
