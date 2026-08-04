package com.phone2pro.camera.core;

/** Product-quality constraints that remain active across every capture mode. */
public enum RenderingConstraint {
    PRESERVE_NATURAL_COLOR,
    PROTECT_HIGHLIGHTS,
    PREFER_DEGHOSTING_OVER_DETAIL,
    CONSERVATIVE_SHARPENING,
    AVOID_SYNTHETIC_TEXTURE
}
