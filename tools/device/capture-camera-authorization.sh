#!/usr/bin/env bash
# Capture Android package and CameraService authorization evidence without modifying the device.

set -Eeuo pipefail

ADB_BIN="adb"
SERIAL=""
OUT_ROOT="${PWD}/camera-authorization-capture"
STOCK_PACKAGE="com.nothing.camera"
REPLACEMENT_PACKAGE="com.phone2pro.camera"
USER_ID="0"

usage() {
  cat <<'EOF'
Usage: capture-camera-authorization.sh [options]

Options:
  --adb PATH                 adb executable (default: adb)
  --serial SERIAL            target adb device serial
  --output DIR               output root (default: ./camera-authorization-capture)
  --stock-package PACKAGE    stock camera package (default: com.nothing.camera)
  --replacement-package PKG  replacement package (default: com.phone2pro.camera)
  --user ID                  Android user ID (default: 0)
  -h, --help                 show help

The collector is read-only. It records package permission, AppOps, UID,
SELinux-process and CameraService state. It does not open a camera endpoint,
change permissions, root the device or copy APK contents.
EOF
}

while (($#)); do
  case "$1" in
    --adb)
      ADB_BIN="${2:?missing adb path}"
      shift 2
      ;;
    --serial)
      SERIAL="${2:?missing serial}"
      shift 2
      ;;
    --output)
      OUT_ROOT="${2:?missing output directory}"
      shift 2
      ;;
    --stock-package)
      STOCK_PACKAGE="${2:?missing stock package}"
      shift 2
      ;;
    --replacement-package)
      REPLACEMENT_PACKAGE="${2:?missing replacement package}"
      shift 2
      ;;
    --user)
      USER_ID="${2:?missing user ID}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      printf 'Unexpected argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

validate_package() {
  local package="$1"
  [[ "$package" =~ ^[A-Za-z0-9_]+([.][A-Za-z0-9_]+)+$ ]] || {
    printf 'Invalid package name: %s\n' "$package" >&2
    exit 2
  }
}

validate_package "$STOCK_PACKAGE"
validate_package "$REPLACEMENT_PACKAGE"
[[ "$USER_ID" =~ ^[0-9]+$ ]] || {
  printf 'Invalid Android user ID: %s\n' "$USER_ID" >&2
  exit 2
}

if [[ "$ADB_BIN" == */* ]]; then
  [[ -x "$ADB_BIN" ]] || {
    printf 'adb executable not found or not executable: %s\n' "$ADB_BIN" >&2
    exit 127
  }
else
  command -v "$ADB_BIN" >/dev/null 2>&1 || {
    printf 'adb executable not found: %s\n' "$ADB_BIN" >&2
    exit 127
  }
fi
command -v sha256sum >/dev/null 2>&1 || {
  printf 'sha256sum is required.\n' >&2
  exit 127
}

ADB=("$ADB_BIN")
[[ -n "$SERIAL" ]] && ADB+=(-s "$SERIAL")

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_ROOT%/}/$STAMP"
DEVICE_DIR="$OUT_DIR/device"
PACKAGES_DIR="$OUT_DIR/packages"
mkdir -p "$DEVICE_DIR" "$PACKAGES_DIR"

run_capture() {
  local output="$1"
  shift
  {
    printf '# command:'
    printf ' %q' "$@"
    printf '\n\n'
    "$@"
  } >"$output" 2>&1 || {
    local rc=$?
    printf '\n# command_exit_code: %d\n' "$rc" >>"$output"
    return 0
  }
}

if ! "${ADB[@]}" get-state >"$DEVICE_DIR/get-state.txt" 2>&1; then
  printf 'Unable to reach adb device. See %s\n' "$DEVICE_DIR/get-state.txt" >&2
  exit 3
fi

run_capture "$DEVICE_DIR/serial.txt" "${ADB[@]}" get-serialno
run_capture "$DEVICE_DIR/build-properties.txt" "${ADB[@]}" shell getprop
run_capture "$DEVICE_DIR/selinux-enforcement.txt" "${ADB[@]}" shell getenforce
run_capture "$DEVICE_DIR/process-contexts.txt" "${ADB[@]}" shell ps -AZ
run_capture "$DEVICE_DIR/package-permissions.txt" "${ADB[@]}" shell dumpsys package permissions
run_capture "$DEVICE_DIR/packages-with-uids.txt" "${ADB[@]}" shell cmd package list packages -U
run_capture "$DEVICE_DIR/camera-service.txt" "${ADB[@]}" shell dumpsys media.camera
run_capture "$DEVICE_DIR/camera-proxy.txt" "${ADB[@]}" shell dumpsys media.camera.proxy
run_capture "$DEVICE_DIR/services.txt" "${ADB[@]}" shell service list

capture_package() {
  local package="$1"
  local role="$2"
  local safe="${package//./_}"
  local directory="$PACKAGES_DIR/$role-$safe"
  mkdir -p "$directory"

  run_capture "$directory/dumpsys-package.txt" \
    "${ADB[@]}" shell dumpsys package "$package"
  run_capture "$directory/appops.txt" \
    "${ADB[@]}" shell appops get "$package"
  run_capture "$directory/package-path.txt" \
    "${ADB[@]}" shell cmd package path "$package"
  run_capture "$directory/package-uid.txt" \
    "${ADB[@]}" shell cmd package list packages -U "$package"
  run_capture "$directory/pid.txt" \
    "${ADB[@]}" shell pidof "$package"
  run_capture "$directory/privapp-permissions.txt" \
    "${ADB[@]}" shell cmd package get-privapp-permissions "$package"
  run_capture "$directory/privapp-deny-permissions.txt" \
    "${ADB[@]}" shell cmd package get-privapp-deny-permissions "$package"
  run_capture "$directory/check-camera-permission.txt" \
    "${ADB[@]}" shell cmd package check-permission \
      android.permission.CAMERA "$package" "$USER_ID"
  run_capture "$directory/check-system-camera-permission.txt" \
    "${ADB[@]}" shell cmd package check-permission \
      android.permission.SYSTEM_CAMERA "$package" "$USER_ID"

  {
    printf 'package=%s\n' "$package"
    printf 'role=%s\n' "$role"
    printf 'user_id=%s\n\n' "$USER_ID"
    printf '[permission checks]\n'
    cat "$directory/check-camera-permission.txt"
    cat "$directory/check-system-camera-permission.txt"
    printf '\n[uid and process]\n'
    cat "$directory/package-uid.txt"
    grep -F -- "$package" "$DEVICE_DIR/process-contexts.txt" || true
    printf '\n[relevant package lines]\n'
    grep -E \
      'userId=|sharedUser|android\.permission\.(CAMERA|SYSTEM_CAMERA)|granted=true|pkgFlags=|privateFlags=' \
      "$directory/dumpsys-package.txt" || true
  } >"$directory/summary.txt"
}

capture_package "$STOCK_PACKAGE" "stock"
capture_package "$REPLACEMENT_PACKAGE" "replacement"

{
  printf 'Camera authorization evidence\n'
  printf '  captured_at_utc: %s\n' "$STAMP"
  printf '  adb_serial_option: %s\n' "${SERIAL:-default}"
  printf '  android_user_id: %s\n' "$USER_ID"
  printf '  stock_package: %s\n' "$STOCK_PACKAGE"
  printf '  replacement_package: %s\n' "$REPLACEMENT_PACKAGE"
  printf '\nEvidence boundary:\n'
  printf '  These files show observable package, permission, AppOps, UID, SELinux and\n'
  printf '  CameraService state. They do not prove an endpoint can be opened unless a\n'
  printf '  separate controlled open attempt and capture result are recorded.\n'
} >"$OUT_DIR/README.txt"

{
  printf 'schemaVersion: 1\n'
  printf 'generatedAtUtc: %s\n' "$STAMP"
  printf 'adbSerial: %q\n' "${SERIAL:-default}"
  printf 'androidUserId: %q\n' "$USER_ID"
  printf 'stockPackage: %q\n' "$STOCK_PACKAGE"
  printf 'replacementPackage: %q\n' "$REPLACEMENT_PACKAGE"
  printf 'outputs:\n'
  while IFS= read -r -d '' file_path; do
    relative="${file_path#"$OUT_DIR/"}"
    printf '  - path: %q\n' "$relative"
    printf '    sizeBytes: %s\n' "$(wc -c <"$file_path" | tr -d ' ')"
    printf '    sha256: %s\n' "$(sha256sum "$file_path" | awk '{print $1}')"
  done < <(find "$OUT_DIR" -type f ! -name manifest.yaml -print0 | sort -z)
} >"$OUT_DIR/manifest.yaml"

printf 'Camera authorization evidence captured: %s\n' "$OUT_DIR"
