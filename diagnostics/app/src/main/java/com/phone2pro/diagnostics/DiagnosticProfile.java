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
            "Run outdoors in good light. Probes the public Camera2 route around 2x, records effective crop and lens metadata, and benchmarks bursts at 1x and 2x.",
            true,
            800
    ),
    OFFICIAL_EXPERT_LENS_ROUTING(
            "official-expert-lens-routing",
            "Official camera Expert 0.6x / 1x / 2x audit",
            "Opens the full official camera. In Expert mode, take exactly one photo at 0.6x, then 1x, then 2x, and return. The app associates each stock-camera image with that ordered lens setting and records EXIF and routing evidence.",
            false,
            0
    ),
    OFFICIAL_EXPERT_DIRECT_ID_LAUNCH(
            "official-expert-direct-id-launch",
            "Official Expert direct ID 2 / 0 / 3 launch audit",
            "Launches the official camera into Expert mode three times while requesting camera IDs 2, 0 and 3. Take one photo after each launch without changing the lens; EXIF verifies whether each requested ultrawide, main or telephoto route was honored.",
            false,
            0
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
