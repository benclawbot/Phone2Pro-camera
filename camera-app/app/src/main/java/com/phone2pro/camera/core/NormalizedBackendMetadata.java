package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/** Framework-independent metadata values emitted by any backend. */
public final class NormalizedBackendMetadata {
    private final String backendId;
    private final Map<BackendMetadataField, Object> values;

    public NormalizedBackendMetadata(
            String backendId,
            Map<BackendMetadataField, Object> values
    ) {
        this.backendId = Objects.requireNonNull(backendId, "backendId");
        if (backendId.isEmpty()) {
            throw new IllegalArgumentException("backendId must not be empty");
        }
        Objects.requireNonNull(values, "values");
        EnumMap<BackendMetadataField, Object> copy = new EnumMap<>(BackendMetadataField.class);
        for (Map.Entry<BackendMetadataField, Object> entry : values.entrySet()) {
            copy.put(
                    Objects.requireNonNull(entry.getKey(), "metadata field"),
                    Objects.requireNonNull(entry.getValue(), "metadata value")
            );
        }
        this.values = Collections.unmodifiableMap(copy);
    }

    public String backendId() { return backendId; }
    public Map<BackendMetadataField, Object> values() { return values; }

    public <T> Optional<T> get(BackendMetadataField field, Class<T> type) {
        Objects.requireNonNull(field, "field");
        Objects.requireNonNull(type, "type");
        Object value = values.get(field);
        if (value == null) {
            return Optional.empty();
        }
        if (!type.isInstance(value)) {
            throw new IllegalStateException(
                    field + " contains " + value.getClass().getName()
                            + " rather than " + type.getName()
            );
        }
        return Optional.of(type.cast(value));
    }
}
