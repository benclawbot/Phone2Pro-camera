package com.phone2pro.camera.capture;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** One ordered still request in a burst, independent from Android request objects. */
public final class CaptureFrameRequest {
    private final int sequenceIndex;
    private final String requestId;
    private final CaptureRequestTemplate template;
    private final List<RequestParameter<?>> parameters;

    public CaptureFrameRequest(
            int sequenceIndex,
            String requestId,
            CaptureRequestTemplate template,
            List<RequestParameter<?>> parameters
    ) {
        if (sequenceIndex < 0) {
            throw new IllegalArgumentException("sequenceIndex must be non-negative");
        }
        this.sequenceIndex = sequenceIndex;
        this.requestId = requireText(requestId, "requestId");
        this.template = Objects.requireNonNull(template, "template");
        Objects.requireNonNull(parameters, "parameters");
        List<RequestParameter<?>> copy = new ArrayList<>(parameters.size());
        for (RequestParameter<?> parameter : parameters) {
            Objects.requireNonNull(parameter, "parameters entry");
            if (parameter.scope() != RequestParameterScope.STILL) {
                throw new IllegalArgumentException(
                        parameter.keyName() + " is not a STILL parameter"
                );
            }
            copy.add(parameter);
        }
        this.parameters = Collections.unmodifiableList(copy);
    }

    public int sequenceIndex() { return sequenceIndex; }
    public String requestId() { return requestId; }
    public CaptureRequestTemplate template() { return template; }
    public List<RequestParameter<?>> parameters() { return parameters; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
