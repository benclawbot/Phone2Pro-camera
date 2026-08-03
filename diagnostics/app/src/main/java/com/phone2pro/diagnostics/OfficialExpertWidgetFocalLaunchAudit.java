package com.phone2pro.diagnostics;

import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/**
 * Exercises the exported preset/widget contract used by Nothing Camera's own widgets.
 * This contract applies a 35 mm equivalent focal-length value after ordinary rear IDs
 * have been normalized to the SAT endpoint.
 */
final class OfficialExpertWidgetFocalLaunchAudit {
    private static final String ACTION_WIDGET_CAMERA =
            "com.nothing.camera.WIDGET_CAMERA";
    private static final String OFFICIAL_CAMERA_ACTIVITY =
            "com.nothing.camera.activity.CameraActivity";

    private static final String EXTRA_WIDGET_CAMERA =
            "com.nothing.camera.WIDGET_CAMERA";
    private static final String EXTRA_IS_FROM_WIDGET =
            "com.nothing.camera.IS_FROM_WIDGET";
    private static final String EXTRA_PREFIX_FLAG_WIDGET =
            "android.intent.extras.CAMERA_PREFIX_FLAG_WIDGET";
    private static final String EXTRA_PREFIX_MAIN_MODE =
            "android.intent.extras.CAMERA_PREFIX_MAIN_MODE";
    private static final String EXTRA_PREFIX_SUB_MODE =
            "android.intent.extras.CAMERA_PREFIX_SUB_MODE";
    private static final String EXTRA_PREFIX_FACING =
            "android.intent.extras.CAMERA_PREFIX_FACING";
    private static final String EXTRA_PREFIX_FOCAL_LENGTH =
            "android.intent.extras.CAMERA_PREFIX_FOCALLENGTH_VALUE";

    private static final String EXTRA_MAIN_MODE =
            "android.intent.extras.CAMERA_MAIN_MODE";
    private static final String EXTRA_SUB_MODE =
            "android.intent.extras.CAMERA_SUB_MODE";
    private static final String EXTRA_FACING =
            "android.intent.extras.CAMERA_FACING";

    private static final String OUTPUT_FOLDER =
            Environment.DIRECTORY_PICTURES
                    + "/Phone2Pro Diagnostics/Official Expert Widget Focal Launch Audit";

    private static final StepSpec[] STEPS = {
            new StepSpec(2, "0.6x", "15mm", 1.64, 15.0),
            new StepSpec(0, "1x", "24mm", 5.56, 24.0),
            new StepSpec(3, "2x", "50mm", 7.10, 50.0)
    };

    private OfficialExpertWidgetFocalLaunchAudit() {
    }

    static Session prepare(Context context) throws Exception {
        return new Session(OfficialExpertDirectLaunchAudit.prepare(context));
    }

    static Intent prepareNextLaunch(Context context, Session session) throws Exception {
        if (session.activeStep != null) {
            throw new IllegalStateException("A widget-focal launch step is already active");
        }
        if (!hasNextStep(session)) {
            throw new IllegalStateException("All widget-focal launch steps are complete");
        }

        StepSpec spec = STEPS[session.nextStepIndex];
        Intent intent = OfficialExpertDirectLaunchAudit.prepareNextLaunch(
                context,
                session.delegate
        );

        // Remove the ordinary direct-ID contract. Nothing Camera normalizes that path to SAT ID 4.
        intent.removeExtra(EXTRA_MAIN_MODE);
        intent.removeExtra(EXTRA_SUB_MODE);
        intent.removeExtra(EXTRA_FACING);
        intent.removeExtra(EXTRA_PREFIX_MAIN_MODE);
        intent.removeExtra(EXTRA_PREFIX_SUB_MODE);
        intent.removeExtra(EXTRA_PREFIX_FACING);

        // Recreate the stock widget/preset launch contract. The "preset-1" suffix sets
        // LaunchIntentParser.mIsFromWidget and enables its focal-length parsing path.
        intent.setAction(ACTION_WIDGET_CAMERA);
        intent.setClassName(packageName(session), OFFICIAL_CAMERA_ACTIVITY);
        intent.putExtra(EXTRA_WIDGET_CAMERA, true);
        intent.putExtra(EXTRA_IS_FROM_WIDGET, true);
        intent.putExtra(EXTRA_PREFIX_FLAG_WIDGET, "preset-1");
        intent.putExtra(EXTRA_PREFIX_MAIN_MODE, "photo");
        intent.putExtra(EXTRA_PREFIX_SUB_MODE, "manual");
        intent.putExtra(EXTRA_PREFIX_FACING, "0");
        intent.putExtra(EXTRA_PREFIX_FOCAL_LENGTH, spec.focalValue);

        session.activeStep = spec;
        session.activeLaunchExtras = widgetExtras(spec);
        return intent;
    }

    static JSONObject finishCurrentStep(Context context, Session session) throws Exception {
        StepSpec spec = session.activeStep;
        JSONObject actualExtras = session.activeLaunchExtras;
        if (spec == null || actualExtras == null) {
            throw new IllegalStateException("No widget-focal launch step is active");
        }

        // The shared direct-launch helper records timing here. Saved-image association and EXIF
        // inspection intentionally occur after all three stock-camera launches have completed.
        JSONObject launchRecord = OfficialExpertDirectLaunchAudit.finishCurrentStep(
                context,
                session.delegate
        );
        launchRecord.put("launchIntentAction", ACTION_WIDGET_CAMERA);
        launchRecord.put(
                "officialCameraComponent",
                packageName(session) + "/" + OFFICIAL_CAMERA_ACTIVITY
        );
        launchRecord.put("launchMechanism", "nothing-camera-widget-preset-focal-length");
        launchRecord.put("extras", actualExtras);
        launchRecord.put("requestedFocalLengthValue", spec.focalValue);
        launchRecord.put("expectedLensButton", spec.lensLabel);
        launchRecord.put("expectedInternalCameraId", spec.expectedCameraId);
        launchRecord.put("expectedPhysicalFocalLengthMm", spec.physicalFocalMm);
        launchRecord.put("expectedFocalLength35mmEquivalent", spec.equivalentFocalMm);
        launchRecord.put(
                "parserReasoning",
                "Nothing Camera first normalizes externally supplied rear IDs to SAT ID 4. "
                        + "Its widget parser then applies CAMERA_PREFIX_FOCALLENGTH_VALUE and, "
                        + "for manual mode, selects ultrawide below 1x, main at 1x, or telephoto "
                        + "at and above the configured tele ratio."
        );

        session.activeStep = null;
        session.activeLaunchExtras = null;
        session.nextStepIndex++;
        return launchRecord;
    }

    static boolean hasNextStep(Session session) {
        return session.nextStepIndex < STEPS.length
                && OfficialExpertDirectLaunchAudit.hasNextStep(session.delegate);
    }

    static String currentInstruction(Session session) {
        StepSpec spec = session.activeStep;
        if (spec == null) {
            throw new IllegalStateException("No widget-focal launch step is active");
        }
        return "Step " + (session.nextStepIndex + 1) + " of " + STEPS.length
                + ": Nothing Camera was launched through its preset path with "
                + spec.focalValue + " (expected " + spec.lensLabel + "). "
                + "Do not change the mode or lens. Take exactly one photo, then press Back.";
    }

    static JSONObject finish(Context context, Session session) throws Exception {
        if (session.activeStep != null) {
            throw new IllegalStateException("Cannot finish while a widget-focal step is active");
        }

        JSONObject report = OfficialExpertDirectLaunchAudit.finish(context, session.delegate);
        boolean complete = report.optBoolean("complete", false);
        boolean allHonored = report.optBoolean("allRequestedCameraIdsHonored", false);

        annotateObservedCaptures(context, report);

        report.put("mode", "official-camera-expert-widget-focal-launch");
        report.put(
                "officialCameraComponent",
                packageName(session) + "/" + OFFICIAL_CAMERA_ACTIVITY
        );
        report.put("launchIntentAction", ACTION_WIDGET_CAMERA);
        report.put("launchContract", new JSONObject()
                .put("mechanism", "Nothing Camera widget/preset parser")
                .put("widgetId", "preset-1")
                .put("mainMode", "photo")
                .put("subMode", "manual")
                .put("backFacingSeed", "0")
                .put("focalLengthExtra", EXTRA_PREFIX_FOCAL_LENGTH)
                .put("requestedSequence", new JSONArray()
                        .put(stepContract(STEPS[0]))
                        .put(stepContract(STEPS[1]))
                        .put(stepContract(STEPS[2]))));
        report.put("allWidgetFocalRoutesHonored", complete ? allHonored : JSONObject.NULL);
        report.put(
                "directIdNormalizationFinding",
                "The preceding direct-ID test stayed at 1x because tryToGetIntentCameraId() "
                        + "normalizes ordinary rear camera IDs to the SAT endpoint when SAT is "
                        + "supported. This audit instead exercises the later widget focal-length "
                        + "selection path used by Nothing Camera's own presets."
        );
        report.put(
                "interpretation",
                complete && allHonored
                        ? "The exported Nothing Camera widget preset contract selected the real "
                        + "ultrawide, main and telephoto routes from 15mm, 24mm and 50mm values."
                        : "At least one focal-length preset was not confirmed by EXIF. Inspect "
                        + "each capture to determine whether the exported widget contract was "
                        + "ignored, restricted, or remapped on this firmware."
        );
        report.put(
                "diagnosticBoundary",
                "The official Nothing camera still owns each privileged camera session. A "
                        + "successful result would provide automatic stock-camera handoff only; "
                        + "it would not expose private CaptureRequest/CaptureResult data or raw "
                        + "frames to the diagnostics or production application."
        );
        return report;
    }

    private static void annotateObservedCaptures(Context context, JSONObject report)
            throws Exception {
        JSONObject observed = report.optJSONObject("observedOfficialCameraAudit");
        JSONArray captures = observed == null
                ? null
                : observed.optJSONArray("associatedCaptures");
        if (captures == null) {
            return;
        }

        int count = Math.min(captures.length(), STEPS.length);
        for (int index = 0; index < count; index++) {
            StepSpec spec = STEPS[index];
            JSONObject capture = captures.getJSONObject(index);
            Object honored = capture.opt("requestedCameraIdHonored");
            capture.put("requestedFocalLengthValue", spec.focalValue);
            capture.put("expectedLensButton", spec.lensLabel);
            capture.put("expectedInternalCameraId", spec.expectedCameraId);
            capture.put("widgetFocalRouteHonored", honored);
            capture.put(
                    "routeDecisionRule",
                    "EXIF is compared with " + spec.physicalFocalMm
                            + " mm physical and " + spec.equivalentFocalMm
                            + " mm equivalent."
            );
            relocateDiagnosticCopy(context, capture, spec);
        }
    }

    private static JSONObject widgetExtras(StepSpec spec) throws Exception {
        return new JSONObject()
                .put(EXTRA_WIDGET_CAMERA, true)
                .put(EXTRA_IS_FROM_WIDGET, true)
                .put(EXTRA_PREFIX_FLAG_WIDGET, "preset-1")
                .put(EXTRA_PREFIX_MAIN_MODE, "photo")
                .put(EXTRA_PREFIX_SUB_MODE, "manual")
                .put(EXTRA_PREFIX_FACING, "0")
                .put(EXTRA_PREFIX_FOCAL_LENGTH, spec.focalValue);
    }

    private static JSONObject stepContract(StepSpec spec) throws Exception {
        return new JSONObject()
                .put("focalLengthValue", spec.focalValue)
                .put("expectedLens", spec.lensLabel)
                .put("expectedInternalCameraId", spec.expectedCameraId)
                .put("expectedPhysicalFocalLengthMm", spec.physicalFocalMm)
                .put("expectedFocalLength35mmEquivalent", spec.equivalentFocalMm);
    }

    private static void relocateDiagnosticCopy(
            Context context,
            JSONObject capture,
            StepSpec spec
    ) throws Exception {
        String copyUriText = capture.optString("directDiagnosticCopyUri", "");
        if (copyUriText.isEmpty()) {
            copyUriText = capture.optString("diagnosticCopyUri", "");
        }
        if (copyUriText.isEmpty()) {
            return;
        }

        JSONObject source = capture.optJSONObject("sourceMediaStore");
        String sourceName = source == null
                ? "capture.jpg"
                : source.optString("displayName", "capture.jpg");
        String extension = extensionFor(sourceName);
        String displayName = String.format(
                Locale.US,
                "phone2pro-official-widget-focal-%s-id-%d%s",
                spec.focalValue.replace(".", "_"),
                spec.expectedCameraId,
                extension
        );

        Uri copyUri = Uri.parse(copyUriText);
        ContentValues values = new ContentValues();
        values.put(MediaStore.Images.Media.DISPLAY_NAME, displayName);
        values.put(MediaStore.Images.Media.RELATIVE_PATH, OUTPUT_FOLDER);
        int updated = context.getContentResolver().update(copyUri, values, null, null);
        capture.put("widgetDiagnosticCopyUri", copyUri.toString());
        capture.put("diagnosticCopyRelocated", updated > 0);
        capture.put("diagnosticCopyFolder", OUTPUT_FOLDER);
        capture.put("diagnosticCopyDisplayName", displayName);
    }

    private static String packageName(Session session) {
        return session.delegate.baseSession.packageName;
    }

    private static String extensionFor(String displayName) {
        int dot = displayName == null ? -1 : displayName.lastIndexOf('.');
        if (dot >= 0 && dot < displayName.length() - 1) {
            return displayName.substring(dot);
        }
        return ".jpg";
    }

    static final class Session {
        final OfficialExpertDirectLaunchAudit.Session delegate;
        private int nextStepIndex;
        private StepSpec activeStep;
        private JSONObject activeLaunchExtras;

        Session(OfficialExpertDirectLaunchAudit.Session delegate) {
            this.delegate = delegate;
        }

        void stopAvailabilityRecording() {
            delegate.stopAvailabilityRecording();
        }
    }

    private static final class StepSpec {
        final int expectedCameraId;
        final String lensLabel;
        final String focalValue;
        final double physicalFocalMm;
        final double equivalentFocalMm;

        StepSpec(
                int expectedCameraId,
                String lensLabel,
                String focalValue,
                double physicalFocalMm,
                double equivalentFocalMm
        ) {
            this.expectedCameraId = expectedCameraId;
            this.lensLabel = lensLabel;
            this.focalValue = focalValue;
            this.physicalFocalMm = physicalFocalMm;
            this.equivalentFocalMm = equivalentFocalMm;
        }
    }
}
