# Camera authorization comparison

Status: deterministic evidence normalization for CAM-080.

## Engineering question

When an ordinary replacement build cannot reach Galaga system-camera endpoints,
which authorization layer is already known to differ from Nothing Camera?

The comparison must not collapse every failure into “privileged access.” It
separates:

1. normal `CAMERA` permission;
2. hidden `SYSTEM_CAMERA` permission;
3. camera AppOps state;
4. installation partition and privileged-app placement;
5. privapp allow/deny output;
6. package UID and flags;
7. observed SELinux process domain;
8. deeper CameraService, provider, HAL, or endpoint-specific enforcement.

## Run

First collect the read-only bundle:

```bash
bash tools/device/capture-camera-authorization.sh \
  --stock-package com.nothing.camera \
  --replacement-package com.phone2pro.camera \
  --output /private/camera-authorization
```

Then normalize the newest capture:

```bash
python3 tools/device/analyze-camera-authorization.py \
  /private/camera-authorization \
  --json /private/camera-authorization/comparison.json \
  --markdown /private/camera-authorization/comparison.md
```

The input may also be one exact timestamped capture directory. Every package
directory in the bundle is normalized, including related-package directories
when a larger collection workflow has added them. `stock` and `replacement`
are the default comparison roles and may be overridden with `--stock-role` and
`--ordinary-role`.

## Primary-gate taxonomy

| ID | Meaning |
|---|---|
| `MISSING_CAMERA_PERMISSION` | The ordinary package lacks normal camera permission. |
| `CAMERA_PERMISSION_UNKNOWN` | The capture did not establish normal camera permission. |
| `MISSING_SYSTEM_CAMERA_GRANT` | Normal camera permission is granted, but `SYSTEM_CAMERA` is denied. |
| `SYSTEM_CAMERA_GRANT_UNKNOWN` | The hidden grant could not be established. |
| `CAMERA_APPOP_DENIED` | Both grants exist, but camera AppOps is denied or ignored. |
| `CAMERA_APPOP_UNKNOWN` | Permission parity exists, but AppOps evidence is incomplete. |
| `PERMISSION_PARITY_DEEPER_GATE_REQUIRED` | Permission/AppOps evidence no longer explains a failure; inspect service, SELinux, provider, or HAL enforcement. |

## Evidence classification

### VERIFIED

Direct command output may establish that one package has a permission, AppOp,
allowlist entry, UID, install path, or process domain while another does not.

### PARTIALLY VERIFIED

The primary-gate result identifies the first observed difference. It does not
prove that satisfying that layer would make an endpoint usable.

### UNKNOWN

The comparison does not prove successful enumeration, characteristics access,
open, session creation, request submission, physical sensor activation, or
capture. Those require a separate controlled endpoint experiment with exact
errors and output verification.

## Production consequence

`GalagaSystemCameraBackend` must remain fail-closed while the replacement
package lacks an independently reproduced authorization path. A static route
mapping and a stock-only permission grant are capability evidence, not a lawful
permission bypass.
