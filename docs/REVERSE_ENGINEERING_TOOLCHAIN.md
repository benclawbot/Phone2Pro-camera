# Reproducible reverse-engineering toolchain

Status: pinned host-tool specification for CAM-004.

The authoritative machine-readable lock is:

```text
config/reverse-engineering-toolchain.json
```

It records the selected versions, profiles, version probes, official sources,
artifact locations and available integrity information. The lock was reviewed
on 2026-08-03 and must be changed in a dedicated pull request when a tool is
upgraded.

## Locked versions

| Tool | Version | Primary role |
|---|---:|---|
| Python | 3.12.x | repository automation and evidence parsers |
| OpenJDK | 21 | JADX, Apktool, bundletool and Ghidra runtime |
| JADX | 1.5.5 | high-level APK/DEX decompilation and call-site navigation |
| Apktool | 3.0.2 | binary resources, manifest and resource-table decoding |
| baksmali | 3.0.9 | instruction-level DEX disassembly |
| Ghidra | 12.1.2 | ELF/native analysis and headless scripts |
| Android Platform-Tools / adb | 37.0.1 | device acquisition and runtime evidence |
| bundletool | 1.18.3 | Android App Bundle and split-APK inspection |
| Frida Python bindings | 17.16.0 | host/device instrumentation protocol |
| Frida CLI tools | 14.10.4 | runtime hook control and process inspection |
| Perfetto | 55.3 | trace capture and `trace_processor_shell` analysis |
| Node.js | 24.x | Frida JavaScript syntax validation |

Host utilities are listed separately in the lock because their exact versions
normally come from the base operating-system image. Evidence runs must still
record their resolved version output in the generated analysis manifest.

## Verify an existing workstation

A non-strict inventory always exits successfully unless the lock is malformed:

```bash
python3 tools/toolchain/verify-re-toolchain.py \
  --profile full \
  --include-host-utilities \
  --json /private/output/re-toolchain-report.json
```

Use strict mode for an evidence-producing workstation:

```bash
python3 tools/toolchain/verify-re-toolchain.py \
  --profile full \
  --strict \
  --include-host-utilities
```

Available profiles:

```text
static    APK, DEX, resource and native-binary analysis
device    ADB acquisition and device-state evidence
dynamic   Frida and Perfetto runtime tracing
firmware  firmware, service and native-library analysis
full      all project reverse-engineering capabilities
```

Tools outside `PATH` can be supplied without editing the lock:

```bash
python3 tools/toolchain/verify-re-toolchain.py \
  --profile static \
  --strict \
  --tool jadx=/opt/jadx/bin/jadx \
  --tool ghidra=/opt/ghidra/bin/ghidra-version
```

The equivalent environment variable is `RE_TOOL_<ID>`, uppercased with dashes
replaced by underscores, for example `RE_TOOL_ANDROID_PLATFORM_TOOLS`.

## Bootstrap a clean host

The bootstrap installs the host-independent tools under a repository-local
prefix and writes both TSV and JSON receipts containing versions, paths,
SHA-256 digests and integrity classification.

Preview the operation:

```bash
bash tools/toolchain/bootstrap-re-toolchain.sh --dry-run
```

Install JADX, Apktool, baksmali, bundletool and Frida:

```bash
bash tools/toolchain/bootstrap-re-toolchain.sh \
  --install-dir "$PWD/.re-toolchain"

export RE_TOOLCHAIN_HOME="$PWD/.re-toolchain"
export PATH="$RE_TOOLCHAIN_HOME/bin:$PATH"
```

Include Ghidra and its non-GUI `ghidra-version` probe:

```bash
bash tools/toolchain/bootstrap-re-toolchain.sh \
  --install-dir "$PWD/.re-toolchain" \
  --with-ghidra
```

The bootstrap enforces a publisher-supplied checksum when one exists in the
lock. When an official release asset has no published checksum, it records the
locally observed digest as `locally-recorded-no-publisher-checksum`. Such an
artifact is reproducible only when the receipt is retained with the experiment;
it is not equivalent to a publisher-authenticated digest.

The following remain explicit host steps for the full profile:

- install Android Platform-Tools 37.0.1 with `sdkmanager` and verify `adb`;
- install the official Perfetto 55.3 prebuilt matching the host, or build tag
  `v55.3` and record the binary digest;
- install Node.js 24.x.

## Container path

A strict static-analysis baseline can be built with Docker or Podman:

```bash
podman build \
  -f containers/re-toolchain/Containerfile \
  -t phone2pro-re-toolchain:2026-08-03 .

podman run --rm \
  -v "$PWD:/workspace:ro" \
  phone2pro-re-toolchain:2026-08-03 \
  --profile static --strict --include-host-utilities
```

The image installs JADX, Apktool, baksmali, bundletool, Frida and Ghidra, then
uses the lock verifier as its entrypoint. A successful default container run is
the clean-environment static baseline. ADB USB access, Perfetto host prebuilts,
Node.js and device-side Frida components remain outside the image because they
are host- or device-specific; mount them and use `--tool` overrides for device,
dynamic, firmware or full profiles.

## Baseline commands

APK and DEX analysis:

```bash
bash tools/apk/analyze-nothing-camera.sh \
  --output /private/output/nothing-camera-analysis \
  /private/input/Camera.apk

jadx --output-dir /private/output/jadx --deobf /private/input/Camera.apk
apktool d -f -o /private/output/apktool /private/input/Camera.apk
baksmali disassemble /private/input/classes.dex -o /private/output/smali
```

Native analysis:

```bash
file /private/input/libcamera.so
readelf -h -l -d -n -Ws /private/input/libcamera.so
strings -a -n 5 /private/input/libcamera.so
analyzeHeadless /private/output/ghidra Phone2Pro \
  -import /private/input/libcamera.so \
  -overwrite -analysisTimeoutPerFile 1800
```

Device and trace acquisition:

```bash
bash tools/device/capture-camera-authorization.sh \
  --serial DEVICE_SERIAL \
  --output /private/output/camera-authorization

frida-ps -Uai
trace_processor_shell query /private/input/trace.perfetto-trace \
  'select * from metadata'
```

## Interpretation and limitations

No single decompiler is authoritative.

- JADX reconstructs Java-like control flow and names; compiler transformations,
  obfuscation, invalid bytecode and decompiler recovery can produce plausible
  but incorrect source. Confirm decisive values and branches against DEX
  instructions or runtime traces.
- Apktool decodes resources for analysis. Rebuilding is not expected to be
  byte-identical and framework-resource selection can affect output.
- baksmali is the instruction-level reference for DEX, but it does not restore
  original source constructs or identifiers. Google v3 uses the
  `com.android.tools.smali` namespace and must not be mixed with `org.jf` v2
  libraries in one process.
- Ghidra signatures, types and control-flow recovery are hypotheses until
  supported by symbols, relocation/import evidence, call sites or runtime
  observations. Auto-analysis options and processor definitions must be
  retained with exported projects.
- Frida host bindings and device server must use the same core version. Hook
  success proves observation at the hooked boundary only; it does not prove
  downstream HAL behavior.
- Perfetto visibility depends on firmware data sources, tracing permissions and
  configuration. Absence from a trace is not proof that an event did not occur.
- ADB output is build-, user- and authorization-specific. Every capture must
  record serial, fingerprint, package versions, user ID and command exit codes.
- bundletool describes bundle/split packaging. It does not replace analysis of
  the exact installed APK set acquired from the tested device.

All generated reports and tool receipts must be stored with immutable input
hashes under the experiment record. Tool upgrades require regenerating the
baseline and recording any changed output before conclusions are carried
forward.
