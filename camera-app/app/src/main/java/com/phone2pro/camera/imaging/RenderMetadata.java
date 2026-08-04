package com.phone2pro.camera.imaging;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/** Immutable typed metadata propagated through every rendering stage. */
public final class RenderMetadata {
    public static final MetadataKey<String> REFERENCE_FRAME_ID = new MetadataKey<>(
            "referenceFrameId", String.class
    );
    public static final MetadataKey<Integer> SOURCE_FRAME_COUNT = new MetadataKey<>(
            "sourceFrameCount", Integer.class
    );
    public static final MetadataKey<String> LENS_ROUTE_ID = new MetadataKey<>(
            "lensRouteId", String.class
    );
    public static final MetadataKey<Long> SENSOR_TIMESTAMP_NS = new MetadataKey<>(
            "sensorTimestampNs", Long.class
    );

    private final Map<MetadataKey<?>, Object> values;

    private RenderMetadata(Map<MetadataKey<?>, Object> values) {
        this.values = Collections.unmodifiableMap(new LinkedHashMap<>(values));
    }

    public static RenderMetadata empty() {
        return new RenderMetadata(Collections.emptyMap());
    }

    public <T> RenderMetadata with(MetadataKey<T> key, T value) {
        Objects.requireNonNull(key, "key");
        Objects.requireNonNull(value, "value");
        if (!key.type().isInstance(value)) {
            throw new IllegalArgumentException("metadata value does not match key type");
        }
        Map<MetadataKey<?>, Object> copy = new LinkedHashMap<>(values);
        copy.put(key, value);
        return new RenderMetadata(copy);
    }

    public <T> Optional<T> get(MetadataKey<T> key) {
        Objects.requireNonNull(key, "key");
        Object value = values.get(key);
        if (value == null) {
            return Optional.empty();
        }
        return Optional.of(key.type().cast(value));
    }

    public boolean contains(MetadataKey<?> key) {
        return values.containsKey(key);
    }

    public Map<String, Object> snapshotByName() {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        for (Map.Entry<MetadataKey<?>, Object> entry : values.entrySet()) {
            snapshot.put(entry.getKey().name(), entry.getValue());
        }
        return Collections.unmodifiableMap(snapshot);
    }
}
