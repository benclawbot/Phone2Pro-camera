#!/usr/bin/env bash
set -Eeuo pipefail

# Disable Git Bash MSYS path conversion for adb calls. The wrapper passes
# /data/... paths to adb.exe, and MSYS otherwise rewrites them to
# C:/Program Files/Git/data/... causing ENOENT/EACCES on the device.
export MSYS_NO_PATHCONV=1

# Bootstrap PATH for fresh shells. Some launchers (notably pi-coding-agent)
# spawn shells with a stale PATH that lacks C:\platform-tools; the python
# helpers below spawn adb.exe via subprocess.run which uses Windows PATH.
# Prepend the two standard ADB install locations if present.
for _adb_path in "/c/platform-tools" "/c/Users/${USER:-thoma}/AppData/Local/Android/Sdk/platform-tools"; do
  if [[ -x "${_adb_path}/adb.exe" ]] && [[ ":$PATH:" != *":${_adb_path}:"* ]]; then
    export PATH="${_adb_path}:$PATH"
  fi
done
unset _adb_path

# Run the existing Expert route collector inside a bounded detached Perfetto
# session and add host/device clock normalization artifacts to its bundle.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
BASE_RUNNER="${SCRIPT_DIR}/run-expert-route-trace.sh"
CLOCK_CAPTURE="${REPO_ROOT}/tools/trace/capture-adb-clock-sample.py"
CLOCK_NORMALIZER="${REPO_ROOT}/tools/trace/normalize-trace-clocks.py"
PERFETTO_CONFIG="${SCRIPT_DIR}/perfetto/expert-routing.pbtx"

ROUTE=""
MODE="camera2"
OUTPUT_ROOT="${REPO_ROOT}/traces/expert-routing"
ADB_SERIAL=""
PASS_ARGS=()
LOCK_DIR=""
MARKER=""
RUN_DIR=""
PERFETTO_SESSION=""
PERFETTO_REMOTE_TRACE=""
PERFETTO_STARTED=0
PERFETTO_STOPPED=0
CLOCK_SAMPLES=""
PERFETTO_REMOTE_CONFIG=""

# Convert script paths to Windows form once. The python interpreter is a
# Windows binary and even with MSYS_NO_PATHCONV=1 the absolute Unix path form
# has triggered an unwanted path conversion on this host. cygpath -w makes the
# arg pass through conversion untouched.
_CLOCK_CAPTURE_WIN="$(cygpath -w "${REPO_ROOT}/tools/trace/capture-adb-clock-sample.py" 2>/dev/null || echo "${REPO_ROOT}/tools/trace/capture-adb-clock-sample.py")"
_CLOCK_NORMALIZER_WIN="$(cygpath -w "${REPO_ROOT}/tools/trace/normalize-trace-clocks.py" 2>/dev/null || echo "${REPO_ROOT}/tools/trace/normalize-trace-clocks.py")"
_PERFETTO_CONFIG_WIN="$(cygpath -w "${PERFETTO_CONFIG}" 2>/dev/null || echo "${PERFETTO_CONFIG}")"

usage() {
  cat <<'EOF'
Usage:
  run-expert-route-perfetto.sh --route 06x|1x|2x [runner options]

This wrapper accepts the existing run-expert-route-trace.sh options. It starts
one bounded Perfetto trace with camera, HAL, Binder and scheduler events,
captures host/device clock samples before and after the interactive run, pulls
the trace into the generated bundle and converts epoch logcat timestamps to
Perfetto's BOOTTIME domain.
EOF
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_file() {
  [[ -f "$1" ]] || fail "required file not found: $1"
}

ADB=(adb)

# Parse only the fields required for deterministic bundle discovery while
# forwarding all supported arguments to the existing runner unchanged.
while (($#)); do
  case "$1" in
    --route)
      (($# >= 2)) || fail "--route requires a value"
      ROUTE="$2"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    --mode)
      (($# >= 2)) || fail "--mode requires a value"
      MODE="$2"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    --output)
      (($# >= 2)) || fail "--output requires a value"
      OUTPUT_ROOT="$2"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    --serial)
      (($# >= 2)) || fail "--serial requires a value"
      ADB_SERIAL="$2"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    -h|--help)
      usage
      printf '\nUnderlying runner options:\n' >&2
      "$BASE_RUNNER" --help
      exit 0
      ;;
    *)
      PASS_ARGS+=("$1")
      if [[ "$1" == --package || "$1" == --frida-device || "$1" == --force-stop-delay || "$1" == --stabilize-seconds || "$1" == --capture-wait-seconds ]]; then
        (($# >= 2)) || fail "$1 requires a value"
        PASS_ARGS+=("$2")
        shift 2
      else
        shift
      fi
      ;;
  esac
done

case "$ROUTE" in
  06x|1x|2x) ;;
  "") fail "--route is required" ;;
  *) fail "unsupported route '$ROUTE'" ;;
esac
case "$MODE" in
  camera2|key-types) ;;
  *) fail "unsupported mode '$MODE'" ;;
esac

need_file "$BASE_RUNNER"
need_file "$CLOCK_CAPTURE"
need_file "$CLOCK_NORMALIZER"
need_file "$PERFETTO_CONFIG"
command -v adb >/dev/null 2>&1 || fail "required command not found: adb"
command -v python3 >/dev/null 2>&1 || fail "required command not found: python3"

CLOCK_SERIAL_ARGS=()
if [[ -n "$ADB_SERIAL" ]]; then
  ADB+=( -s "$ADB_SERIAL" )
  CLOCK_SERIAL_ARGS+=( --serial "$ADB_SERIAL" )
fi

mkdir -p "$OUTPUT_ROOT"
LOCK_DIR="${OUTPUT_ROOT%/}/.perfetto-run-lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  fail "another synchronized trace wrapper is active under $OUTPUT_ROOT"
fi
MARKER="${LOCK_DIR}/started"
: >"$MARKER"
CLOCK_SAMPLES="${LOCK_DIR}/clock-samples.jsonl"
UTC_STAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
PERFETTO_SESSION="p2p_${UTC_STAMP}_${ROUTE}_${MODE}"
PERFETTO_REMOTE_TRACE="/data/misc/perfetto-traces/${PERFETTO_SESSION}.perfetto-trace"

stop_perfetto() {
  if ((PERFETTO_STARTED == 1 && PERFETTO_STOPPED == 0)); then
    set +e
    "${ADB[@]}" shell perfetto --attach="$PERFETTO_SESSION" --stop </dev/null
    local status=$?
    set -e
    PERFETTO_STOPPED=1
    return "$status"
  fi
  return 0
}

find_run_dir() {
  local candidates=()
  while IFS= read -r -d '' path; do
    candidates+=("$path")
  done < <(find "$OUTPUT_ROOT" -mindepth 1 -maxdepth 1 -type d \
    -name "*-${ROUTE}-${MODE}" -newer "$MARKER" -print0)
  if ((${#candidates[@]} != 1)); then
    fail "expected one new ${ROUTE}/${MODE} run directory, found ${#candidates[@]}"
  fi
  RUN_DIR="${candidates[0]}"
}

rehash_bundle() {
  local target="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    (
      cd "$target"
      find . -type f ! -name SHA256SUMS -print0 | sort -z \
        | xargs -0 sha256sum
    ) >"${target}/SHA256SUMS"
  elif command -v shasum >/dev/null 2>&1; then
    (
      cd "$target"
      find . -type f ! -name SHA256SUMS -print0 | sort -z \
        | xargs -0 shasum -a 256
    ) >"${target}/SHA256SUMS"
  else
    printf 'warning: sha256sum/shasum unavailable; bundle manifest was not refreshed\n' >&2
  fi
}

cleanup() {
  local status=$?
  set +e
  stop_perfetto >/dev/null 2>&1
  if [[ -n "$LOCK_DIR" ]]; then
    rm -rf "$LOCK_DIR"
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! "${ADB[@]}" shell command -v perfetto </dev/null | grep -q '/perfetto$'; then
  fail "on-device perfetto command is unavailable"
fi

python3 "$_CLOCK_CAPTURE_WIN" --phase before-perfetto --output "$(cygpath -w "$CLOCK_SAMPLES" 2>/dev/null || echo "$CLOCK_SAMPLES")" \
  "${CLOCK_SERIAL_ARGS[@]}"

# Detached mode is bounded by duration_ms in the config and is explicitly
# stopped by the EXIT trap, preventing a leaked indefinite tracing session.
# Perfetto v49 on this device refuses `-c -` (stdin) when the config contains
# buffers{} or atrace_aps. Push to /data/misc/perfetto-configs/ where the
# Perfetto service can read it (SELinux denies /data/local/tmp for this user).
PERFETTO_REMOTE_CONFIG="/data/misc/perfetto-configs/${PERFETTO_SESSION}.pbtx"

if ! "${ADB[@]}" push "$_PERFETTO_CONFIG_WIN" "$PERFETTO_REMOTE_CONFIG" </dev/null; then
  fail "failed to push Perfetto config to $PERFETTO_REMOTE_CONFIG"
fi
if ! "${ADB[@]}" shell perfetto --config "$PERFETTO_REMOTE_CONFIG" --txt \
  --detach="$PERFETTO_SESSION" -o "$PERFETTO_REMOTE_TRACE"; then
  fail "failed to start detached Perfetto session"
fi
PERFETTO_STARTED=1

python3 "$_CLOCK_CAPTURE_WIN" --phase after-perfetto-start --output "$(cygpath -w "$CLOCK_SAMPLES" 2>/dev/null || echo "$CLOCK_SAMPLES")" \
  "${CLOCK_SERIAL_ARGS[@]}"

set +e
# Unset MSYS_NO_PATHCONV for the inner runner. The frida shim it invokes
# (tools/trace/frida-durable-shim.py when the portable wrapper is used) has a
# shebang that needs normal path translation — /tmp/p2p-frida.XXXXXX/frida must
# resolve to C:\Users\<user>\AppData\Local\Temp\... not to C:\tmp\... which is
# what MSYS rewrites it to when MSYS_NO_PATHCONV=1 is set. The inner runner's
# own adb calls don't pass /data/... args so this is safe; restore after.
_SAVED_MSYS_NO_PATHCONV="$MSYS_NO_PATHCONV"
unset MSYS_NO_PATHCONV
"$BASE_RUNNER" "${PASS_ARGS[@]}"
RUNNER_STATUS=$?
if [[ -n "$_SAVED_MSYS_NO_PATHCONV" ]]; then
  export MSYS_NO_PATHCONV="$_SAVED_MSYS_NO_PATHCONV"
fi
unset _SAVED_MSYS_NO_PATHCONV
set -e

python3 "$_CLOCK_CAPTURE_WIN" --phase before-perfetto-stop --output "$(cygpath -w "$CLOCK_SAMPLES" 2>/dev/null || echo "$CLOCK_SAMPLES")" \
  "${CLOCK_SERIAL_ARGS[@]}"

if ! stop_perfetto; then
  fail "failed to stop detached Perfetto session"
fi

python3 "$_CLOCK_CAPTURE_WIN" --phase after-perfetto-stop --output "$(cygpath -w "$CLOCK_SAMPLES" 2>/dev/null || echo "$CLOCK_SAMPLES")" \
  "${CLOCK_SERIAL_ARGS[@]}"

find_run_dir
mv "$CLOCK_SAMPLES" "${RUN_DIR}/clock-samples.jsonl"

if ! "${ADB[@]}" pull "$PERFETTO_REMOTE_TRACE" \
  "${RUN_DIR}/expert-routing.perfetto-trace" </dev/null; then
  fail "failed to pull Perfetto trace"
fi
"${ADB[@]}" shell rm -f "$PERFETTO_REMOTE_TRACE" </dev/null || true

NORMALIZE_ARGS=(
  "${RUN_DIR}/clock-samples.jsonl"
  --output "$(cygpath -w "${RUN_DIR}/clock-normalization.json" 2>/dev/null || echo "${RUN_DIR}/clock-normalization.json")"
)
if [[ -f "${RUN_DIR}/camera-service.log" ]]; then
  NORMALIZE_ARGS+=(
    --logcat "$(cygpath -w "${RUN_DIR}/camera-service.log" 2>/dev/null || echo "${RUN_DIR}/camera-service.log")"
    --normalized-logcat "$(cygpath -w "${RUN_DIR}/camera-service.boottime.jsonl" 2>/dev/null || echo "${RUN_DIR}/camera-service.boottime.jsonl")"
  )
fi
python3 "$CLOCK_NORMALIZER" "${NORMALIZE_ARGS[@]}"

cat >"${RUN_DIR}/perfetto-status.json" <<EOF
{
  "schemaVersion": 1,
  "session": "${PERFETTO_SESSION}",
  "remoteTrace": "${PERFETTO_REMOTE_TRACE}",
  "localTrace": "expert-routing.perfetto-trace",
  "config": "tools/device/perfetto/expert-routing.pbtx",
  "primaryTraceClock": "BUILTIN_CLOCK_BOOTTIME",
  "runnerExitStatus": ${RUNNER_STATUS},
  "stoppedExplicitly": true
}
EOF

rehash_bundle "$RUN_DIR"
printf '\nSynchronized Perfetto bundle completed: %s\n' "$RUN_DIR" >&2

if ((RUNNER_STATUS != 0)); then
  fail "underlying route runner exited with status $RUNNER_STATUS"
fi
