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

final class OfficialExpertCameraAudit {
    private static final float[] EXPECTED_ZOOMS = {0.6f, 1.0f, 2.0f};
    private static final String OUTPUT_FOLDER =
            Environment.DIRECTORY_PICTURES
                    + "/Phone2Pro Diagnostics/Official Expert Camera Audit";

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

    private OfficialExpertCameraAudit() {
    }

    static Session prepare(Context context) throws Exception {
        ContentResolver resolver = context.getContentResolver();
        long baselineImageId = latestImageId(resolver);
        long launchEpochMillis = System.currentTimeMillis();
        long launchElapsedMillis = SystemClock.elapsedRealtime();

        Intent launchIntent = new Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
        ResolveInfo resolved = context.getPackageManager().resolveActivity(
                launchIntent,
                PackageManager.MATCH_DEFAULT_ONLY
        );
        if (resolved == null || resolved.activityInfo == null) {
            throw new IllegalStateException("No default still-camera activity resolved");
        }

        launchIntent.setClassName(
                resolved.activityInfo.packageName,
                resolved.activityInfo.name
        );

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
                launchIntent,
                resolved.activityInfo.packageName,
                resolved.activityInfo.name,
                baselineImageId,
                launchEpochMillis,
                launchElapsedMillis,
                cameraManager,
                callback,
                availabilityEvents
        );
    }

    static JSONObject finish(Context context, Session session) throws Exception {
        session.stopAvailabilityRecording();

        List<MediaAsset> allAssets = waitForNewAssets(context, session);
        List<MediaAsset> primaryImages = new ArrayList<>();
        List<MediaAsset> auxiliaryImages = new ArrayList<>();
        for (MediaAsset asset : allAssets) {
            if (asset.isPrimaryStill()) {
                primaryImages.add(asset);
            } else {
                auxiliaryImages.add(asset);
            }
        }

        JSONObject audit = new JSONObject();
        audit.put("mode", "official-camera-expert");
        audit.put("requiredCaptureOrder", new JSONArray()
                .put("0.6x")
                .put("1x")
                .put("2x"));
        audit.put("officialCameraPackage", session.packageName);
        audit.put("officialCameraComponent",
                session.packageName + "/" + session.activityName);
        audit.put("officialCameraPackageInfo", packageInfo(context, session.packageName));
        audit.put("launchIntentAction", session.launchIntent.getAction());
        audit.put("baselineImageId", session.baselineImageId);
        audit.put("launchEpochMillis", session.launchEpochMillis);
        audit.put("launchElapsedRealtimeMillis", session.launchElapsedMillis);
        audit.put("returnEpochMillis", System.currentTimeMillis());
        audit.put("returnElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        audit.put("cameraAvailabilityEvents", copyArray(session.availabilityEvents));
        audit.put("newMediaAssetCount", allAssets.size());
        audit.put("newPrimaryStillCount", primaryImages.size());
        audit.put("newAuxiliaryAssetCount", auxiliaryImages.size());

        JSONArray captures = new JSONArray();
        int associatedCount = Math.min(EXPECTED_ZOOMS.length, primaryImages.size());
        for (int index = 0; index < associatedCount; index++) {
            captures.put(inspectAndCopy(
                    context,
                    primaryImages.get(index),
                    EXPECTED_ZOOMS[index]
            ));
        }
        audit.put("associatedCaptures", captures);

        JSONArray unassociatedPrimary = new JSONArray();
        for (int index = associatedCount; index < primaryImages.size(); index++) {
            unassociatedPrimary.put(primaryImages.get(index).toJson());
        }
        audit.put("unassociatedPrimaryAssets", unassociatedPrimary);

        JSONArray auxiliary = new JSONArray();
        for (MediaAsset asset : auxiliaryImages) {
            auxiliary.put(asset.toJson());
        }
        audit.put("auxiliaryAssets", auxiliary);
        audit.put("routingSummary", routingSummary(captures));
        audit.put("complete", associatedCount == EXPECTED_ZOOMS.length);
        audit.put(
                "associationRule",
                "The first three new non-RAW still images created after launch are associated "
                        + "in chronological order with the instructed Expert-mode sequence: "
                        + "0.6x, 1x, then 2x. Take exactly one photo at each setting and no extras."
        );
        audit.put(
                "diagnosticBoundary",
                "Android does not allow this third-party diagnostics app to read the official "
                        + "camera application's private CaptureRequest or CaptureResult. The audit "
                        + "therefore records the resolved official camera component, public camera "
                        + "availability transitions, exact output files, MediaStore metadata, hashes, "
                        + "EXIF lens metadata, and image geometry for each instructed Expert-mode step."
        );
        return audit;
    }

    private static List<MediaAsset> waitForNewAssets(Context context, Session session)
            throws Exception {
        long deadline = SystemClock.elapsedRealtime() + 15_000L;
        List<MediaAsset> assets = new ArrayList<>();
        do {
            assets = queryNewAssets(context, session);
            int primaryCount = 0;
            for (MediaAsset asset : assets) {
                if (asset.isPrimaryStill()) {
                    primaryCount++;
                }
            }
            if (primaryCount >= EXPECTED_ZOOMS.length) {
                break;
            }
            Thread.sleep(500L);
        } while (SystemClock.elapsedRealtime() < deadline);
        return assets;
    }

    private static List<MediaAsset> queryNewAssets(Context context, Session session) {
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
        String[] args = {String.valueOf(session.baselineImageId)};
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
                long effectiveTime = asset.dateTakenMillis > 0L
                        ? asset.dateTakenMillis
                        : asset.dateAddedSeconds * 1000L;
                boolean recentEnough = effectiveTime == 0L
                        || effectiveTime >= session.launchEpochMillis - 5_000L;
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
            float expectedZoom
    ) throws Exception {
        JSONObject capture = new JSONObject();
        capture.put("expectedLensButton", zoomLabel(expectedZoom));
        capture.put("expectedZoom", expectedZoom);
        capture.put("sourceMediaStore", source.toJson());
        capture.put("sourceUri", source.uri.toString());
        capture.put("sha256", sha256(context.getContentResolver(), source.uri));
        capture.put("exif", readExif(context.getContentResolver(), source.uri));
        Uri copy = copyToDiagnosticsFolder(context, source, expectedZoom);
        capture.put("diagnosticCopyUri", copy.toString());
        return capture;
    }

    private static Uri copyToDiagnosticsFolder(
            Context context,
            MediaAsset source,
            float expectedZoom
    ) throws Exception {
        String extension = extensionFor(source.displayName, source.mimeType);
        ContentValues values = new ContentValues();
        values.put(
                MediaStore.Images.Media.DISPLAY_NAME,
                "phone2pro-official-expert-" + zoomFileLabel(expectedZoom)
                        + "-" + timestamp() + extension
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

    private static JSONObject routingSummary(JSONArray captures) throws JSONException {
        JSONObject summary = new JSONObject();
        summary.put("capturedCount", captures.length());
        if (captures.length() < EXPECTED_ZOOMS.length) {
            summary.put("exifSuggestsDistinctLensRoutes", JSONObject.NULL);
            summary.put("reason", "Fewer than three associated primary still images");
            return summary;
        }

        double equivalentZeroSix = exifNumber(captures.getJSONObject(0),
                "FocalLengthIn35mmFilm");
        double equivalentOne = exifNumber(captures.getJSONObject(1),
                "FocalLengthIn35mmFilm");
        double equivalentTwo = exifNumber(captures.getJSONObject(2),
                "FocalLengthIn35mmFilm");
        double physicalZeroSix = exifNumber(captures.getJSONObject(0), "FocalLength");
        double physicalOne = exifNumber(captures.getJSONObject(1), "FocalLength");
        double physicalTwo = exifNumber(captures.getJSONObject(2), "FocalLength");
        double digitalZeroSix = exifNumber(captures.getJSONObject(0), "DigitalZoomRatio");
        double digitalOne = exifNumber(captures.getJSONObject(1), "DigitalZoomRatio");
        double digitalTwo = exifNumber(captures.getJSONObject(2), "DigitalZoomRatio");

        summary.put("focalLength35mmEquivalent", new JSONObject()
                .put("0.6x", finiteOrNull(equivalentZeroSix))
                .put("1x", finiteOrNull(equivalentOne))
                .put("2x", finiteOrNull(equivalentTwo)));
        summary.put("physicalFocalLengthMm", new JSONObject()
                .put("0.6x", finiteOrNull(physicalZeroSix))
                .put("1x", finiteOrNull(physicalOne))
                .put("2x", finiteOrNull(physicalTwo)));
        summary.put("digitalZoomRatio", new JSONObject()
                .put("0.6x", finiteOrNull(digitalZeroSix))
                .put("1x", finiteOrNull(digitalOne))
                .put("2x", finiteOrNull(digitalTwo)));

        if (Double.isFinite(equivalentZeroSix)
                && Double.isFinite(equivalentOne)
                && Double.isFinite(equivalentTwo)
                && equivalentOne > 0.0) {
            summary.put("equivalentFocalRatios", new JSONObject()
                    .put("0.6xTo1x", equivalentZeroSix / equivalentOne)
                    .put("2xTo1x", equivalentTwo / equivalentOne));
            summary.put(
                    "exifSuggestsDistinctLensRoutes",
                    equivalentZeroSix < equivalentOne * 0.8
                            && equivalentTwo > equivalentOne * 1.5
            );
        } else {
            summary.put("exifSuggestsDistinctLensRoutes", JSONObject.NULL);
        }

        summary.put(
                "interpretationNote",
                "Different 35 mm-equivalent focal lengths or lens models strongly support "
                        + "different physical camera routes. Identical focal metadata with a "
                        + "higher DigitalZoomRatio supports cropping. Image registration remains "
                        + "the final check because OEM EXIF can be incomplete or normalized."
        );
        return summary;
    }

    private static double exifNumber(JSONObject capture, String tag) {
        JSONObject exif = capture.optJSONObject("exif");
        JSONObject numeric = exif == null ? null : exif.optJSONObject("numericValues");
        return numeric == null ? Double.NaN : numeric.optDouble(tag, Double.NaN);
    }

    private static Object finiteOrNull(double value) {
        return Double.isFinite(value) ? value : JSONObject.NULL;
    }

    private static String sha256(ContentResolver resolver, Uri uri) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[64 * 1024];
        try (InputStream stream = resolver.openInputStream(uri)) {
            if (stream == null) {
                throw new IllegalStateException("Unable to open captured image for hashing");
            }
            int read;
            while ((read = stream.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
        }

        StringBuilder hex = new StringBuilder();
        for (byte value : digest.digest()) {
            hex.append(String.format(Locale.US, "%02x", value & 0xff));
        }
        return hex.toString();
    }

    private static long latestImageId(ContentResolver resolver) {
        Uri collection = MediaStore.Images.Media.getContentUri(
                MediaStore.VOLUME_EXTERNAL_PRIMARY
        );
        try (Cursor cursor = resolver.query(
                collection,
                new String[]{MediaStore.Images.Media._ID},
                null,
                null,
                MediaStore.Images.Media._ID + " DESC"
        )) {
            return cursor != null && cursor.moveToFirst() ? cursor.getLong(0) : 0L;
        }
    }

    private static JSONObject packageInfo(Context context, String packageName)
            throws JSONException {
        JSONObject output = new JSONObject();
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(packageName, 0);
            output.put("packageName", packageName);
            output.put("versionName",
                    info.versionName == null ? JSONObject.NULL : info.versionName);
            output.put("longVersionCode", info.getLongVersionCode());
        } catch (PackageManager.NameNotFoundException error) {
            output.put("packageName", packageName);
            output.put("error", error.toString());
        }
        return output;
    }

    private static void appendAvailabilityEvent(
            JSONArray events,
            String cameraId,
            boolean available
    ) {
        synchronized (events) {
            try {
                events.put(new JSONObject()
                        .put("cameraId", cameraId)
                        .put("available", available)
                        .put("epochMillis", System.currentTimeMillis())
                        .put("elapsedRealtimeMillis", SystemClock.elapsedRealtime()));
            } catch (JSONException ignored) {
                // Primitive event construction should not fail.
            }
        }
    }

    private static JSONArray copyArray(JSONArray source) throws JSONException {
        synchronized (source) {
            return new JSONArray(source.toString());
        }
    }

    private static String extensionFor(String displayName, String mimeType) {
        if (displayName != null) {
            int dot = displayName.lastIndexOf('.');
            if (dot >= 0 && dot < displayName.length() - 1) {
                return displayName.substring(dot);
            }
        }
        if ("image/heic".equals(mimeType) || "image/heif".equals(mimeType)) {
            return ".heic";
        }
        return ".jpg";
    }

    private static String zoomLabel(float zoom) {
        if (Math.abs(zoom - 0.6f) < 0.01f) {
            return "0.6x";
        }
        if (Math.abs(zoom - 1.0f) < 0.01f) {
            return "1x";
        }
        return "2x";
    }

    private static String zoomFileLabel(float zoom) {
        return zoomLabel(zoom).replace('.', '_');
    }

    private static String timestamp() {
        return new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
                .format(new Date());
    }

    static final class Session {
        final Intent launchIntent;
        final String packageName;
        final String activityName;
        final long baselineImageId;
        final long launchEpochMillis;
        final long launchElapsedMillis;
        final CameraManager cameraManager;
        final CameraManager.AvailabilityCallback availabilityCallback;
        final JSONArray availabilityEvents;
        private boolean recordingStopped;

        Session(
                Intent launchIntent,
                String packageName,
                String activityName,
                long baselineImageId,
                long launchEpochMillis,
                long launchElapsedMillis,
                CameraManager cameraManager,
                CameraManager.AvailabilityCallback availabilityCallback,
                JSONArray availabilityEvents
        ) {
            this.launchIntent = launchIntent;
            this.packageName = packageName;
            this.activityName = activityName;
            this.baselineImageId = baselineImageId;
            this.launchEpochMillis = launchEpochMillis;
            this.launchElapsedMillis = launchElapsedMillis;
            this.cameraManager = cameraManager;
            this.availabilityCallback = availabilityCallback;
            this.availabilityEvents = availabilityEvents;
        }

        void stopAvailabilityRecording() {
            if (!recordingStopped && cameraManager != null && availabilityCallback != null) {
                cameraManager.unregisterAvailabilityCallback(availabilityCallback);
            }
            recordingStopped = true;
        }
    }

    private static final class MediaAsset {
        final long id;
        final Uri uri;
        final String displayName;
        final String mimeType;
        final long width;
        final long height;
        final long sizeBytes;
        final long dateAddedSeconds;
        final long dateModifiedSeconds;
        final long dateTakenMillis;
        final String relativePath;
        final long orientation;
        final String ownerPackageName;

        MediaAsset(
                long id,
                Uri uri,
                String displayName,
                String mimeType,
                long width,
                long height,
                long sizeBytes,
                long dateAddedSeconds,
                long dateModifiedSeconds,
                long dateTakenMillis,
                String relativePath,
                long orientation,
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
            long id = longValue(cursor, MediaStore.Images.Media._ID);
            return new MediaAsset(
                    id,
                    ContentUris.withAppendedId(collection, id),
                    stringValue(cursor, MediaStore.Images.Media.DISPLAY_NAME),
                    stringValue(cursor, MediaStore.Images.Media.MIME_TYPE),
                    longValue(cursor, MediaStore.Images.Media.WIDTH),
                    longValue(cursor, MediaStore.Images.Media.HEIGHT),
                    longValue(cursor, MediaStore.Images.Media.SIZE),
                    longValue(cursor, MediaStore.Images.Media.DATE_ADDED),
                    longValue(cursor, MediaStore.Images.Media.DATE_MODIFIED),
                    longValue(cursor, MediaStore.Images.Media.DATE_TAKEN),
                    stringValue(cursor, MediaStore.Images.Media.RELATIVE_PATH),
                    longValue(cursor, MediaStore.Images.Media.ORIENTATION),
                    stringValue(cursor, MediaStore.MediaColumns.OWNER_PACKAGE_NAME)
            );
        }

        boolean isPrimaryStill() {
            if (mimeType == null) {
                return false;
            }
            String normalized = mimeType.toLowerCase(Locale.US);
            return normalized.equals("image/jpeg")
                    || normalized.equals("image/jpg")
                    || normalized.equals("image/heic")
                    || normalized.equals("image/heif")
                    || normalized.equals("image/webp");
        }

        long effectiveCaptureTime() {
            if (dateTakenMillis > 0L) {
                return dateTakenMillis;
            }
            if (dateAddedSeconds > 0L) {
                return dateAddedSeconds * 1000L;
            }
            return id;
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("id", id)
                    .put("uri", uri.toString())
                    .put("displayName", nullable(displayName))
                    .put("mimeType", nullable(mimeType))
                    .put("width", width)
                    .put("height", height)
                    .put("sizeBytes", sizeBytes)
                    .put("dateAddedSeconds", dateAddedSeconds)
                    .put("dateModifiedSeconds", dateModifiedSeconds)
                    .put("dateTakenMillis", dateTakenMillis)
                    .put("relativePath", nullable(relativePath))
                    .put("orientation", orientation)
                    .put("ownerPackageName", nullable(ownerPackageName));
        }
    }

    private static long longValue(Cursor cursor, String column) {
        int index = cursor.getColumnIndex(column);
        return index < 0 || cursor.isNull(index) ? 0L : cursor.getLong(index);
    }

    private static String stringValue(Cursor cursor, String column) {
        int index = cursor.getColumnIndex(column);
        return index < 0 || cursor.isNull(index) ? null : cursor.getString(index);
    }

    private static Object nullable(String value) {
        return value == null ? JSONObject.NULL : value;
    }
}
