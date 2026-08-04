package com.phone2pro.diagnostics;

import android.app.ActivityManager;
import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraExtensionCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.os.Build;
import android.os.PowerManager;
import android.util.Size;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;
import java.util.Collection;
import java.util.Set;

final class PlatformCapabilityReporter {
    private static final int[] FORMATS = {
            ImageFormat.JPEG,
            ImageFormat.YUV_420_888,
            ImageFormat.RAW_SENSOR,
            ImageFormat.RAW10,
            ImageFormat.RAW12,
            ImageFormat.PRIVATE,
            ImageFormat.DEPTH16,
            ImageFormat.DEPTH_POINT_CLOUD,
            ImageFormat.HEIC
    };

    private final Context context;

    PlatformCapabilityReporter(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject build() throws Exception {
        JSONObject root = new JSONObject();
        root.put("schemaVersion", 3);
        root.put("generatedAtEpochMillis", System.currentTimeMillis());
        root.put("device", device());
        root.put("cameras", cameras());
        root.put("sensors", sensors());
        root.put("hardwareCodecs", codecs());
        return root;
    }

    private JSONObject device() {
        JSONObject result = CameraJson.object(
                "manufacturer", Build.MANUFACTURER,
                "brand", Build.BRAND,
                "model", Build.MODEL,
                "device", Build.DEVICE,
                "product", Build.PRODUCT,
                "hardware", Build.HARDWARE,
                "board", Build.BOARD,
                "androidRelease", Build.VERSION.RELEASE,
                "sdkInt", Build.VERSION.SDK_INT,
                "securityPatch", Build.VERSION.SECURITY_PATCH,
                "fingerprint", Build.FINGERPRINT
        );
        if (Build.VERSION.SDK_INT >= 31) {
            CameraJson.put(result, "socManufacturer", Build.SOC_MANUFACTURER);
            CameraJson.put(result, "socModel", Build.SOC_MODEL);
        }

        ActivityManager activityManager = context.getSystemService(ActivityManager.class);
        if (activityManager != null) {
            ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
            activityManager.getMemoryInfo(memory);
            CameraJson.put(result, "memoryClassMb", activityManager.getMemoryClass());
            CameraJson.put(result, "largeMemoryClassMb", activityManager.getLargeMemoryClass());
            CameraJson.put(result, "totalMemoryBytes", memory.totalMem);
            CameraJson.put(result, "availableMemoryBytes", memory.availMem);
            CameraJson.put(result, "lowMemory", memory.lowMemory);
        }
        PowerManager powerManager = context.getSystemService(PowerManager.class);
        if (powerManager != null) {
            CameraJson.put(result, "thermalStatus", powerManager.getCurrentThermalStatus());
            CameraJson.put(result, "powerSaveMode", powerManager.isPowerSaveMode());
        }
        return result;
    }

    private JSONObject cameras() throws Exception {
        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }
        JSONObject result = new JSONObject();
        JSONArray publicIds = new JSONArray();
        JSONArray entries = new JSONArray();
        for (String id : manager.getCameraIdList()) {
            publicIds.put(id);
            entries.put(cameraEntry(manager, id, manager.getCameraCharacteristics(id)));
        }
        result.put("publicCameraIds", publicIds);
        result.put("cameraEntries", entries);

        JSONArray concurrent = new JSONArray();
        for (Set<String> set : manager.getConcurrentCameraIds()) {
            concurrent.put(new JSONArray(set));
        }
        result.put("concurrentCameraIdSets", concurrent);
        return result;
    }

    private JSONObject cameraEntry(
            CameraManager manager,
            String id,
            CameraCharacteristics characteristics
    ) {
        JSONObject camera = new JSONObject();
        CameraJson.put(camera, "id", id);
        put(camera, "lensFacing", characteristics.get(CameraCharacteristics.LENS_FACING));
        put(camera, "hardwareLevel",
                characteristics.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL));
        put(camera, "sensorOrientation",
                characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION));
        put(camera, "physicalCameraIds", characteristics.getPhysicalCameraIds());
        put(camera, "capabilities",
                characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES));
        put(camera, "flashAvailable",
                characteristics.get(CameraCharacteristics.FLASH_INFO_AVAILABLE));
        put(camera, "focalLengthsMm",
                characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS));
        put(camera, "apertures",
                characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES));
        put(camera, "minimumFocusDistance",
                characteristics.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE));
        put(camera, "maxDigitalZoom",
                characteristics.get(CameraCharacteristics.SCALER_AVAILABLE_MAX_DIGITAL_ZOOM));
        put(camera, "zoomRatioRange",
                characteristics.get(CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE));
        put(camera, "opticalStabilizationModes",
                characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION));
        put(camera, "videoStabilizationModes",
                characteristics.get(CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES));
        put(camera, "pixelArraySize",
                characteristics.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE));
        put(camera, "activeArray",
                characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE));
        put(camera, "physicalSensorSizeMm",
                characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE));
        put(camera, "exposureTimeRangeNs",
                characteristics.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE));
        put(camera, "sensitivityRange",
                characteristics.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE));
        put(camera, "maxAnalogSensitivity",
                characteristics.get(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY));
        put(camera, "maxRawOutputs",
                characteristics.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_RAW));
        put(camera, "maxProcessedOutputs",
                characteristics.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_PROC));
        put(camera, "maxStallingOutputs",
                characteristics.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_PROC_STALLING));
        CameraJson.put(camera, "streamConfigurations", streams(
                characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        ));
        CameraJson.put(camera, "metadata", metadata(characteristics));

        if (Build.VERSION.SDK_INT >= 31) {
            JSONArray extensions = new JSONArray();
            try {
                CameraExtensionCharacteristics extensionCharacteristics =
                        manager.getCameraExtensionCharacteristics(id);
                for (Integer extension : extensionCharacteristics.getSupportedExtensions()) {
                    extensions.put(extension);
                }
            } catch (Throwable error) {
                extensions.put(CameraJson.object("error", CameraJson.error(error)));
            }
            CameraJson.put(camera, "extensions", extensions);
        }
        return camera;
    }

    private JSONObject metadata(CameraCharacteristics characteristics) {
        JSONObject result = new JSONObject();
        JSONArray characteristicNames = new JSONArray();
        JSONArray vendorValues = new JSONArray();
        for (CameraCharacteristics.Key<?> key : characteristics.getKeys()) {
            characteristicNames.put(key.getName());
            if (!key.getName().startsWith("android.")) {
                JSONObject item = CameraJson.object("name", key.getName());
                try {
                    Object value = readCharacteristic(characteristics, key);
                    CameraJson.put(item, "value", CameraJson.value(value));
                    CameraJson.put(item, "javaValueClass",
                            value == null ? JSONObject.NULL : value.getClass().getName());
                } catch (Throwable error) {
                    CameraJson.put(item, "error", CameraJson.error(error));
                }
                vendorValues.put(item);
            }
        }
        CameraJson.put(result, "characteristicKeyNames", characteristicNames);
        CameraJson.put(result, "vendorCharacteristicValues", vendorValues);
        CameraJson.put(result, "captureRequestKeyNames",
                requestKeyNames(characteristics.getAvailableCaptureRequestKeys()));
        CameraJson.put(result, "captureResultKeyNames",
                resultKeyNames(characteristics.getAvailableCaptureResultKeys()));
        CameraJson.put(result, "sessionRequestKeyNames",
                requestKeyNames(characteristics.getAvailableSessionKeys()));
        CameraJson.put(result, "physicalCameraRequestKeyNames",
                requestKeyNames(characteristics.getAvailablePhysicalCameraRequestKeys()));
        CameraJson.put(result, "keysNeedingPermission",
                characteristicKeyNames(characteristics.getKeysNeedingPermission()));
        return result;
    }

    private JSONObject streams(StreamConfigurationMap map) {
        JSONObject result = new JSONObject();
        if (map == null) {
            return result;
        }
        for (int format : FORMATS) {
            try {
                Size[] sizes = map.getOutputSizes(format);
                if (sizes == null) {
                    continue;
                }
                JSONArray entries = new JSONArray();
                Arrays.stream(sizes)
                        .sorted((left, right) -> Long.compare(
                                (long) right.getWidth() * right.getHeight(),
                                (long) left.getWidth() * left.getHeight()
                        ))
                        .forEach(size -> entries.put(CameraJson.object(
                                "size", CameraJson.value(size),
                                "minFrameDurationNs", safeMinDuration(map, format, size),
                                "stallDurationNs", safeStallDuration(map, format, size)
                        )));
                CameraJson.put(result, formatName(format), entries);
            } catch (Throwable error) {
                CameraJson.put(result, formatName(format), CameraJson.object(
                        "error", CameraJson.error(error)
                ));
            }
        }
        return result;
    }

    private static Object safeMinDuration(StreamConfigurationMap map, int format, Size size) {
        try {
            return map.getOutputMinFrameDuration(format, size);
        } catch (Throwable error) {
            return CameraJson.object("error", CameraJson.error(error));
        }
    }

    private static Object safeStallDuration(StreamConfigurationMap map, int format, Size size) {
        try {
            return map.getOutputStallDuration(format, size);
        } catch (Throwable error) {
            return CameraJson.object("error", CameraJson.error(error));
        }
    }

    private JSONArray sensors() {
        JSONArray result = new JSONArray();
        SensorManager manager = context.getSystemService(SensorManager.class);
        if (manager == null) {
            return result;
        }
        for (Sensor sensor : manager.getSensorList(Sensor.TYPE_ALL)) {
            result.put(CameraJson.object(
                    "name", sensor.getName(),
                    "vendor", sensor.getVendor(),
                    "type", sensor.getType(),
                    "stringType", sensor.getStringType(),
                    "version", sensor.getVersion(),
                    "resolution", sensor.getResolution(),
                    "maximumRange", sensor.getMaximumRange(),
                    "powerMilliAmps", sensor.getPower(),
                    "minDelayMicros", sensor.getMinDelay(),
                    "maxDelayMicros", sensor.getMaxDelay(),
                    "reportingMode", sensor.getReportingMode()
            ));
        }
        return result;
    }

    private JSONArray codecs() {
        JSONArray result = new JSONArray();
        for (MediaCodecInfo codec : new MediaCodecList(
                MediaCodecList.ALL_CODECS
        ).getCodecInfos()) {
            if (!codec.isHardwareAccelerated()) {
                continue;
            }
            result.put(CameraJson.object(
                    "name", codec.getName(),
                    "canonicalName", codec.getCanonicalName(),
                    "encoder", codec.isEncoder(),
                    "vendor", codec.isVendor(),
                    "softwareOnly", codec.isSoftwareOnly(),
                    "supportedTypes", CameraJson.value(codec.getSupportedTypes())
            ));
        }
        return result;
    }

    private static JSONArray requestKeyNames(Collection<CaptureRequest.Key<?>> keys) {
        JSONArray result = new JSONArray();
        if (keys != null) {
            for (CaptureRequest.Key<?> key : keys) {
                result.put(key.getName());
            }
        }
        return result;
    }

    private static JSONArray resultKeyNames(Collection<CaptureResult.Key<?>> keys) {
        JSONArray result = new JSONArray();
        if (keys != null) {
            for (CaptureResult.Key<?> key : keys) {
                result.put(key.getName());
            }
        }
        return result;
    }

    private static JSONArray characteristicKeyNames(
            Collection<CameraCharacteristics.Key<?>> keys
    ) {
        JSONArray result = new JSONArray();
        if (keys != null) {
            for (CameraCharacteristics.Key<?> key : keys) {
                result.put(key.getName());
            }
        }
        return result;
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static Object readCharacteristic(
            CameraCharacteristics characteristics,
            CameraCharacteristics.Key<?> key
    ) {
        return characteristics.get((CameraCharacteristics.Key) key);
    }

    private static void put(JSONObject target, String name, Object value) {
        CameraJson.put(target, name, CameraJson.value(value));
    }

    private static String formatName(int format) {
        switch (format) {
            case ImageFormat.JPEG:
                return "JPEG";
            case ImageFormat.YUV_420_888:
                return "YUV_420_888";
            case ImageFormat.RAW_SENSOR:
                return "RAW_SENSOR";
            case ImageFormat.RAW10:
                return "RAW10";
            case ImageFormat.RAW12:
                return "RAW12";
            case ImageFormat.PRIVATE:
                return "PRIVATE";
            case ImageFormat.DEPTH16:
                return "DEPTH16";
            case ImageFormat.DEPTH_POINT_CLOUD:
                return "DEPTH_POINT_CLOUD";
            case ImageFormat.HEIC:
                return "HEIC";
            default:
                return "FORMAT_" + format;
        }
    }
}
