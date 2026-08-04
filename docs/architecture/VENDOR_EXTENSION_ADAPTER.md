# Vendor-extension adapter and safe fallback rules

Status: executable interface specification for CAM-108.

Vendor behavior is isolated from portable camera logic. No MediaTek or Nothing key is enabled from name discovery alone.

## Evidence classification

- **VERIFIED:** Build/probe gates, scope enforcement, runtime fallback rules and unit tests are implemented.
- **HYPOTHESIS:** Future feature-specific policies and timeouts remain design choices until measured.
- **UNKNOWN:** No MediaTek/Nothing feature is production-enabled by this change; exact safe values and effects remain feature- and build-specific.

## Exact-build allowlisting

`VendorBuildIdentity` contains manufacturer, model, device and full build fingerprint. A `VendorFeaturePolicy` must list exact identities; family-level matches are insufficient.

A feature is enabled only when:

1. a policy exists;
2. the current build exactly matches an allowlisted build;
3. an isolated probe exists for the same feature and build;
4. the probe status is `VERIFIED_SUPPORTED`;
5. the probe confidence is `VERIFIED`.

`REJECTED`, `TIMEOUT`, `VALUE_MISMATCH`, `INEFFECTIVE` and `UNKNOWN` all select the public fallback.

## Setting scope

Every `VendorSetting` declares `SESSION` or `PER_FRAME` scope. `VendorConfiguration` stores those settings in separate immutable lists and rejects any key supplied in the wrong phase.

Session settings must be applied before stream configuration by a vendor-specific adapter. Per-frame settings are supplied only to request builders. Portable capture code cannot move a setting between those phases.

## Adapter boundary

`VendorSettingsApplier` is the only bridge to Android/vendor objects:

```text
applySessionSettings(settings, timeout)
applyPerFrameSettings(settings, timeout)
```

The portable layer owns only build identities, policies, typed values, plans and results. Vendor-key construction, reflection and Camera2 interop stay inside an adapter implementation.

## Known public fallback

Every plan carries `PublicFallbackConfiguration.galagaMain()`:

```text
backend: public-main-camera2
Camera2 ID: 0
route: 1× main
rendering: OPTICAL
evidence: verified ordinary-app Galaga baseline
```

Fallback does not pretend to satisfy an auxiliary optical request. Higher layers must report the requested vendor feature as unavailable or degraded and identify the actual public main route.

## Runtime verification

Planning success is not enough. Runtime application returns one of:

- `APPLIED_AND_VERIFIED`
- `REJECTED`
- `TIMEOUT`
- `VALUE_MISMATCH`
- `INEFFECTIVE`
- `ERROR`

Only `APPLIED_AND_VERIFIED` within the feature timeout keeps the vendor policy active. Every other result discards active vendor settings and selects the known public configuration.

A result that reports success after the timeout is still treated as a timeout. A plan already in fallback state does not execute vendor code.

## Safety properties

- No generic device-family allowlist.
- No enablement from vendor-tag presence alone.
- No setting can migrate between session and request scope.
- No rejected, ineffective or mismatched result remains active.
- No timeout is ignored.
- No fallback plan retains partial vendor settings.
- The public fallback is known before vendor execution starts.
- Production code must log feature ID, build, status and non-sensitive evidence without image content.

## Current implementation boundary

This work provides the adapter contracts and policies. It does not enable an actual MediaTek/Nothing feature. Each future feature requires its own typed policy, isolated probe evidence, exact build entry and Android adapter implementation before registration.
