package com.phone2pro.camera.imaging;

/** Image defects that trigger conservative rendering fallbacks. */
public enum ArtifactType {
    MISALIGNMENT,
    GHOSTING,
    HALO,
    RINGING,
    HIGHLIGHT_CLIPPING,
    COLOR_SHIFT,
    NOISE_AMPLIFICATION,
    SYNTHETIC_TEXTURE
}
