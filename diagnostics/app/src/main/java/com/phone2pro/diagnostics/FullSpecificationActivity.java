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
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class FullSpecificationActivity extends Activity {
    private static final int CAMERA_PERMISSION_REQUEST = 200;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private Button runButton;
    private ProgressBar progressBar;
    private TextView statusView;
    private boolean running;

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
        root.setPadding(dp(24), dp(38), dp(24), dp(32));
        root.setBackgroundColor(Color.rgb(15, 15, 15));
        scroll.addView(root);

        TextView title = text("CMF Camera Platform Specification", 25, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView description = text(
                "Build one evidence-backed JSON specification of the public camera surface, hidden and system-only ID boundary, stream sessions, request and result metadata, vendor tags, sensor calibration, and burst performance.",
                15,
                Color.LTGRAY
        );
        description.setPadding(0, dp(14), 0, dp(18));
        description.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(description);

        TextView privacy = text(
                "All analysis stays on the phone. The run drains test YUV frames without saving photographs and does not require network access.",
                13,
                Color.rgb(185, 185, 185)
        );
        privacy.setPadding(0, 0, 0, dp(20));
        privacy.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(privacy);

        runButton = new Button(this);
        runButton.setAllCaps(false);
        runButton.setText("Build full camera specification");
        runButton.setOnClickListener(v -> ensurePermissionAndRun());
        root.addView(runButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        progressBar = new ProgressBar(this);
        progressBar.setIndeterminate(true);
        progressBar.setVisibility(View.GONE);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        progressParams.topMargin = dp(20);
        root.addView(progressBar, progressParams);

        statusView = text(
                "Ready. Keep the phone still and leave the app open during the capture and session tests.",
                14,
                Color.rgb(215, 215, 215)
        );
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        statusView.setPadding(0, dp(18), 0, 0);
        statusView.setTextIsSelectable(true);
        root.addView(statusView);
        return scroll;
    }

    private void ensurePermissionAndRun() {
        if (running) {
            return;
        }
        if (checkSelfPermission(Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            runSpecification();
            return;
        }
        statusView.setText("Camera permission is required to open devices and validate sessions.");
        requestPermissions(
                new String[]{Manifest.permission.CAMERA},
                CAMERA_PERMISSION_REQUEST
        );
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            String[] permissions,
            int[] grantResults
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) {
            return;
        }
        if (grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            runSpecification();
        } else {
            statusView.setText("Camera permission denied. No specification was created.");
        }
    }

    private void runSpecification() {
        running = true;
        runButton.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);
        statusView.setText("Starting full camera platform specification…");

        worker.execute(() -> {
            try {
                FullSpecificationRunner runner = new FullSpecificationRunner(
                        this,
                        message -> runOnUiThread(() -> statusView.setText(message))
                );
                JSONObject report = runner.run();
                Uri reportUri = ReportStorage.saveJsonReport(
                        this,
                        "full-camera-platform-specification",
                        report.toString(2)
                );
                runOnUiThread(() -> finishSuccess(reportUri, report));
            } catch (Throwable error) {
                runOnUiThread(() -> finishFailure(error));
            }
        });
    }

    private void finishSuccess(Uri uri, JSONObject report) {
        running = false;
        runButton.setEnabled(true);
        progressBar.setVisibility(View.GONE);

        JSONObject full = report.optJSONObject("fullCameraPlatformSpecification");
        JSONObject route = full == null
                ? null
                : full.optJSONObject("routeClassification");
        String classification = route == null
                ? "unavailable"
                : route.optString("classification", "unavailable");
        String summary = "Specification complete.\n"
                + "Route classification: " + classification + "\n\n"
                + "Saved to Downloads/Phone2Pro Diagnostics\n"
                + uri;
        statusView.setText(summary);
    }

    private void finishFailure(Throwable error) {
        running = false;
        runButton.setEnabled(true);
        progressBar.setVisibility(View.GONE);
        statusView.setText(
                "The run failed before the JSON report was saved:\n" + error
        );
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
