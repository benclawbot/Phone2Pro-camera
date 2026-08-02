package com.phone2pro.diagnostics;

enum DiagnosticProfile {
    STATIC_AUDIT(
            "static-hardware-vendor",
            "Static hardware & vendor audit",
            "Run anytime. Finds public/hidden camera IDs, Camera2 capabilities, vendor metadata keys, sensors, codecs, memory, and thermal state.",
            false,
            0
    ),
    NIGHT_LOW_LIGHT(
            "night-low-light",
            "Night / low-light capture audit",
            "Run after dark. Tests accepted zoom routes, capture metadata, exposure, OIS, low-light lens selection, and an 8-frame burst.",
            true,
            1500
    ),
    DAYLIGHT_LENS_ROUTING(
            "daylight-lens-routing",
            "Daylight lens-routing audit",
            "Run outdoors in good light. Tests 0.6x, 1x, 2x, 4x, 10x, and 20x requests, sensor switching metadata, sample geometry, and an 8-frame burst.",
            true,
            800
    );

    final String fileLabel;
    final String buttonLabel;
    final String description;
    final boolean capturesImages;
    final long settleMillis;

    DiagnosticProfile(
            String fileLabel,
            String buttonLabel,
            String description,
            boolean capturesImages,
            long settleMillis
    ) {
        this.fileLabel = fileLabel;
        this.buttonLabel = buttonLabel;
        this.description = description;
        this.capturesImages = capturesImages;
        this.settleMillis = settleMillis;
    }
}
