package com.phone2pro.diagnostics;

import android.graphics.Point;
import android.graphics.Rect;
import android.hardware.camera2.params.BlackLevelPattern;
import android.hardware.camera2.params.ColorSpaceTransform;
import android.hardware.camera2.params.Face;
import android.hardware.camera2.params.MeteringRectangle;
import android.hardware.camera2.params.RggbChannelVector;
import android.hardware.camera2.params.TonemapCurve;
import android.util.Pair;
import android.util.Range;
import android.util.Rational;
import android.util.Size;
import android.util.SizeF;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.lang.reflect.Array;
import java.util.Collection;
import java.util.Map;

final class CameraJson {
    private static final int MAX_ARRAY_ITEMS = 512;

    private CameraJson() {
    }

    static Object value(Object input) {
        if (input == null) {
            return JSONObject.NULL;
        }
        if (input instanceof JSONObject || input instanceof JSONArray
                || input instanceof String || input instanceof Number
                || input instanceof Boolean) {
            return input;
        }
        if (input instanceof Character || input instanceof Enum<?>) {
            return input.toString();
        }
        if (input instanceof Size) {
            Size size = (Size) input;
            return object("width", size.getWidth(), "height", size.getHeight());
        }
        if (input instanceof SizeF) {
            SizeF size = (SizeF) input;
            return object("width", size.getWidth(), "height", size.getHeight());
        }
        if (input instanceof Rect) {
            Rect rect = (Rect) input;
            return object(
                    "left", rect.left,
                    "top", rect.top,
                    "right", rect.right,
                    "bottom", rect.bottom,
                    "width", rect.width(),
                    "height", rect.height()
            );
        }
        if (input instanceof Point) {
            Point point = (Point) input;
            return object("x", point.x, "y", point.y);
        }
        if (input instanceof Range<?>) {
            Range<?> range = (Range<?>) input;
            return object("lower", value(range.getLower()), "upper", value(range.getUpper()));
        }
        if (input instanceof Rational) {
            Rational rational = (Rational) input;
            return object(
                    "numerator", rational.getNumerator(),
                    "denominator", rational.getDenominator(),
                    "doubleValue", rational.doubleValue()
            );
        }
        if (input instanceof Pair<?, ?>) {
            Pair<?, ?> pair = (Pair<?, ?>) input;
            return object("first", value(pair.first), "second", value(pair.second));
        }
        if (input instanceof BlackLevelPattern) {
            BlackLevelPattern pattern = (BlackLevelPattern) input;
            int[] offsets = new int[4];
            pattern.copyTo(offsets, 0);
            return value(offsets);
        }
        if (input instanceof RggbChannelVector) {
            RggbChannelVector vector = (RggbChannelVector) input;
            return object(
                    "red", vector.getRed(),
                    "greenEven", vector.getGreenEven(),
                    "greenOdd", vector.getGreenOdd(),
                    "blue", vector.getBlue()
            );
        }
        if (input instanceof ColorSpaceTransform) {
            ColorSpaceTransform transform = (ColorSpaceTransform) input;
            Rational[] elements = new Rational[9];
            transform.copyElements(elements, 0);
            return value(elements);
        }
        if (input instanceof MeteringRectangle) {
            MeteringRectangle rectangle = (MeteringRectangle) input;
            return object(
                    "rect", value(rectangle.getRect()),
                    "weight", rectangle.getMeteringWeight()
            );
        }
        if (input instanceof Face) {
            Face face = (Face) input;
            JSONObject result = object(
                    "bounds", value(face.getBounds()),
                    "score", face.getScore(),
                    "id", face.getId()
            );
            put(result, "leftEye", value(face.getLeftEyePosition()));
            put(result, "rightEye", value(face.getRightEyePosition()));
            put(result, "mouth", value(face.getMouthPosition()));
            return result;
        }
        if (input instanceof TonemapCurve) {
            TonemapCurve curve = (TonemapCurve) input;
            return object(
                    "red", tonemapPoints(curve, TonemapCurve.CHANNEL_RED),
                    "green", tonemapPoints(curve, TonemapCurve.CHANNEL_GREEN),
                    "blue", tonemapPoints(curve, TonemapCurve.CHANNEL_BLUE)
            );
        }
        if (input instanceof Collection<?>) {
            JSONArray result = new JSONArray();
            int index = 0;
            for (Object item : (Collection<?>) input) {
                if (index >= MAX_ARRAY_ITEMS) {
                    result.put(object("truncated", true, "remainingUnknown", true));
                    break;
                }
                result.put(value(item));
                index++;
            }
            return result;
        }
        if (input instanceof Map<?, ?>) {
            JSONObject result = new JSONObject();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) input).entrySet()) {
                put(result, String.valueOf(entry.getKey()), value(entry.getValue()));
            }
            return result;
        }
        Class<?> type = input.getClass();
        if (type.isArray()) {
            int length = Array.getLength(input);
            JSONArray result = new JSONArray();
            int limit = Math.min(length, MAX_ARRAY_ITEMS);
            for (int index = 0; index < limit; index++) {
                result.put(value(Array.get(input, index)));
            }
            if (length > limit) {
                result.put(object("truncated", true, "originalLength", length));
            }
            return result;
        }
        return object(
                "class", type.getName(),
                "stringValue", String.valueOf(input)
        );
    }

    static JSONObject error(Throwable error) {
        JSONObject result = new JSONObject();
        put(result, "type", error.getClass().getName());
        put(result, "message", String.valueOf(error.getMessage()));
        put(result, "string", error.toString());
        return result;
    }

    static JSONObject object(Object... keyValues) {
        JSONObject result = new JSONObject();
        for (int index = 0; index + 1 < keyValues.length; index += 2) {
            put(result, String.valueOf(keyValues[index]), keyValues[index + 1]);
        }
        return result;
    }

    static void put(JSONObject target, String key, Object value) {
        try {
            target.put(key, value == null ? JSONObject.NULL : value);
        } catch (JSONException ignored) {
            // JSONObject only rejects non-finite numbers. Preserve the field as text.
            try {
                target.put(key, String.valueOf(value));
            } catch (JSONException impossible) {
                // Key is always non-null and finite after String conversion.
            }
        }
    }

    private static JSONArray tonemapPoints(TonemapCurve curve, int channel) {
        int count = curve.getPointCount(channel);
        float[] points = new float[count * TonemapCurve.POINT_SIZE];
        curve.copyColorCurve(channel, points, 0);
        return (JSONArray) value(points);
    }
}
