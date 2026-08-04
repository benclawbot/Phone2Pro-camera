package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Strongly typed key for metadata that must survive pipeline stages. */
public final class MetadataKey<T> {
    private final String name;
    private final Class<T> type;

    public MetadataKey(String name, Class<T> type) {
        this.name = Objects.requireNonNull(name, "name");
        this.type = Objects.requireNonNull(type, "type");
        if (name.isEmpty()) {
            throw new IllegalArgumentException("metadata key name must not be empty");
        }
    }

    public String name() { return name; }
    public Class<T> type() { return type; }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof MetadataKey)) {
            return false;
        }
        MetadataKey<?> key = (MetadataKey<?>) other;
        return name.equals(key.name) && type.equals(key.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, type);
    }
}
