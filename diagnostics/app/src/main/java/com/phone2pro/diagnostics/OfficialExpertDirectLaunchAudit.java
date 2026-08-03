package com.phone2pro.diagnostics;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.database.Cursor;
import android.hardware.camera2.CameraManager;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Environment;
import android.os.SystemClock;
import android.provider.MediaStore;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;

final class OfficialExpertDirectLaunchAudit {
    private static final String EXTRA_PREFIX_MAIN_MODE =
            "android.intent.extras.CAMERA_PREFIX_MAIN_MODE";
    private static final String EXTRA_PREFIX_SUB_MODE =
            "android.intent.extras.CAMERA_PREFIX_SUB_MODE";
    private static final String EXTRA_PREFIX_FACING =
            "android.intent.extras.CAMERA_PREFIX_FACING";
    private static final String EXTRA_MAIN_MODE =
            "android.intent.extras.CAMERA_MAIN_MODE";
    private static final String EXTRA_SUB_MODE =
            "android.intent.extras.CAMERA_SUB_MODE";
    private static final String EXTRA_FACING =
            "android.intent.extras.CAMERA_FACING";

    private static final String OUTPUT_FOLDER =
            Environment.DIRECTORY_PICTURES
                    + "/Phone2Pro Diagnostics/Official Expert Direct Launch Audit";

    private static final StepSpec[] STEPS = {
            new StepSpec(2, "0.6x", 1.64, 15.0),
            new StepSpec(0, "1x", 5.56, 24.0),
            new StepSpec(3, "2x", 7.10, 50.0)
    };

    private static final String[] EXIF_TAGS = {
            "Make",
            "Model",
            "Software",
            "DateTimeOriginal",
            "SubSecTimeOriginal",
            "OffsetTimeOriginal",
            "ImageWidth",
            "ImageLength",
            "PixelXDimension",
            "PixelYDimension",
            "Orientation",
            "FocalLength",
            "FocalLengthIn35mmFilm",
            "DigitalZoomRatio",
            "LensMake",
            "LensModel",
            "LensSpecification",
            "FNumber",
            "ApertureValue",
            "ExposureTime",
            "PhotographicSensitivity",
            "ISOSpeedRatings",
            "BrightnessValue",
            "ExposureBiasValue",
            "WhiteBalance",
            "Flash",
            "MeteringMode",
            "SceneType",
            "SceneCaptureType",
            "CustomRendered"
    };

    private OfficialExpertDirectLaunchAudit() {
    }

    static Session prepare(Context context) throws Exception {
        Intent probe = new Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
        ResolveInfo resolved = context.getPackageManager().resolveActivity(
                probe,
                PackageManager.MATCH_DEFAULT_ONLY
        );
        if (resolved == null || resolved.activityInfo == null) {
            throw new IllegalStateException("No default still-camera activity resolved");
        }

        JSONArray availabilityEvents = new JSONArray();
        CameraManager cameraManager = context.getSystemService(CameraManager.class);
        CameraManager.AvailabilityCallback callback = null;
        if (cameraManager != null) {
            callback = new CameraManager.AvailabilityCallback() {
                @Override
                public void onCameraAvailable(String cameraId) {
                    appendAvailabilityEvent(availabilityEvents, cameraId, true);
                }

                @Override
                public void onCameraUnavailable(String cameraId) {
                    appendAvailabilityEvent(availabilityEvents, cameraId, false);
                }
            };
            cameraManager.registerAvailabilityCallback(context.getMainExecutor(), callback);
        }

        return new Session(
                resolved.activityInfo.packageName,
                resolved.activityInfo.name,
                System.currentTimeMillis(),
                SystemClock.elapsedRealtime(),
                cameraManager,
                callback,
                availabilityEvents
        );
    }

    static Intent prepareNextLaunch(Context context, Session session) throws Exception {
        if (session.currentStep != null) {
            throw new IllegalStateException("A direct-launch step is already active");
        }
        if (!hasNextStep(session)) {
            throw new IllegalStateException("All direct-launch steps are complete");
        }

        StepSpec spec = STEPS[session.nextStepIndex];
        long baselineImageId = latestImageId(context.getContentResolver());
        long launchEpochMillis = System.currentTimeMillis();
        long launchElapsedMillis = SystemClock.elapsedRealtime();
        int availabilityStartIndex = availabilityLength(session.availabilityEvents);

        Intent intent = new Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
        intent.setClassName(session.packageName, session.activityName);
        intent.putExtra(EXTRA_PREFIX_MAIN_MODE, "photo");
        intent.putExtra(EXTRA_PREFIX_SUB_MODE, "manual");
        intent.putExtra(EXTRA_PREFIX_FACING, String.valueOf(spec.cameraId));
        intent.putExtra(EXTRA_MAIN_MODE, "photo");
        intent.putExtra(EXTRA_SUB_MODE, "manual");
        intent.putExtra(EXTRA_FACING, spec.cameraId);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        JSONObject launchExtras = new JSONObject()
                .put(EXTRA_PREFIX_MAIN_MODE, "photo")
                .put(EXTRA_PREFIX_SUB_MODE, "manual")
                .put(EXTRA_PREFIX_FACING, String.valueOf(spec.cameraId))
                .put(EXTRA_MAIN_MODE, "photo")
                .put(EXTRA_SUB_MODE, "manual")
                .put(EXTRA_FACING, spec.cameraId);

        session.currentStep = new StepRuntime(
                spec,
                baselineImageId,
                launchEpochMillis,
                launchElapsedMillis,
                availabilityStartIndex,
                launchExtras
        );
        return intent;
    }

    static JSONObject finishCurrentStep(Context context, Session session) throws Exception {
        StepRuntime runtime = session.currentStep;
        if (runtime == null) {
            throw new IllegalStateException("No direct-launch step is active");
        }

        long returnEpochMillis = System.currentTimeMillis();
        long returnElapsedMillis = SystemClock.elapsedRealtime();
        List<MediaAsset> assets = waitForNewAssets(context, session, runtime);
        List<MediaAsset> primary = new ArrayList<>();
        List<MediaAsset> auxiliary = new ArrayList<>();
        for (MediaAsset asset : assets) {
            if (asset.isPrimaryStill()) {
                primary.add(asset);
            } else {
                auxiliary.add(asset);
            }
        }

        JSONObject step = new JSONObject();
        step.put("stepNumber", session.nextStepIndex + 1);
        step.put("expectedLensButton", runtime.spec.lensLabel);
        step.put("requestedCameraId", runtime.spec.cameraId);
        step.put("expectedPhysicalFocalLengthMm", runtime.spec.physicalFocalMm);
        step.put("expectedFocalLength35mmEquivalent", runtime.spec.equivalentFocalMm);
        step.put("officialCameraPackage", session.packageName);
        step.put("officialCameraComponent", session.packageName + "/" + session.activityName);
        step.put("launchIntentAction", MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
        step.put("launchExtras", runtime.launchExtras);
        step.put("baselineImageId", runtime.baselineImageId);
        step.put("launchEpochMillis", runtime.launchEpochMillis);
        step.put("launchElapsedRealtimeMillis", runtime.launchElapsedMillis);
        step.put("returnEpochMillis", returnEpochMillis);
        step.put("returnElapsedRealtimeMillis", returnElapsedMillis);
        step.put(
                "cameraAvailabilityEvents",
                availabilitySlice(session.availabilityEvents, runtime.availabilityStartIndex)
        );
        step.put("newMediaAssetCount", assets.size());
        step.put("newPrimaryStillCount", primary.size());
        step.put("newAuxiliaryAssetCount", auxiliary.size());

        JSONArray primaryJson = new JSONArray();
        for (MediaAsset asset : primary) {
            primaryJson.put(asset.toJson());
        }
        step.put("newPrimaryAssets", primaryJson);

        JSONArray auxiliaryJson = new JSONArray();
        for (MediaAsset asset : auxiliary) {
            auxiliaryJson.put(asset.toJson());
        }
        step.put("newAuxiliaryAssets", auxiliaryJson);

        if (!primary.isEmpty()) {
            JSONObject capture = inspectAndCopy(context, primary.get(0), runtime.spec);
            step.put("associatedCapture", capture);
            step.put(
                    "requestedCameraIdHonored",
                    routeMatchesExpected(capture, runtime.spec)
            );
        } else {
            step.put("associatedCapture", JSONObject.NULL);
            step.put("requestedCameraIdHonored", JSONObject.NULL);
            step.put("error", "No new primary still image was found after this launch");
        }

        step.put(
                "associationRule",
                "This step has its own MediaStore baseline. The first new non-RAW still image "
                        + "owned by the official camera after this single launch is associated "
                        + "with requested camera ID " + runtime.spec.cameraId + "."
        );

        session.stepReports.put(step);
        session.currentStep = null;
        session.nextStepIndex++;
        return step;
    }

    static boolean hasNextStep(Session session) {
        return session.nextStepIndex < STEPS.length;
    }

    static int nextStepNumber(Session session) {
        return session.nextStepIndex + 1;
    }

    static String currentInstruction(Session session) {
        StepSpec spec = STEPS[session.nextStepIndex];
        return "Step " + (session.nextStepIndex + 1) + " of " + STEPS.length
                + ": requested camera ID " + spec.cameraId + " (" + spec.lensLabel + "). "
                + "Do not change the lens. Take exactly one photo, then press Back.";
    }

    static JSONObject finish(Context context, Session session) throws Exception {
        if (session.currentStep != null) {
            throw new IllegalStateException("Cannot finish while a launch step is active");
        }
        session.stopAvailabilityRecording();

        JSONObject report = new JSONObject();
        report.put("mode", "official-camera-expert-direct-id-launch");
        report.put("officialCameraPackage", session.packageName);
        report.put("officialCameraComponent", session.packageName + "/" + session.activityName);
        report.put("officialCameraPackageInfo", packageInfo(context, session.packageName));
        report.put("sessionStartedEpochMillis", session.sessionStartedEpochMillis);
        report.put("sessionStartedElapsedRealtimeMillis",
                session.sessionStartedElapsedRealtimeMillis);
        report.put("sessionFinishedEpochMillis", System.currentTimeMillis());
        report.put("sessionFinishedElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        report.put("launchContract", new JSONObject()
                .put("mainMode", "photo")
                .put("subMode", "manual")
                .put("cameraIdExtra", EXTRA_PREFIX_FACING)
                .put("requestedSequence", new JSONArray()
                        .put(new JSONObject().put("cameraId", 2).put("lens", "0.6x"))
                        .put(new JSONObject().put("cameraId", 0).put("lens", "1x"))
                        .put(new JSONObject().put("cameraId", 3).put("lens", "2x"))));
        report.put("steps", session.stepReports);
        report.put("allCameraAvailabilityEvents", copyArray(session.availabilityEvents));

        boolean complete = session.stepReports.length() == STEPS.length;
        boolean allHonored = complete;
        for (int index = 0; index < session.stepReports.length(); index++) {
            Object value = session.stepReports.getJSONObject(index)
                    .opt("requestedCameraIdHonored");
            allHonored &= value instanceof Boolean && (Boolean) value;
        }
        report.put("complete", complete);
        report.put("allRequestedCameraIdsHonored", complete ? allHonored : JSONObject.NULL);
        report.put(
                "interpretation",
                allHonored
                        ? "The exported official-camera launch contract honored IDs 2, 0 and 3 "
                        + "as ultrawide, main and telephoto in Expert mode."
                        : "One or more requested IDs were not confirmed by the resulting EXIF. "
                        + "Inspect each step to determine whether the stock app ignored, remapped "
                        + "or persisted a previous lens selection."
        );
        report.put(
                "diagnosticBoundary",
                "The official Nothing camera owns each privileged camera session. This audit "
                        + "validates only the exported launch contract and resulting saved image; "
                        + "it cannot expose the stock app's private CaptureRequest, CaptureResult "
                        + "or raw frames to the calling diagnostics app."
        );
        return report;
    }

    private static List<MediaAsset> waitForNewAssets(
            Context context,
            Session session,
            StepRuntime runtime
    ) throws Exception {
        long deadline = SystemClock.elapsedRealtime() + 15_000L;
        List<MediaAsset> assets = new ArrayList<>();
        do {
            assets = queryNewAssets(context, session, runtime);
            boolean foundPrimary = false;
            for (MediaAsset asset : assets) {
                if (asset.isPrimaryStill()) {
                    foundPrimary = true;
                    break;
                }
            }
            if (foundPrimary) {
                Thread.sleep(400L);
                return queryNewAssets(context, session, runtime);
            }
            Thread.sleep(400L);
        } while (SystemClock.elapsedRealtime() < deadline);
        return assets;
    }

    private static List<MediaAsset> queryNewAssets(
            Context context,
            Session session,
            StepRuntime runtime
    ) {
        Uri collection = MediaStore.Images.Media.getContentUri(
                MediaStore.VOLUME_EXTERNAL_PRIMARY
        );
        String[] projection = {
                MediaStore.Images.Media._ID,
                MediaStore.Images.Media.DISPLAY_NAME,
                MediaStore.Images.Media.MIME_TYPE,
                MediaStore.Images.Media.WIDTH,
                MediaStore.Images.Media.HEIGHT,
                MediaStore.Images.Media.SIZE,
                MediaStore.Images.Media.DATE_ADDED,
                MediaStore.Images.Media.DATE_MODIFIED,
                MediaStore.Images.Media.DATE_TAKEN,
                MediaStore.Images.Media.RELATIVE_PATH,
                MediaStore.Images.Media.ORIENTATION,
                MediaStore.MediaColumns.OWNER_PACKAGE_NAME
        };
        String selection = MediaStore.Images.Media._ID + " > ?";
        String[] args = {String.valueOf(runtime.baselineImageId)};
        String order = MediaStore.Images.Media.DATE_TAKEN + " ASC, "
                + MediaStore.Images.Media._ID + " ASC";

        List<MediaAsset> result = new ArrayList<>();
        try (Cursor cursor = context.getContentResolver().query(
                collection,
                projection,
                selection,
                args,
                order
        )) {
            if (cursor == null) {
                return result;
            }
            while (cursor.moveToNext()) {
                MediaAsset asset = MediaAsset.fromCursor(collection, cursor);
                long effectiveTime = asset.effectiveCaptureTime();
                boolean recentEnough = effectiveTime == 0L
                        || effectiveTime >= runtime.launchEpochMillis - 5_000L;
                boolean matchingOwner = asset.ownerPackageName == null
                        || asset.ownerPackageName.isEmpty()
                        || session.packageName.equals(asset.ownerPackageName);
                if (recentEnough && matchingOwner) {
                    result.add(asset);
                }
            }
        }
        result.sort(Comparator
                .comparingLong(MediaAsset::effectiveCaptureTime)
                .thenComparingLong(asset -> asset.id));
        return result;
    }

    private static JSONObject inspectAndCopy(
            Context context,
            MediaAsset source,
            StepSpec spec
    ) throws Exception {
        JSONObject capture = new JSONObject();
        capture.put("sourceMediaStore", source.toJson());
        capture.put("sourceUri", source.uri.toString());
        capture.put("sha256", sha256(context.getContentResolver(), source.uri));
        capture.put("exif", readExif(context.getContentResolver(), source.uri));
        Uri copy = copyToDiagnosticsFolder(context, source, spec);
        capture.put("diagnosticCopyUri", copy.toString());
        return capture;
    }

    private static boolean routeMatchesExpected(
            JSONObject capture,
            StepSpec spec
    ) {
        JSONObject numeric = capture.optJSONObject("exif") == null
                ? null
                : capture.optJSONObject("exif").optJSONObject("numericValues");
        if (numeric == null) {
            return false;
        }

        double physical = numeric.optDouble("FocalLength", Double.NaN);
        double equivalent = numeric.optDouble("FocalLengthIn35mmFilm", Double.NaN);
        boolean physicalKnown = Double.isFinite(physical);
        boolean equivalentKnown = Double.isFinite(equivalent);
        boolean physicalMatches = physicalKnown
                && Math.abs(physical - spec.physicalFocalMm) <= 0.25;
        boolean equivalentMatches = equivalentKnown
                && Math.abs(equivalent - spec.equivalentFocalMm) <= 2.0;

        if (physicalKnown && equivalentKnown) {
            return physicalMatches && equivalentMatches;
        }
        return physicalMatches || equivalentMatches;
    }

    private static Uri copyToDiagnosticsFolder(
            Context context,
            MediaAsset source,
            StepSpec spec
    ) throws Exception {
        String extension = extensionFor(source.displayName, source.mimeType);
        ContentValues values = new ContentValues();
        values.put(
                MediaStore.Images.Media.DISPLAY_NAME,
                "phone2pro-official-direct-id-" + spec.cameraId + "-"
                        + spec.lensLabel.replace('.', '_') + "-" + timestamp() + extension
        );
        values.put(MediaStore.Images.Media.MIME_TYPE, source.mimeType);
        values.put(MediaStore.Images.Media.RELATIVE_PATH, OUTPUT_FOLDER);
        values.put(MediaStore.Images.Media.IS_PENDING, 1);

        ContentResolver resolver = context.getContentResolver();
        Uri destination = resolver.insert(
                MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                values
        );
        if (destination == null) {
            throw new IllegalStateException("MediaStore refused diagnostic image copy");
        }

        boolean completed = false;
        try (InputStream input = resolver.openInputStream(source.uri);
             OutputStream output = resolver.openOutputStream(destination, "w")) {
            if (input == null || output == null) {
                throw new IllegalStateException("Unable to copy official camera image");
            }
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            completed = true;
        } finally {
            if (!completed) {
                resolver.delete(destination, null, null);
            }
        }

        values.clear();
        values.put(MediaStore.Images.Media.IS_PENDING, 0);
        resolver.update(destination, values, null, null);
        return destination;
    }

    private static JSONObject readExif(ContentResolver resolver, Uri uri) throws Exception {
        JSONObject output = new JSONObject();
        JSONObject raw = new JSONObject();
        JSONObject numeric = new JSONObject();

        try (InputStream stream = resolver.openInputStream(uri)) {
            if (stream == null) {
                throw new IllegalStateException("Unable to open captured image for EXIF");
            }
            ExifInterface exif = new ExifInterface(stream);
            for (String tag : EXIF_TAGS) {
                String value = exif.getAttribute(tag);
                raw.put(tag, value == null ? JSONObject.NULL : value);
            }
            putExifNumber(exif, numeric, "FocalLength");
            putExifNumber(exif, numeric, "FocalLengthIn35mmFilm");
            putExifNumber(exif, numeric, "DigitalZoomRatio");
            putExifNumber(exif, numeric, "FNumber");
            putExifNumber(exif, numeric, "ApertureValue");
            putExifNumber(exif, numeric, "ExposureTime");
            putExifNumber(exif, numeric, "PhotographicSensitivity");
            putExifNumber(exif, numeric, "ISOSpeedRatings");
            putExifNumber(exif, numeric, "BrightnessValue");
            putExifNumber(exif, numeric, "ExposureBiasValue");
        }

        output.put("rawAttributes", raw);
        output.put("numericValues", numeric);
        return output;
    }

    private static void putExifNumber(
            ExifInterface exif,
            JSONObject output,
            String tag
    ) throws JSONException {
        double value = exif.getAttributeDouble(tag, Double.NaN);
        output.put(tag, Double.isFinite(value) ? value : JSONObject.NULL);
    }

    private static long latestImageId(ContentResolver resolver) {
        Uri collection = MediaStore.Images.Media.getContentUri(
                MediaStore.VOLUME_EXTERNAL_PRIMARY
        );
        String[] projection = {MediaStore.Images.Media._ID};
        String order = MediaStore.Images.Media._ID + " DESC";
        try (Cursor cursor = resolver.query(collection, projection, null, null, order)) {
            if (cursor != null && cursor.moveToFirst()) {
                return cursor.getLong(0);
            }
        }
        return -1L;
    }

    @SuppressWarnings("deprecation")
    private static JSONObject packageInfo(Context context, String packageName)
            throws Exception {
        PackageInfo info = context.getPackageManager().getPackageInfo(packageName, 0);
        return new JSONObject()
                .put("packageName", packageName)
                .put("versionName", info.versionName)
                .put("longVersionCode", info.getLongVersionCode());
    }

    private static String sha256(ContentResolver resolver, Uri uri) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = resolver.openInputStream(uri)) {
            if (stream == null) {
                throw new IllegalStateException("Unable to open captured image for hashing");
            }
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = stream.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
        }
        StringBuilder value = new StringBuilder();
        for (byte item : digest.digest()) {
            value.append(String.format(Locale.US, "%02x", item & 0xff));
        }
        return value.toString();
    }

    private static String extensionFor(String displayName, String mimeType) {
        int dot = displayName == null ? -1 : displayName.lastIndexOf('.');
        if (dot >= 0 && dot < displayName.length() - 1) {
            return displayName.substring(dot);
        }
        if ("image/heic".equals(mimeType) || "image/heif".equals(mimeType)) {
            return ".heic";
        }
        return ".jpg";
    }

    private static String timestamp() {
        return new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
                .format(new Date());
    }

    private static void appendAvailabilityEvent(
            JSONArray events,
            String cameraId,
            boolean available
    ) {
        synchronized (events) {
            events.put(new JSONObject()
                    .put("cameraId", cameraId)
                    .put("available", available)
                    .put("epochMillis", System.currentTimeMillis())
                    .put("elapsedRealtimeMillis", SystemClock.elapsedRealtime()));
        }
    }

    private static int availabilityLength(JSONArray events) {
        synchronized (events) {
            return events.length();
        }
    }

    private static JSONArray availabilitySlice(JSONArray source, int start)
            throws JSONException {
        JSONArray result = new JSONArray();
        synchronized (source) {
            for (int index = start; index < source.length(); index++) {
                result.put(new JSONObject(source.getJSONObject(index).toString()));
            }
        }
        return result;
    }

    private static JSONArray copyArray(JSONArray source) throws JSONException {
        return availabilitySlice(source, 0);
    }

    static final class Session {
        final String packageName;
        final String activityName;
        final long sessionStartedEpochMillis;
        final long sessionStartedElapsedRealtimeMillis;
        final JSONArray availabilityEvents;
        final JSONArray stepReports = new JSONArray();

        private final CameraManager cameraManager;
        private final CameraManager.AvailabilityCallback availabilityCallback;
        private int nextStepIndex;
        private StepRuntime currentStep;
        private boolean availabilityStopped;

        Session(
                String packageName,
                String activityName,
                long sessionStartedEpochMillis,
                long sessionStartedElapsedRealtimeMillis,
                CameraManager cameraManager,
                CameraManager.AvailabilityCallback availabilityCallback,
                JSONArray availabilityEvents
        ) {
            this.packageName = packageName;
            this.activityName = activityName;
            this.sessionStartedEpochMillis = sessionStartedEpochMillis;
            this.sessionStartedElapsedRealtimeMillis = sessionStartedElapsedRealtimeMillis;
            this.cameraManager = cameraManager;
            this.availabilityCallback = availabilityCallback;
            this.availabilityEvents = availabilityEvents;
        }

        void stopAvailabilityRecording() {
            if (!availabilityStopped
                    && cameraManager != null
                    && availabilityCallback != null) {
                cameraManager.unregisterAvailabilityCallback(availabilityCallback);
            }
            availabilityStopped = true;
        }
    }

    private static final class StepSpec {
        final int cameraId;
        final String lensLabel;
        final double physicalFocalMm;
        final double equivalentFocalMm;

        StepSpec(
                int cameraId,
                String lensLabel,
                double physicalFocalMm,
                double equivalentFocalMm
        ) {
            this.cameraId = cameraId;
            this.lensLabel = lensLabel;
            this.physicalFocalMm = physicalFocalMm;
            this.equivalentFocalMm = equivalentFocalMm;
        }
    }

    private static final class StepRuntime {
        final StepSpec spec;
        final long baselineImageId;
        final long launchEpochMillis;
        final long launchElapsedMillis;
        final int availabilityStartIndex;
        final JSONObject launchExtras;

        StepRuntime(
                StepSpec spec,
                long baselineImageId,
                long launchEpochMillis,
                long launchElapsedMillis,
                int availabilityStartIndex,
                JSONObject launchExtras
        ) {
            this.spec = spec;
            this.baselineImageId = baselineImageId;
            this.launchEpochMillis = launchEpochMillis;
            this.launchElapsedMillis = launchElapsedMillis;
            this.availabilityStartIndex = availabilityStartIndex;
            this.launchExtras = launchExtras;
        }
    }

    private static final class MediaAsset {
        final long id;
        final Uri uri;
        final String displayName;
        final String mimeType;
        final int width;
        final int height;
        final long sizeBytes;
        final long dateAddedSeconds;
        final long dateModifiedSeconds;
        final long dateTakenMillis;
        final String relativePath;
        final int orientation;
        final String ownerPackageName;

        MediaAsset(
                long id,
                Uri uri,
                String displayName,
                String mimeType,
                int width,
                int height,
                long sizeBytes,
                long dateAddedSeconds,
                long dateModifiedSeconds,
                long dateTakenMillis,
                String relativePath,
                int orientation,
                String ownerPackageName
        ) {
            this.id = id;
            this.uri = uri;
            this.displayName = displayName;
            this.mimeType = mimeType;
            this.width = width;
            this.height = height;
            this.sizeBytes = sizeBytes;
            this.dateAddedSeconds = dateAddedSeconds;
            this.dateModifiedSeconds = dateModifiedSeconds;
            this.dateTakenMillis = dateTakenMillis;
            this.relativePath = relativePath;
            this.orientation = orientation;
            this.ownerPackageName = ownerPackageName;
        }

        static MediaAsset fromCursor(Uri collection, Cursor cursor) {
            long id = cursor.getLong(0);
            return new MediaAsset(
                    id,
                    ContentUris.withAppendedId(collection, id),
                    nullableString(cursor, 1),
                    nullableString(cursor, 2),
                    cursor.getInt(3),
                    cursor.getInt(4),
                    cursor.getLong(5),
                    cursor.getLong(6),
                    cursor.getLong(7),
                    cursor.getLong(8),
                    nullableString(cursor, 9),
                    cursor.getInt(10),
                    nullableString(cursor, 11)
            );
        }

        long effectiveCaptureTime() {
            if (dateTakenMillis > 0L) {
                return dateTakenMillis;
            }
            if (dateAddedSeconds > 0L) {
                return dateAddedSeconds * 1000L;
            }
            return 0L;
        }

        boolean isPrimaryStill() {
            if (displayName != null
                    && displayName.toLowerCase(Locale.US).endsWith(".dng")) {
                return false;
            }
            return mimeType != null
                    && mimeType.startsWith("image/")
                    && !"image/x-adobe-dng".equals(mimeType);
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("id", id)
                    .put("uri", uri.toString())
                    .put("displayName", displayName)
                    .put("mimeType", mimeType)
                    .put("width", width)
                    .put("height", height)
                    .put("sizeBytes", sizeBytes)
                    .put("dateAddedSeconds", dateAddedSeconds)
                    .put("dateModifiedSeconds", dateModifiedSeconds)
                    .put("dateTakenMillis", dateTakenMillis)
                    .put("relativePath", relativePath)
                    .put("orientation", orientation)
                    .put("ownerPackageName", ownerPackageName);
        }

        private static String nullableString(Cursor cursor, int column) {
            return cursor.isNull(column) ? null : cursor.getString(column);
        }
    }
}
