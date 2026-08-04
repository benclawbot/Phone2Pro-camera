package com.phone2pro.camera.capture;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.imaging.TimestampDomain;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Portable session configuration before CameraX or Camera2 binding. */
public final class CaptureSessionPlan {
    private final long generation;
    private final String backendId;
    private final SessionBinderKind binderKind;
    private final OpticalRoute route;
    private final ResolvedCameraEndpoint endpoint;
    private final CaptureProfile profile;
    private final TimestampDomain metadataTimestampDomain;
    private final List<StreamSpec> streams;
    private final List<RequestParameter<?>> sessionParameters;
    private final List<RequestParameter<?>> repeatingParameters;
    private final List<RequestParameter<?>> stillParameters;

    public CaptureSessionPlan(
            long generation,
            String backendId,
            SessionBinderKind binderKind,
            OpticalRoute route,
            ResolvedCameraEndpoint endpoint,
            CaptureProfile profile,
            TimestampDomain metadataTimestampDomain,
            List<StreamSpec> streams,
            List<RequestParameter<?>> sessionParameters,
            List<RequestParameter<?>> repeatingParameters,
            List<RequestParameter<?>> stillParameters
    ) {
        if (generation < 0) {
            throw new IllegalArgumentException("generation must be non-negative");
        }
        this.backendId = requireText(backendId, "backendId");
        this.binderKind = Objects.requireNonNull(binderKind, "binderKind");
        this.route = Objects.requireNonNull(route, "route");
        this.endpoint = Objects.requireNonNull(endpoint, "endpoint");
        this.profile = Objects.requireNonNull(profile, "profile");
        this.metadataTimestampDomain = Objects.requireNonNull(
                metadataTimestampDomain,
                "metadataTimestampDomain"
        );
        if (metadataTimestampDomain == TimestampDomain.UNKNOWN) {
            throw new IllegalArgumentException("session metadata timestamp domain must be known");
        }
        this.streams = immutableNonEmpty(streams, "streams");
        this.sessionParameters = scopedCopy(
                sessionParameters,
                RequestParameterScope.SESSION,
                "sessionParameters"
        );
        this.repeatingParameters = scopedCopy(
                repeatingParameters,
                RequestParameterScope.REPEATING,
                "repeatingParameters"
        );
        this.stillParameters = scopedCopy(
                stillParameters,
                RequestParameterScope.STILL,
                "stillParameters"
        );
        this.generation = generation;
        validateBinderBoundary();
    }

    public long generation() { return generation; }
    public String backendId() { return backendId; }
    public SessionBinderKind binderKind() { return binderKind; }
    public OpticalRoute route() { return route; }
    public ResolvedCameraEndpoint endpoint() { return endpoint; }
    public CaptureProfile profile() { return profile; }
    public TimestampDomain metadataTimestampDomain() { return metadataTimestampDomain; }
    public List<StreamSpec> streams() { return streams; }
    public List<RequestParameter<?>> sessionParameters() { return sessionParameters; }
    public List<RequestParameter<?>> repeatingParameters() { return repeatingParameters; }
    public List<RequestParameter<?>> stillParameters() { return stillParameters; }

    private void validateBinderBoundary() {
        if (binderKind == SessionBinderKind.CAMERAX_PUBLIC) {
            if (!sessionParameters.isEmpty()) {
                throw new IllegalArgumentException(
                        "CameraX public binder cannot promise arbitrary session parameters"
                );
            }
            for (StreamSpec stream : streams) {
                if (stream.physicalOutput() || stream.role() == StreamRole.REPROCESS_INPUT) {
                    throw new IllegalArgumentException(
                            "CameraX public binder cannot bind physical outputs or reprocessing inputs"
                    );
                }
            }
        }
        if (binderKind != SessionBinderKind.CAMERA2_VENDOR_ADAPTER) {
            for (RequestParameter<?> parameter : allParameters()) {
                if (parameter.keyName().startsWith("com.mediatek.")
                        || parameter.keyName().startsWith("com.nothing.")) {
                    throw new IllegalArgumentException(
                            "vendor key requires CAMERA2_VENDOR_ADAPTER"
                    );
                }
            }
        }
    }

    private List<RequestParameter<?>> allParameters() {
        List<RequestParameter<?>> all = new ArrayList<>();
        all.addAll(sessionParameters);
        all.addAll(repeatingParameters);
        all.addAll(stillParameters);
        return all;
    }

    private static <T> List<T> immutableNonEmpty(List<T> values, String name) {
        Objects.requireNonNull(values, name);
        if (values.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        List<T> copy = new ArrayList<>(values.size());
        for (T value : values) {
            copy.add(Objects.requireNonNull(value, name + " entry"));
        }
        return Collections.unmodifiableList(copy);
    }

    private static List<RequestParameter<?>> scopedCopy(
            List<RequestParameter<?>> values,
            RequestParameterScope scope,
            String name
    ) {
        Objects.requireNonNull(values, name);
        List<RequestParameter<?>> copy = new ArrayList<>(values.size());
        for (RequestParameter<?> parameter : values) {
            Objects.requireNonNull(parameter, name + " entry");
            if (parameter.scope() != scope) {
                throw new IllegalArgumentException(
                        parameter.keyName() + " belongs to " + parameter.scope()
                                + " rather than " + scope
                );
            }
            copy.add(parameter);
        }
        return Collections.unmodifiableList(copy);
    }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
