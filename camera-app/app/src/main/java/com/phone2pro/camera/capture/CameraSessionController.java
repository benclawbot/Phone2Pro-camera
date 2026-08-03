package com.phone2pro.camera.capture;

import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import androidx.annotation.NonNull;
import androidx.annotation.OptIn;
import androidx.camera.camera2.interop.Camera2CameraInfo;
import androidx.camera.camera2.interop.ExperimentalCamera2Interop;
import androidx.camera.core.CameraFilter;
import androidx.camera.core.CameraInfo;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.LifecycleOwner;

import com.google.common.util.concurrent.ListenableFuture;
import com.phone2pro.camera.backend.GalagaSystemCameraBackend;
import com.phone2pro.camera.backend.PublicMainBackend;
import com.phone2pro.camera.backend.UnverifiedSystemEndpointAccess;
import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.core.RouteBackend;
import com.phone2pro.camera.core.RouteDecision;
import com.phone2pro.camera.core.RouteNegotiator;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * CameraX lifecycle/session bootstrap for the currently verified ordinary-app backend.
 *
 * <p>Auxiliary route buttons are negotiated through the same abstraction but remain unavailable
 * until a verified backend is added. The controller never substitutes zoom crop for an optical
 * route.</p>
 */
@OptIn(markerClass = ExperimentalCamera2Interop.class)
public final class CameraSessionController {
    public interface Listener {
        void onCapabilitiesReady(
                DeviceCapabilitySnapshot capabilities,
                RouteDecision ultrawide,
                RouteDecision main,
                RouteDecision telephoto
        );

        void onSessionReady(OpticalRoute route, RouteDecision decision, CaptureProfile profile);

        void onRouteUnavailable(OpticalRoute route, RouteDecision decision);

        void onCaptureSaved(@NonNull Uri uri);

        void onError(@NonNull String message, Throwable error);
    }

    private final Context context;
    private final LifecycleOwner lifecycleOwner;
    private final Preview.SurfaceProvider surfaceProvider;
    private final Listener listener;
    private final Executor mainExecutor;
    private final ExecutorService cameraExecutor = Executors.newSingleThreadExecutor();
    private final RouteNegotiator routeNegotiator;

    private ProcessCameraProvider cameraProvider;
    private DeviceCapabilitySnapshot capabilities;
    private ImageCapture imageCapture;
    private OpticalRoute selectedRoute = OpticalRoute.MAIN;
    private CaptureProfile captureProfile = CaptureProfile.AUTO;

    public CameraSessionController(
            Context context,
            LifecycleOwner lifecycleOwner,
            Preview.SurfaceProvider surfaceProvider,
            Listener listener
    ) {
        this.context = context.getApplicationContext();
        this.lifecycleOwner = lifecycleOwner;
        this.surfaceProvider = surfaceProvider;
        this.listener = listener;
        this.mainExecutor = ContextCompat.getMainExecutor(context);

        List<RouteBackend> backends = new ArrayList<>();
        backends.add(new GalagaSystemCameraBackend(
                new UnverifiedSystemEndpointAccess(
                        "Static route recovery does not establish package authorization."
                )
        ));
        backends.add(new PublicMainBackend());
        this.routeNegotiator = new RouteNegotiator(backends);
    }

    public void start() {
        ListenableFuture<ProcessCameraProvider> future = ProcessCameraProvider.getInstance(context);
        future.addListener(() -> {
            try {
                cameraProvider = future.get();
                capabilities = buildCapabilitySnapshot(cameraProvider);
                listener.onCapabilitiesReady(
                        capabilities,
                        routeNegotiator.select(OpticalRoute.ULTRAWIDE, capabilities),
                        routeNegotiator.select(OpticalRoute.MAIN, capabilities),
                        routeNegotiator.select(OpticalRoute.TELEPHOTO, capabilities)
                );
                bindSelectedRoute();
            } catch (Exception error) {
                listener.onError("Unable to initialize CameraX.", error);
            }
        }, mainExecutor);
    }

    public void selectRoute(OpticalRoute route) {
        selectedRoute = route;
        if (cameraProvider != null && capabilities != null) {
            bindSelectedRoute();
        }
    }

    public void setCaptureProfile(CaptureProfile profile) {
        captureProfile = profile;
        if (cameraProvider != null && capabilities != null) {
            bindSelectedRoute();
        }
    }

    public OpticalRoute selectedRoute() {
        return selectedRoute;
    }

    public CaptureProfile captureProfile() {
        return captureProfile;
    }

    public void takePhoto() {
        ImageCapture capture = imageCapture;
        if (capture == null) {
            listener.onError("Capture is unavailable until a camera session is ready.", null);
            return;
        }

        String stamp = new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
                .format(new Date());
        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, "P2P_" + stamp);
        values.put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg");
        values.put(
                MediaStore.MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_PICTURES + "/Phone2Pro"
        );

        ImageCapture.OutputFileOptions options = new ImageCapture.OutputFileOptions.Builder(
                context.getContentResolver(),
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                values
        ).build();

        capture.takePicture(options, mainExecutor, new ImageCapture.OnImageSavedCallback() {
            @Override
            public void onImageSaved(@NonNull ImageCapture.OutputFileResults output) {
                Uri uri = output.getSavedUri();
                if (uri == null) {
                    listener.onError("The image was saved but MediaStore returned no URI.", null);
                    return;
                }
                listener.onCaptureSaved(uri);
            }

            @Override
            public void onError(@NonNull ImageCaptureException error) {
                listener.onError("Photo capture failed: " + error.getMessage(), error);
            }
        });
    }

    public void shutdown() {
        cameraExecutor.shutdown();
    }

    private void bindSelectedRoute() {
        RouteDecision decision = routeNegotiator.select(selectedRoute, capabilities);
        if (!decision.support().isAvailable()) {
            imageCapture = null;
            cameraProvider.unbindAll();
            listener.onRouteUnavailable(selectedRoute, decision);
            return;
        }
        if (!PublicMainBackend.BACKEND_ID.equals(decision.backendId())) {
            listener.onError("No session binder is installed for " + decision.backendId() + ".", null);
            return;
        }

        try {
            Preview preview = new Preview.Builder().build();
            preview.setSurfaceProvider(surfaceProvider);

            imageCapture = new ImageCapture.Builder()
                    .setCaptureMode(captureProfile.imageCaptureMode())
                    .setJpegQuality(captureProfile == CaptureProfile.QUICK ? 92 : 96)
                    .build();

            ResolvedCameraEndpoint endpoint = decision.endpoint().orElseThrow(
                    () -> new IllegalStateException(
                            "Backend " + decision.backendId() + " did not resolve a Camera2 endpoint."
                    )
            );
            CameraSelector selector = selectorForCameraId(endpoint.cameraId());
            cameraProvider.unbindAll();
            cameraProvider.bindToLifecycle(lifecycleOwner, selector, preview, imageCapture);
            listener.onSessionReady(selectedRoute, decision, captureProfile);
        } catch (RuntimeException error) {
            imageCapture = null;
            listener.onError("Unable to bind the selected camera route.", error);
        }
    }

    private DeviceCapabilitySnapshot buildCapabilitySnapshot(ProcessCameraProvider provider) {
        Set<String> publicIds = new LinkedHashSet<>();
        for (CameraInfo cameraInfo : provider.getAvailableCameraInfos()) {
            try {
                publicIds.add(Camera2CameraInfo.from(cameraInfo).getCameraId());
            } catch (RuntimeException ignored) {
                // An inaccessible ID is not promoted into the public capability snapshot.
            }
        }
        return new DeviceCapabilitySnapshot(
                Build.MANUFACTURER == null ? "" : Build.MANUFACTURER,
                Build.MODEL == null ? "" : Build.MODEL,
                Build.DEVICE == null ? "" : Build.DEVICE,
                publicIds
        );
    }

    private CameraSelector selectorForCameraId(String cameraId) {
        CameraFilter filter = cameraInfos -> {
            List<CameraInfo> matches = new ArrayList<>();
            for (CameraInfo cameraInfo : cameraInfos) {
                try {
                    if (cameraId.equals(Camera2CameraInfo.from(cameraInfo).getCameraId())) {
                        matches.add(cameraInfo);
                    }
                } catch (RuntimeException ignored) {
                    // Ignore CameraInfo entries that cannot be bridged to Camera2.
                }
            }
            return matches;
        };
        return new CameraSelector.Builder().addCameraFilter(filter).build();
    }
}
