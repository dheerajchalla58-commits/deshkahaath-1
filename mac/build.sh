#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "Build this app on an Apple Silicon Mac." >&2
  exit 1
fi
command -v uv >/dev/null || { echo "Install uv to build the Mac app." >&2; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${DESH_BUILD_DIR:-$ROOT/dist}"
APP="$OUTPUT/Desh Ke Haath.app"
RES="$APP/Contents/Resources"
mkdir -p "$APP/Contents/MacOS" "$RES"
cp "$ROOT/mac/Info.plist" "$APP/Contents/Info.plist"
swiftc -O "$ROOT/mac/DeshKeHaath.swift" -framework Cocoa -framework WebKit -o "$APP/Contents/MacOS/DeshKeHaath"

# A relocatable Python runtime lets the recipient run the app without installing Python.
uv python install 3.12
PY_SOURCE="$(uv python find --managed-python 3.12)"
PY_ROOT="$("$PY_SOURCE" -c 'import sys; print(sys.base_prefix)')"
cp -R "$PY_ROOT" "$RES/python"
PY="$RES/python/bin/python3"
uv pip install --python "$PY" -r "$ROOT/requirements.txt" "mflux==0.24.0"
mkdir -p "$RES/project"
cp "$ROOT/app.py" "$ROOT/models.py" "$ROOT/local_image.py" "$RES/project/"
cp -R "$ROOT/data" "$ROOT/static" "$ROOT/templates" "$ROOT/mac" "$RES/project/"
find "$RES/project" -name '__pycache__' -type d -prune -exec rm -rf {} +

# Smoke check: no model download or GPU is required on the CI host.
"$PY" -c 'import flask, huggingface_hub, importlib.util; assert importlib.util.find_spec("mflux")'
TEST_PORT_FILE="$(mktemp)"
rm -f "$TEST_PORT_FILE"
DESH_SKIP_MODEL_DOWNLOAD=1 DESH_PORT_FILE="$TEST_PORT_FILE" PYTHONPATH="$RES/project" "$PY" "$RES/project/mac/desktop_server.py" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; rm -f "$TEST_PORT_FILE"' EXIT
for _ in {1..120}; do [[ -s "$TEST_PORT_FILE" ]] && break; sleep 0.25; done
[[ -s "$TEST_PORT_FILE" ]] || { echo "Local server did not start." >&2; exit 1; }
curl --fail --silent "http://127.0.0.1:$(cat "$TEST_PORT_FILE")/products" >/dev/null
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT
rm -f "$TEST_PORT_FILE"
plutil -lint "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$OUTPUT/DeshKeHaath-macOS-arm64.zip"
echo "Built $OUTPUT/DeshKeHaath-macOS-arm64.zip"
