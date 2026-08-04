package com.phone2pro.camera.ui;

import com.phone2pro.camera.core.RouteDecision;
import com.phone2pro.camera.core.RouteRendering;

import java.util.Locale;
import java.util.Objects;

/** User-facing route label derived from typed backend evidence. */
public final class RoutePresentation {
    private final String controlLabel;
    private final String renderingLabel;
    private final String accessibilityLabel;
    private final boolean available;
    private final RouteRendering rendering;

    private RoutePresentation(
            String controlLabel,
            String renderingLabel,
            String accessibilityLabel,
            boolean available,
            RouteRendering rendering
    ) {
        this.controlLabel = Objects.requireNonNull(controlLabel, "controlLabel");
        this.renderingLabel = Objects.requireNonNull(renderingLabel, "renderingLabel");
        this.accessibilityLabel = Objects.requireNonNull(
                accessibilityLabel,
                "accessibilityLabel"
        );
        this.available = available;
        this.rendering = Objects.requireNonNull(rendering, "rendering");
        if (controlLabel.isEmpty() || renderingLabel.isEmpty() || accessibilityLabel.isEmpty()) {
            throw new IllegalArgumentException("route labels must not be empty");
        }
    }

    public static RoutePresentation from(RouteDecision decision) {
        Objects.requireNonNull(decision, "decision");
        boolean available = decision.support().isAvailable();
        RouteRendering rendering = decision.support().rendering();
        String renderingLabel;
        switch (rendering) {
            case OPTICAL:
                renderingLabel = "Optical";
                break;
            case IN_SENSOR:
                renderingLabel = "In-sensor";
                break;
            case DIGITAL:
                renderingLabel = "Digital";
                break;
            case UNAVAILABLE:
                renderingLabel = "Unavailable";
                break;
            default:
                throw new IllegalStateException("Unhandled rendering: " + rendering);
        }
        if (available && rendering == RouteRendering.UNAVAILABLE) {
            throw new IllegalArgumentException("available route cannot render as unavailable");
        }
        if (!available && rendering != RouteRendering.UNAVAILABLE) {
            throw new IllegalArgumentException("unavailable route must render as unavailable");
        }
        String route = decision.route().label();
        String control = route + "\n" + renderingLabel;
        String accessibility = String.format(
                Locale.US,
                "%s route, %s. %s",
                route,
                renderingLabel.toLowerCase(Locale.US),
                decision.support().reason()
        );
        return new RoutePresentation(
                control,
                renderingLabel,
                accessibility,
                available,
                rendering
        );
    }

    public String controlLabel() { return controlLabel; }
    public String renderingLabel() { return renderingLabel; }
    public String accessibilityLabel() { return accessibilityLabel; }
    public boolean available() { return available; }
    public RouteRendering rendering() { return rendering; }
}
