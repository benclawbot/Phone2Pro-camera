package com.phone2pro.camera;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.activity.ComponentActivity;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;

import com.phone2pro.camera.capture.CameraSessionController;
import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteDecision;

import java.util.LinkedHashMap;
import java.util.Map;

/** First production-app shell: preview, transparent route negotiation and MediaStore capture. */
public final class MainActivity extends ComponentActivity
        implements CameraSessionController.Listener {

    private final Map<OpticalRoute, Button> routeButtons = new LinkedHashMap<>();
    private final Map<CaptureProfile, Button> profileButtons = new LinkedHashMap<>();

    private PreviewView previewView;
    private TextView statusView;
    private Button captureButton;
    private ImageView latestImageView;
    private CameraSessionController controller;
    private Uri latestUri;

    private final ActivityResultLauncher<String> cameraPermissionLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.RequestPermission(),
                    granted -> {
                        if (granted) {
                            startCamera();
                        } else {
                            showStatus("Camera permission is required. No image data leaves the device.");
                        }
                    }
            );

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        setContentView(buildUi());

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCamera();
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA);
        }
    }

    @Override
    protected void onDestroy() {
        if (controller != null) {
            controller.shutdown();
        }
        super.onDestroy();
    }

    private View buildUi() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        previewView = new PreviewView(this);
        previewView.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
        previewView.setScaleType(PreviewView.ScaleType.FILL_CENTER);
        root.addView(
                previewView,
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                )
        );

        statusView = new TextView(this);
        statusView.setTextColor(Color.WHITE);
        statusView.setTextSize(14);
        statusView.setPadding(dp(12), dp(10), dp(12), dp(10));
        statusView.setBackgroundColor(0xB3000000);
        statusView.setText("Initializing on-device camera…");
        FrameLayout.LayoutParams statusParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.TOP
        );
        root.addView(statusView, statusParams);

        LinearLayout profileBar = new LinearLayout(this);
        profileBar.setOrientation(LinearLayout.HORIZONTAL);
        profileBar.setGravity(Gravity.CENTER);
        profileBar.setPadding(dp(8), dp(6), dp(8), dp(6));
        profileBar.setBackgroundColor(0x88000000);
        for (CaptureProfile profile : CaptureProfile.values()) {
            Button button = compactButton(profile.label());
            button.setOnClickListener(view -> {
                if (controller != null) {
                    controller.setCaptureProfile(profile);
                    updateProfileSelection(profile);
                    showStatus(profile.implementationStatus());
                }
            });
            profileButtons.put(profile, button);
            profileBar.addView(button, weightedButtonParams());
        }
        FrameLayout.LayoutParams profileParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(54),
                Gravity.TOP
        );
        profileParams.topMargin = dp(56);
        root.addView(profileBar, profileParams);

        LinearLayout bottomPanel = new LinearLayout(this);
        bottomPanel.setOrientation(LinearLayout.VERTICAL);
        bottomPanel.setGravity(Gravity.CENTER);
        bottomPanel.setPadding(dp(10), dp(8), dp(10), dp(12));
        bottomPanel.setBackgroundColor(0xA6000000);

        LinearLayout routeBar = new LinearLayout(this);
        routeBar.setOrientation(LinearLayout.HORIZONTAL);
        routeBar.setGravity(Gravity.CENTER);
        addRouteButton(routeBar, OpticalRoute.ULTRAWIDE);
        addRouteButton(routeBar, OpticalRoute.MAIN);
        addRouteButton(routeBar, OpticalRoute.TELEPHOTO);
        bottomPanel.addView(
                routeBar,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        dp(58)
                )
        );

        FrameLayout captureRow = new FrameLayout(this);
        latestImageView = new ImageView(this);
        latestImageView.setVisibility(View.GONE);
        latestImageView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        latestImageView.setContentDescription("Open latest photo");
        latestImageView.setBackgroundColor(0xFF303030);
        latestImageView.setOnClickListener(view -> openLatestPhoto());
        FrameLayout.LayoutParams latestParams = new FrameLayout.LayoutParams(
                dp(64),
                dp(64),
                Gravity.START | Gravity.CENTER_VERTICAL
        );
        captureRow.addView(latestImageView, latestParams);

        captureButton = new Button(this);
        captureButton.setText("●");
        captureButton.setTextSize(34);
        captureButton.setTextColor(Color.WHITE);
        captureButton.setContentDescription("Take photo");
        captureButton.setEnabled(false);
        captureButton.setOnClickListener(view -> {
            captureButton.setEnabled(false);
            showStatus("Capturing on device…");
            if (controller != null) {
                controller.takePhoto();
            }
        });
        FrameLayout.LayoutParams captureParams = new FrameLayout.LayoutParams(
                dp(82),
                dp(72),
                Gravity.CENTER
        );
        captureRow.addView(captureButton, captureParams);

        bottomPanel.addView(
                captureRow,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        dp(78)
                )
        );

        FrameLayout.LayoutParams bottomParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(156),
                Gravity.BOTTOM
        );
        root.addView(bottomPanel, bottomParams);

        updateProfileSelection(CaptureProfile.AUTO);
        updateRouteSelection(OpticalRoute.MAIN);
        return root;
    }

    private void addRouteButton(LinearLayout routeBar, OpticalRoute route) {
        Button button = compactButton(route.label());
        button.setOnClickListener(view -> {
            updateRouteSelection(route);
            if (controller != null) {
                controller.selectRoute(route);
            }
        });
        routeButtons.put(route, button);
        routeBar.addView(button, weightedButtonParams());
    }

    private Button compactButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setTextSize(13);
        button.setAllCaps(false);
        button.setSingleLine(false);
        button.setPadding(dp(4), 0, dp(4), 0);
        button.setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(0xFF323232)
        );
        return button;
    }

    private LinearLayout.LayoutParams weightedButtonParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(48), 1f);
        params.setMarginStart(dp(3));
        params.setMarginEnd(dp(3));
        return params;
    }

    private void startCamera() {
        if (controller != null) {
            return;
        }
        controller = new CameraSessionController(
                this,
                this,
                previewView.getSurfaceProvider(),
                this
        );
        controller.start();
    }

    @Override
    public void onCapabilitiesReady(
            DeviceCapabilitySnapshot capabilities,
            RouteDecision ultrawide,
            RouteDecision main,
            RouteDecision telephoto
    ) {
        updateRouteButton(OpticalRoute.ULTRAWIDE, ultrawide);
        updateRouteButton(OpticalRoute.MAIN, main);
        updateRouteButton(OpticalRoute.TELEPHOTO, telephoto);

        showStatus(
                "Public camera IDs: " + capabilities.publicCameraIds()
                        + ". Optical auxiliary routes stay unavailable until a verified backend exists."
        );
    }

    @Override
    public void onSessionReady(
            OpticalRoute route,
            RouteDecision decision,
            CaptureProfile profile
    ) {
        updateRouteSelection(route);
        updateProfileSelection(profile);
        captureButton.setEnabled(true);
        showStatus(
                route + " via " + decision.support().mechanism()
                        + ". " + profile.implementationStatus() + "."
        );
    }

    @Override
    public void onRouteUnavailable(OpticalRoute route, RouteDecision decision) {
        captureButton.setEnabled(false);
        showStatus(route.label() + " unavailable: " + decision.support().reason());
    }

    @Override
    public void onCaptureSaved(@NonNull Uri uri) {
        latestUri = uri;
        latestImageView.setImageURI(null);
        latestImageView.setImageURI(uri);
        latestImageView.setVisibility(View.VISIBLE);
        captureButton.setEnabled(true);
        showStatus("Saved on device: " + uri);
    }

    @Override
    public void onError(@NonNull String message, Throwable error) {
        captureButton.setEnabled(controller != null && OpticalRoute.MAIN.equals(controller.selectedRoute()));
        showStatus(error == null ? message : message + " (" + error.getClass().getSimpleName() + ")");
    }

    private void updateRouteButton(OpticalRoute route, RouteDecision decision) {
        Button button = routeButtons.get(route);
        if (button == null) {
            return;
        }
        if (decision.support().isAvailable()) {
            button.setText(route.label() + "\nOptical");
            button.setAlpha(1f);
        } else {
            button.setText(route.label() + "\nUnavailable");
            button.setAlpha(0.62f);
        }
        // Keep unavailable routes clickable so the exact reason remains visible.
        button.setEnabled(true);
    }

    private void updateRouteSelection(OpticalRoute selected) {
        for (Map.Entry<OpticalRoute, Button> entry : routeButtons.entrySet()) {
            boolean active = entry.getKey().equals(selected);
            entry.getValue().setBackgroundTintList(
                    android.content.res.ColorStateList.valueOf(
                            active ? 0xFF5B5B5B : 0xFF323232
                    )
            );
        }
    }

    private void updateProfileSelection(CaptureProfile selected) {
        for (Map.Entry<CaptureProfile, Button> entry : profileButtons.entrySet()) {
            boolean active = entry.getKey() == selected;
            entry.getValue().setBackgroundTintList(
                    android.content.res.ColorStateList.valueOf(
                            active ? 0xFF5B5B5B : 0xFF323232
                    )
            );
        }
    }

    private void openLatestPhoto() {
        if (latestUri == null) {
            return;
        }
        Intent intent = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(latestUri, "image/jpeg")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivity(intent);
        } catch (RuntimeException error) {
            onError("No system image viewer accepted the latest photo.", error);
        }
    }

    private void showStatus(String message) {
        statusView.setText(message);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
