package com.phone2pro.camera.capture;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Builds ordered still bursts and validates every backend modifier output. */
public final class CaptureRequestPlanner {
    public StillBurstPlan planStillBurst(
            CaptureSessionPlan sessionPlan,
            String captureId,
            int frameCount,
            CaptureRequestTemplate template,
            List<BackendRequestModifier> modifiers,
            CaptureCancellation cancellation
    ) {
        Objects.requireNonNull(sessionPlan, "sessionPlan");
        Objects.requireNonNull(template, "template");
        Objects.requireNonNull(modifiers, "modifiers");
        Objects.requireNonNull(cancellation, "cancellation");
        if (frameCount <= 0 || frameCount > 64) {
            throw new IllegalArgumentException("frameCount must be between 1 and 64");
        }
        if (template == CaptureRequestTemplate.PREVIEW
                || template == CaptureRequestTemplate.VIDEO_RECORD) {
            throw new IllegalArgumentException("still burst requires a still-capable template");
        }

        List<CaptureFrameRequest> frames = new ArrayList<>(frameCount);
        for (int index = 0; index < frameCount; index++) {
            cancellation.throwIfCancelled();
            String requestId = captureId + ":" + index;
            CaptureRequestContext context = new CaptureRequestContext(
                    sessionPlan,
                    captureId,
                    requestId,
                    index,
                    template
            );
            List<RequestParameter<?>> parameters = new ArrayList<>(
                    sessionPlan.stillParameters()
            );
            for (BackendRequestModifier modifier : modifiers) {
                cancellation.throwIfCancelled();
                Objects.requireNonNull(modifier, "modifier");
                if (modifier.modifierId() == null || modifier.modifierId().trim().isEmpty()) {
                    throw new IllegalArgumentException("modifierId must not be blank");
                }
                List<RequestParameter<?>> modified = modifier.modify(
                        context,
                        Collections.unmodifiableList(parameters)
                );
                parameters = validatedParameters(sessionPlan, modified, modifier.modifierId());
            }
            parameters = validatedParameters(sessionPlan, parameters, "base plan");
            frames.add(new CaptureFrameRequest(index, requestId, template, parameters));
        }
        return new StillBurstPlan(captureId, sessionPlan.generation(), frames);
    }

    private static List<RequestParameter<?>> validatedParameters(
            CaptureSessionPlan sessionPlan,
            List<RequestParameter<?>> parameters,
            String source
    ) {
        Objects.requireNonNull(parameters, source + " parameters");
        List<RequestParameter<?>> copy = new ArrayList<>(parameters.size());
        Set<String> keys = new HashSet<>();
        for (RequestParameter<?> parameter : parameters) {
            Objects.requireNonNull(parameter, source + " parameter");
            if (parameter.scope() != RequestParameterScope.STILL) {
                throw new IllegalArgumentException(
                        source + " emitted non-STILL parameter " + parameter.keyName()
                );
            }
            if (!keys.add(parameter.keyName())) {
                throw new IllegalArgumentException(
                        source + " emitted duplicate parameter " + parameter.keyName()
                );
            }
            if (sessionPlan.binderKind() != SessionBinderKind.CAMERA2_VENDOR_ADAPTER
                    && isVendorKey(parameter.keyName())) {
                throw new IllegalArgumentException(
                        source + " emitted vendor key outside vendor adapter"
                );
            }
            copy.add(parameter);
        }
        return copy;
    }

    private static boolean isVendorKey(String keyName) {
        return keyName.startsWith("com.mediatek.") || keyName.startsWith("com.nothing.");
    }
}
