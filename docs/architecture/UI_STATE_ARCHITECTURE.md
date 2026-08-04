# Preview, controls and UI state architecture

Status: executable interface specification for CAM-106.

The production activity currently uses a simple Android view hierarchy. This specification defines the state boundary that future UI work must follow without coupling presentation to CameraX, Camera2 or vendor backends.

## Evidence classification

- **VERIFIED:** The state types, reducer invariants, route presentation, accessibility behavior and tests described here are implemented.
- **PARTIALLY VERIFIED:** The current activity consumes the typed route presenter, but the complete activity has not yet migrated to the reducer.
- **HYPOTHESIS:** Final interaction timing, animations, haptics and visual layout require device and accessibility testing.
- **UNKNOWN:** Product-specific focus UI timing and processing-queue limits remain unknown until measured and user-tested.

## State separation

Camera/backend state and UI-owned state are different immutable objects.

`CameraBackendSnapshot` contains only camera facts supplied by the controller:

- runtime device capabilities;
- selected optical route;
- route decision and backend evidence;
- preview state;
- whether a session is ready;
- optional backend error.

`CameraUiState` contains only presentation and user-interaction state:

- foreground/background lifecycle;
- display orientation;
- focus/metering gesture state;
- immediate capture feedback;
- background-processing job count;
- selected capture profile;
- settings visibility;
- status text;
- latest persisted asset identifier.

`CameraUiReducer` consumes `UiEvent` and creates a new `CameraUiState`. It never accepts or mutates a backend object. Camera controllers replace the complete `CameraBackendSnapshot` when backend state changes.

`CameraScreenModel` combines both snapshots for rendering while retaining direct access to the separate source objects.

## Preview and lifecycle

`PreviewState` distinguishes:

- stopped;
- starting;
- streaming;
- paused;
- error.

A ready camera session requires an available route and a streaming preview. The shutter is disabled when:

- the application is not foreground;
- no camera session is ready;
- focus is actively being resolved;
- a capture or save operation is in progress.

Moving to background closes settings and cancels UI focus feedback. The controller remains responsible for unbinding or reopening camera resources.

## Orientation

`PreviewOrientation` accepts only 0, 90, 180 and 270 degrees after normalization. Android display rotation, sensor orientation and JPEG orientation remain controller/adaptor responsibilities; the UI state stores only the display-relative result.

## Focus and metering

`MeteringPoint` stores preview-normalized coordinates in `[0, 1]`, independent of pixels, cropping and rotation. `FocusMeteringState` distinguishes idle, requested, locked, failed and cancelled states.

A requested, locked or failed focus state must retain the exact metering point. Invalid coordinates fail before a backend request is constructed.

## Lens and zoom transparency

`RoutePresentation` derives all labels from `RouteDecision.support().rendering()`:

- `OPTICAL` → **Optical**
- `IN_SENSOR` → **In-sensor**
- `DIGITAL` → **Digital**
- `UNAVAILABLE` → **Unavailable**

The activity now uses this presenter for route buttons and accessibility descriptions. No available digital or in-sensor route can inherit a hardcoded optical label.

Unavailable controls remain selectable so users can inspect the exact reason rather than encountering a silent no-op.

## Capture feedback and background processing

Immediate capture feedback is separate from processing state:

```text
READY
→ CAPTURING
→ SAVING
→ SAVED
```

Errors are explicit. Invalid transitions, such as saving without a started capture or completing a nonexistent processing job, fail closed.

`processingJobCount` tracks persisted captures still undergoing on-device processing. It does not disable the shutter. Once the current asset is persisted, `CameraScreenModel.shutterEnabled()` may become true while previous jobs continue in the background, provided the session is ready and the app is foreground.

This contract supports responsive capture while processing continues without claiming that the current single-frame CameraX path already uses a background imaging pipeline.

## Capture modes and settings

Capture profile and settings visibility are UI-owned. Selecting `Quick`, `Auto` or `Max Detail` changes UI state and then requests the controller to apply the corresponding verified or planned capture behavior. Backend state is replaced separately when the session is recreated.

## Accessibility

Every route presentation supplies a non-empty accessibility label containing:

- route label;
- optical/in-sensor/digital/unavailable classification;
- the backend reason.

The shutter accessibility label explains why capture is unavailable or states when previous captures continue processing on device. Latest-photo and other controls retain explicit content descriptions.

## Current integration boundary

The activity uses `RoutePresentation` today. The reducer and screen model are ready for incremental migration of lifecycle, metering, capture feedback and processing-queue rendering. Android framework objects remain outside these pure Java contracts, allowing unit tests and future UI toolkit replacement without changing backend semantics.
