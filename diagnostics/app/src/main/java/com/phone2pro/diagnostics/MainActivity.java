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
import android.widget.TextView;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION_REQUEST = 100;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private Button startButton;
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
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(24), dp(48), dp(24), dp(24));
        root.setBackgroundColor(Color.rgb(16, 16, 16));

        TextView title = text("Phone2Pro capability audit", 26, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView description = text(
                "Press the button once. The app collects the public Camera2, sensor, codec, memory, and thermal information needed to plan the camera app, then saves one JSON report locally.",
                15,
                Color.LTGRAY
        );
        description.setGravity(Gravity.CENTER_HORIZONTAL);
        description.setPadding(0, dp(12), 0, dp(28));
        root.addView(description);

        startButton = new Button(this);
        startButton.setText(R.string.start_diagnostics);
        startButton.setAllCaps(false);
        startButton.setOnClickListener(v -> ensurePermissionAndStart());
        root.addView(startButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        statusView = text("Ready.", 14, Color.rgb(210, 210, 210));
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        statusView.setPadding(0, dp(24), 0, 0);
        statusView.setTextIsSelectable(true);
        root.addView(statusView);
        return root;
    }

    private void ensurePermissionAndStart() {
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            runDiagnostics();
        } else {
            statusView.setText("Camera permission is required to inspect all public camera capabilities.");
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) {
            return;
        }
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            runDiagnostics();
        } else {
            statusView.setText("Permission denied. No report was created.");
        }
    }

    private void runDiagnostics() {
        startButton.setEnabled(false);
        statusView.setText("Collecting phone capabilities and creating the report…");

        worker.execute(() -> {
            try {
                JSONObject report = new CapabilityReporter(this).build();
                Uri reportUri = ReportStorage.saveJsonReport(this, report.toString(2));
                runOnUiThread(() -> {
                    statusView.setText(
                            "Report complete.\nSaved in Downloads/Phone2Pro Diagnostics\n" + reportUri
                    );
                    startButton.setEnabled(true);
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    statusView.setText("Diagnostics failed:\n" + error);
                    startButton.setEnabled(true);
                });
            }
        });
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
