package com.phone2pro.diagnostics;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.IOException;
import java.text.DateFormat;
import java.util.Date;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION_REQUEST = 100;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private TextView reportView;
    private ImageView latestThumbnail;
    private JSONObject latestReport;
    private Uri latestPhotoUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
        restoreLatestThumbnail();
    }

    @Override
    protected void onResume() {
        super.onResume();
        restoreLatestThumbnail();
    }

    @Override
    protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }

    private View buildUi() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(16, 16, 16));

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(20), dp(20), dp(108));

        TextView title = text("Phone2Pro capability audit", 24, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        content.addView(title);

        TextView subtitle = text(
                "Static Camera2, sensor, codec, memory, thermal, and gallery-interoperability diagnostics. All output remains on this phone.",
                14,
                Color.LTGRAY
        );
        subtitle.setPadding(0, dp(8), 0, dp(16));
        content.addView(subtitle);

        Button audit = button(getString(R.string.run_audit));
        audit.setOnClickListener(v -> ensurePermissionAndRunAudit());
        content.addView(audit);

        Button export = button(getString(R.string.export_report));
        export.setOnClickListener(v -> exportReport());
        content.addView(export);

        Button galleryTest = button(getString(R.string.gallery_test));
        galleryTest.setOnClickListener(v -> createGalleryTestJpeg());
        content.addView(galleryTest);

        reportView = text("No report generated yet.", 12, Color.rgb(210, 210, 210));
        reportView.setTextIsSelectable(true);
        reportView.setTypeface(Typeface.MONOSPACE);
        reportView.setPadding(0, dp(12), 0, 0);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(reportView);
        content.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
        ));

        root.addView(content, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));

        latestThumbnail = new ImageView(this);
        latestThumbnail.setContentDescription(getString(R.string.thumbnail_description));
        latestThumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);
        GradientDrawable circle = new GradientDrawable();
        circle.setShape(GradientDrawable.OVAL);
        circle.setColor(Color.rgb(45, 45, 45));
        circle.setStroke(dp(2), Color.WHITE);
        latestThumbnail.setBackground(circle);
        latestThumbnail.setClipToOutline(true);
        latestThumbnail.setOnClickListener(v -> {
            if (latestPhotoUri != null) {
                MediaInterop.openInDefaultViewer(this, latestPhotoUri);
            } else {
                Toast.makeText(this, "Create a gallery test JPEG first", Toast.LENGTH_SHORT).show();
            }
        });

        FrameLayout.LayoutParams thumbnailParams = new FrameLayout.LayoutParams(dp(72), dp(72));
        thumbnailParams.gravity = Gravity.BOTTOM | Gravity.START;
        thumbnailParams.setMargins(dp(24), 0, 0, dp(24));
        root.addView(latestThumbnail, thumbnailParams);

        TextView hint = text("Tap to open in default viewer", 12, Color.LTGRAY);
        FrameLayout.LayoutParams hintParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        hintParams.gravity = Gravity.BOTTOM | Gravity.START;
        hintParams.setMargins(dp(108), 0, 0, dp(48));
        root.addView(hint, hintParams);
        return root;
    }

    private void ensurePermissionAndRunAudit() {
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            runAudit();
        } else {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_REQUEST
                && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            runAudit();
        } else if (requestCode == CAMERA_PERMISSION_REQUEST) {
            Toast.makeText(this, "Camera permission is required for the complete audit", Toast.LENGTH_LONG).show();
        }
    }

    private void runAudit() {
        reportView.setText("Collecting capabilities…");
        worker.execute(() -> {
            try {
                JSONObject report = new CapabilityReporter(this).build();
                latestReport = report;
                String formatted = report.toString(2);
                runOnUiThread(() -> reportView.setText(formatted));
            } catch (Exception error) {
                runOnUiThread(() -> reportView.setText("Audit failed:\n" + error));
            }
        });
    }

    private void exportReport() {
        JSONObject report = latestReport;
        if (report == null) {
            Toast.makeText(this, "Run the capability audit first", Toast.LENGTH_SHORT).show();
            return;
        }
        worker.execute(() -> {
            try {
                Uri uri = MediaInterop.saveJsonReport(this, report.toString(2));
                runOnUiThread(() -> Toast.makeText(
                        this,
                        "Report saved to Downloads/Phone2Pro Diagnostics\n" + uri,
                        Toast.LENGTH_LONG
                ).show());
            } catch (Exception error) {
                runOnUiThread(() -> Toast.makeText(this, "Export failed: " + error, Toast.LENGTH_LONG).show());
            }
        });
    }

    private void createGalleryTestJpeg() {
        worker.execute(() -> {
            Bitmap bitmap = Bitmap.createBitmap(1200, 900, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(bitmap);
            canvas.drawColor(Color.rgb(25, 25, 28));
            Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
            paint.setColor(Color.WHITE);
            paint.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
            paint.setTextSize(68f);
            canvas.drawText("Phone2Pro Camera", 72f, 150f, paint);
            paint.setTypeface(Typeface.DEFAULT);
            paint.setTextSize(42f);
            canvas.drawText("Gallery interoperability test", 72f, 240f, paint);
            paint.setColor(Color.rgb(185, 255, 210));
            canvas.drawText(DateFormat.getDateTimeInstance().format(new Date()), 72f, 330f, paint);
            paint.setColor(Color.LTGRAY);
            paint.setTextSize(34f);
            canvas.drawText("Tap the bottom-left thumbnail to open", 72f, 690f, paint);
            canvas.drawText("this JPEG in the phone's default viewer.", 72f, 745f, paint);

            try {
                Uri uri = MediaInterop.saveJpeg(this, bitmap);
                bitmap.recycle();
                Bitmap thumbnail = MediaInterop.loadThumbnail(this, uri, 240);
                latestPhotoUri = uri;
                runOnUiThread(() -> {
                    latestThumbnail.setImageBitmap(thumbnail);
                    Toast.makeText(this, "JPEG saved to DCIM/Phone2Pro Camera", Toast.LENGTH_LONG).show();
                });
            } catch (IOException error) {
                bitmap.recycle();
                runOnUiThread(() -> Toast.makeText(this, "JPEG test failed: " + error, Toast.LENGTH_LONG).show());
            }
        });
    }

    private void restoreLatestThumbnail() {
        Uri uri = MediaInterop.getLatestPhotoUri(this);
        if (uri == null) {
            latestPhotoUri = null;
            if (latestThumbnail != null) {
                latestThumbnail.setImageDrawable(null);
            }
            return;
        }
        worker.execute(() -> {
            try {
                Bitmap thumbnail = MediaInterop.loadThumbnail(this, uri, 240);
                latestPhotoUri = uri;
                runOnUiThread(() -> latestThumbnail.setImageBitmap(thumbnail));
            } catch (IOException | SecurityException error) {
                MediaInterop.clearLatestPhoto(this);
                latestPhotoUri = null;
                runOnUiThread(() -> latestThumbnail.setImageDrawable(null));
            }
        });
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.bottomMargin = dp(8);
        button.setLayoutParams(params);
        return button;
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
