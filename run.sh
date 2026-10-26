#!/usr/bin/env sh
# One-command setup + start on macOS/Linux:  ./run.sh   (flags: --yes, --check, --no-llm, --no-browser, --port N)
cd "$(dirname "$0")" || exit 1
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then exec "$candidate" scripts/launch.py "$@"; fi
done
echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/" >&2
exit 1
