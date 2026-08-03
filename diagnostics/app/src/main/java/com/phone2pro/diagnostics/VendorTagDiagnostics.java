package com.phone2pro.diagnostics;

import android.annotation.SuppressLint;
import android.content.Context;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.os.Handler;
import android.os.HandlerThread;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.reflect.Method;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

final class VendorTagDiagnostics implements AutoCloseable {
    private static final long TIMEOUT_SECONDS = 8;

    private static final Map<Integer, String> TEMPLATES = new LinkedHashMap<>();

    static {
        TEMPLATES.put(CameraDevice.TEMPLATE_PREVIEW, "preview");
        TEMPLATES.put(CameraDevice.TEMPLATE_STILL_CAPTURE, "still-capture");
        TEMPLATES.put(CameraDevice.TEMPLATE_RECORD, "record");
        TEMPLATES.put(CameraDevice.TEMPLATE_VIDEO_SNAPSHOT, "video-snapshot");
        TEMPLATES.put(CameraDevice.TEMPLATE_ZERO_SHUTTER_LAG, "zero-shutter-lag");
        TEMPLATES.put(CameraDevice.TEMPLATE_MANUAL, "manual");
    }

    private final Context context;
    private final HandlerThread thread = new HandlerThread("VendorTagDiagnostics");
    private Handler handler;

    VendorTagDiagnostics(Context context) {
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
        JSONArray cameras = new JSONArray();
        for (String id : manager.getCameraIdList()) {
            cameras.put(runCamera(manager, id));
        }
        report.put("cameras", cameras);
        report.put("typeRecoveryNote",
                "Java type recovery uses target-runtime reflection when permitted. Missing type fields remain unknown and are not guessed.");
        return report;
    }

    private JSONObject runCamera(CameraManager manager, String id) {
        JSONObject camera = new JSONObject();
        CameraJson.put(camera, "cameraId", id);
        CameraDevice device = null;
        try {
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            camera.put("characteristics", characteristicEntries(characteristics));
            camera.put("requestKeys", keyEntries(
                    characteristics.getAvailableCaptureRequestKeys()
            ));
            camera.put("resultKeys", resultKeyEntries(
                    characteristics.getAvailableCaptureResultKeys()
            ));
            camera.put("sessionKeys", keyEntries(
                    characteristics.getAvailableSessionKeys()
            ));
            camera.put("physicalRequestKeys", keyEntries(
                    characteristics.getAvailablePhysicalCameraRequestKeys()
            ));

            device = open(manager, id);
            JSONArray templates = new JSONArray();
            for (Map.Entry<Integer, String> template : TEMPLATES.entrySet()) {
                templates.put(defaultTemplate(device, template.getKey(), template.getValue()));
            }
            camera.put("defaultRequestTemplates", templates);
        } catch (Throwable error) {
            CameraJson.put(camera, "error", CameraJson.error(error));
        } finally {
            if (device != null) {
                device.close();
            }
        }
        return camera;
    }

    private JSONArray characteristicEntries(CameraCharacteristics characteristics) {
        JSONArray entries = new JSONArray();
        for (CameraCharacteristics.Key<?> key : characteristics.getKeys()) {
            JSONObject entry = keyEntry(key, key.getName());
            try {
                Object value = readCharacteristic(characteristics, key);
                CameraJson.put(entry, "value", CameraJson.value(value));
                CameraJson.put(entry, "javaValueClass",
                        value == null ? JSONObject.NULL : value.getClass().getName());
            } catch (Throwable error) {
                CameraJson.put(entry, "readError", CameraJson.error(error));
            }
            entries.put(entry);
        }
        return entries;
    }

    private JSONArray keyEntries(Collection<CaptureRequest.Key<?>> keys) {
        JSONArray entries = new JSONArray();
        if (keys == null) {
            return entries;
        }
        for (CaptureRequest.Key<?> key : keys) {
            entries.put(keyEntry(key, key.getName()));
        }
        return entries;
    }

    private JSONArray resultKeyEntries(Collection<CaptureResult.Key<?>> keys) {
        JSONArray entries = new JSONArray();
        if (keys == null) {
            return entries;
        }
        for (CaptureResult.Key<?> key : keys) {
            entries.put(keyEntry(key, key.getName()));
        }
        return entries;
    }

    private JSONObject defaultTemplate(CameraDevice device, int templateId, String name) {
        JSONObject output = new JSONObject();
        CameraJson.put(output, "templateId", templateId);
        CameraJson.put(output, "templateName", name);
        try {
            CaptureRequest request = device.createCaptureRequest(templateId).build();
            JSONArray values = new JSONArray();
            for (CaptureRequest.Key<?> key : request.getKeys()) {
                Object value = readRequest(request, key);
                if (value == null) {
                    continue;
                }
                JSONObject entry = keyEntry(key, key.getName());
                CameraJson.put(entry, "value", CameraJson.value(value));
                CameraJson.put(entry, "javaValueClass", value.getClass().getName());
                values.put(entry);
            }
            CameraJson.put(output, "supported", true);
            CameraJson.put(output, "nonNullDefaultCount", values.length());
            CameraJson.put(output, "values", values);
        } catch (Throwable error) {
            CameraJson.put(output, "supported", false);
            CameraJson.put(output, "error", CameraJson.error(error));
        }
        return output;
    }

    private static JSONObject keyEntry(Object key, String name) {
        JSONObject entry = new JSONObject();
        CameraJson.put(entry, "name", name);
        CameraJson.put(entry, "vendor", !name.startsWith("android."));
        CameraJson.put(entry, "keyClass", key.getClass().getName());
        try {
            Method getType = key.getClass().getDeclaredMethod("getType");
            getType.setAccessible(true);
            Object type = getType.invoke(key);
            CameraJson.put(entry, "declaredJavaType", String.valueOf(type));
            CameraJson.put(entry, "typeRecovery", "reflection");
        } catch (Throwable error) {
            CameraJson.put(entry, "declaredJavaType", JSONObject.NULL);
            CameraJson.put(entry, "typeRecovery", "unavailable");
            CameraJson.put(entry, "typeRecoveryError", error.getClass().getName());
        }
        return entry;
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

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readCharacteristic(
            CameraCharacteristics characteristics,
            CameraCharacteristics.Key<?> key
    ) {
        return characteristics.get((CameraCharacteristics.Key) key);
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readRequest(CaptureRequest request, CaptureRequest.Key<?> key) {
        return request.get((CaptureRequest.Key) key);
    }

    @Override
    public void close() {
        if (thread.isAlive()) {
            thread.quitSafely();
        }
    }
}
