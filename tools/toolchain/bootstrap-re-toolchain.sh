#!/usr/bin/env bash
# Bootstrap the host-independent portion of the pinned reverse-engineering toolchain.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCK_FILE="$REPO_ROOT/config/reverse-engineering-toolchain.json"
INSTALL_DIR="${RE_TOOLCHAIN_HOME:-$REPO_ROOT/.re-toolchain}"
WITH_GHIDRA=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: bootstrap-re-toolchain.sh [options]

Options:
  --install-dir DIR   installation root (default: ./.re-toolchain)
  --lock FILE        alternate toolchain lock JSON
  --with-ghidra      also download and unpack the large Ghidra distribution
  --dry-run          print planned actions without downloading or installing
  -h, --help         show help

The bootstrap installs pinned JADX, Apktool, baksmali, bundletool and Frida host
tools. Ghidra is optional because of its size. Android Platform-Tools and
Perfetto remain explicit host steps because their official binaries are
platform-specific. Run verify-re-toolchain.py afterwards.
EOF
}

while (($#)); do
  case "$1" in
    --install-dir)
      INSTALL_DIR="${2:?missing install directory}"
      shift 2
      ;;
    --lock)
      LOCK_FILE="${2:?missing lock file}"
      shift 2
      ;;
    --with-ghidra)
      WITH_GHIDRA=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
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

for command in python3 java curl unzip sha256sum; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Required bootstrap command unavailable: %s\n' "$command" >&2
    exit 127
  }
done
[[ -f "$LOCK_FILE" ]] || {
  printf 'Toolchain lock not found: %s\n' "$LOCK_FILE" >&2
  exit 2
}

LOCK_FILE="$(cd "$(dirname "$LOCK_FILE")" && pwd)/$(basename "$LOCK_FILE")"
INSTALL_DIR="$(mkdir -p "$INSTALL_DIR" && cd "$INSTALL_DIR" && pwd)"
DOWNLOAD_DIR="$INSTALL_DIR/downloads"
OPT_DIR="$INSTALL_DIR/opt"
BIN_DIR="$INSTALL_DIR/bin"
RECEIPT_TSV="$INSTALL_DIR/bootstrap-receipt.tsv"
mkdir -p "$DOWNLOAD_DIR" "$OPT_DIR" "$BIN_DIR"

lock_value() {
  local tool_id="$1"
  local expression="$2"
  python3 - "$LOCK_FILE" "$tool_id" "$expression" <<'PY'
import json
import sys

path, tool_id, expression = sys.argv[1:]
lock = json.load(open(path, encoding="utf-8"))
tool = next((item for item in lock["tools"] if item["id"] == tool_id), None)
if tool is None:
    raise SystemExit(f"unknown tool id: {tool_id}")
value = tool
for part in expression.split("."):
    value = value.get(part) if isinstance(value, dict) else None
    if value is None:
        break
if value is not None:
    print(value)
PY
}

record_receipt() {
  local tool_id="$1"
  local version="$2"
  local path="$3"
  local digest="$4"
  local integrity="$5"
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$tool_id" "$version" "$path" "$digest" "$integrity" >>"$RECEIPT_TSV"
}

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if ((DRY_RUN == 0)); then
    "$@"
  fi
}

download_tool() {
  local tool_id="$1"
  local filename="$2"
  local version url expected target actual integrity
  version="$(lock_value "$tool_id" version)"
  url="$(lock_value "$tool_id" artifact.url)"
  expected="$(lock_value "$tool_id" artifact.sha256)"
  [[ -n "$version" && -n "$url" ]] || {
    printf 'Lock has no downloadable artifact for %s\n' "$tool_id" >&2
    exit 2
  }
  target="$DOWNLOAD_DIR/$filename"
  if [[ ! -f "$target" ]]; then
    run curl --fail --location --retry 3 --output "$target" "$url"
  else
    printf 'Using existing download: %s\n' "$target"
  fi
  if ((DRY_RUN)); then
    return 0
  fi
  actual="$(sha256sum "$target" | awk '{print $1}')"
  if [[ -n "$expected" ]]; then
    [[ "$actual" == "$expected" ]] || {
      printf 'Checksum mismatch for %s: expected %s, got %s\n' \
        "$tool_id" "$expected" "$actual" >&2
      exit 4
    }
    integrity="publisher-checksum-verified"
  else
    integrity="locally-recorded-no-publisher-checksum"
  fi
  record_receipt "$tool_id" "$version" "$target" "$actual" "$integrity"
}

write_wrapper() {
  local path="$1"
  shift
  if ((DRY_RUN)); then
    printf 'Would write wrapper: %s\n' "$path"
    return
  fi
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -Eeuo pipefail\n'
    printf 'exec'
    printf ' %q' "$@"
    printf ' "$@"\n'
  } >"$path"
  chmod 0755 "$path"
}

write_ghidra_version_wrapper() {
  local path="$1"
  local ghidra_root="$2"
  local properties="$ghidra_root/Ghidra/application.properties"
  if ((DRY_RUN)); then
    printf 'Would write Ghidra version wrapper: %s\n' "$path"
    return
  fi
  [[ -f "$properties" ]] || {
    printf 'Ghidra application properties not found: %s\n' "$properties" >&2
    exit 5
  }
  cat >"$path" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
version="\$(sed -n 's/^application.version=//p' '$properties' | head -n 1)"
[[ -n "\$version" ]] || { echo 'Unable to read Ghidra version.' >&2; exit 1; }
printf 'Ghidra %s\\n' "\$version"
EOF
  chmod 0755 "$path"
}

: >"$RECEIPT_TSV"
printf 'tool_id\tversion\tpath\tsha256\tintegrity\n' >>"$RECEIPT_TSV"

jadx_version="$(lock_value jadx version)"
download_tool jadx "jadx-$jadx_version.zip"
if ((DRY_RUN == 0)); then
  rm -rf "$OPT_DIR/jadx-$jadx_version"
  mkdir -p "$OPT_DIR/jadx-$jadx_version"
  unzip -q "$DOWNLOAD_DIR/jadx-$jadx_version.zip" -d "$OPT_DIR/jadx-$jadx_version"
  ln -sfn "$OPT_DIR/jadx-$jadx_version/bin/jadx" "$BIN_DIR/jadx"
  ln -sfn "$OPT_DIR/jadx-$jadx_version/bin/jadx-gui" "$BIN_DIR/jadx-gui"
fi

apktool_version="$(lock_value apktool version)"
download_tool apktool "apktool-$apktool_version.jar"
write_wrapper "$BIN_DIR/apktool" java -jar "$DOWNLOAD_DIR/apktool-$apktool_version.jar"

baksmali_version="$(lock_value baksmali version)"
download_tool baksmali "baksmali-$baksmali_version-fat-release.jar"
write_wrapper "$BIN_DIR/baksmali" java -jar \
  "$DOWNLOAD_DIR/baksmali-$baksmali_version-fat-release.jar"

bundletool_version="$(lock_value bundletool version)"
download_tool bundletool "bundletool-$bundletool_version.jar"
write_wrapper "$BIN_DIR/bundletool" java -jar "$DOWNLOAD_DIR/bundletool-$bundletool_version.jar"

if ((WITH_GHIDRA)); then
  ghidra_version="$(lock_value ghidra version)"
  download_tool ghidra "ghidra-$ghidra_version.zip"
  if ((DRY_RUN == 0)); then
    rm -rf "$OPT_DIR/ghidra-$ghidra_version"
    mkdir -p "$OPT_DIR/ghidra-$ghidra_version"
    unzip -q "$DOWNLOAD_DIR/ghidra-$ghidra_version.zip" -d "$OPT_DIR/ghidra-$ghidra_version"
    ghidra_root="$(find "$OPT_DIR/ghidra-$ghidra_version" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    [[ -n "$ghidra_root" ]] || {
      printf 'Unable to locate unpacked Ghidra directory.\n' >&2
      exit 5
    }
    ln -sfn "$ghidra_root/ghidraRun" "$BIN_DIR/ghidraRun"
    ln -sfn "$ghidra_root/support/analyzeHeadless" "$BIN_DIR/analyzeHeadless"
    write_ghidra_version_wrapper "$BIN_DIR/ghidra-version" "$ghidra_root"
  else
    write_ghidra_version_wrapper "$BIN_DIR/ghidra-version" \
      "$OPT_DIR/ghidra-$ghidra_version/ghidra_$ghidra_version"
  fi
fi

frida_version="$(lock_value frida version)"
frida_tools_version="$(lock_value frida-tools version)"
if ((DRY_RUN)); then
  printf 'Would create Python virtual environment and install frida==%s frida-tools==%s.\n' \
    "$frida_version" "$frida_tools_version"
else
  python3 -m venv "$INSTALL_DIR/venv"
  "$INSTALL_DIR/venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip
  "$INSTALL_DIR/venv/bin/python" -m pip install --disable-pip-version-check \
    "frida==$frida_version" \
    "frida-tools==$frida_tools_version"
  for executable in frida frida-ps frida-trace frida-discover frida-kill; do
    if [[ -x "$INSTALL_DIR/venv/bin/$executable" ]]; then
      ln -sfn "$INSTALL_DIR/venv/bin/$executable" "$BIN_DIR/$executable"
    fi
  done
  "$INSTALL_DIR/venv/bin/python" - <<'PY' >>"$RECEIPT_TSV"
import hashlib
import importlib.metadata

for distribution_name in ("frida", "frida-tools"):
    distribution = importlib.metadata.distribution(distribution_name)
    version = distribution.version
    metadata_path = next(
        (
            distribution.locate_file(item)
            for item in (distribution.files or [])
            if str(item).endswith(".dist-info/METADATA")
        ),
        None,
    )
    if metadata_path is not None and metadata_path.is_file():
        digest = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
        path = str(metadata_path)
    else:
        digest = "n/a"
        path = "distribution-metadata-unavailable"
    print(f"{distribution_name}\t{version}\t{path}\t{digest}\tinstalled-distribution-metadata")
PY
fi

if ((DRY_RUN == 0)); then
  python3 - "$RECEIPT_TSV" "$INSTALL_DIR/bootstrap-receipt.json" <<'PY'
import csv
import json
import sys

source, destination = sys.argv[1:]
with open(source, encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream, delimiter="\t"))
with open(destination, "w", encoding="utf-8") as stream:
    json.dump({"schemaVersion": 1, "artifacts": rows}, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
fi

cat <<EOF
Bootstrap complete.

Add to PATH:
  export RE_TOOLCHAIN_HOME="$INSTALL_DIR"
  export PATH="$BIN_DIR:\$PATH"

Still required for the full profile:
  - Android SDK Platform-Tools 37.0.1
  - Perfetto trace_processor_shell 55.3 for the current host
  - Node.js 24
EOF
if ((WITH_GHIDRA == 0)); then
  printf '  - Ghidra 12.1.2 (rerun with --with-ghidra)\n'
fi
cat <<EOF

Verify with:
  python3 "$SCRIPT_DIR/verify-re-toolchain.py" --profile full --strict --include-host-utilities
EOF
