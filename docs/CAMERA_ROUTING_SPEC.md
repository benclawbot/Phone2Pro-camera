# Camera routing specification

The authoritative machine-readable route map is [`spec/camera-routing-spec.v1.json`](../spec/camera-routing-spec.v1.json).

## Status meanings

- `COMPLETE`: the route is represented from trigger through endpoint/session to output without an unknown transition.
- `BOUNDED`: the known steps are ordered and evidenced, and `opaqueBoundary` identifies the exact unresolved transition.
- `UNAVAILABLE`: no verified ordinary-app route exists; privilege requirements and a transparent fallback are mandatory.

## Route families

The specification deliberately keeps these paths separate:

- stock Expert 0.6×, 1× and 2× selection;
- external widget or shortcut handoff to the stock camera;
- ordinary-app direct Camera2 IDs 0 and 1;
- public zoom/crop on ID 0;
- replacement-app ultrawide and telephoto requests.

A stock-camera handoff is not treated as direct Camera2 access. Public zoom/crop remains digital unless independent sensor evidence proves otherwise. A main-camera fallback cannot be labelled as an auxiliary optical route.

## Validation

Run:

```sh
python3 tools/validate-routing-spec.py
```

The validator checks route IDs, ordered steps, evidence paths, opaque boundaries, privilege rules, fallback references, unresolved issue links, and optical/digital truthfulness.

Firmware or stock-camera changes require a new routing version or an explicit update to the current build scope. Unknown endpoint IDs, sensor scenarios, SAT decisions, and active physical sensors remain linked to their active research issues.
