package com.phone2pro.diagnostics;

import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.util.Size;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

final class SensorProfileDiagnostics {
    private static final int[] FORMATS = {
            ImageFormat.JPEG,
            ImageFormat.YUV_420_888,
            ImageFormat.RAW_SENSOR,
            ImageFormat.PRIVATE
    };

    private final Context context;

    SensorProfileDiagnostics(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject run() throws Exception {
        CameraManager manager = context.getSystemService(CameraManager.class);
        if (manager == null) {
            throw new IllegalStateException("Camera service is unavailable");
        }
        JSONObject report = new JSONObject();
        JSONArray cameras = new JSONArray();
        for (String id : manager.getCameraIdList()) {
            cameras.put(profile(id, manager.getCameraCharacteristics(id)));
        }
        report.put("cameras", cameras);
        report.put("dynamicMeasurementsNote",
                "Noise profile, rolling-shutter skew and per-frame black-level results are captured in captureTrace when the HAL reports them.");
        return report;
    }

    private JSONObject profile(String id, CameraCharacteristics c) {
        JSONObject result = new JSONObject();
        CameraJson.put(result, "cameraId", id);
        put(result, "lensFacing", c.get(CameraCharacteristics.LENS_FACING));
        put(result, "sensorOrientation", c.get(CameraCharacteristics.SENSOR_ORIENTATION));
        put(result, "pixelArraySize", c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE));
        put(result, "activeArray", c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE));
        put(result, "preCorrectionActiveArray",
                c.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE));
        put(result, "physicalSizeMm", c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE));
        put(result, "colorFilterArrangement",
                c.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT));
        put(result, "blackLevelPattern", c.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN));
        put(result, "whiteLevel", c.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL));
        put(result, "maxAnalogSensitivity",
                c.get(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY));
        put(result, "sensitivityRange", c.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE));
        put(result, "exposureTimeRangeNs",
                c.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE));
        put(result, "maxFrameDurationNs",
                c.get(CameraCharacteristics.SENSOR_INFO_MAX_FRAME_DURATION));
        put(result, "timestampSource", c.get(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE));

        put(result, "referenceIlluminant1",
                c.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1));
        put(result, "referenceIlluminant2",
                c.get(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2));
        put(result, "calibrationTransform1",
                c.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1));
        put(result, "calibrationTransform2",
                c.get(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2));
        put(result, "colorTransform1",
                c.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1));
        put(result, "colorTransform2",
                c.get(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2));
        put(result, "forwardMatrix1",
                c.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX1));
        put(result, "forwardMatrix2",
                c.get(CameraCharacteristics.SENSOR_FORWARD_MATRIX2));

        put(result, "focalLengthsMm",
                c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS));
        put(result, "apertures", c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES));
        put(result, "minimumFocusDistance",
                c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE));
        put(result, "hyperfocalDistance",
                c.get(CameraCharacteristics.LENS_INFO_HYPERFOCAL_DISTANCE));
        put(result, "focusDistanceCalibration",
                c.get(CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION));
        put(result, "intrinsicCalibration",
                c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION));
        put(result, "distortion", c.get(CameraCharacteristics.LENS_DISTORTION));
        put(result, "poseTranslation", c.get(CameraCharacteristics.LENS_POSE_TRANSLATION));
        put(result, "poseRotation", c.get(CameraCharacteristics.LENS_POSE_ROTATION));
        put(result, "poseReference", c.get(CameraCharacteristics.LENS_POSE_REFERENCE));
        put(result, "shadingMapSize", c.get(CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE));
        put(result, "opticalStabilizationModes",
                c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION));

        put(result, "hotPixelModes",
                c.get(CameraCharacteristics.HOT_PIXEL_AVAILABLE_HOT_PIXEL_MODES));
        put(result, "noiseReductionModes",
                c.get(CameraCharacteristics.NOISE_REDUCTION_AVAILABLE_NOISE_REDUCTION_MODES));
        put(result, "edgeModes", c.get(CameraCharacteristics.EDGE_AVAILABLE_EDGE_MODES));
        put(result, "lensShadingMapModes",
                c.get(CameraCharacteristics.STATISTICS_INFO_AVAILABLE_LENS_SHADING_MAP_MODES));
        put(result, "tonemapMaxCurvePoints",
                c.get(CameraCharacteristics.TONEMAP_MAX_CURVE_POINTS));

        StreamConfigurationMap map = c.get(
                CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
        );
        CameraJson.put(result, "streamTiming", streamTiming(map));
        return result;
    }

    private JSONArray streamTiming(StreamConfigurationMap map) {
        JSONArray result = new JSONArray();
        if (map == null) {
            return result;
        }
        for (int format : FORMATS) {
            Size[] sizes;
            try {
                sizes = map.getOutputSizes(format);
            } catch (Throwable error) {
                result.put(CameraJson.object(
                        "format", formatName(format),
                        "error", CameraJson.error(error)
                ));
                continue;
            }
            if (sizes == null) {
                continue;
            }
            Arrays.stream(sizes)
                    .sorted((left, right) -> Long.compare(
                            (long) right.getWidth() * right.getHeight(),
                            (long) left.getWidth() * left.getHeight()
                    ))
                    .limit(8)
                    .forEach(size -> {
                        JSONObject item = CameraJson.object(
                                "format", formatName(format),
                                "size", CameraJson.value(size)
                        );
                        try {
                            CameraJson.put(
                                    item,
                                    "minFrameDurationNs",
                                    map.getOutputMinFrameDuration(format, size)
                            );
                        } catch (Throwable error) {
                            CameraJson.put(item, "minFrameDurationError", CameraJson.error(error));
                        }
                        try {
                            CameraJson.put(
                                    item,
                                    "stallDurationNs",
                                    map.getOutputStallDuration(format, size)
                            );
                        } catch (Throwable error) {
                            CameraJson.put(item, "stallDurationError", CameraJson.error(error));
                        }
                        result.put(item);
                    });
        }
        return result;
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
            case ImageFormat.PRIVATE:
                return "PRIVATE";
            default:
                return "FORMAT_" + format;
        }
    }
}
