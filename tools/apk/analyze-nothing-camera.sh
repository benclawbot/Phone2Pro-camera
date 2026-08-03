#!/usr/bin/env bash
# Static analysis pipeline for Nothing Camera base/split APKs.
# The script reads local APK artifacts and writes only derived analysis output.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_ROOT="${PWD}/nothing-camera-analysis"
KEYWORDS_FILE="$SCRIPT_DIR/routing-keywords.txt"
MANIFEST_EXTRACTOR="$SCRIPT_DIR/extract-manifest-permissions.py"
RUN_JADX=1
RUN_APKTOOL=1
APKS=()

usage() {
  cat <<'EOF'
Usage: analyze-nothing-camera.sh [options] <base.apk> [split.apk ...]
       analyze-nothing-camera.sh [options] <directory-containing-apks>

Options:
  --output DIR       Analysis output root (default: ./nothing-camera-analysis)
  --keywords FILE   Search vocabulary (default: tools/apk/routing-keywords.txt)
  --no-jadx          Skip JADX decompilation
  --no-apktool       Skip apktool resource decoding
  -h, --help         Show help

Optional tools are used when present: python3, apksigner, apkanalyzer,
aapt2/aapt, jadx, apktool, zipinfo, unzip, file, readelf, nm, strings and
rg/grep. Python 3 enables the built-in binary-manifest and DEX reports.
EOF
}

while (($#)); do
  case "$1" in
    --output)
      OUT_ROOT="${2:?missing output directory}"
      shift 2
      ;;
    --keywords)
      KEYWORDS_FILE="${2:?missing keyword file}"
      shift 2
      ;;
    --no-jadx)
      RUN_JADX=0
      shift
      ;;
    --no-apktool)
      RUN_APKTOOL=0
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
      if [[ -d "$1" ]]; then
        while IFS= read -r -d '' apk; do APKS+=("$apk"); done \
          < <(find "$1" -maxdepth 1 -type f -name '*.apk' -print0 | sort -z)
      else
        APKS+=("$1")
      fi
      shift
      ;;
  esac
done

if ((${#APKS[@]} == 0)); then
  printf 'No APK files supplied.\n' >&2
  usage >&2
  exit 2
fi

for apk in "${APKS[@]}"; do
  if [[ ! -f "$apk" ]]; then
    printf 'APK not found: %s\n' "$apk" >&2
    exit 2
  fi
  case "$apk" in
    *.apk) ;;
    *) printf 'Not an APK filename: %s\n' "$apk" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$KEYWORDS_FILE" ]]; then
  printf 'Keyword file not found: %s\n' "$KEYWORDS_FILE" >&2
  exit 2
fi

command -v sha256sum >/dev/null 2>&1 || {
  printf 'sha256sum is required.\n' >&2
  exit 127
}
command -v unzip >/dev/null 2>&1 || {
  printf 'unzip is required.\n' >&2
  exit 127
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_ROOT%/}/$STAMP"
INPUT_DIR="$OUT_DIR/input-metadata"
UNPACKED_DIR="$OUT_DIR/unpacked"
NATIVE_DIR="$OUT_DIR/native-analysis"
REPORT_DIR="$OUT_DIR/reports"
JADX_DIR="$OUT_DIR/jadx"
APKTOOL_DIR="$OUT_DIR/apktool"
mkdir -p "$INPUT_DIR" "$UNPACKED_DIR" "$NATIVE_DIR" "$REPORT_DIR"

LOG_FILE="$OUT_DIR/analysis.log"
exec > >(tee -a "$LOG_FILE") 2>&1

printf 'Nothing Camera APK analysis\n'
printf '  UTC timestamp: %s\n' "$STAMP"
printf '  Output: %s\n' "$OUT_DIR"
printf '  APK count: %d\n' "${#APKS[@]}"

have() { command -v "$1" >/dev/null 2>&1; }

safe_name() {
  basename "$1" | tr -c 'A-Za-z0-9._-' '_'
}

run_optional() {
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

for apk in "${APKS[@]}"; do
  name="$(safe_name "$apk")"
  size="$(wc -c <"$apk" | tr -d ' ')"
  hash="$(sha256sum "$apk" | awk '{print $1}')"
  {
    printf 'path=%s\n' "$(cd "$(dirname "$apk")" && pwd)/$(basename "$apk")"
    printf 'size_bytes=%s\n' "$size"
    printf 'sha256=%s\n' "$hash"
  } >"$INPUT_DIR/$name.meta.txt"

  if have python3 && [[ -f "$MANIFEST_EXTRACTOR" ]]; then
    if python3 "$MANIFEST_EXTRACTOR" "$apk" \
      --json "$INPUT_DIR/$name.manifest-permissions.json"; then
      :
    else
      rc=$?
      printf 'manifest_permission_extractor_exit_code=%d\n' "$rc" \
        >"$INPUT_DIR/$name.manifest-permissions.error.txt"
    fi
  else
    printf 'python3 or manifest extractor unavailable\n' \
      >"$INPUT_DIR/$name.manifest-permissions.unavailable.txt"
  fi

  mkdir -p "$UNPACKED_DIR/$name"
  unzip -q -o "$apk" -d "$UNPACKED_DIR/$name" \
    >"$INPUT_DIR/$name.unzip.txt" 2>&1 || true

  if have zipinfo; then
    run_optional "$INPUT_DIR/$name.zipinfo.txt" zipinfo -l "$apk"
  else
    run_optional "$INPUT_DIR/$name.unzip-list.txt" unzip -l "$apk"
  fi

  if have apksigner; then
    run_optional "$INPUT_DIR/$name.apksigner.txt" \
      apksigner verify --verbose --print-certs "$apk"
  fi

  if have apkanalyzer; then
    run_optional "$INPUT_DIR/$name.manifest.xml" apkanalyzer manifest print "$apk"
    run_optional "$INPUT_DIR/$name.files.txt" apkanalyzer files list "$apk"
    run_optional "$INPUT_DIR/$name.dex-packages.txt" apkanalyzer dex packages "$apk"
  elif have aapt2; then
    run_optional "$INPUT_DIR/$name.badging.txt" aapt2 dump badging "$apk"
    run_optional "$INPUT_DIR/$name.xmltree-manifest.txt" \
      aapt2 dump xmltree "$apk" AndroidManifest.xml
  elif have aapt; then
    run_optional "$INPUT_DIR/$name.badging.txt" aapt dump badging "$apk"
    run_optional "$INPUT_DIR/$name.xmltree-manifest.txt" \
      aapt dump xmltree "$apk" AndroidManifest.xml
  fi
done

if ((RUN_JADX)) && have jadx; then
  mkdir -p "$JADX_DIR"
  JADX_ARGS=(
    --output-dir "$JADX_DIR"
    --deobf
    --show-bad-code
    --escape-unicode
    --threads-count "$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf 4)"
  )
  printf 'Running JADX...\n'
  jadx "${JADX_ARGS[@]}" "${APKS[@]}" >"$REPORT_DIR/jadx.log" 2>&1 || true
else
  printf 'JADX skipped or unavailable.\n'
fi

if ((RUN_APKTOOL)) && have apktool; then
  for apk in "${APKS[@]}"; do
    name="$(safe_name "$apk")"
    printf 'Running apktool for %s...\n' "$name"
    apktool d -f -o "$APKTOOL_DIR/$name" "$apk" \
      >"$REPORT_DIR/$name.apktool.log" 2>&1 || true
  done
else
  printf 'apktool skipped or unavailable.\n'
fi

if have python3; then
  printf 'Building method-level DEX routing index...\n'
  python3 "$SCRIPT_DIR/build-dex-routing-index.py" "${APKS[@]}" \
    --json "$REPORT_DIR/dex-routing-index.json" \
    --markdown "$REPORT_DIR/dex-routing-index.md" \
    >"$REPORT_DIR/dex-routing-index.log" 2>&1 || true
else
  printf 'DEX routing index skipped: python3 unavailable.\n'
fi

if have python3; then
  printf 'Extracting Galaga Expert/manual route...\n'
  python3 "$SCRIPT_DIR/extract-galaga-expert-route.py" "${APKS[@]}" \
    --json "$REPORT_DIR/galaga-expert-route.json" \
    --markdown "$REPORT_DIR/galaga-expert-route.md" \
    --allow-incomplete \
    >"$REPORT_DIR/galaga-expert-route.log" 2>&1 || true
else
  printf 'Galaga Expert route extraction skipped: python3 unavailable.\n'
fi

while IFS= read -r -d '' library; do
  relative="${library#"$UNPACKED_DIR/"}"
  safe="$(printf '%s' "$relative" | tr '/ ' '__')"
  {
    printf 'path=%s\n' "$relative"
    printf 'size_bytes=%s\n' "$(wc -c <"$library" | tr -d ' ')"
    printf 'sha256=%s\n' "$(sha256sum "$library" | awk '{print $1}')"
    if have file; then file "$library"; fi
  } >"$NATIVE_DIR/$safe.meta.txt"

  if have readelf; then
    run_optional "$NATIVE_DIR/$safe.elf-header.txt" readelf -h -l -d "$library"
    run_optional "$NATIVE_DIR/$safe.symbols.txt" readelf -Ws "$library"
    run_optional "$NATIVE_DIR/$safe.notes.txt" readelf -n "$library"
  elif have nm; then
    run_optional "$NATIVE_DIR/$safe.symbols.txt" nm -D -C "$library"
  fi

  if have strings; then
    run_optional "$NATIVE_DIR/$safe.strings.txt" strings -a -n 5 "$library"
  fi
done < <(find "$UNPACKED_DIR" -type f -name '*.so' -print0 | sort -z)

if have strings; then
  while IFS= read -r -d '' artifact; do
    relative="${artifact#"$UNPACKED_DIR/"}"
    safe="$(printf '%s' "$relative" | tr '/ ' '__')"
    run_optional "$REPORT_DIR/$safe.strings.txt" strings -a -n 5 "$artifact"
  done < <(find "$UNPACKED_DIR" -type f \( -name '*.dex' -o -name '*.jar' -o -name '*.bin' \) -print0 | sort -z)
fi

SEARCH_ROOTS=()
[[ -d "$JADX_DIR" ]] && SEARCH_ROOTS+=("$JADX_DIR")
[[ -d "$APKTOOL_DIR" ]] && SEARCH_ROOTS+=("$APKTOOL_DIR")
SEARCH_ROOTS+=("$REPORT_DIR" "$NATIVE_DIR")

if have rg; then
  rg --no-heading --line-number --text --ignore-case \
    --fixed-strings -f "$KEYWORDS_FILE" "${SEARCH_ROOTS[@]}" \
    >"$REPORT_DIR/routing-keyword-hits.txt" 2>"$REPORT_DIR/routing-keyword-hits.stderr.txt" || true
else
  : >"$REPORT_DIR/routing-keyword-hits.txt"
  while IFS= read -r keyword; do
    [[ -n "$keyword" ]] || continue
    grep -R -I -n -i -F -- "$keyword" "${SEARCH_ROOTS[@]}" \
      >>"$REPORT_DIR/routing-keyword-hits.txt" 2>/dev/null || true
  done <"$KEYWORDS_FILE"
fi

find "$JADX_DIR" -type f 2>/dev/null | sort >"$REPORT_DIR/jadx-files.txt" || true
find "$APKTOOL_DIR" -type f 2>/dev/null | sort >"$REPORT_DIR/apktool-files.txt" || true
find "$UNPACKED_DIR" -type f 2>/dev/null | sort >"$REPORT_DIR/archive-files.txt" || true

if [[ -d "$JADX_DIR" ]] && have rg; then
  rg --no-heading --line-number --text \
    'System\.loadLibrary|native [A-Za-z0-9_<>, ?\[\]]+ [A-Za-z0-9_$]+\(|registerNatives|JNI_OnLoad' \
    "$JADX_DIR" >"$REPORT_DIR/jni-native-hits.txt" 2>/dev/null || true
  rg --no-heading --line-number --text \
    'CaptureRequest\.(Key|Builder)|SessionConfiguration|OutputConfiguration|CameraManager|CameraDevice|CameraCaptureSession' \
    "$JADX_DIR" >"$REPORT_DIR/camera2-call-sites.txt" 2>/dev/null || true
fi

{
  printf 'schemaVersion: 1\n'
  printf 'generatedAtUtc: %s\n' "$STAMP"
  printf 'inputs:\n'
  for apk in "${APKS[@]}"; do
    printf '  - path: %q\n' "$(cd "$(dirname "$apk")" && pwd)/$(basename "$apk")"
    printf '    sizeBytes: %s\n' "$(wc -c <"$apk" | tr -d ' ')"
    printf '    sha256: %s\n' "$(sha256sum "$apk" | awk '{print $1}')"
  done
  printf 'tools:\n'
  for tool in python3 apksigner apkanalyzer aapt2 aapt jadx apktool zipinfo unzip file readelf nm strings rg grep; do
    if have "$tool"; then
      version="$($tool --version 2>&1 | head -n 1 || true)"
      printf '  %s: %q\n' "$tool" "$version"
    else
      printf '  %s: unavailable\n' "$tool"
    fi
  done
  printf 'outputs:\n'
  while IFS= read -r -d '' file_path; do
    relative="${file_path#"$OUT_DIR/"}"
    printf '  - path: %q\n' "$relative"
    printf '    sizeBytes: %s\n' "$(wc -c <"$file_path" | tr -d ' ')"
    printf '    sha256: %s\n' "$(sha256sum "$file_path" | awk '{print $1}')"
  done < <(find "$OUT_DIR" -type f ! -name manifest.yaml -print0 | sort -z)
} >"$OUT_DIR/manifest.yaml"

printf '\nAnalysis complete: %s\n' "$OUT_DIR"
printf 'Start review with input-metadata/*.manifest-permissions.json, reports/galaga-expert-route.md, reports/dex-routing-index.md, reports/routing-keyword-hits.txt and reports/camera2-call-sites.txt.\n'
