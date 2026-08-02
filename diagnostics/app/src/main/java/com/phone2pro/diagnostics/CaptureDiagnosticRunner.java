package com.phone2pro.diagnostics;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureFailure;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Range;
import android.util.Size;
import android.util.SizeF;
import android.view.Surface;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.lang.reflect.Array;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class CaptureDiagnosticRunner implements AutoCloseable {
    private static final float[] NIGHT_ZOOM_REQUESTS =
            {0.6f, 1.0f, 2.0f, 4.0f, 10.0f, 20.0f};
    private static final float[] DAYLIGHT_ZOOM_REQUESTS =
            {0.6f, 1.0f, 1.5f, 1.8f, 1.9f, 2.0f, 2.1f, 2.2f, 2.5f, 3.0f, 4.0f, 10.0f, 20.0f};
    private static final String MTK_EFFECTIVE_CROP =
            "com.mediatek.control.capture.scalerCropRegion";
    private static final String NOTHING_INSENSOR_ZOOM =
            "com.nothing.camera.insensorzoom.enable";
    private static final String NOTHING_REMOSAIC =
            "com.nothing.camera.remosaic.status";
    private static final Set<String> IMPORTANT_RESULT_KEYS = new HashSet<>(Arrays.asList(
            "android.logicalMultiCamera.activePhysicalId",
            "android.lens.focalLength",
            "android.lens.aperture",
            "android.lens.opticalStabilizationMode",
            "android.control.zoomRatio",
            "android.scaler.cropRegion",
            "android.sensor.exposureTime",
            "android.sensor.sensitivity",
            "android.sensor.timestamp",
            "android.sensor.rollingShutterSkew",
            "android.control.aeState",
            "android.control.afState",
            "android.control.awbState"
    ));

    private final Context context;
    private final DiagnosticProfile profile;
    private final HandlerThread cameraThread =
            new HandlerThread("Phone2ProDiagnosticsCamera");

    private Handler cameraHandler;
    private CameraDevice cameraDevice;
    private CameraCaptureSession session;
    private ImageReader jpegReader;
    private SurfaceTexture previewTexture;
    private Surface previewSurface;
    private CameraCharacteristics characteristics;
    private String cameraId;
    private Size captureSize;

    CaptureDiagnosticRunner(Context context, DiagnosticProfile profile) {
        this.context = context.getApplicationContext();
        this.profile = profile;
    }

    JSONObject run() throws Exception {
        JSONObject report = new JSONObject();
        report.put("profile", profile.fileLabel);
        report.put("startedAtElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        report.put("thermalStatusBefore", thermalStatus());

        cameraThread.start();
        cameraHandler = new Handler(cameraThread.getLooper());

        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }

        if (profile == DiagnosticProfile.DAYLIGHT_LENS_ROUTING) {
            report.put("systemOnlyCameraOpenProbe", probeSystemOnlyCameraOpen(manager));
        }

        cameraId = findRearCamera(manager);
        characteristics = manager.getCameraCharacteristics(cameraId);
        report.put("cameraId", cameraId);
        report.put("advertisedZoomRange", jsonValue(
                characteristics.get(CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE)
        ));
        report.put("activeArray", jsonValue(
                characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)
        ));

        openCamera(manager);
        configureSession();
        report.put("captureJpegSize", captureSize.toString());

        JSONArray samples = new JSONArray();
        for (float zoom : zoomRequests()) {
            samples.put(captureZoomSample(zoom));
        }
        report.put("zoomSamples", samples);

        JSONObject burstAt1x = runBurst(8, 1.0f);
        report.put("eightFrameBurst", burstAt1x);
        report.put("eightFrameBurstAt1x", burstAt1x);
        if (profile == DiagnosticProfile.DAYLIGHT_LENS_ROUTING) {
            report.put("eightFrameBurstAt2x", runBurst(8, 2.0f));
        }

        report.put("thermalStatusAfter", thermalStatus());
        report.put("finishedAtElapsedRealtimeMillis", SystemClock.elapsedRealtime());
        return report;
    }

    private float[] zoomRequests() {
        return profile == DiagnosticProfile.DAYLIGHT_LENS_ROUTING
                ? DAYLIGHT_ZOOM_REQUESTS
                : NIGHT_ZOOM_REQUESTS;
    }

    private String findRearCamera(CameraManager manager) throws CameraAccessException {
        for (String id : manager.getCameraIdList()) {
            Integer facing = manager.getCameraCharacteristics(id)
                    .get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) {
                return id;
            }
        }
        throw new IllegalStateException("No public rear camera is available");
    }

    @SuppressLint("MissingPermission")
    private JSONArray probeSystemOnlyCameraOpen(CameraManager manager) throws JSONException {
        JSONArray probes = new JSONArray();
        for (int numericId = 2; numericId <= 5; numericId++) {
            String candidate = String.valueOf(numericId);
            JSONObject probe = new JSONObject();
            probe.put("id", candidate);
            CountDownLatch latch = new CountDownLatch(1);
            AtomicReference<String> outcome = new AtomicReference<>("timeout");
            AtomicReference<Integer> callbackError = new AtomicReference<>();

            try {
                manager.openCamera(candidate, new CameraDevice.StateCallback() {
                    @Override
                    public void onOpened(CameraDevice camera) {
                        outcome.set("opened");
                        camera.close();
                        latch.countDown();
                    }

                    @Override
                    public void onDisconnected(CameraDevice camera) {
                        outcome.set("disconnected");
                        camera.close();
                        latch.countDown();
                    }

                    @Override
                    public void onError(CameraDevice camera, int error) {
                        callbackError.set(error);
                        outcome.set("callback-error");
                        camera.close();
                        latch.countDown();
                    }
                }, cameraHandler);

                boolean completed = latch.await(3, TimeUnit.SECONDS);
                probe.put("completed", completed);
                probe.put("outcome", outcome.get());
                if (callbackError.get() != null) {
                    probe.put("callbackErrorCode", callbackError.get());
                    probe.put("callbackErrorName", cameraErrorName(callbackError.get()));
                }
            } catch (Exception error) {
                probe.put("completed", true);
                probe.put("outcome", "exception");
                probe.put("errorType", error.getClass().getName());
                probe.put("message", String.valueOf(error.getMessage()));
                if (error instanceof CameraAccessException) {
                    probe.put("cameraAccessReason",
                            ((CameraAccessException) error).getReason());
                }
            }
            probes.put(probe);
            SystemClock.sleep(150);
        }
        return probes;
    }

    private static String cameraErrorName(int error) {
        switch (error) {
            case CameraDevice.StateCallback.ERROR_CAMERA_IN_USE:
                return "ERROR_CAMERA_IN_USE";
            case CameraDevice.StateCallback.ERROR_MAX_CAMERAS_IN_USE:
                return "ERROR_MAX_CAMERAS_IN_USE";
            case CameraDevice.StateCallback.ERROR_CAMERA_DISABLED:
                return "ERROR_CAMERA_DISABLED";
            case CameraDevice.StateCallback.ERROR_CAMERA_DEVICE:
                return "ERROR_CAMERA_DEVICE";
            case CameraDevice.StateCallback.ERROR_CAMERA_SERVICE:
                return "ERROR_CAMERA_SERVICE";
            default:
                return "UNKNOWN_" + error;
        }
    }

    @SuppressLint("MissingPermission")
    private void openCamera(CameraManager manager) throws Exception {
        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<Exception> failure = new AtomicReference<>();
        manager.openCamera(cameraId, new CameraDevice.StateCallback() {
            @Override
            public void onOpened(CameraDevice camera) {
                cameraDevice = camera;
                latch.countDown();
            }

            @Override
            public void onDisconnected(CameraDevice camera) {
                camera.close();
                failure.set(new IllegalStateException("Rear camera disconnected"));
                latch.countDown();
            }

            @Override
            public void onError(CameraDevice camera, int error) {
                camera.close();
                failure.set(new IllegalStateException(
                        "Rear camera open error " + cameraErrorName(error)
                ));
                latch.countDown();
            }
        }, cameraHandler);

        await(latch, 8, "opening rear camera");
        if (failure.get() != null) {
            throw failure.get();
        }
        if (cameraDevice == null) {
            throw new IllegalStateException("Rear camera did not open");
        }
    }

    private void configureSession() throws Exception {
        captureSize = chooseJpegSize(characteristics);
        jpegReader = ImageReader.newInstance(
                captureSize.getWidth(),
                captureSize.getHeight(),
                ImageFormat.JPEG,
                24
        );
        previewTexture = new SurfaceTexture(0);
        previewTexture.setDefaultBufferSize(1280, 720);
        previewSurface = new Surface(previewTexture);

        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<Exception> failure = new AtomicReference<>();
        cameraDevice.createCaptureSession(
                Arrays.asList(previewSurface, jpegReader.getSurface()),
                new CameraCaptureSession.StateCallback() {
                    @Override
                    public void onConfigured(CameraCaptureSession configured) {
                        session = configured;
                        latch.countDown();
                    }

                    @Override
                    public void onConfigureFailed(CameraCaptureSession configured) {
                        failure.set(new IllegalStateException(
                                "Capture session configuration failed"
                        ));
                        latch.countDown();
                    }
                },
                cameraHandler
        );
        await(latch, 8, "configuring capture session");
        if (failure.get() != null) {
            throw failure.get();
        }
    }

    private Size chooseJpegSize(CameraCharacteristics cameraCharacteristics) {
        android.hardware.camera2.params.StreamConfigurationMap map =
                cameraCharacteristics.get(
                        CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
                );
        if (map == null || map.getOutputSizes(ImageFormat.JPEG) == null) {
            return new Size(1920, 1440);
        }
        Size best = null;
        for (Size size : map.getOutputSizes(ImageFormat.JPEG)) {
            long pixels = (long) size.getWidth() * size.getHeight();
            if (pixels > 5_000_000L) {
                continue;
            }
            if (best == null
                    || pixels > (long) best.getWidth() * best.getHeight()) {
                best = size;
            }
        }
        return best != null ? best : map.getOutputSizes(ImageFormat.JPEG)[0];
    }

    private JSONObject captureZoomSample(float requestedZoom) throws Exception {
        JSONObject sample = new JSONObject();
        sample.put("requestedZoom", requestedZoom);
        long start = SystemClock.elapsedRealtime();

        try {
            CaptureRequest.Builder preview = cameraDevice.createCaptureRequest(
                    CameraDevice.TEMPLATE_PREVIEW
            );
            preview.addTarget(previewSurface);
            applyAutomaticControls(preview);
            preview.set(CaptureRequest.CONTROL_ZOOM_RATIO, requestedZoom);
            session.setRepeatingRequest(preview.build(), null, cameraHandler);
            Thread.sleep(profile.settleMillis);
        } catch (Exception error) {
            sample.put("requestAccepted", false);
            sample.put("error", error.toString());
            sample.put("durationMillis", SystemClock.elapsedRealtime() - start);
            return sample;
        }

        CountDownLatch imageLatch = new CountDownLatch(1);
        CountDownLatch resultLatch = new CountDownLatch(1);
        AtomicReference<byte[]> jpegBytes = new AtomicReference<>();
        AtomicReference<TotalCaptureResult> captureResult = new AtomicReference<>();
        AtomicReference<String> captureError = new AtomicReference<>();

        jpegReader.setOnImageAvailableListener(reader -> {
            try (Image image = reader.acquireNextImage()) {
                if (image == null) {
                    return;
                }
                ByteBuffer buffer = image.getPlanes()[0].getBuffer();
                byte[] bytes = new byte[buffer.remaining()];
                buffer.get(bytes);
                jpegBytes.set(bytes);
            } catch (Exception error) {
                captureError.set(error.toString());
            } finally {
                imageLatch.countDown();
            }
        }, cameraHandler);

        CaptureRequest.Builder still = cameraDevice.createCaptureRequest(
                CameraDevice.TEMPLATE_STILL_CAPTURE
        );
        still.addTarget(jpegReader.getSurface());
        applyAutomaticControls(still);
        still.set(CaptureRequest.CONTROL_ZOOM_RATIO, requestedZoom);
        still.set(CaptureRequest.JPEG_QUALITY, (byte) 95);
        enableOisIfAvailable(still);

        session.capture(still.build(), new CameraCaptureSession.CaptureCallback() {
            @Override
            public void onCaptureCompleted(
                    CameraCaptureSession captureSession,
                    CaptureRequest request,
                    TotalCaptureResult result
            ) {
                captureResult.set(result);
                resultLatch.countDown();
            }

            @Override
            public void onCaptureFailed(
                    CameraCaptureSession captureSession,
                    CaptureRequest request,
                    CaptureFailure failure
            ) {
                captureError.set("Capture failed: reason=" + failure.getReason());
                resultLatch.countDown();
            }
        }, cameraHandler);

        await(resultLatch, 15,
                "receiving capture metadata at " + requestedZoom + "x");
        await(imageLatch, 15, "receiving JPEG at " + requestedZoom + "x");

        sample.put("requestAccepted", captureError.get() == null);
        if (captureError.get() != null) {
            sample.put("error", captureError.get());
        }
        if (captureResult.get() != null) {
            sample.put("captureResult", captureResultJson(captureResult.get()));
            sample.put(
                    "derivedRoutingEvidence",
                    deriveRoutingEvidence(captureResult.get(), requestedZoom)
            );
        }
        if (jpegBytes.get() != null) {
            sample.put("jpegBytes", jpegBytes.get().length);
            sample.put(
                    "savedSample",
                    ReportStorage.saveJpegSample(
                            context,
                            profile.fileLabel,
                            requestedZoom,
                            jpegBytes.get()
                    ).toString()
            );
        }
        sample.put("durationMillis", SystemClock.elapsedRealtime() - start);
        return sample;
    }

    private JSONObject deriveRoutingEvidence(
            TotalCaptureResult result,
            float requestedZoom
    ) throws JSONException {
        JSONObject evidence = new JSONObject();
        evidence.put("requestedZoom", requestedZoom);

        Object standardZoom = resultValueByName(
                result,
                "android.control.zoomRatio"
        );
        Object activePhysicalId = resultValueByName(
                result,
                "android.logicalMultiCamera.activePhysicalId"
        );
        Object focalLength = resultValueByName(
                result,
                "android.lens.focalLength"
        );
        Object effectiveCrop = resultValueByName(result, MTK_EFFECTIVE_CROP);
        Object inSensorZoom = resultValueByName(result, NOTHING_INSENSOR_ZOOM);
        Object remosaic = resultValueByName(result, NOTHING_REMOSAIC);

        evidence.put("standardZoomEcho", jsonValue(standardZoom));
        evidence.put("activePhysicalId", jsonValue(activePhysicalId));
        evidence.put("focalLengthMm", jsonValue(focalLength));
        evidence.put("mediatekEffectiveCrop", jsonValue(effectiveCrop));
        evidence.put("nothingInSensorZoom", jsonValue(inSensorZoom));
        evidence.put("nothingRemosaic", jsonValue(remosaic));

        Double effectiveZoom = effectiveZoomFromCrop(effectiveCrop);
        if (effectiveZoom != null) {
            evidence.put("effectiveDigitalZoom", effectiveZoom);
            evidence.put(
                    "requestClampedOrIgnored",
                    Math.abs(effectiveZoom - requestedZoom) > 0.15
            );
        } else {
            evidence.put("effectiveDigitalZoom", JSONObject.NULL);
            evidence.put("requestClampedOrIgnored", JSONObject.NULL);
        }
        return evidence;
    }

    private Double effectiveZoomFromCrop(Object cropValue) {
        Rect active = characteristics.get(
                CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE
        );
        if (active == null || cropValue == null) {
            return null;
        }

        double cropWidth;
        if (cropValue instanceof Rect) {
            cropWidth = ((Rect) cropValue).width();
        } else if (cropValue.getClass().isArray()
                && Array.getLength(cropValue) >= 4) {
            Object widthValue = Array.get(cropValue, 2);
            if (!(widthValue instanceof Number)) {
                return null;
            }
            cropWidth = ((Number) widthValue).doubleValue();
        } else {
            return null;
        }

        if (cropWidth <= 0) {
            return null;
        }
        return active.width() / cropWidth;
    }

    private Object resultValueByName(
            TotalCaptureResult result,
            String targetName
    ) {
        for (CaptureResult.Key<?> key : result.getKeys()) {
            if (targetName.equals(key.getName())) {
                return readResult(result, key);
            }
        }
        return null;
    }

    private JSONObject runBurst(int frameCount, float zoom) throws Exception {
        JSONObject result = new JSONObject();
        result.put("requestedFrames", frameCount);
        result.put("requestedZoom", zoom);

        AtomicInteger receivedImages = new AtomicInteger();
        AtomicInteger completedResults = new AtomicInteger();
        CountDownLatch imageLatch = new CountDownLatch(frameCount);
        CountDownLatch resultLatch = new CountDownLatch(frameCount);
        JSONArray sensorTimestamps = new JSONArray();
        List<Long> timestampValues = new ArrayList<>();

        jpegReader.setOnImageAvailableListener(reader -> {
            try (Image image = reader.acquireNextImage()) {
                if (image != null) {
                    receivedImages.incrementAndGet();
                }
            } finally {
                imageLatch.countDown();
            }
        }, cameraHandler);

        List<CaptureRequest> requests = new ArrayList<>();
        for (int index = 0; index < frameCount; index++) {
            CaptureRequest.Builder request = cameraDevice.createCaptureRequest(
                    CameraDevice.TEMPLATE_STILL_CAPTURE
            );
            request.addTarget(jpegReader.getSurface());
            applyAutomaticControls(request);
            request.set(CaptureRequest.CONTROL_ZOOM_RATIO, zoom);
            request.set(CaptureRequest.JPEG_QUALITY, (byte) 90);
            enableOisIfAvailable(request);
            requests.add(request.build());
        }

        long start = SystemClock.elapsedRealtime();
        session.captureBurst(requests, new CameraCaptureSession.CaptureCallback() {
            @Override
            public void onCaptureCompleted(
                    CameraCaptureSession captureSession,
                    CaptureRequest request,
                    TotalCaptureResult captureResult
            ) {
                Long timestamp = captureResult.get(CaptureResult.SENSOR_TIMESTAMP);
                synchronized (sensorTimestamps) {
                    sensorTimestamps.put(
                            timestamp == null ? JSONObject.NULL : timestamp
                    );
                    if (timestamp != null) {
                        timestampValues.add(timestamp);
                    }
                }
                completedResults.incrementAndGet();
                resultLatch.countDown();
            }

            @Override
            public void onCaptureFailed(
                    CameraCaptureSession captureSession,
                    CaptureRequest request,
                    CaptureFailure failure
            ) {
                resultLatch.countDown();
            }
        }, cameraHandler);

        boolean resultsComplete = resultLatch.await(30, TimeUnit.SECONDS);
        boolean imagesComplete = imageLatch.await(30, TimeUnit.SECONDS);
        result.put("completedResults", completedResults.get());
        result.put("receivedImages", receivedImages.get());
        result.put("resultsComplete", resultsComplete);
        result.put("imagesComplete", imagesComplete);
        result.put("wallTimeMillis", SystemClock.elapsedRealtime() - start);
        result.put("sensorTimestampsNs", sensorTimestamps);
        addBurstTiming(result, timestampValues);
        return result;
    }

    private void addBurstTiming(JSONObject output, List<Long> timestamps)
            throws JSONException {
        JSONArray deltas = new JSONArray();
        if (timestamps.size() < 2) {
            output.put("interFrameDeltasNs", deltas);
            output.put("meanInterFrameMillis", JSONObject.NULL);
            output.put("estimatedFramesPerSecond", JSONObject.NULL);
            return;
        }

        long sum = 0;
        for (int index = 1; index < timestamps.size(); index++) {
            long delta = timestamps.get(index) - timestamps.get(index - 1);
            deltas.put(delta);
            sum += delta;
        }
        double meanNs = (double) sum / (timestamps.size() - 1);
        output.put("interFrameDeltasNs", deltas);
        output.put("meanInterFrameMillis", meanNs / 1_000_000.0);
        output.put("estimatedFramesPerSecond", 1_000_000_000.0 / meanNs);
    }

    private void applyAutomaticControls(CaptureRequest.Builder request) {
        request.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
        request.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON);
        request.set(CaptureRequest.CONTROL_AWB_MODE, CaptureRequest.CONTROL_AWB_MODE_AUTO);
        request.set(
                CaptureRequest.CONTROL_AF_MODE,
                CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE
        );
    }

    private void enableOisIfAvailable(CaptureRequest.Builder request) {
        int[] modes = characteristics.get(
                CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION
        );
        if (modes == null) {
            return;
        }
        for (int mode : modes) {
            if (mode == CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE_ON) {
                request.set(
                        CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE,
                        CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE_ON
                );
                return;
            }
        }
    }

    private JSONObject captureResultJson(TotalCaptureResult result)
            throws JSONException {
        JSONObject output = new JSONObject();
        JSONArray keyNames = new JSONArray();
        JSONObject important = new JSONObject();
        JSONObject vendor = new JSONObject();

        for (CaptureResult.Key<?> key : result.getKeys()) {
            String name = key.getName();
            keyNames.put(name);
            Object value = readResult(result, key);
            if (IMPORTANT_RESULT_KEYS.contains(name)) {
                important.put(name, jsonValue(value));
            }
            if (!name.startsWith("android.")) {
                vendor.put(name, jsonValue(value));
            }
        }
        output.put("keyNames", keyNames);
        output.put("importantValues", important);
        output.put("vendorValues", vendor);
        return output;
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readResult(
            TotalCaptureResult result,
            CaptureResult.Key<?> key
    ) {
        return result.get((CaptureResult.Key) key);
    }

    private int thermalStatus() {
        PowerManager manager = context.getSystemService(PowerManager.class);
        return manager == null ? -1 : manager.getCurrentThermalStatus();
    }

    private static void await(
            CountDownLatch latch,
            int seconds,
            String operation
    ) throws Exception {
        if (!latch.await(seconds, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out while " + operation);
        }
    }

    private static Object jsonValue(Object value) throws JSONException {
        if (value == null) {
            return JSONObject.NULL;
        }
        if (value instanceof Number
                || value instanceof Boolean
                || value instanceof String) {
            return value;
        }
        if (value instanceof Rect) {
            return ((Rect) value).flattenToString();
        }
        if (value instanceof Range<?>
                || value instanceof Size
                || value instanceof SizeF) {
            return value.toString();
        }
        if (value instanceof Collection<?>) {
            JSONArray array = new JSONArray();
            for (Object item : (Collection<?>) value) {
                array.put(jsonValue(item));
            }
            return array;
        }
        Class<?> type = value.getClass();
        if (type.isArray()) {
            JSONArray array = new JSONArray();
            int length = Array.getLength(value);
            for (int index = 0; index < length; index++) {
                array.put(jsonValue(Array.get(value, index)));
            }
            return array;
        }
        return String.valueOf(value);
    }

    @Override
    public void close() {
        if (session != null) {
            session.close();
            session = null;
        }
        if (cameraDevice != null) {
            cameraDevice.close();
            cameraDevice = null;
        }
        if (jpegReader != null) {
            jpegReader.close();
            jpegReader = null;
        }
        if (previewSurface != null) {
            previewSurface.release();
            previewSurface = null;
        }
        if (previewTexture != null) {
            previewTexture.release();
            previewTexture = null;
        }
        cameraThread.quitSafely();
    }
}
