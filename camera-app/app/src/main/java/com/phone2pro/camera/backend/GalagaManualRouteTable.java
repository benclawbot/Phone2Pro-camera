package com.phone2pro.camera.backend;

import com.phone2pro.camera.core.OpticalRoute;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Galaga manual/Expert endpoint table recovered from Nothing Camera 16.1.01.93.20.
 *
 * <p>This table records static binary evidence only. It does not grant access to system camera
 * endpoints and must always be combined with an independent authorization probe.</p>
 */
public final class GalagaManualRouteTable {
    public static final String ULTRAWIDE_CAMERA_ID = "2";
    public static final String WIDE_CAMERA_ID = "0";
    public static final String TELEPHOTO_CAMERA_ID = "3";

    private final Map<OpticalRoute, String> endpoints;

    public GalagaManualRouteTable() {
        Map<OpticalRoute, String> discovered = new LinkedHashMap<>();
        discovered.put(OpticalRoute.ULTRAWIDE, ULTRAWIDE_CAMERA_ID);
        discovered.put(OpticalRoute.MAIN, WIDE_CAMERA_ID);
        discovered.put(OpticalRoute.TELEPHOTO, TELEPHOTO_CAMERA_ID);
        endpoints = Collections.unmodifiableMap(discovered);
    }

    public Optional<String> cameraIdFor(OpticalRoute route) {
        return Optional.ofNullable(endpoints.get(route));
    }

    public Map<OpticalRoute, String> endpoints() {
        return endpoints;
    }
}
