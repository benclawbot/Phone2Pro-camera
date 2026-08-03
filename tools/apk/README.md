# Nothing Camera Static Analysis

`analyze-nothing-camera.sh` produces a repeatable static-analysis workspace from locally acquired base and split APKs.

## Run

```bash
chmod +x tools/apk/analyze-nothing-camera.sh
./tools/apk/analyze-nothing-camera.sh \
  --output "$HOME/phone2pro-analysis" \
  "$HOME/phone2pro-evidence/apks"
```

A directory argument loads every top-level `.apk` file in lexical order. Individual APK paths can also be supplied explicitly.

## Tooling

Required:

- Bash
- `sha256sum`
- `unzip`

Used when available:

- Android SDK `apksigner`
- Android SDK `apkanalyzer`, `aapt2` or `aapt`
- JADX
- apktool
- `readelf` or `nm`
- `strings`
- ripgrep (`rg`) or grep

The script records every available tool version in the output manifest. Missing optional tools reduce coverage but do not invalidate the remaining artifacts.

## Outputs

```text
<output>/<timestamp>/
├── input-metadata/      hashes, certificates, manifest/package reports
├── unpacked/            archive contents
├── jadx/                combined base/split decompilation
├── apktool/             per-APK resource decoding
├── native-analysis/     ELF metadata, symbols and strings
├── reports/             keyword, JNI and Camera2 call-site indexes
├── analysis.log
└── manifest.yaml
```

Start with:

- `reports/routing-keyword-hits.txt`
- `reports/camera2-call-sites.txt`
- `reports/jni-native-hits.txt`
- base APK manifest/certificate reports under `input-metadata/`

## Static-analysis priorities

1. Manifest permissions, privileged components and exported launch routes.
2. Camera ID constants and logical/SAT selection tables.
3. Expert-mode lens button handlers and state reducers.
4. `CameraManager.openCamera()` call sites and wrappers.
5. `SessionConfiguration` and output setup.
6. Vendor `CaptureRequest.Key` construction and write ordering.
7. Widget/shortcut focal parsing and state restoration.
8. JNI declarations, loaded libraries and native callbacks.
9. Device profiles, feature flags, overlays and Galaga-specific resources.

## Evidence handling

The base/split APKs are proprietary artifacts from the user's device. Keep them outside the public repository. Commit only hashes, independently written analysis, small legally appropriate excerpts where necessary, and machine-readable derived facts.

## Method-level DEX routing index

`build-dex-routing-index.py` parses APK or DEX bytecode directly and does not
require JADX. It identifies exact method identities, `const-string` references,
Camera2 invocations, application camera-open dispatchers, session-parameter
construction, physical-output selection and MediaTek/Nothing routing metadata.
It also builds a bounded reverse caller graph and models command/executor
callbacks through explicit synthetic edges.

```bash
python3 tools/apk/build-dex-routing-index.py \
  /private/path/Camera.apk \
  --json /private/output/dex-routing-index.json \
  --markdown /private/output/dex-routing-index.md \
  --max-caller-depth 8
```

The regular `analyze-nothing-camera.sh` pipeline now creates this report
automatically. The evidence class is `STATIC_REFERENCE_ONLY`: recovered symbols
and call paths do not establish runtime execution, privilege or optical output.

## Galaga Expert route extraction

```bash
python3 tools/apk/extract-galaga-expert-route.py \
  /private/path/Camera-16.1.01.93.20.apk \
  --json /private/output/galaga-expert-route.json \
  --markdown /private/output/galaga-expert-route.md
```

The extractor verifies the Galaga manual zoom table and the named integer
camera-ID dispatch boundary. It exits non-zero when the expected mapping or
required call-site checks change. `--allow-incomplete` is intended only for the
broader multi-APK inventory pipeline.
