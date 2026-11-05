#!/usr/bin/env bash
# Read-only check: is the running plate instance worth driving?
# Usage: scripts/doctor.sh [port]   (default 8811)
set -euo pipefail

PORT="${1:-8811}"
BASE="http://127.0.0.1:${PORT}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
fail=0

say() { printf '%s %s\n' "$1" "$2"; }

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# 1. Port answers.
if ! curl -fsS --max-time 5 "${BASE}/index.html" -o "${tmpdir}/served.html"; then
  say "FAIL" "no HTTP response from ${BASE}/index.html — is the server running on ${PORT}?"
  exit 1
fi
say "ok" "port ${PORT} serving"

# 2. Served document is the current build (byte-exact, via files so no trailing bytes are lost).
served_sum="$(shasum -a 256 "${tmpdir}/served.html" | awk '{print $1}')"
disk_sum="$(shasum -a 256 "${ROOT}/dist/index.html" | awk '{print $1}')"
if [ "$served_sum" != "$disk_sum" ]; then
  say "FAIL" "served index.html differs from dist/index.html — rebuild and restart the server"
  fail=1
else
  say "ok" "served index.html matches dist/index.html"
fi

# 3. Right page.
case "$(cat "${tmpdir}/served.html")" in
  *'<main class="plate">'*) say "ok" "page carries <main class=\"plate\">" ;;
  *) say "FAIL" "page is not the plate (missing main.plate)"; fail=1 ;;
esac

# 4. Data the assertions compare against.
if curl -fsS --max-time 5 "${BASE}/data.json" | python3 -c '
import json, sys
need = {"total", "as_at", "purposes", "stage1", "traditions", "denominations"}
d = json.load(sys.stdin)
missing = need - set(d)
raise SystemExit(f"missing keys: {sorted(missing)}" if missing else 0)
'; then
  say "ok" "data.json parses with aggregate keys"
else
  say "FAIL" "data.json unreadable or incomplete"; fail=1
fi

# 5. Build freshness relative to sources.
newest_src="$(ls -t "${ROOT}"/*.py "${ROOT}"/*.csv 2>/dev/null | head -1)"
if [ -n "$newest_src" ] && [ "$newest_src" -nt "${ROOT}/dist/index.html" ]; then
  say "WARN" "$(basename "$newest_src") is newer than dist/index.html — rerun python3 build_site.py"
fi

# 6. Tracked build output state.
say "info" "git status dist:"
git -C "$ROOT" status --short dist | sed 's/^/    /' || true

exit "$fail"
