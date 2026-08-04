package com.phone2pro.diagnostics;

import android.annotation.SuppressLint;
import android.content.Context;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.LinkedHashSet;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class CameraOpenDiagnostics implements AutoCloseable {
    private static final int NUMERIC_ID_LIMIT = 16;
    private static final long OPEN_TIMEOUT_SECONDS = 5;

    private final Context context;
    private final HandlerThread thread = new HandlerThread("CameraOpenDiagnostics");
    private Handler handler;

    CameraOpenDiagnostics(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject run() throws Exception {
        thread.start();
        handler = new Handler(thread.getLooper());

        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }

        JSONObject report = new JSONObject();
        JSONArray availability = new JSONArray();
        CameraManager.AvailabilityCallback availabilityCallback =
                new CameraManager.AvailabilityCallback() {
                    @Override
                    public void onCameraAvailable(String cameraId) {
                        availability.put(CameraJson.object(
                                "elapsedRealtimeMillis", SystemClock.elapsedRealtime(),
                                "event", "available",
                                "cameraId", cameraId
                        ));
                    }

                    @Override
                    public void onCameraUnavailable(String cameraId) {
                        availability.put(CameraJson.object(
                                "elapsedRealtimeMillis", SystemClock.elapsedRealtime(),
                                "event", "unavailable",
                                "cameraId", cameraId
                        ));
                    }

                    @Override
                    public void onCameraAccessPrioritiesChanged() {
                        availability.put(CameraJson.object(
                                "elapsedRealtimeMillis", SystemClock.elapsedRealtime(),
                                "event", "access-priorities-changed"
                        ));
                    }
                };

        manager.registerAvailabilityCallback(availabilityCallback, handler);
        try {
            Set<String> ids = new LinkedHashSet<>();
            JSONArray publicIds = new JSONArray();
            for (String id : manager.getCameraIdList()) {
                ids.add(id);
                publicIds.put(id);
            }
            for (int number = 0; number < NUMERIC_ID_LIMIT; number++) {
                ids.add(Integer.toString(number));
            }

            JSONArray probes = new JSONArray();
            for (String id : ids) {
                probes.put(probe(manager, id, contains(publicIds, id)));
                SystemClock.sleep(100);
            }
            report.put("publicCameraIds", publicIds);
            report.put("candidateIdLimitExclusive", NUMERIC_ID_LIMIT);
            report.put("probes", probes);
            report.put("availabilityEvents", availability);
            report.put("completedAtElapsedRealtimeMillis", SystemClock.elapsedRealtime());
            return report;
        } finally {
            manager.unregisterAvailabilityCallback(availabilityCallback);
        }
    }

    @SuppressLint("MissingPermission")
    private JSONObject probe(CameraManager manager, String id, boolean publiclyListed) {
        JSONObject item = new JSONObject();
        CameraJson.put(item, "cameraId", id);
        CameraJson.put(item, "publiclyListed", publiclyListed);
        long start = SystemClock.elapsedRealtime();

        try {
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            CameraJson.put(item, "characteristicsReadable", true);
            CameraJson.put(item, "lensFacing", CameraJson.value(
                    characteristics.get(CameraCharacteristics.LENS_FACING)
            ));
            CameraJson.put(item, "hardwareLevel", CameraJson.value(
                    characteristics.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)
            ));
            CameraJson.put(item, "physicalCameraIds", CameraJson.value(
                    characteristics.getPhysicalCameraIds()
            ));
            CameraJson.put(item, "capabilities", CameraJson.value(
                    characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
            ));
            CameraJson.put(item, "focalLengthsMm", CameraJson.value(
                    characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
            ));
        } catch (Throwable error) {
            CameraJson.put(item, "characteristicsReadable", false);
            CameraJson.put(item, "characteristicsError", cameraError(error));
        }

        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<String> outcome = new AtomicReference<>("timeout");
        AtomicReference<Throwable> callbackFailure = new AtomicReference<>();
        AtomicInteger callbackCode = new AtomicInteger(-1);
        AtomicReference<CameraDevice> openedDevice = new AtomicReference<>();

        try {
            manager.openCamera(id, new CameraDevice.StateCallback() {
                @Override
                public void onOpened(CameraDevice camera) {
                    openedDevice.set(camera);
                    outcome.set("opened");
                    latch.countDown();
                }

                @Override
                public void onDisconnected(CameraDevice camera) {
                    callbackFailure.set(new IllegalStateException("camera disconnected"));
                    outcome.set("disconnected");
                    camera.close();
                    latch.countDown();
                }

                @Override
                public void onError(CameraDevice camera, int error) {
                    callbackCode.set(error);
                    callbackFailure.set(new IllegalStateException(errorName(error)));
                    outcome.set("callback-error");
                    camera.close();
                    latch.countDown();
                }
            }, handler);

            boolean completed = latch.await(OPEN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
            CameraJson.put(item, "openCompleted", completed);
            CameraJson.put(item, "openOutcome", outcome.get());
            if (callbackCode.get() >= 0) {
                CameraJson.put(item, "callbackErrorCode", callbackCode.get());
                CameraJson.put(item, "callbackErrorName", errorName(callbackCode.get()));
            }
            if (callbackFailure.get() != null) {
                CameraJson.put(item, "callbackError", cameraError(callbackFailure.get()));
            }
        } catch (Throwable error) {
            CameraJson.put(item, "openCompleted", true);
            CameraJson.put(item, "openOutcome", "exception");
            CameraJson.put(item, "openError", cameraError(error));
        } finally {
            CameraDevice device = openedDevice.get();
            if (device != null) {
                device.close();
            }
        }

        CameraJson.put(
                item,
                "durationMillis",
                SystemClock.elapsedRealtime() - start
        );
        return item;
    }

    private static JSONObject cameraError(Throwable error) {
        JSONObject result = CameraJson.error(error);
        if (error instanceof CameraAccessException) {
            CameraJson.put(
                    result,
                    "cameraAccessReason",
                    ((CameraAccessException) error).getReason()
            );
        }
        return result;
    }

    private static boolean contains(JSONArray array, String value) {
        for (int index = 0; index < array.length(); index++) {
            if (value.equals(array.optString(index))) {
                return true;
            }
        }
        return false;
    }

    private static String errorName(int error) {
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

    @Override
    public void close() {
        if (thread.isAlive()) {
            thread.quitSafely();
        }
    }
}
