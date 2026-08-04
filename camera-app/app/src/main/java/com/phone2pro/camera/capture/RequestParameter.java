package com.phone2pro.camera.capture;

import java.util.Objects;

/** Typed parameter kept independent from Camera2 Key objects. */
public final class RequestParameter<T> {
    private final String keyName;
    private final Class<T> valueType;
    private final T value;
    private final RequestParameterScope scope;

    public RequestParameter(
            String keyName,
            Class<T> valueType,
            T value,
            RequestParameterScope scope
    ) {
        this.keyName = Objects.requireNonNull(keyName, "keyName");
        this.valueType = Objects.requireNonNull(valueType, "valueType");
        this.value = Objects.requireNonNull(value, "value");
        this.scope = Objects.requireNonNull(scope, "scope");
        if (keyName.isEmpty()) {
            throw new IllegalArgumentException("keyName must not be empty");
        }
        if (!valueType.isInstance(value)) {
            throw new IllegalArgumentException("value does not match valueType");
        }
    }

    public String keyName() { return keyName; }
    public Class<T> valueType() { return valueType; }
    public T value() { return value; }
    public RequestParameterScope scope() { return scope; }
}
