#!/usr/bin/env bash
# Collect a read-only camera-platform evidence bundle from an attached Android device.
#
# The script does not require root and does not change device settings. Some commands
# may fail because Android intentionally restricts access; failures are retained as
# evidence rather than hidden.

set -Eeuo pipefail

PACKAGE="com.nothing.camera"
PULL_APKS=0
PULL_READABLE_CONFIG=0
OUT_ROOT="${PWD}/camera-platform-evidence"

usage() {
  cat <<'EOF'
Usage: collect-camera-platform.sh [options]

Options:
  --package NAME            Stock camera package (default: com.nothing.camera)
  --output DIR              Evidence output root (default: ./camera-platform-evidence)
  --pull-apks               Pull all APK paths reported by PackageManager
  --pull-readable-config    Pull selected readable camera/VINTF/permission configuration
  -h, --help                Show this help

The output may contain device identifiers, package certificates, logs and proprietary
binaries. Review it before sharing and do not commit raw bundles to a public repository.
EOF
}

while (($#)); do
  case "$1" in
    --package)
      PACKAGE="${2:?missing package name}"
      shift 2
      ;;
    --output)
      OUT_ROOT="${2:?missing output directory}"
      shift 2
      ;;
    --pull-apks)
      PULL_APKS=1
      shift
      ;;
    --pull-readable-config)
      PULL_READABLE_CONFIG=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$1" >&2
    exit 127
  }
}

require_command adb
require_command sha256sum

adb start-server >/dev/null
adb wait-for-device

SERIAL="$(adb get-serialno 2>/dev/null || true)"
if [[ -z "$SERIAL" || "$SERIAL" == "unknown" ]]; then
  printf 'No usable Android device is connected.\n' >&2
  exit 1
fi

STATE="$(adb get-state 2>/dev/null || true)"
if [[ "$STATE" != "device" ]]; then
  printf 'ADB device is not authorized/ready (state: %s).\n' "$STATE" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_SERIAL="$(printf '%s' "$SERIAL" | tr -c 'A-Za-z0-9._-' '_')"
OUT_DIR="${OUT_ROOT%/}/${STAMP}-${SAFE_SERIAL}"
RAW_DIR="$OUT_DIR/raw"
APK_DIR="$OUT_DIR/apks"
CONFIG_DIR="$OUT_DIR/config"
LOG_FILE="$OUT_DIR/collection.log"
mkdir -p "$RAW_DIR" "$APK_DIR" "$CONFIG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

printf 'Collecting camera platform evidence\n'
printf '  UTC timestamp: %s\n' "$STAMP"
printf '  Device serial: %s\n' "$SERIAL"
printf '  Package: %s\n' "$PACKAGE"
printf '  Output: %s\n' "$OUT_DIR"

run_host() {
  local name="$1"
  shift
  local output="$RAW_DIR/$name"
  {
    printf '# host command:'
    printf ' %q' "$@"
    printf '\n# collected_utc: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    "$@"
  } >"$output" 2>&1 || {
    local rc=$?
    printf '\n# command_exit_code: %d\n' "$rc" >>"$output"
    return 0
  }
}

run_shell() {
  local name="$1"
  local command="$2"
  local output="$RAW_DIR/$name"
  {
    printf '# device command: %s\n' "$command"
    printf '# collected_utc: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    adb shell "$command"
  } >"$output" 2>&1 || {
    local rc=$?
    printf '\n# command_exit_code: %d\n' "$rc" >>"$output"
    return 0
  }
}

# Host/device identity and immutable build context.
run_host "adb-version.txt" adb version
run_shell "device-id.txt" "id; getenforce; uname -a; cat /proc/version 2>/dev/null"
run_shell "getprop.txt" "getprop"
run_shell "build-context.txt" "printf 'fingerprint='; getprop ro.build.fingerprint; printf 'release='; getprop ro.build.version.release; printf 'sdk='; getprop ro.build.version.sdk; printf 'security_patch='; getprop ro.build.version.security_patch; printf 'product='; getprop ro.product.name; printf 'device='; getprop ro.product.device; printf 'model='; getprop ro.product.model; printf 'hardware='; getprop ro.hardware; printf 'kernel='; uname -r"

# Package identity, paths, permissions, grants and signing metadata exposed by PackageManager.
run_shell "package-dumpsys.txt" "dumpsys package '$PACKAGE'"
run_shell "package-paths.txt" "pm path '$PACKAGE'"
run_shell "package-list-entry.txt" "cmd package list packages -f -U --show-versioncode | grep -F '$PACKAGE' || true"
run_shell "package-permissions.txt" "cmd package get-package-info '$PACKAGE' 2>&1 || true; dumpsys package '$PACKAGE' | sed -n '/requested permissions:/,/install permissions:/p; /install permissions:/,/User 0:/p; /User 0:/,/Dexopt state:/p'"
run_shell "package-apex-and-libraries.txt" "dumpsys package '$PACKAGE' | grep -E -i 'usesLibrary|uses-library|sharedUser|codePath|resourcePath|nativeLibrary|primaryCpuAbi|secondaryCpuAbi|pkgFlags|privateFlags|signatures|SigningInfo' || true"
run_shell "package-appops.txt" "cmd appops get '$PACKAGE' 2>&1 || true"
run_shell "package-role-holders.txt" "cmd role holders android.app.role.SYSTEM_CAMERA 2>&1 || true; cmd role holders android.app.role.CAMERA 2>&1 || true"

# Camera framework state and caller-visible inventory.
run_shell "camera-dumpsys.txt" "dumpsys media.camera 2>&1"
run_shell "camera-proxy-dumpsys.txt" "dumpsys media.camera.proxy 2>&1"
run_shell "camera-service-list.txt" "service list | grep -E -i 'camera|media|sensor|isp' || true"
run_shell "dumpsys-services.txt" "dumpsys -l | grep -E -i 'camera|media|sensor|isp' || true"
run_shell "camera-processes.txt" "ps -AZ | grep -E -i 'camera|cameraserver|provider|isp|mtkcam|sensor' || true"
run_shell "camera-properties.txt" "getprop | grep -E -i 'camera|cam\.|mtkcam|sensor|isp|eis|hdr' || true"
run_shell "camera-modules.txt" "cat /proc/modules 2>/dev/null | grep -E -i 'camera|imgsensor|cam_cal|lens|ois|flash|ccu|seninf|adaptor' || true"
run_shell "camera-devnodes.txt" "ls -laZ /dev 2>/dev/null | grep -E -i 'camera|cam|seninf|imgsensor|ccu|isp|v4l|media' || true"

# HAL/provider/VINTF inventory. lshal may be absent on AIDL-only builds.
run_shell "lshal-camera.txt" "lshal 2>&1 | grep -E -i 'camera|provider|isp|sensor' || true"
run_shell "service-manager-camera.txt" "cmd -l 2>/dev/null | grep -E -i 'camera|media|sensor|isp' || true"
run_shell "vintf-camera.txt" "for f in /vendor/etc/vintf/manifest.xml /vendor/etc/vintf/manifest/*.xml /odm/etc/vintf/manifest.xml /odm/etc/vintf/manifest/*.xml; do [ -r \"\$f\" ] || continue; echo \"===== \$f =====\"; grep -n -E -i -C 4 'camera|provider|isp|sensor' \"\$f\" || true; done"
run_shell "camera-binaries.txt" "for d in /vendor/bin /vendor/bin/hw /odm/bin /odm/bin/hw /system/bin /system_ext/bin; do [ -d \"\$d\" ] || continue; echo \"===== \$d =====\"; ls -laZ \"\$d\" 2>/dev/null | grep -E -i 'camera|provider|isp|mtkcam|sensor|ccu' || true; done"
run_shell "camera-libraries.txt" "for d in /vendor/lib64 /vendor/lib64/hw /odm/lib64 /odm/lib64/hw /system/lib64 /system_ext/lib64; do [ -d \"\$d\" ] || continue; echo \"===== \$d =====\"; ls -la \"\$d\" 2>/dev/null | grep -E -i 'camera|mtkcam|camhal|feature|isp|sensor|eis|mfnr|hdr' || true; done"

# Permission definitions and privileged allowlists. Only readable files are searched.
run_shell "camera-permission-files.txt" "for d in /system/etc/permissions /system_ext/etc/permissions /product/etc/permissions /vendor/etc/permissions /odm/etc/permissions; do [ -d \"\$d\" ] || continue; echo \"===== \$d =====\"; grep -R -n -E -i 'SYSTEM_CAMERA|$PACKAGE|camera' \"\$d\"/*.xml 2>/dev/null || true; done"
run_shell "package-seinfo.txt" "ps -AZ | grep -F '$PACKAGE' || true; dumpsys package '$PACKAGE' | grep -E -i 'seinfo|uid=|sharedUser|pkgFlags|privateFlags' || true"

# Kernel/source correlation data.
run_shell "kernel-build-id.txt" "uname -a; cat /proc/sys/kernel/osrelease 2>/dev/null; cat /proc/sys/kernel/version 2>/dev/null; getprop ro.kernel.version; getprop ro.bootimage.build.fingerprint; getprop ro.vendor.build.fingerprint; getprop ro.odm.build.fingerprint"
run_shell "loaded-module-metadata.txt" "for m in /sys/module/*; do n=\${m##*/}; case \"\$n\" in *cam*|*camera*|*imgsensor*|*seninf*|*ccu*|*isp*|*ois*|*lens*|*flash*) echo \"===== \$n =====\"; cat \"\$m/version\" 2>/dev/null || true; readlink -f \"\$m\" 2>/dev/null || true;; esac; done"

# Optional APK acquisition. Paths can include split APKs. Pull failures are logged.
if ((PULL_APKS)); then
  mapfile -t APK_PATHS < <(adb shell "pm path '$PACKAGE'" 2>/dev/null | tr -d '\r' | sed -n 's/^package://p')
  if ((${#APK_PATHS[@]} == 0)); then
    printf 'No APK paths returned for %s.\n' "$PACKAGE"
  else
    for remote in "${APK_PATHS[@]}"; do
      base="$(basename "$remote")"
      printf 'Pulling APK: %s\n' "$remote"
      adb pull "$remote" "$APK_DIR/$base" >"$APK_DIR/$base.pull.log" 2>&1 || true
    done
  fi

  if command -v apksigner >/dev/null 2>&1; then
    for apk in "$APK_DIR"/*.apk; do
      [[ -e "$apk" ]] || continue
      apksigner verify --verbose --print-certs "$apk" >"$apk.apksigner.txt" 2>&1 || true
    done
  else
    printf 'apksigner not found; certificate verification skipped.\n'
  fi
fi

# Optional pull of selected readable configuration files. This intentionally avoids
# broad partition copying and never escalates privileges.
if ((PULL_READABLE_CONFIG)); then
  CONFIG_PATHS=(
    /vendor/etc/vintf/manifest.xml
    /odm/etc/vintf/manifest.xml
    /vendor/etc/permissions
    /odm/etc/permissions
    /product/etc/permissions
    /system_ext/etc/permissions
  )
  for remote in "${CONFIG_PATHS[@]}"; do
    safe="$(printf '%s' "$remote" | sed 's#^/##; s#/#__#g')"
    printf 'Pulling readable configuration: %s\n' "$remote"
    adb pull "$remote" "$CONFIG_DIR/$safe" >"$CONFIG_DIR/$safe.pull.log" 2>&1 || true
  done
fi

# Manifest and cryptographic hashes. Hashes are generated last so the manifest covers
# every retained artifact except itself.
{
  printf 'schemaVersion: 1\n'
  printf 'collectedAtUtc: %s\n' "$STAMP"
  printf 'adbSerial: %s\n' "$SERIAL"
  printf 'package: %s\n' "$PACKAGE"
  printf 'pullApks: %s\n' "$PULL_APKS"
  printf 'pullReadableConfig: %s\n' "$PULL_READABLE_CONFIG"
  printf 'files:\n'
  while IFS= read -r -d '' file; do
    rel="${file#"$OUT_DIR/"}"
    size="$(wc -c <"$file" | tr -d ' ')"
    hash="$(sha256sum "$file" | awk '{print $1}')"
    printf '  - path: %q\n' "$rel"
    printf '    sizeBytes: %s\n' "$size"
    printf '    sha256: %s\n' "$hash"
  done < <(find "$OUT_DIR" -type f ! -name manifest.yaml -print0 | sort -z)
} >"$OUT_DIR/manifest.yaml"

printf '\nCollection complete: %s\n' "$OUT_DIR"
printf 'Review the bundle for personal/proprietary data before sharing.\n'
