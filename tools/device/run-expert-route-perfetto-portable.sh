#!/usr/bin/env bash
set -Eeuo pipefail

# Run the synchronized Expert trace workflow through a durable Frida CLI shim.
# This preserves observer output on Windows Git Bash and other hosts where the
# interactive Frida process can otherwise be terminated before -o is flushed.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
BASE_WRAPPER="${SCRIPT_DIR}/run-expert-route-perfetto.sh"
FRIDA_RUNNER="${REPO_ROOT}/tools/trace/run-frida-cli-observer.py"
FRIDA_SHIM_SOURCE="${REPO_ROOT}/tools/trace/frida-durable-shim.py"
SHIM_DIR=""

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

for path in "$BASE_WRAPPER" "$FRIDA_RUNNER" "$FRIDA_SHIM_SOURCE"; do
  [[ -f "$path" ]] || fail "required file not found: $path"
done
command -v python3 >/dev/null 2>&1 || fail "required command not found: python3"
REAL_FRIDA="$(command -v frida || true)"
[[ -n "$REAL_FRIDA" ]] || fail "required command not found: frida"

SHIM_DIR="$(mktemp -d "${TMPDIR:-/tmp}/p2p-frida.XXXXXX")"
cleanup() {
  local status=$?
  if [[ -n "$SHIM_DIR" ]]; then
    rm -rf "$SHIM_DIR"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

cp "$FRIDA_SHIM_SOURCE" "${SHIM_DIR}/frida"
chmod +x "${SHIM_DIR}/frida"
export P2P_REAL_FRIDA="$REAL_FRIDA"
export P2P_FRIDA_RUNNER="$FRIDA_RUNNER"
export PATH="${SHIM_DIR}:${PATH}"

printf 'Using durable Frida capture through %s\n' "$REAL_FRIDA" >&2
printf 'Complete the assigned camera interaction, then press Enter or Ctrl-D.\n' >&2

"$BASE_WRAPPER" "$@"
