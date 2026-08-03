package com.phone2pro.diagnostics;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int PERMISSION_REQUEST = 100;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final List<Button> profileButtons = new ArrayList<>();
    private DiagnosticProfile pendingProfile;
    private TextView statusView;

    private OfficialExpertCameraAudit.Session officialExpertSession;
    private boolean officialCameraLeftDiagnostics;
    private boolean processingOfficialCameraReturn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (officialExpertSession != null
                && officialCameraLeftDiagnostics
                && !processingOfficialCameraReturn) {
            officialCameraLeftDiagnostics = false;
            processingOfficialCameraReturn = true;
            finishOfficialExpertAudit();
        }
    }

    @Override
    protected void onStop() {
        if (officialExpertSession != null && !processingOfficialCameraReturn) {
            officialCameraLeftDiagnostics = true;
        }
        super.onStop();
    }

    @Override
    protected void onDestroy() {
        if (officialExpertSession != null) {
            officialExpertSession.stopAvailabilityRecording();
        }
        worker.shutdownNow();
        super.onDestroy();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(24), dp(40), dp(24), dp(32));
        root.setBackgroundColor(Color.rgb(16, 16, 16));
        scroll.addView(root);

        TextView title = text("Phone2Pro diagnostics", 26, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView description = text(
                "Choose one diagnostic profile. Each run creates a separately named JSON report. Capture profiles also save clearly named image samples.",
                15,
                Color.LTGRAY
        );
        description.setGravity(Gravity.CENTER_HORIZONTAL);
        description.setPadding(0, dp(12), 0, dp(24));
        root.addView(description);

        addProfile(root, DiagnosticProfile.STATIC_AUDIT);
        addProfile(root, DiagnosticProfile.NIGHT_LOW_LIGHT);
        addProfile(root, DiagnosticProfile.DAYLIGHT_LENS_ROUTING);
        addProfile(root, DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING);

        statusView = text(
                "Ready. Use the official Expert-mode audit to compare the stock camera's 0.6x, 1x and 2x routes.",
                14,
                Color.rgb(210, 210, 210)
        );
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        statusView.setPadding(0, dp(24), 0, 0);
        statusView.setTextIsSelectable(true);
        root.addView(statusView);
        return scroll;
    }

    private void addProfile(LinearLayout root, DiagnosticProfile profile) {
        Button button = new Button(this);
        button.setText(profile.buttonLabel);
        button.setAllCaps(false);
        button.setOnClickListener(v -> ensurePermissionsAndStart(profile));
        profileButtons.add(button);
        root.addView(button, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        TextView details = text(profile.description, 13, Color.rgb(185, 185, 185));
        details.setPadding(dp(8), dp(4), dp(8), dp(18));
        root.addView(details);
    }

    private void ensurePermissionsAndStart(DiagnosticProfile profile) {
        pendingProfile = profile;
        List<String> missing = missingPermissions(profile);
        if (missing.isEmpty()) {
            startProfile(profile);
            return;
        }

        if (profile == DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING) {
            statusView.setText(
                    "Camera permission and full Photos and videos access are required to associate the three official-camera images with 0.6x, 1x and 2x."
            );
        } else {
            statusView.setText("Camera permission is required for this diagnostics profile.");
        }
        requestPermissions(missing.toArray(new String[0]), PERMISSION_REQUEST);
    }

    private List<String> missingPermissions(DiagnosticProfile profile) {
        List<String> missing = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.CAMERA);
        }

        if (profile == DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING) {
            String mediaPermission = Build.VERSION.SDK_INT >= 33
                    ? Manifest.permission.READ_MEDIA_IMAGES
                    : Manifest.permission.READ_EXTERNAL_STORAGE;
            if (checkSelfPermission(mediaPermission) != PackageManager.PERMISSION_GRANTED) {
                missing.add(mediaPermission);
            }
        }
        return missing;
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            String[] permissions,
            int[] grantResults
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != PERMISSION_REQUEST) {
            return;
        }

        boolean allGranted = grantResults.length > 0;
        for (int result : grantResults) {
            allGranted &= result == PackageManager.PERMISSION_GRANTED;
        }

        if (allGranted && pendingProfile != null
                && missingPermissions(pendingProfile).isEmpty()) {
            startProfile(pendingProfile);
        } else if (pendingProfile == DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING) {
            statusView.setText(
                    "Permission denied or limited. Grant Camera and full Photos and videos access, not selected-photo access, then run the Expert-mode audit again."
            );
        } else {
            statusView.setText("Permission denied. No report was created.");
        }
    }

    private void startProfile(DiagnosticProfile profile) {
        if (profile == DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING) {
            showOfficialExpertInstructions();
        } else {
            runDiagnostics(profile);
        }
    }

    private void showOfficialExpertInstructions() {
        new AlertDialog.Builder(this)
                .setTitle("Official camera Expert-mode audit")
                .setMessage(
                        "Keep the phone in the same position and point it at a scene with both near and distant detail.\n\n"
                                + "In the official camera:\n"
                                + "1. Switch to Expert mode.\n"
                                + "2. Select 0.6x and take exactly one photo.\n"
                                + "3. Select 1x and take exactly one photo.\n"
                                + "4. Select 2x and take exactly one photo.\n"
                                + "5. Press Back to return here.\n\n"
                                + "Do not take extra photos during this sequence. Leave JPEG or HEIF output enabled; RAW may also be enabled."
                )
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Open official camera", (dialog, which) ->
                        prepareOfficialExpertAudit())
                .show();
    }

    private void prepareOfficialExpertAudit() {
        setButtonsEnabled(false);
        statusView.setText("Preparing the official Expert-mode audit…");

        worker.execute(() -> {
            try {
                OfficialExpertCameraAudit.Session session =
                        OfficialExpertCameraAudit.prepare(this);
                runOnUiThread(() -> launchOfficialCamera(session));
            } catch (Exception error) {
                runOnUiThread(() -> {
                    statusView.setText(
                            "Unable to launch the official camera audit:\n" + error
                    );
                    setButtonsEnabled(true);
                });
            }
        });
    }

    private void launchOfficialCamera(OfficialExpertCameraAudit.Session session) {
        officialExpertSession = session;
        officialCameraLeftDiagnostics = false;
        processingOfficialCameraReturn = false;
        statusView.setText(
                "Official camera opened. In Expert mode take exactly one 0.6x, one 1x and one 2x photo in that order, then return."
        );
        try {
            startActivity(session.launchIntent);
        } catch (RuntimeException error) {
            session.stopAvailabilityRecording();
            officialExpertSession = null;
            statusView.setText("Official camera launch failed:\n" + error);
            setButtonsEnabled(true);
        }
    }

    private void finishOfficialExpertAudit() {
        OfficialExpertCameraAudit.Session session = officialExpertSession;
        officialExpertSession = null;
        statusView.setText(
                "Associating the official Expert-mode photos with 0.6x, 1x and 2x and reading lens metadata…"
        );

        worker.execute(() -> {
            try {
                JSONObject officialAudit = OfficialExpertCameraAudit.finish(this, session);
                JSONObject report = new CapabilityReporter(this).build();
                report.put(
                        "selectedProfile",
                        selectedProfileJson(DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING)
                );
                report.put("officialCameraExpertAudit", officialAudit);

                Uri reportUri = ReportStorage.saveJsonReport(
                        this,
                        DiagnosticProfile.OFFICIAL_EXPERT_LENS_ROUTING.fileLabel,
                        report.toString(2)
                );
                boolean complete = officialAudit.optBoolean("complete", false);
                runOnUiThread(() -> {
                    String message = complete
                            ? "Official Expert-mode audit complete."
                            : "Official Expert-mode audit saved, but fewer than three primary photos were associated.";
                    message += "\nReport: Downloads/Phone2Pro Diagnostics\n"
                            + reportUri
                            + "\nAssociated copies: Pictures/Phone2Pro Diagnostics/Official Expert Camera Audit";
                    statusView.setText(message);
                    processingOfficialCameraReturn = false;
                    setButtonsEnabled(true);
                });
            } catch (Exception error) {
                session.stopAvailabilityRecording();
                runOnUiThread(() -> {
                    statusView.setText(
                            "Official Expert-mode audit failed before its report could be saved:\n"
                                    + error
                    );
                    processingOfficialCameraReturn = false;
                    setButtonsEnabled(true);
                });
            }
        });
    }

    private void runDiagnostics(DiagnosticProfile profile) {
        setButtonsEnabled(false);
        statusView.setText(
                "Running " + profile.buttonLabel
                        + "… Keep the phone steady and the app open."
        );

        worker.execute(() -> {
            try {
                JSONObject report = new CapabilityReporter(this).build();
                report.put("selectedProfile", selectedProfileJson(profile));

                String captureWarning = null;
                if (profile.capturesImages) {
                    try (CaptureDiagnosticRunner runner =
                                 new CaptureDiagnosticRunner(this, profile)) {
                        report.put("captureAudit", runner.run());
                    } catch (Exception captureError) {
                        captureWarning = captureError.toString();
                        report.put("captureAuditError", captureWarning);
                    }
                }

                Uri reportUri = ReportStorage.saveJsonReport(
                        this,
                        profile.fileLabel,
                        report.toString(2)
                );
                String finalCaptureWarning = captureWarning;
                runOnUiThread(() -> {
                    String message = "Report complete.\n"
                            + "Downloads/Phone2Pro Diagnostics\n"
                            + reportUri;
                    if (profile.capturesImages) {
                        message += "\nSamples: Pictures/Phone2Pro Diagnostics";
                    }
                    if (finalCaptureWarning != null) {
                        message += "\n\nCapture audit reported an error but the JSON was saved:\n"
                                + finalCaptureWarning;
                    }
                    statusView.setText(message);
                    setButtonsEnabled(true);
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    statusView.setText(
                            "Diagnostics failed before a report could be saved:\n" + error
                    );
                    setButtonsEnabled(true);
                });
            }
        });
    }

    private JSONObject selectedProfileJson(DiagnosticProfile profile) throws Exception {
        return new JSONObject()
                .put("id", profile.fileLabel)
                .put("label", profile.buttonLabel)
                .put("description", profile.description);
    }

    private void setButtonsEnabled(boolean enabled) {
        for (Button button : profileButtons) {
            button.setEnabled(enabled);
        }
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
