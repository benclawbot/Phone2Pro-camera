package com.phone2pro.diagnostics;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.OutputConfiguration;
import android.hardware.camera2.params.SessionConfiguration;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
import android.util.Size;
import android.view.Surface;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

final class SessionMatrixDiagnostics implements AutoCloseable {
    private static final long TIMEOUT_SECONDS = 8;
    private static final long MAX_TEST_PIXELS = 5_000_000L;

    private final Context context;
    private final HandlerThread thread = new HandlerThread("SessionMatrixDiagnostics");
    private Handler handler;
    private Executor executor;

    SessionMatrixDiagnostics(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject run() throws Exception {
        thread.start();
        handler = new Handler(thread.getLooper());
        executor = command -> handler.post(command);

        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }

        JSONObject report = new JSONObject();
        JSONArray cameras = new JSONArray();
        for (String id : manager.getCameraIdList()) {
            cameras.put(runCamera(manager, id));
        }
        report.put("cameras", cameras);
        report.put("testPixelLimit", MAX_TEST_PIXELS);
        report.put("completedAtElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        return report;
    }

    private JSONObject runCamera(CameraManager manager, String id) {
        JSONObject result = new JSONObject();
        CameraJson.put(result, "cameraId", id);
        CameraDevice device = null;
        try {
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            StreamConfigurationMap map = characteristics.get(
                    CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
            );
            if (map == null) {
                throw new IllegalStateException("No stream configuration map");
            }

            CameraJson.put(
                    result,
                    "availableSessionKeys",
                    keyNames(characteristics.getAvailableSessionKeys())
            );
            device = open(manager, id);
            JSONArray scenarios = new JSONArray();
            for (ScenarioSpec spec : buildScenarios(map)) {
                scenarios.put(testScenario(device, spec));
            }
            result.put("scenarios", scenarios);
        } catch (Throwable error) {
            CameraJson.put(result, "error", CameraJson.error(error));
        } finally {
            if (device != null) {
                device.close();
            }
        }
        return result;
    }

    private List<ScenarioSpec> buildScenarios(StreamConfigurationMap map) {
        Size jpeg = chooseSize(map.getOutputSizes(ImageFormat.JPEG));
        Size yuv = chooseSize(map.getOutputSizes(ImageFormat.YUV_420_888));
        Size raw = chooseSize(map.getOutputSizes(ImageFormat.RAW_SENSOR));
        List<ScenarioSpec> specs = new ArrayList<>();
        specs.add(new ScenarioSpec("private-preview", true, null, null, null));
        if (jpeg != null) {
            specs.add(new ScenarioSpec("jpeg", false, jpeg, null, null));
            specs.add(new ScenarioSpec("private+jpeg", true, jpeg, null, null));
        }
        if (yuv != null) {
            specs.add(new ScenarioSpec("yuv", false, null, yuv, null));
            specs.add(new ScenarioSpec("private+yuv", true, null, yuv, null));
        }
        if (raw != null) {
            specs.add(new ScenarioSpec("raw", false, null, null, raw));
            specs.add(new ScenarioSpec("private+raw", true, null, null, raw));
        }
        if (jpeg != null && yuv != null) {
            specs.add(new ScenarioSpec("jpeg+yuv", false, jpeg, yuv, null));
            specs.add(new ScenarioSpec("private+jpeg+yuv", true, jpeg, yuv, null));
        }
        if (jpeg != null && raw != null) {
            specs.add(new ScenarioSpec("jpeg+raw", false, jpeg, null, raw));
            specs.add(new ScenarioSpec("private+jpeg+raw", true, jpeg, null, raw));
        }
        return specs;
    }

    private JSONObject testScenario(CameraDevice device, ScenarioSpec spec) {
        JSONObject result = new JSONObject();
        CameraJson.put(result, "name", spec.name);
        CameraJson.put(result, "streams", spec.describe());
        long start = SystemClock.elapsedRealtime();

        List<AutoCloseable> resources = new ArrayList<>();
        List<Surface> surfaces = new ArrayList<>();
        CameraCaptureSession configured = null;
        try {
            if (spec.preview) {
                SurfaceTexture texture = new SurfaceTexture(0);
                texture.setDefaultBufferSize(1280, 720);
                Surface surface = new Surface(texture);
                surfaces.add(surface);
                resources.add(surface::release);
                resources.add(texture::release);
            }
            if (spec.jpeg != null) {
                ImageReader reader = ImageReader.newInstance(
                        spec.jpeg.getWidth(), spec.jpeg.getHeight(), ImageFormat.JPEG, 2
                );
                surfaces.add(reader.getSurface());
                resources.add(reader);
            }
            if (spec.yuv != null) {
                ImageReader reader = ImageReader.newInstance(
                        spec.yuv.getWidth(), spec.yuv.getHeight(), ImageFormat.YUV_420_888, 2
                );
                surfaces.add(reader.getSurface());
                resources.add(reader);
            }
            if (spec.raw != null) {
                ImageReader reader = ImageReader.newInstance(
                        spec.raw.getWidth(), spec.raw.getHeight(), ImageFormat.RAW_SENSOR, 2
                );
                surfaces.add(reader.getSurface());
                resources.add(reader);
            }
            if (surfaces.isEmpty()) {
                throw new IllegalStateException("Scenario has no outputs");
            }

            List<OutputConfiguration> outputs = new ArrayList<>();
            for (Surface surface : surfaces) {
                outputs.add(new OutputConfiguration(surface));
            }
            SessionConfiguration proposed = new SessionConfiguration(
                    SessionConfiguration.SESSION_REGULAR,
                    outputs,
                    executor,
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            // Only used for isSessionConfigurationSupported().
                        }

                        @Override
                        public void onConfigureFailed(CameraCaptureSession session) {
                            // Only used for isSessionConfigurationSupported().
                        }
                    }
            );
            try {
                CameraJson.put(
                        result,
                        "isSessionConfigurationSupported",
                        device.isSessionConfigurationSupported(proposed)
                );
            } catch (Throwable error) {
                CameraJson.put(result, "supportQueryError", CameraJson.error(error));
            }

            CountDownLatch latch = new CountDownLatch(1);
            AtomicReference<CameraCaptureSession> sessionRef = new AtomicReference<>();
            AtomicReference<Throwable> failure = new AtomicReference<>();
            device.createCaptureSession(
                    surfaces,
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            sessionRef.set(session);
                            latch.countDown();
                        }

                        @Override
                        public void onConfigureFailed(CameraCaptureSession session) {
                            failure.set(new IllegalStateException("onConfigureFailed"));
                            latch.countDown();
                        }
                    },
                    handler
            );

            boolean completed = latch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
            configured = sessionRef.get();
            CameraJson.put(result, "completed", completed);
            CameraJson.put(result, "configured", configured != null);
            if (failure.get() != null) {
                CameraJson.put(result, "configurationError", CameraJson.error(failure.get()));
            }
        } catch (Throwable error) {
            CameraJson.put(result, "completed", true);
            CameraJson.put(result, "configured", false);
            CameraJson.put(result, "error", CameraJson.error(error));
        } finally {
            if (configured != null) {
                configured.close();
            }
            for (int index = resources.size() - 1; index >= 0; index--) {
                try {
                    resources.get(index).close();
                } catch (Exception ignored) {
                    // Continue releasing the remaining outputs.
                }
            }
            SystemClock.sleep(100);
        }
        CameraJson.put(result, "durationMillis", SystemClock.elapsedRealtime() - start);
        return result;
    }

    @SuppressLint("MissingPermission")
    private CameraDevice open(CameraManager manager, String id) throws Exception {
        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<CameraDevice> device = new AtomicReference<>();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        manager.openCamera(id, new CameraDevice.StateCallback() {
            @Override
            public void onOpened(CameraDevice camera) {
                device.set(camera);
                latch.countDown();
            }

            @Override
            public void onDisconnected(CameraDevice camera) {
                camera.close();
                failure.set(new IllegalStateException("camera disconnected"));
                latch.countDown();
            }

            @Override
            public void onError(CameraDevice camera, int error) {
                camera.close();
                failure.set(new IllegalStateException("camera open error " + error));
                latch.countDown();
            }
        }, handler);
        if (!latch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out opening camera " + id);
        }
        if (failure.get() != null) {
            throw new IllegalStateException("Unable to open camera " + id, failure.get());
        }
        if (device.get() == null) {
            throw new IllegalStateException("Camera " + id + " returned no device");
        }
        return device.get();
    }

    private static JSONArray keyNames(List<android.hardware.camera2.CaptureRequest.Key<?>> keys) {
        JSONArray result = new JSONArray();
        if (keys == null) {
            return result;
        }
        for (android.hardware.camera2.CaptureRequest.Key<?> key : keys) {
            result.put(key.getName());
        }
        return result;
    }

    private static Size chooseSize(Size[] sizes) {
        if (sizes == null || sizes.length == 0) {
            return null;
        }
        return Arrays.stream(sizes)
                .filter(size -> (long) size.getWidth() * size.getHeight() <= MAX_TEST_PIXELS)
                .max((left, right) -> Long.compare(
                        (long) left.getWidth() * left.getHeight(),
                        (long) right.getWidth() * right.getHeight()
                ))
                .orElse(sizes[sizes.length - 1]);
    }

    @Override
    public void close() {
        if (thread.isAlive()) {
            thread.quitSafely();
        }
    }

    private static final class ScenarioSpec {
        final String name;
        final boolean preview;
        final Size jpeg;
        final Size yuv;
        final Size raw;

        ScenarioSpec(String name, boolean preview, Size jpeg, Size yuv, Size raw) {
            this.name = name;
            this.preview = preview;
            this.jpeg = jpeg;
            this.yuv = yuv;
            this.raw = raw;
        }

        JSONArray describe() {
            JSONArray result = new JSONArray();
            if (preview) {
                result.put(CameraJson.object(
                        "format", "PRIVATE",
                        "size", CameraJson.object("width", 1280, "height", 720)
                ));
            }
            if (jpeg != null) {
                result.put(CameraJson.object("format", "JPEG", "size", CameraJson.value(jpeg)));
            }
            if (yuv != null) {
                result.put(CameraJson.object("format", "YUV_420_888", "size", CameraJson.value(yuv)));
            }
            if (raw != null) {
                result.put(CameraJson.object("format", "RAW_SENSOR", "size", CameraJson.value(raw)));
            }
            return result;
        }
    }
}
