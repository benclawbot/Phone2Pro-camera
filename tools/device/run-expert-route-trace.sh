#!/usr/bin/env bash
set -Eeuo pipefail

# Collect one controlled Nothing Camera Expert routing trace.
#
# This script observes an authorized test device. It does not change package
# permissions, camera metadata, SELinux policy, or application files.
#
# Examples:
#   tools/device/run-expert-route-trace.sh --route 06x --mode camera2
#   tools/device/run-expert-route-trace.sh --route 2x --mode key-types
#
# The user completes the stock-camera interaction while Frida is attached:
# enter Expert mode, select only the assigned lens, wait, take one photo, wait,
# exit the camera, then stop Frida with Ctrl-C.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

PACKAGE="com.nothing.camera"
ROUTE=""
MODE="camera2"
OUTPUT_ROOT="${REPO_ROOT}/traces/expert-routing"
ADB_SERIAL=""
FRIDA_DEVICE="-U"
LOGCAT_ENABLED=1
DUMPSYS_ENABLED=1
FORCE_STOP_DELAY=2
STABILIZE_SECONDS=3
CAPTURE_WAIT_SECONDS=3

usage() {
  cat <<'EOF'
Usage:
  run-expert-route-trace.sh --route 06x|1x|2x [options]

Required:
  --route ROUTE             Controlled optical route: 06x, 1x, or 2x.

Options:
  --mode MODE               camera2 or key-types. Default: camera2.
  --output DIR              Output root. Default: traces/expert-routing.
  --package NAME            Camera package. Default: com.nothing.camera.
  --serial SERIAL           ADB device serial.
  --frida-device ARG        Frida device selector. Default: -U.
  --no-logcat               Do not collect synchronized camera logcat.
  --no-dumpsys              Do not collect media.camera snapshots.
  --force-stop-delay SEC    Delay after force-stop. Default: 2.
  --stabilize-seconds SEC   Documented preview wait. Default: 3.
  --capture-wait-seconds SEC Documented post-capture wait. Default: 3.
  -h, --help                Show this help.

This command creates a timestamped local bundle. It does not upload images or
trace data. Raw logs may contain device/package metadata; review before sharing.
EOF
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

is_nonnegative_integer() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

while (($#)); do
  case "$1" in
    --route)
      (($# >= 2)) || fail "--route requires a value"
      ROUTE="$2"
      shift 2
      ;;
    --mode)
      (($# >= 2)) || fail "--mode requires a value"
      MODE="$2"
      shift 2
      ;;
    --output)
      (($# >= 2)) || fail "--output requires a value"
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --package)
      (($# >= 2)) || fail "--package requires a value"
      PACKAGE="$2"
      shift 2
      ;;
    --serial)
      (($# >= 2)) || fail "--serial requires a value"
      ADB_SERIAL="$2"
      shift 2
      ;;
    --frida-device)
      (($# >= 2)) || fail "--frida-device requires a value"
      FRIDA_DEVICE="$2"
      shift 2
      ;;
    --no-logcat)
      LOGCAT_ENABLED=0
      shift
      ;;
    --no-dumpsys)
      DUMPSYS_ENABLED=0
      shift
      ;;
    --force-stop-delay)
      (($# >= 2)) || fail "--force-stop-delay requires a value"
      FORCE_STOP_DELAY="$2"
      shift 2
      ;;
    --stabilize-seconds)
      (($# >= 2)) || fail "--stabilize-seconds requires a value"
      STABILIZE_SECONDS="$2"
      shift 2
      ;;
    --capture-wait-seconds)
      (($# >= 2)) || fail "--capture-wait-seconds requires a value"
      CAPTURE_WAIT_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

case "$ROUTE" in
  06x|1x|2x) ;;
  "") fail "--route is required" ;;
  *) fail "unsupported route '$ROUTE'; use 06x, 1x, or 2x" ;;
esac

case "$MODE" in
  camera2)
    FRIDA_SCRIPT="${REPO_ROOT}/tools/frida/trace-camera2-routing.js"
    ;;
  key-types)
    FRIDA_SCRIPT="${REPO_ROOT}/tools/frida/dump-camera-key-types.js"
    ;;
  *)
    fail "unsupported mode '$MODE'; use camera2 or key-types"
    ;;
esac

for value in "$FORCE_STOP_DELAY" "$STABILIZE_SECONDS" "$CAPTURE_WAIT_SECONDS"; do
  is_nonnegative_integer "$value" || fail "timing values must be non-negative integers"
done

need_command adb
need_command frida
[[ -f "$FRIDA_SCRIPT" ]] || fail "Frida script not found: $FRIDA_SCRIPT"

ADB=(adb)
if [[ -n "$ADB_SERIAL" ]]; then
  ADB+=( -s "$ADB_SERIAL" )
fi

# Treat the Frida selector as one argument by default. Advanced users can call
# the script through a wrapper if their environment needs multiple selector args.
FRIDA=(frida "$FRIDA_DEVICE")

DEVICE_STATE="$(${ADB[@]} get-state 2>/dev/null || true)"
[[ "$DEVICE_STATE" == "device" ]] || fail "ADB device is not ready (state: ${DEVICE_STATE:-unknown})"

if ! "${ADB[@]}" shell pm path "$PACKAGE" </dev/null | grep -q '^package:'; then
  fail "package not installed or not visible: $PACKAGE"
fi

UTC_STAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
RUN_DIR="${OUTPUT_ROOT%/}/${UTC_STAMP}-${ROUTE}-${MODE}"
mkdir -p "$RUN_DIR"

LOGCAT_PID=""
FRIDA_STATUS=0
CLEANED_UP=0

stop_logcat() {
  if [[ -n "$LOGCAT_PID" ]] && kill -0 "$LOGCAT_PID" 2>/dev/null; then
    kill -INT "$LOGCAT_PID" 2>/dev/null || true
    wait "$LOGCAT_PID" 2>/dev/null || true
  fi
  LOGCAT_PID=""
}

cleanup() {
  local exit_status=$?
  if ((CLEANED_UP == 0)); then
    CLEANED_UP=1
    stop_logcat
    {
      printf 'cleanupUtc=%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
      printf 'scriptExitStatus=%s\n' "$exit_status"
      printf 'fridaExitStatus=%s\n' "$FRIDA_STATUS"
    } >>"${RUN_DIR}/run-status.txt" 2>/dev/null || true
  fi
  exit "$exit_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

BUILD_FINGERPRINT="$(${ADB[@]} shell getprop ro.build.fingerprint </dev/null | tr -d '\r')"
SDK_INT="$(${ADB[@]} shell getprop ro.build.version.sdk </dev/null | tr -d '\r')"
SECURITY_PATCH="$(${ADB[@]} shell getprop ro.build.version.security_patch </dev/null | tr -d '\r')"
CAMERA_VERSION="$(${ADB[@]} shell dumpsys package "$PACKAGE" </dev/null \
  | tr -d '\r' \
  | sed -n 's/^[[:space:]]*versionName=//p' \
  | head -n 1)"

cat >"${RUN_DIR}/run-metadata.json" <<EOF
{
  "schemaVersion": 1,
  "createdAtUtc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "route": "${ROUTE}",
  "traceMode": "${MODE}",
  "packageName": "${PACKAGE}",
  "cameraPackageVersion": "${CAMERA_VERSION}",
  "buildFingerprint": "${BUILD_FINGERPRINT}",
  "sdkInt": "${SDK_INT}",
  "securityPatch": "${SECURITY_PATCH}",
  "expectedPreviewStabilizationSeconds": ${STABILIZE_SECONDS},
  "expectedPostCaptureWaitSeconds": ${CAPTURE_WAIT_SECONDS},
  "imageDataCollectedByScript": false,
  "requestMutationPerformedByScript": false
}
EOF

{
  printf 'startUtc=%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  printf 'runDirectory=%s\n' "$RUN_DIR"
  printf 'route=%s\n' "$ROUTE"
  printf 'mode=%s\n' "$MODE"
} >"${RUN_DIR}/run-status.txt"

"${ADB[@]}" shell pm path "$PACKAGE" </dev/null >"${RUN_DIR}/package-paths.txt" 2>&1 || true
"${ADB[@]}" shell dumpsys package "$PACKAGE" </dev/null >"${RUN_DIR}/package-dumpsys-before.txt" 2>&1 || true
"${ADB[@]}" shell cmd appops get "$PACKAGE" </dev/null >"${RUN_DIR}/appops-before.txt" 2>&1 || true
"${ADB[@]}" shell getprop </dev/null >"${RUN_DIR}/getprop.txt" 2>&1 || true

if ((DUMPSYS_ENABLED == 1)); then
  "${ADB[@]}" shell dumpsys media.camera </dev/null >"${RUN_DIR}/media-camera-before.txt" 2>&1 || true
fi

"${ADB[@]}" shell am force-stop "$PACKAGE" </dev/null
sleep "$FORCE_STOP_DELAY"
"${ADB[@]}" logcat -c </dev/null || true

if ((LOGCAT_ENABLED == 1)); then
  # Keep the collection bounded to camera-related tags. Tag availability differs
  # between firmware builds, so an empty log is recorded rather than treated as failure.
  "${ADB[@]}" logcat -v epoch \
    'CameraService:V' \
    'CameraProviderManager:V' \
    'cameraserver:V' \
    'mtkcam:V' \
    'MtkCam:V' \
    'CameraManagerGlobal:V' \
    '*:S' \
    >"${RUN_DIR}/camera-service.log" 2>&1 &
  LOGCAT_PID=$!
fi

cat >&2 <<EOF

Controlled Expert route: ${ROUTE}
Trace mode: ${MODE}
Output: ${RUN_DIR}

After Nothing Camera appears:
  1. Enter Expert mode.
  2. Select only ${ROUTE}.
  3. Wait ${STABILIZE_SECONDS} seconds.
  4. Take one photograph.
  5. Wait ${CAPTURE_WAIT_SECONDS} seconds.
  6. Exit the camera.
  7. Stop Frida with Ctrl-C.

Do not select another lens during this run.

EOF

set +e
"${FRIDA[@]}" -f "$PACKAGE" -l "$FRIDA_SCRIPT" -o "${RUN_DIR}/frida.log"
FRIDA_STATUS=$?
set -e

stop_logcat

if ((DUMPSYS_ENABLED == 1)); then
  "${ADB[@]}" shell dumpsys media.camera </dev/null >"${RUN_DIR}/media-camera-after.txt" 2>&1 || true
fi
"${ADB[@]}" shell dumpsys package "$PACKAGE" </dev/null >"${RUN_DIR}/package-dumpsys-after.txt" 2>&1 || true
"${ADB[@]}" shell cmd appops get "$PACKAGE" </dev/null >"${RUN_DIR}/appops-after.txt" 2>&1 || true

cat >"${RUN_DIR}/output-association-template.json" <<EOF
{
  "schemaVersion": 1,
  "route": "${ROUTE}",
  "capture": {
    "mediaStoreId": null,
    "filename": null,
    "createdAt": null,
    "width": null,
    "height": null,
    "focalLengthMm": null,
    "focalLength35mmEquivalent": null,
    "aperture": null,
    "digitalZoomRatio": null
  },
  "validation": {
    "matchesAssignedOpticalRoute": null,
    "notes": "Fill from non-image MediaStore/EXIF metadata. Do not add the image to this bundle."
  }
}
EOF

hash_file() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path"
  else
    return 127
  fi
}

if command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1; then
  (
    cd "$RUN_DIR"
    find . -type f ! -name 'SHA256SUMS' -print0 \
      | sort -z \
      | while IFS= read -r -d '' file; do
          hash_file "$file"
        done
  ) >"${RUN_DIR}/SHA256SUMS"
else
  printf 'warning: sha256sum/shasum unavailable; no hash manifest created\n' >&2
fi

{
  printf 'completeUtc=%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  printf 'fridaExitStatus=%s\n' "$FRIDA_STATUS"
} >>"${RUN_DIR}/run-status.txt"

printf '\nTrace bundle created: %s\n' "$RUN_DIR" >&2
printf 'Fill output-association-template.json before comparing routes.\n' >&2

# Ctrl-C is the expected way to finish an interactive Frida session. Treat 0 and
# 130 as completed collections; retain other statuses as failures.
if [[ "$FRIDA_STATUS" -ne 0 && "$FRIDA_STATUS" -ne 130 ]]; then
  fail "Frida exited with status $FRIDA_STATUS; bundle retained for diagnosis"
fi
