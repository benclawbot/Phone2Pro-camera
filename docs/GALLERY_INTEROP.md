# Gallery and default photo-viewer integration

This is a requirement for the future production camera app. It is intentionally outside the diagnostics app.

## Required behavior

The camera screen has a small circular latest-photo thumbnail in the bottom-left position, matching the familiar behavior shown in the reference screenshots.

- After a JPEG is successfully written, the thumbnail updates immediately.
- The thumbnail always represents the latest successful capture from this app, not an uncommitted processing preview.
- Tapping it opens that specific `content://` image URI through Android's `ACTION_VIEW` intent.
- Android launches the user's selected/default photo viewer. If no default has been chosen, Android may present its normal app chooser.
- The viewer supplies its own native menus and actions, including share, edit, favorite/add-to, delete, details, and overflow actions.
- Returning from the viewer restores the camera screen and its prior mode/zoom state.
- If the photo was deleted or moved, the app clears the stale thumbnail and shows a placeholder.

## Storage model

- Final JPEGs are inserted through `MediaStore.Images`.
- Album path: `DCIM/Phone2Pro Camera`.
- The app uses `IS_PENDING` while writing and publishes only complete JPEGs.
- The stored MediaStore URI is retained as the latest-capture pointer.
- A thumbnail is loaded with `ContentResolver.loadThumbnail`.
- Because the app opens media it created itself, broad photo-library permission is not required for this interaction on modern Android versions.

## Scope boundary

The diagnostics app has one purpose: start the capability-measurement workflow and save its JSON report. It does not capture user photos or implement camera-screen, thumbnail, gallery, or viewer behavior.
