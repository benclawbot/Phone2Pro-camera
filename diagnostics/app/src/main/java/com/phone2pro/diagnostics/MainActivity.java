package com.phone2pro.diagnostics;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
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
    private static final int CAMERA_PERMISSION_REQUEST = 100;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final List<Button> profileButtons = new ArrayList<>();
    private DiagnosticProfile pendingProfile;
    private TextView statusView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
    }

    @Override
    protected void onDestroy() {
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
                "Choose the profile that matches the current conditions. Each run creates a separately named JSON report. Capture profiles also save clearly named JPEG samples.",
                15,
                Color.LTGRAY
        );
        description.setGravity(Gravity.CENTER_HORIZONTAL);
        description.setPadding(0, dp(12), 0, dp(24));
        root.addView(description);

        addProfile(root, DiagnosticProfile.STATIC_AUDIT);
        addProfile(root, DiagnosticProfile.NIGHT_LOW_LIGHT);
        addProfile(root, DiagnosticProfile.DAYLIGHT_LENS_ROUTING);

        statusView = text("Ready. Run the static audit first, then the profile matching the light.", 14,
                Color.rgb(210, 210, 210));
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
        button.setOnClickListener(v -> ensurePermissionAndStart(profile));
        profileButtons.add(button);
        root.addView(button, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        TextView details = text(profile.description, 13, Color.rgb(185, 185, 185));
        details.setPadding(dp(8), dp(4), dp(8), dp(18));
        root.addView(details);
    }

    private void ensurePermissionAndStart(DiagnosticProfile profile) {
        pendingProfile = profile;
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            runDiagnostics(profile);
        } else {
            statusView.setText("Camera permission is required for the selected diagnostics profile.");
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) {
            return;
        }
        if (grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED
                && pendingProfile != null) {
            runDiagnostics(pendingProfile);
        } else {
            statusView.setText("Permission denied. No report was created.");
        }
    }

    private void runDiagnostics(DiagnosticProfile profile) {
        setButtonsEnabled(false);
        statusView.setText("Running " + profile.buttonLabel + "… Keep the phone steady and the app open.");

        worker.execute(() -> {
            try {
                JSONObject report = new CapabilityReporter(this).build();
                JSONObject profileInfo = new JSONObject();
                profileInfo.put("id", profile.fileLabel);
                profileInfo.put("label", profile.buttonLabel);
                profileInfo.put("description", profile.description);
                report.put("selectedProfile", profileInfo);

                String captureWarning = null;
                if (profile.capturesImages) {
                    try (CaptureDiagnosticRunner runner = new CaptureDiagnosticRunner(this, profile)) {
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
                    statusView.setText("Diagnostics failed before a report could be saved:\n" + error);
                    setButtonsEnabled(true);
                });
            }
        });
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
