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
            "Run outdoors in good light. Probes system-only camera IDs, tests dense zoom steps around 2x plus 0.6x to 20x, derives the real crop/zoom path, and benchmarks 8-frame bursts at 1x and 2x.",
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
