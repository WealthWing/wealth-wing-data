#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: ./run.sh [--debug | --help]"
}

if [[ $# -gt 1 ]]; then
    usage >&2
    exit 2
fi

case "${1:-}" in
    --help|-h)
        usage
        exit 0
        ;;
    ""|--debug) ;;
    *)
        usage >&2
        exit 2
        ;;
esac

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    python_bin="${VIRTUAL_ENV}/bin/python"
elif [[ -x venv/bin/python ]]; then
    python_bin="venv/bin/python"
elif [[ -x .venv/bin/python ]]; then
    python_bin=".venv/bin/python"
else
    python_bin="python3"
fi

if [[ "${1:-}" == "--debug" ]]; then
    if ! "$python_bin" -c 'import debugpy' >/dev/null 2>&1; then
        echo "Debug mode requires debugpy. Install it with:" >&2
        echo "  $python_bin -m pip install -r requirements-dev.txt" >&2
        exit 1
    fi

    echo "Starting debug server at http://127.0.0.1:8000/docs"
    echo "To debug, select 'WealthWing API (Attach)' in VS Code and press F5."
    exec "$python_bin" -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 \
        -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --env-file .env
fi

echo "Running in dev mode at http://127.0.0.1:8000/docs"
exec "$python_bin" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
