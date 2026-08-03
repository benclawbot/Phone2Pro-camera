package com.phone2pro.diagnostics;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureFailure;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
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
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class CaptureTraceDiagnostics implements AutoCloseable {
    private static final int BURST_COUNT = 8;
    private static final long TIMEOUT_SECONDS = 15;
    private static final long MAX_PIXELS = 3_200_000L;

    private final Context context;
    private final HandlerThread thread = new HandlerThread("CaptureTraceDiagnostics");
    private Handler handler;
    private CameraDevice device;
    private CameraCaptureSession session;
    private SurfaceTexture previewTexture;
    private Surface previewSurface;
    private ImageReader yuvReader;

    CaptureTraceDiagnostics(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject run() throws Exception {
        thread.start();
        handler = new Handler(thread.getLooper());

        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }
        String cameraId = findRear(manager);
        CameraCharacteristics characteristics = manager.getCameraCharacteristics(cameraId);
        Size yuvSize = chooseYuvSize(characteristics);

        JSONObject report = new JSONObject();
        report.put("cameraId", cameraId);
        report.put("format", "YUV_420_888");
        report.put("size", CameraJson.value(yuvSize));
        report.put("burstFrameCount", BURST_COUNT);

        device = open(manager, cameraId);
        configure(yuvSize);
        CaptureRequest preview = startPreview();
        report.put("previewRequest", requestJson(preview));
        SystemClock.sleep(700);
        report.put("singleCapture", runSingleCapture());
        report.put("burst", runBurst());
        report.put("completedAtElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        return report;
    }

    private JSONObject runSingleCapture() throws Exception {
        CountDownLatch resultLatch = new CountDownLatch(1);
        CountDownLatch imageLatch = new CountDownLatch(1);
        AtomicReference<TotalCaptureResult> resultRef = new AtomicReference<>();
        AtomicReference<CaptureFailure> failureRef = new AtomicReference<>();
        AtomicReference<Long> imageTimestamp = new AtomicReference<>();
        long start = SystemClock.elapsedRealtime();

        yuvReader.setOnImageAvailableListener(reader -> {
            try (Image image = reader.acquireNextImage()) {
                if (image != null) {
                    imageTimestamp.set(image.getTimestamp());
                }
            } finally {
                imageLatch.countDown();
            }
        }, handler);

        CaptureRequest request = stillRequest();
        int sequenceId = session.capture(request, new CameraCaptureSession.CaptureCallback() {
            @Override
            public void onCaptureCompleted(
                    CameraCaptureSession captureSession,
                    CaptureRequest captureRequest,
                    TotalCaptureResult result
            ) {
                resultRef.set(result);
                resultLatch.countDown();
            }

            @Override
            public void onCaptureFailed(
                    CameraCaptureSession captureSession,
                    CaptureRequest captureRequest,
                    CaptureFailure failure
            ) {
                failureRef.set(failure);
                resultLatch.countDown();
            }
        }, handler);

        boolean resultReceived = resultLatch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        boolean imageReceived = imageLatch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        JSONObject output = new JSONObject();
        output.put("sequenceId", sequenceId);
        output.put("resultReceived", resultReceived);
        output.put("imageReceived", imageReceived);
        output.put("durationMillis", SystemClock.elapsedRealtime() - start);
        output.put("request", requestJson(request));
        if (resultRef.get() != null) {
            output.put("result", resultJson(resultRef.get()));
        }
        if (imageTimestamp.get() != null) {
            output.put("imageTimestampNs", imageTimestamp.get());
        }
        if (failureRef.get() != null) {
            output.put("failure", failureJson(failureRef.get()));
        }
        return output;
    }

    private JSONObject runBurst() throws Exception {
        CountDownLatch resultLatch = new CountDownLatch(BURST_COUNT);
        CountDownLatch imageLatch = new CountDownLatch(BURST_COUNT);
        JSONArray results = new JSONArray();
        JSONArray failures = new JSONArray();
        JSONArray imageTimestamps = new JSONArray();
        AtomicInteger imageCount = new AtomicInteger();
        long start = SystemClock.elapsedRealtime();

        yuvReader.setOnImageAvailableListener(reader -> {
            Image image = null;
            try {
                image = reader.acquireNextImage();
                if (image != null) {
                    synchronized (imageTimestamps) {
                        imageTimestamps.put(image.getTimestamp());
                    }
                    imageCount.incrementAndGet();
                }
            } finally {
                if (image != null) {
                    image.close();
                }
                imageLatch.countDown();
            }
        }, handler);

        List<CaptureRequest> requests = new ArrayList<>();
        for (int index = 0; index < BURST_COUNT; index++) {
            requests.add(stillRequest());
        }

        int sequenceId = session.captureBurst(
                requests,
                new CameraCaptureSession.CaptureCallback() {
                    @Override
                    public void onCaptureCompleted(
                            CameraCaptureSession captureSession,
                            CaptureRequest request,
                            TotalCaptureResult result
                    ) {
                        JSONObject entry = new JSONObject();
                        CameraJson.put(entry, "frameNumber", result.getFrameNumber());
                        CameraJson.put(entry, "sequenceId", result.getSequenceId());
                        CameraJson.put(entry, "sensorTimestampNs", CameraJson.value(
                                result.get(CaptureResult.SENSOR_TIMESTAMP)
                        ));
                        CameraJson.put(entry, "exposureTimeNs", CameraJson.value(
                                result.get(CaptureResult.SENSOR_EXPOSURE_TIME)
                        ));
                        CameraJson.put(entry, "sensitivityIso", CameraJson.value(
                                result.get(CaptureResult.SENSOR_SENSITIVITY)
                        ));
                        synchronized (results) {
                            results.put(entry);
                        }
                        resultLatch.countDown();
                    }

                    @Override
                    public void onCaptureFailed(
                            CameraCaptureSession captureSession,
                            CaptureRequest request,
                            CaptureFailure failure
                    ) {
                        synchronized (failures) {
                            failures.put(failureJson(failure));
                        }
                        resultLatch.countDown();
                    }
                },
                handler
        );

        boolean allResults = resultLatch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        boolean allImages = imageLatch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        long duration = SystemClock.elapsedRealtime() - start;
        JSONObject output = new JSONObject();
        output.put("sequenceId", sequenceId);
        output.put("requestedFrameCount", BURST_COUNT);
        output.put("resultCount", results.length());
        output.put("imageCount", imageCount.get());
        output.put("allResultsReceived", allResults);
        output.put("allImagesReceived", allImages);
        output.put("durationMillis", duration);
        output.put("effectiveFramesPerSecond",
                duration > 0 ? results.length() * 1000.0 / duration : JSONObject.NULL);
        output.put("results", results);
        output.put("imageTimestampsNs", imageTimestamps);
        output.put("failures", failures);
        return output;
    }

    private CaptureRequest startPreview() throws Exception {
        CaptureRequest.Builder builder = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
        builder.addTarget(previewSurface);
        automatic(builder);
        CaptureRequest request = builder.build();
        session.setRepeatingRequest(request, null, handler);
        return request;
    }

    private CaptureRequest stillRequest() throws Exception {
        CaptureRequest.Builder builder = device.createCaptureRequest(
                CameraDevice.TEMPLATE_STILL_CAPTURE
        );
        builder.addTarget(yuvReader.getSurface());
        automatic(builder);
        return builder.build();
    }

    private static void automatic(CaptureRequest.Builder builder) {
        builder.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
        builder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON);
        builder.set(CaptureRequest.CONTROL_AWB_MODE, CaptureRequest.CONTROL_AWB_MODE_AUTO);
        builder.set(
                CaptureRequest.CONTROL_AF_MODE,
                CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE
        );
    }

    private JSONObject requestJson(CaptureRequest request) {
        JSONObject output = new JSONObject();
        JSONArray keys = new JSONArray();
        for (CaptureRequest.Key<?> key : request.getKeys()) {
            JSONObject entry = new JSONObject();
            CameraJson.put(entry, "name", key.getName());
            CameraJson.put(entry, "vendor", !key.getName().startsWith("android."));
            try {
                Object value = readRequest(request, key);
                CameraJson.put(entry, "value", CameraJson.value(value));
                CameraJson.put(entry, "javaValueClass",
                        value == null ? JSONObject.NULL : value.getClass().getName());
            } catch (Throwable error) {
                CameraJson.put(entry, "readError", CameraJson.error(error));
            }
            keys.put(entry);
        }
        CameraJson.put(output, "keyCount", keys.length());
        CameraJson.put(output, "keys", keys);
        return output;
    }

    private JSONObject resultJson(TotalCaptureResult result) {
        JSONObject output = new JSONObject();
        CameraJson.put(output, "frameNumber", result.getFrameNumber());
        CameraJson.put(output, "sequenceId", result.getSequenceId());
        JSONArray keys = new JSONArray();
        for (CaptureResult.Key<?> key : result.getKeys()) {
            JSONObject entry = new JSONObject();
            CameraJson.put(entry, "name", key.getName());
            CameraJson.put(entry, "vendor", !key.getName().startsWith("android."));
            try {
                Object value = readResult(result, key);
                CameraJson.put(entry, "value", CameraJson.value(value));
                CameraJson.put(entry, "javaValueClass",
                        value == null ? JSONObject.NULL : value.getClass().getName());
            } catch (Throwable error) {
                CameraJson.put(entry, "readError", CameraJson.error(error));
            }
            keys.put(entry);
        }
        CameraJson.put(output, "keyCount", keys.length());
        CameraJson.put(output, "keys", keys);
        return output;
    }

    private static JSONObject failureJson(CaptureFailure failure) {
        return CameraJson.object(
                "reason", failure.getReason(),
                "sequenceId", failure.getSequenceId(),
                "frameNumber", failure.getFrameNumber(),
                "imageCaptured", failure.wasImageCaptured()
        );
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readRequest(CaptureRequest request, CaptureRequest.Key<?> key) {
        return request.get((CaptureRequest.Key) key);
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readResult(CaptureResult result, CaptureResult.Key<?> key) {
        return result.get((CaptureResult.Key) key);
    }

    private void configure(Size yuvSize) throws Exception {
        previewTexture = new SurfaceTexture(0);
        previewTexture.setDefaultBufferSize(1280, 720);
        previewSurface = new Surface(previewTexture);
        yuvReader = ImageReader.newInstance(
                yuvSize.getWidth(), yuvSize.getHeight(), ImageFormat.YUV_420_888, 12
        );

        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<CameraCaptureSession> sessionRef = new AtomicReference<>();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        device.createCaptureSession(
                Arrays.asList(previewSurface, yuvReader.getSurface()),
                new CameraCaptureSession.StateCallback() {
                    @Override
                    public void onConfigured(CameraCaptureSession configured) {
                        sessionRef.set(configured);
                        latch.countDown();
                    }

                    @Override
                    public void onConfigureFailed(CameraCaptureSession configured) {
                        failure.set(new IllegalStateException("onConfigureFailed"));
                        latch.countDown();
                    }
                },
                handler
        );
        if (!latch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out configuring trace session");
        }
        if (failure.get() != null) {
            throw new IllegalStateException("Trace session failed", failure.get());
        }
        session = sessionRef.get();
        if (session == null) {
            throw new IllegalStateException("Trace session returned no session");
        }
    }

    @SuppressLint("MissingPermission")
    private CameraDevice open(CameraManager manager, String id) throws Exception {
        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<CameraDevice> deviceRef = new AtomicReference<>();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        manager.openCamera(id, new CameraDevice.StateCallback() {
            @Override
            public void onOpened(CameraDevice camera) {
                deviceRef.set(camera);
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
        if (deviceRef.get() == null) {
            throw new IllegalStateException("Camera " + id + " returned no device");
        }
        return deviceRef.get();
    }

    private static String findRear(CameraManager manager) throws Exception {
        for (String id : manager.getCameraIdList()) {
            Integer facing = manager.getCameraCharacteristics(id)
                    .get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) {
                return id;
            }
        }
        throw new IllegalStateException("No public rear camera");
    }

    private static Size chooseYuvSize(CameraCharacteristics characteristics) {
        StreamConfigurationMap map = characteristics.get(
                CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
        );
        if (map == null || map.getOutputSizes(ImageFormat.YUV_420_888) == null) {
            return new Size(1920, 1080);
        }
        Size[] sizes = map.getOutputSizes(ImageFormat.YUV_420_888);
        return Arrays.stream(sizes)
                .filter(size -> (long) size.getWidth() * size.getHeight() <= MAX_PIXELS)
                .max((left, right) -> Long.compare(
                        (long) left.getWidth() * left.getHeight(),
                        (long) right.getWidth() * right.getHeight()
                ))
                .orElse(sizes[sizes.length - 1]);
    }

    @Override
    public void close() {
        if (session != null) {
            session.close();
        }
        if (device != null) {
            device.close();
        }
        if (yuvReader != null) {
            yuvReader.close();
        }
        if (previewSurface != null) {
            previewSurface.release();
        }
        if (previewTexture != null) {
            previewTexture.release();
        }
        if (thread.isAlive()) {
            thread.quitSafely();
        }
    }
}
