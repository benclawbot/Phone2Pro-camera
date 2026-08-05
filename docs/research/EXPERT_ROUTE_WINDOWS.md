# Windows 11 Expert-route trace capture

**Issue:** CAM-040 / #37  
**Host:** Windows 11 with Git Bash  
**Target:** CMF Phone 2 Pro (`Galaga`)

Use the portable wrapper on Windows instead of launching the synchronized runner directly:

```bash
tools/device/run-expert-route-perfetto-portable.sh \
  --route 06x \
  --mode camera2
```

The wrapper resolves the real Windows Frida executable before adding a temporary compatibility shim to `PATH`. The existing synchronized workflow then runs unchanged, while the shim captures Frida stdout and stderr continuously and flushes every line into `frida.log`.

## Why the portable wrapper exists

An interactive Frida CLI process terminated from Git Bash can exit before its `-o` output buffer is flushed. The resulting bundle can contain a valid Perfetto trace, CameraService log and photograph association but an empty `frida.log`. Exit status `137` is treated as a failed observer run, not as evidence that the stock app emitted no Camera2 events.

The durable wrapper instead:

- keeps the Frida REPL path, so current Frida tools continue supplying the Java bridge to loaded observer scripts;
- pipes the child process through a Python supervisor;
- writes and flushes output one line at a time;
- preserves launch and injection errors in `frida.log`;
- records `frida-runner-status.json` with exit status, line count, byte count and whether termination was forced;
- sends EOF to Frida when the operator presses Enter or Ctrl-D;
- uses terminate/kill only after a bounded graceful-detach timeout.

## Prerequisites

From Git Bash in the repository root:

```bash
adb get-state
adb shell pm path com.nothing.camera
adb shell command -v perfetto
frida --version
frida-ps -U
python3 --version
```

`python3` must resolve inside Git Bash. When the Windows launcher is available only as `python`, add a local `python3` shim before running the workflow.

## Interaction

For each assigned route:

1. Run the portable wrapper.
2. Enter Expert mode in Nothing Camera.
3. Select only the assigned lens.
4. Wait for preview stabilization.
5. Take one photograph.
6. Wait for completion and exit Nothing Camera.
7. Return to Git Bash and press **Enter**. Ctrl-D also produces a clean EOF.

Do not use Task Manager, `taskkill /F`, terminal-window closure or repeated Ctrl-C to stop Frida. Those paths can produce status 137 and discard buffered observer output.

## Required output checks

Before accepting a bundle, verify:

```bash
test -s traces/expert-routing/<run>/frida.log
cat traces/expert-routing/<run>/frida-runner-status.json
wc -l traces/expert-routing/<run>/camera-service.boottime.jsonl
```

A successful durable observer record should have:

- `processExitStatus` equal to `0` or an explicitly accepted clean-detach status;
- `forcedTermination` equal to `false`;
- positive `lineCount` and `outputBytes`;
- parseable observer events in `frida.log`;
- a non-empty normalized CameraService JSONL file when camera logcat was collected.

The raw image remains outside the trace bundle. Fill `output-association-template.json` from MediaStore and EXIF metadata only.
