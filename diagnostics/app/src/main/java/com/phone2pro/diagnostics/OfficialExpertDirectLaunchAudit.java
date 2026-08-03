package com.phone2pro.diagnostics;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Environment;
import android.os.SystemClock;
import android.provider.MediaStore;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
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

    private OfficialExpertDirectLaunchAudit() {
    }

    static Session prepare(Context context) throws Exception {
        return new Session(
                OfficialExpertCameraAudit.prepare(context),
                System.currentTimeMillis(),
                SystemClock.elapsedRealtime()
        );
    }

    static Intent prepareNextLaunch(Context context, Session session) throws Exception {
        if (session.stepActive) {
            throw new IllegalStateException("A direct-launch step is already active");
        }
        if (!hasNextStep(session)) {
            throw new IllegalStateException("All direct-launch steps are complete");
        }

        StepSpec spec = STEPS[session.nextStepIndex];
        Intent intent = new Intent(session.baseSession.launchIntent);
        intent.putExtra(EXTRA_PREFIX_MAIN_MODE, "photo");
        intent.putExtra(EXTRA_PREFIX_SUB_MODE, "manual");
        intent.putExtra(EXTRA_PREFIX_FACING, String.valueOf(spec.cameraId));
        intent.putExtra(EXTRA_MAIN_MODE, "photo");
        intent.putExtra(EXTRA_SUB_MODE, "manual");
        intent.putExtra(EXTRA_FACING, spec.cameraId);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        JSONObject launch = new JSONObject()
                .put("stepNumber", session.nextStepIndex + 1)
                .put("requestedCameraId", spec.cameraId)
                .put("expectedLensButton", spec.lensLabel)
                .put("expectedPhysicalFocalLengthMm", spec.physicalFocalMm)
                .put("expectedFocalLength35mmEquivalent", spec.equivalentFocalMm)
                .put("launchEpochMillis", System.currentTimeMillis())
                .put("launchElapsedRealtimeMillis", SystemClock.elapsedRealtime())
                .put("extras", new JSONObject()
                        .put(EXTRA_PREFIX_MAIN_MODE, "photo")
                        .put(EXTRA_PREFIX_SUB_MODE, "manual")
                        .put(EXTRA_PREFIX_FACING, String.valueOf(spec.cameraId))
                        .put(EXTRA_MAIN_MODE, "photo")
                        .put(EXTRA_SUB_MODE, "manual")
                        .put(EXTRA_FACING, spec.cameraId));
        session.launchRecords.put(launch);
        session.stepActive = true;
        return intent;
    }

    static JSONObject finishCurrentStep(Context context, Session session) throws Exception {
        if (!session.stepActive) {
            throw new IllegalStateException("No direct-launch step is active");
        }

        JSONObject launch = session.launchRecords.getJSONObject(session.nextStepIndex);
        launch.put("returnEpochMillis", System.currentTimeMillis());
        launch.put("returnElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        session.stepActive = false;
        session.nextStepIndex++;
        return launch;
    }

    static boolean hasNextStep(Session session) {
        return session.nextStepIndex < STEPS.length;
    }

    static String currentInstruction(Session session) {
        StepSpec spec = STEPS[session.nextStepIndex];
        return "Step " + (session.nextStepIndex + 1) + " of " + STEPS.length
                + ": requested camera ID " + spec.cameraId + " (" + spec.lensLabel + "). "
                + "Do not change the lens. Take exactly one photo, then press Back.";
    }

    static JSONObject finish(Context context, Session session) throws Exception {
        if (session.stepActive) {
            throw new IllegalStateException("Cannot finish while a launch step is active");
        }

        JSONObject observed = OfficialExpertCameraAudit.finish(context, session.baseSession);
        JSONArray captures = observed.optJSONArray("associatedCaptures");
        boolean complete = observed.optBoolean("complete", false)
                && captures != null
                && captures.length() == STEPS.length;
        boolean allHonored = complete;

        if (captures != null) {
            int count = Math.min(captures.length(), STEPS.length);
            for (int index = 0; index < count; index++) {
                JSONObject capture = captures.getJSONObject(index);
                StepSpec spec = STEPS[index];
                boolean honored = routeMatchesExpected(capture, spec);
                capture.put("requestedCameraId", spec.cameraId);
                capture.put("requestedCameraIdHonored", honored);
                capture.put("directLaunch", session.launchRecords.getJSONObject(index));
                Uri directCopy = copyToDirectFolder(context, capture, spec);
                if (directCopy != null) {
                    capture.put("directDiagnosticCopyUri", directCopy.toString());
                }
                allHonored &= honored;
            }
        }

        JSONObject report = new JSONObject();
        report.put("mode", "official-camera-expert-direct-id-launch");
        report.put("officialCameraPackage", session.baseSession.packageName);
        report.put(
                "officialCameraComponent",
                session.baseSession.packageName + "/" + session.baseSession.activityName
        );
        report.put("sessionStartedEpochMillis", session.startedEpochMillis);
        report.put("sessionStartedElapsedRealtimeMillis", session.startedElapsedMillis);
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
        report.put("launchRecords", session.launchRecords);
        report.put("observedOfficialCameraAudit", observed);
        report.put("complete", complete);
        report.put("allRequestedCameraIdsHonored", complete ? allHonored : JSONObject.NULL);
        report.put(
                "interpretation",
                complete && allHonored
                        ? "The exported official-camera launch contract honored IDs 2, 0 and 3 "
                        + "as ultrawide, main and telephoto in Expert mode."
                        : "At least one requested camera ID was not confirmed by the saved-image "
                        + "EXIF, or the three-step capture sequence was incomplete."
        );
        report.put(
                "diagnosticBoundary",
                "The official Nothing camera owns each privileged camera session. This audit "
                        + "validates only the exported launch contract and resulting saved images; "
                        + "it cannot expose the stock app's private CaptureRequest, CaptureResult "
                        + "or raw frames to the calling diagnostics app."
        );
        return report;
    }

    private static boolean routeMatchesExpected(JSONObject capture, StepSpec spec) {
        JSONObject exif = capture.optJSONObject("exif");
        JSONObject numeric = exif == null ? null : exif.optJSONObject("numericValues");
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

    private static Uri copyToDirectFolder(
            Context context,
            JSONObject capture,
            StepSpec spec
    ) throws Exception {
        String sourceValue = capture.optString("diagnosticCopyUri", null);
        if (sourceValue == null) {
            return null;
        }

        JSONObject media = capture.optJSONObject("sourceMediaStore");
        String mimeType = media == null
                ? "image/jpeg"
                : media.optString("mimeType", "image/jpeg");
        String extension = mimeType.contains("heic") || mimeType.contains("heif")
                ? ".heic"
                : ".jpg";

        ContentValues values = new ContentValues();
        values.put(
                MediaStore.Images.Media.DISPLAY_NAME,
                "phone2pro-official-direct-id-" + spec.cameraId + "-"
                        + spec.lensLabel.replace('.', '_') + extension
        );
        values.put(MediaStore.Images.Media.MIME_TYPE, mimeType);
        values.put(MediaStore.Images.Media.RELATIVE_PATH, OUTPUT_FOLDER);
        values.put(MediaStore.Images.Media.IS_PENDING, 1);

        ContentResolver resolver = context.getContentResolver();
        Uri destination = resolver.insert(
                MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                values
        );
        if (destination == null) {
            return null;
        }

        boolean complete = false;
        try (InputStream input = resolver.openInputStream(Uri.parse(sourceValue));
             OutputStream output = resolver.openOutputStream(destination, "w")) {
            if (input == null || output == null) {
                throw new IllegalStateException("Unable to copy direct-launch diagnostic image");
            }
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            complete = true;
        } finally {
            if (!complete) {
                resolver.delete(destination, null, null);
            }
        }

        values.clear();
        values.put(MediaStore.Images.Media.IS_PENDING, 0);
        resolver.update(destination, values, null, null);
        return destination;
    }

    static final class Session {
        final OfficialExpertCameraAudit.Session baseSession;
        final long startedEpochMillis;
        final long startedElapsedMillis;
        final JSONArray launchRecords = new JSONArray();

        private int nextStepIndex;
        private boolean stepActive;

        Session(
                OfficialExpertCameraAudit.Session baseSession,
                long startedEpochMillis,
                long startedElapsedMillis
        ) {
            this.baseSession = baseSession;
            this.startedEpochMillis = startedEpochMillis;
            this.startedElapsedMillis = startedElapsedMillis;
        }

        void stopAvailabilityRecording() {
            baseSession.stopAvailabilityRecording();
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
}
