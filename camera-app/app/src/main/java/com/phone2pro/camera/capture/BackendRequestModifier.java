package com.phone2pro.camera.capture;

import java.util.List;

/** Isolated portable boundary for backend-specific still-request parameters. */
public interface BackendRequestModifier {
    String modifierId();

    /**
     * Return the complete modified parameter list. Implementations must preserve STILL scope and
     * must not emit vendor keys outside a vendor-adapter session.
     */
    List<RequestParameter<?>> modify(
            CaptureRequestContext context,
            List<RequestParameter<?>> currentParameters
    );
}
