# Device Evidence Collection

`collect-camera-platform.sh` creates a read-only evidence bundle from a connected CMF Phone 2 Pro or another Android device.

It is designed for CAM-001, CAM-002, CAM-020, CAM-050, CAM-051, CAM-052 and CAM-080 through CAM-085.

## Requirements

- Linux, macOS or WSL shell with Bash.
- Android Platform Tools with `adb` available in `PATH`.
- USB debugging enabled and the host authorized.
- `sha256sum`.
- Optional Android SDK `apksigner` for local APK certificate reports.

## Basic collection

```bash
chmod +x tools/device/collect-camera-platform.sh
./tools/device/collect-camera-platform.sh
```

The basic mode records build identity, package state, requested/granted permissions, app-ops, camera dumpsys data, visible services, provider/VINTF entries, processes, properties, loaded modules, binaries, libraries, permission XML matches and kernel identifiers.

Commands that are denied or absent are retained with their error text and exit code. A denied command can be useful evidence of a framework, filesystem or SELinux boundary.

## Include the stock camera APKs

```bash
./tools/device/collect-camera-platform.sh --pull-apks
```

This pulls every base/split APK path reported for `com.nothing.camera`. When `apksigner` is installed, the script also records certificate and verification output.

The APKs are proprietary device artifacts. Keep them in a controlled local evidence store and do not commit them to this public repository.

## Include readable configuration

```bash
./tools/device/collect-camera-platform.sh --pull-readable-config
```

This attempts to pull selected VINTF and permission directories using ordinary ADB access. It does not use `su`, remount partitions or change device policy.

Both optional modes may be combined:

```bash
./tools/device/collect-camera-platform.sh \
  --pull-apks \
  --pull-readable-config \
  --output "$HOME/phone2pro-evidence"
```

## Output structure

```text
<output>/<UTC timestamp>-<ADB serial>/
├── raw/                 command output
├── apks/                optional APKs and certificate reports
├── config/              optional readable configuration
├── collection.log
└── manifest.yaml        relative paths, sizes and SHA-256 hashes
```

## Minimum artifacts needed for Expert-routing analysis

After collection, prioritize:

1. `raw/package-dumpsys.txt`
2. `raw/package-paths.txt`
3. `raw/package-permissions.txt`
4. `raw/package-appops.txt`
5. `raw/camera-dumpsys.txt`
6. `raw/camera-service-list.txt`
7. `raw/vintf-camera.txt`
8. `raw/camera-permission-files.txt`
9. `raw/camera-processes.txt`
10. APKs and `*.apksigner.txt`, when collected

The first decision is whether Nothing Camera is granted `android.permission.SYSTEM_CAMERA` or another privileged path. The second is whether its runtime camera session opens system-only IDs `2`–`5` directly or opens public ID `0` with a proprietary logical/SAT configuration.

## Privacy and sharing

The bundle can include:

- ADB serial and device build identifiers;
- package certificate information;
- process and service state;
- logs containing package names and UIDs;
- proprietary APKs and configuration.

Review and redact the bundle before sharing. The repository should receive only hashes, normalized findings and legally redistributable source material unless a private evidence workflow is deliberately established.
