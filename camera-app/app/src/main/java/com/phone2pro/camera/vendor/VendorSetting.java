package com.phone2pro.camera.vendor;

import java.util.Objects;

/** Typed OEM metadata setting with an immutable lifecycle scope. */
public final class VendorSetting<T> {
    private final String keyName;
    private final Class<T> valueType;
    private final T value;
    private final VendorSettingScope scope;

    public VendorSetting(
            String keyName,
            Class<T> valueType,
            T value,
            VendorSettingScope scope
    ) {
        this.keyName = requireText(keyName, "keyName");
        this.valueType = Objects.requireNonNull(valueType, "valueType");
        this.value = Objects.requireNonNull(value, "value");
        if (!valueType.isInstance(value)) {
            throw new IllegalArgumentException("value does not match valueType");
        }
        this.scope = Objects.requireNonNull(scope, "scope");
    }

    public String keyName() { return keyName; }
    public Class<T> valueType() { return valueType; }
    public T value() { return value; }
    public VendorSettingScope scope() { return scope; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
