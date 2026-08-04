package com.phone2pro.camera.capture;

import java.util.Collections;
import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Diff between active and requested session plans. */
public final class SessionRecreationDecision {
    private final Set<SessionRecreationReason> reasons;

    private SessionRecreationDecision(Set<SessionRecreationReason> reasons) {
        this.reasons = Collections.unmodifiableSet(
                reasons.isEmpty()
                        ? EnumSet.of(SessionRecreationReason.NONE)
                        : EnumSet.copyOf(reasons)
        );
    }

    public static SessionRecreationDecision compare(
            CaptureSessionPlan active,
            CaptureSessionPlan requested
    ) {
        Objects.requireNonNull(active, "active");
        Objects.requireNonNull(requested, "requested");
        EnumSet<SessionRecreationReason> reasons = EnumSet.noneOf(
                SessionRecreationReason.class
        );
        if (!active.backendId().equals(requested.backendId())) {
            reasons.add(SessionRecreationReason.BACKEND_CHANGED);
        }
        if (active.binderKind() != requested.binderKind()) {
            reasons.add(SessionRecreationReason.BINDER_CHANGED);
        }
        if (!active.endpoint().cameraId().equals(requested.endpoint().cameraId())
                || active.endpoint().mechanism() != requested.endpoint().mechanism()) {
            reasons.add(SessionRecreationReason.ENDPOINT_CHANGED);
        }
        if (!active.route().equals(requested.route())) {
            reasons.add(SessionRecreationReason.ROUTE_CHANGED);
        }
        if (!active.streams().equals(requested.streams())) {
            reasons.add(SessionRecreationReason.STREAMS_CHANGED);
        }
        if (!parametersEqual(active.sessionParameters(), requested.sessionParameters())) {
            reasons.add(SessionRecreationReason.SESSION_PARAMETERS_CHANGED);
        }
        if (active.metadataTimestampDomain() != requested.metadataTimestampDomain()) {
            reasons.add(SessionRecreationReason.TIMESTAMP_DOMAIN_CHANGED);
        }
        return new SessionRecreationDecision(reasons);
    }

    public static SessionRecreationDecision transientRecovery() {
        return new SessionRecreationDecision(
                EnumSet.of(SessionRecreationReason.TRANSIENT_RECOVERY)
        );
    }

    public Set<SessionRecreationReason> reasons() { return reasons; }

    public boolean recreateRequired() {
        return !reasons.contains(SessionRecreationReason.NONE);
    }

    private static boolean parametersEqual(
            List<RequestParameter<?>> left,
            List<RequestParameter<?>> right
    ) {
        if (left.size() != right.size()) {
            return false;
        }
        for (int index = 0; index < left.size(); index++) {
            RequestParameter<?> a = left.get(index);
            RequestParameter<?> b = right.get(index);
            if (!a.keyName().equals(b.keyName())
                    || !a.valueType().equals(b.valueType())
                    || !a.value().equals(b.value())
                    || a.scope() != b.scope()) {
                return false;
            }
        }
        return true;
    }
}
