package com.phone2pro.diagnostics;

import android.app.ActivityManager;
import android.content.Context;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraExtensionCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.os.Build;
import android.os.PowerManager;
import android.util.Range;
import android.util.Size;
import android.util.SizeF;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

final class CapabilityReporter {
    private final Context context;

    CapabilityReporter(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject build() throws Exception {
        JSONObject root = new JSONObject();
        root.put("schemaVersion", 1);
        root.put("generatedAtEpochMillis", System.currentTimeMillis());
        root.put("device", buildDevice());
        root.put("cameras", buildCameras());
        root.put("sensors", buildSensors());
        root.put("hardwareCodecs", buildCodecs());
        return root;
    }

    private JSONObject buildDevice() throws JSONException {
        JSONObject device = new JSONObject();
        device.put("manufacturer", Build.MANUFACTURER);
        device.put("brand", Build.BRAND);
        device.put("model", Build.MODEL);
        device.put("device", Build.DEVICE);
        device.put("product", Build.PRODUCT);
        device.put("hardware", Build.HARDWARE);
        device.put("board", Build.BOARD);
        device.put("androidRelease", Build.VERSION.RELEASE);
        device.put("sdkInt", Build.VERSION.SDK_INT);
        device.put("securityPatch", Build.VERSION.SECURITY_PATCH);
        device.put("fingerprint", Build.FINGERPRINT);
        if (Build.VERSION.SDK_INT >= 31) {
            device.put("socManufacturer", Build.SOC_MANUFACTURER);
            device.put("socModel", Build.SOC_MODEL);
        }

        ActivityManager activityManager = context.getSystemService(ActivityManager.class);
        if (activityManager != null) {
            ActivityManager.MemoryInfo memoryInfo = new ActivityManager.MemoryInfo();
            activityManager.getMemoryInfo(memoryInfo);
            device.put("memoryClassMb", activityManager.getMemoryClass());
            device.put("largeMemoryClassMb", activityManager.getLargeMemoryClass());
            device.put("totalMemoryBytes", memoryInfo.totalMem);
            device.put("availableMemoryBytes", memoryInfo.availMem);
            device.put("lowMemory", memoryInfo.lowMemory);
        }

        PowerManager powerManager = context.getSystemService(PowerManager.class);
        if (powerManager != null) {
            device.put("thermalStatus", powerManager.getCurrentThermalStatus());
            device.put("powerSaveMode", powerManager.isPowerSaveMode());
        }
        return device;
    }

    private JSONObject buildCameras() throws Exception {
        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }
        JSONObject result = new JSONObject();
        JSONArray publicIds = new JSONArray();
        JSONArray cameras = new JSONArray();
        Set<String> reportedIds = new LinkedHashSet<>();

        for (String id : manager.getCameraIdList()) {
            publicIds.put(id);
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            cameras.put(buildCamera(manager, id, characteristics, true));
            reportedIds.add(id);
            for (String physicalId : characteristics.getPhysicalCameraIds()) {
                if (reportedIds.add(physicalId)) {
                    cameras.put(buildCamera(
                            manager,
                            physicalId,
                            manager.getCameraCharacteristics(physicalId),
                            false
                    ));
                }
            }
        }

        result.put("publicCameraIds", publicIds);
        result.put("cameraEntries", cameras);
        if (Build.VERSION.SDK_INT >= 30) {
            JSONArray concurrent = new JSONArray();
            for (Set<String> combination : manager.getConcurrentCameraIds()) {
                concurrent.put(new JSONArray(combination));
            }
            result.put("concurrentCameraIdSets", concurrent);
        }
        return result;
    }

    private JSONObject buildCamera(
            CameraManager manager,
            String id,
            CameraCharacteristics c,
            boolean independentlyOpenable
    ) throws Exception {
        JSONObject camera = new JSONObject();
        camera.put("id", id);
        camera.put("independentlyOpenable", independentlyOpenable);
        camera.put("lensFacing", lensFacing(c.get(CameraCharacteristics.LENS_FACING)));
        camera.put("sensorOrientation", value(c.get(CameraCharacteristics.SENSOR_ORIENTATION)));
        camera.put("hardwareLevel", hardwareLevel(c.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)));
        camera.put("physicalCameraIds", new JSONArray(c.getPhysicalCameraIds()));
        camera.put("capabilities", capabilities(c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)));
        camera.put("flashAvailable", value(c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE)));
        camera.put("focalLengthsMm", value(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)));
        camera.put("apertures", value(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES)));
        camera.put("minimumFocusDistance", value(c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE)));
        camera.put("maxDigitalZoom", value(c.get(CameraCharacteristics.SCALER_AVAILABLE_MAX_DIGITAL_ZOOM)));
        if (Build.VERSION.SDK_INT >= 30) {
            camera.put("zoomRatioRange", value(c.get(CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE)));
        }
        camera.put("opticalStabilizationModes", value(c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)));
        camera.put("videoStabilizationModes", value(c.get(CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES)));
        camera.put("maxAfRegions", value(c.get(CameraCharacteristics.CONTROL_MAX_REGIONS_AF)));
        camera.put("pixelArraySize", value(c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)));
        camera.put("activeArray", value(c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)));
        camera.put("physicalSensorSizeMm", value(c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)));
        camera.put("exposureTimeRangeNs", value(c.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)));
        camera.put("sensitivityRange", value(c.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)));
        camera.put("maxAnalogSensitivity", value(c.get(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY)));
        camera.put("maxRawOutputs", value(c.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_RAW)));
        camera.put("maxProcessedOutputs", value(c.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_PROC)));
        camera.put("maxStallingOutputs", value(c.get(CameraCharacteristics.REQUEST_MAX_NUM_OUTPUT_PROC_STALLING)));
        camera.put("outputSizes", outputSizes(c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)));

        if (independentlyOpenable && Build.VERSION.SDK_INT >= 31) {
            JSONArray extensions = new JSONArray();
            for (Integer extension : manager.getCameraExtensionCharacteristics(id).getSupportedExtensions()) {
                JSONObject item = new JSONObject();
                item.put("id", extension);
                item.put("name", extensionName(extension));
                extensions.put(item);
            }
            camera.put("extensions", extensions);
        }
        return camera;
    }

    private JSONObject outputSizes(StreamConfigurationMap map) throws JSONException {
        JSONObject sizes = new JSONObject();
        if (map == null) {
            return sizes;
        }
        sizes.put("jpeg", sizes(map.getOutputSizes(ImageFormat.JPEG)));
        sizes.put("yuv420", sizes(map.getOutputSizes(ImageFormat.YUV_420_888)));
        sizes.put("rawSensor", sizes(map.getOutputSizes(ImageFormat.RAW_SENSOR)));
        sizes.put("private", sizes(map.getOutputSizes(ImageFormat.PRIVATE)));
        sizes.put("highResolutionJpeg", sizes(map.getHighResolutionOutputSizes(ImageFormat.JPEG)));
        sizes.put("highResolutionYuv420", sizes(map.getHighResolutionOutputSizes(ImageFormat.YUV_420_888)));
        return sizes;
    }

    private JSONArray sizes(Size[] sizes) {
        JSONArray result = new JSONArray();
        if (sizes != null) {
            Arrays.stream(sizes)
                    .sorted((a, b) -> Long.compare(
                            (long) b.getWidth() * b.getHeight(),
                            (long) a.getWidth() * a.getHeight()
                    ))
                    .forEach(size -> result.put(size.getWidth() + "x" + size.getHeight()));
        }
        return result;
    }

    private JSONArray capabilities(int[] values) throws JSONException {
        JSONArray result = new JSONArray();
        if (values == null) {
            return result;
        }
        for (int capability : values) {
            JSONObject item = new JSONObject();
            item.put("id", capability);
            item.put("name", capabilityName(capability));
            result.put(item);
        }
        return result;
    }

    private JSONArray buildSensors() throws JSONException {
        SensorManager manager = context.getSystemService(SensorManager.class);
        JSONArray sensors = new JSONArray();
        if (manager == null) {
            return sensors;
        }
        List<Sensor> all = manager.getSensorList(Sensor.TYPE_ALL);
        for (Sensor sensor : all) {
            JSONObject item = new JSONObject();
            item.put("name", sensor.getName());
            item.put("vendor", sensor.getVendor());
            item.put("type", sensor.getType());
            item.put("stringType", sensor.getStringType());
            item.put("version", sensor.getVersion());
            item.put("resolution", sensor.getResolution());
            item.put("maximumRange", sensor.getMaximumRange());
            item.put("powerMilliAmps", sensor.getPower());
            item.put("minDelayMicros", sensor.getMinDelay());
            item.put("maxDelayMicros", sensor.getMaxDelay());
            item.put("reportingMode", sensor.getReportingMode());
            sensors.put(item);
        }
        return sensors;
    }

    private JSONArray buildCodecs() throws JSONException {
        JSONArray result = new JSONArray();
        for (MediaCodecInfo codec : new MediaCodecList(MediaCodecList.ALL_CODECS).getCodecInfos()) {
            if (!codec.isHardwareAccelerated()) {
                continue;
            }
            JSONObject item = new JSONObject();
            item.put("name", codec.getName());
            item.put("canonicalName", codec.getCanonicalName());
            item.put("encoder", codec.isEncoder());
            item.put("vendor", codec.isVendor());
            item.put("softwareOnly", codec.isSoftwareOnly());
            item.put("supportedTypes", new JSONArray(Arrays.asList(codec.getSupportedTypes())));
            result.put(item);
        }
        return result;
    }

    private static Object value(Object value) {
        if (value == null) {
            return JSONObject.NULL;
        }
        if (value instanceof int[]) {
            return new JSONArray(Arrays.stream((int[]) value).boxed().toList());
        }
        if (value instanceof float[]) {
            JSONArray result = new JSONArray();
            for (float number : (float[]) value) {
                result.put(number);
            }
            return result;
        }
        if (value instanceof long[]) {
            JSONArray result = new JSONArray();
            for (long number : (long[]) value) {
                result.put(number);
            }
            return result;
        }
        if (value instanceof Size size) {
            return size.getWidth() + "x" + size.getHeight();
        }
        if (value instanceof SizeF size) {
            return size.getWidth() + "x" + size.getHeight();
        }
        if (value instanceof Rect rect) {
            return rect.flattenToString();
        }
        if (value instanceof Range<?> range) {
            return range.toString();
        }
        return value;
    }

    private static String lensFacing(Integer facing) {
        if (facing == null) {
            return "UNKNOWN";
        }
        return switch (facing) {
            case CameraCharacteristics.LENS_FACING_FRONT -> "FRONT";
            case CameraCharacteristics.LENS_FACING_BACK -> "BACK";
            case CameraCharacteristics.LENS_FACING_EXTERNAL -> "EXTERNAL";
            default -> "UNKNOWN_" + facing;
        };
    }

    private static String hardwareLevel(Integer level) {
        if (level == null) {
            return "UNKNOWN";
        }
        return switch (level) {
            case CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "LEGACY";
            case CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "LIMITED";
            case CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "FULL";
            case CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "LEVEL_3";
            case CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL";
            default -> "UNKNOWN_" + level;
        };
    }

    private static String capabilityName(int capability) {
        return switch (capability) {
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE -> "BACKWARD_COMPATIBLE";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR -> "MANUAL_SENSOR";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING -> "MANUAL_POST_PROCESSING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW -> "RAW";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_PRIVATE_REPROCESSING -> "PRIVATE_REPROCESSING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_READ_SENSOR_SETTINGS -> "READ_SENSOR_SETTINGS";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_BURST_CAPTURE -> "BURST_CAPTURE";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_YUV_REPROCESSING -> "YUV_REPROCESSING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT -> "DEPTH_OUTPUT";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_CONSTRAINED_HIGH_SPEED_VIDEO -> "CONSTRAINED_HIGH_SPEED_VIDEO";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MOTION_TRACKING -> "MOTION_TRACKING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA -> "LOGICAL_MULTI_CAMERA";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MONOCHROME -> "MONOCHROME";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_SECURE_IMAGE_DATA -> "SECURE_IMAGE_DATA";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_OFFLINE_PROCESSING -> "OFFLINE_PROCESSING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_ULTRA_HIGH_RESOLUTION_SENSOR -> "ULTRA_HIGH_RESOLUTION_SENSOR";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_REMOSAIC_REPROCESSING -> "REMOSAIC_REPROCESSING";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT -> "DYNAMIC_RANGE_TEN_BIT";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_STREAM_USE_CASE -> "STREAM_USE_CASE";
            case CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_COLOR_SPACE_PROFILES -> "COLOR_SPACE_PROFILES";
            default -> "UNKNOWN_" + capability;
        };
    }

    private static String extensionName(int extension) {
        return switch (extension) {
            case CameraExtensionCharacteristics.EXTENSION_AUTOMATIC -> "AUTOMATIC";
            case CameraExtensionCharacteristics.EXTENSION_FACE_RETOUCH -> "FACE_RETOUCH";
            case CameraExtensionCharacteristics.EXTENSION_BOKEH -> "BOKEH";
            case CameraExtensionCharacteristics.EXTENSION_HDR -> "HDR";
            case CameraExtensionCharacteristics.EXTENSION_NIGHT -> "NIGHT";
            default -> "UNKNOWN_" + extension;
        };
    }
}
