package com.phone2pro.camera.diagnostics;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.core.RouteRendering;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Complete non-content report for one capture transaction. */
public final class CaptureDiagnosticReport {
    private final String reportId;
    private final String buildFingerprint;
    private final String appVersion;
    private final String backendId;
    private final OpticalRoute route;
    private final RouteMechanism mechanism;
    private final RouteRendering rendering;
    private final CaptureProfile captureProfile;
    private final List<StreamConfigurationReport> streams;
    private final List<ConfigurationEntryReport> configuration;
    private final TimingReport timings;
    private final UserFacingError error;

    public CaptureDiagnosticReport(
            String reportId,
            String buildFingerprint,
            String appVersion,
            String backendId,
            OpticalRoute route,
            RouteMechanism mechanism,
            RouteRendering rendering,
            CaptureProfile captureProfile,
            List<StreamConfigurationReport> streams,
            List<ConfigurationEntryReport> configuration,
            TimingReport timings,
            UserFacingError error
    ) {
        this.reportId = requireText(reportId, "reportId");
        this.buildFingerprint = requireText(buildFingerprint, "buildFingerprint");
        this.appVersion = requireText(appVersion, "appVersion");
        this.backendId = requireText(backendId, "backendId");
        this.route = Objects.requireNonNull(route, "route");
        this.mechanism = Objects.requireNonNull(mechanism, "mechanism");
        this.rendering = Objects.requireNonNull(rendering, "rendering");
        this.captureProfile = Objects.requireNonNull(captureProfile, "captureProfile");
        this.streams = immutableCopy(streams, "streams");
        this.configuration = immutableCopy(configuration, "configuration");
        this.timings = Objects.requireNonNull(timings, "timings");
        this.error = error;
        if (rendering == RouteRendering.UNAVAILABLE && error == null) {
            throw new IllegalArgumentException("unavailable capture report requires an error");
        }
    }

    public String reportId() { return reportId; }
    public String buildFingerprint() { return buildFingerprint; }
    public String appVersion() { return appVersion; }
    public String backendId() { return backendId; }
    public OpticalRoute route() { return route; }
    public RouteMechanism mechanism() { return mechanism; }
    public RouteRendering rendering() { return rendering; }
    public CaptureProfile captureProfile() { return captureProfile; }
    public List<StreamConfigurationReport> streams() { return streams; }
    public List<ConfigurationEntryReport> configuration() { return configuration; }
    public TimingReport timings() { return timings; }
    public Optional<UserFacingError> error() { return Optional.ofNullable(error); }

    /** Reports intentionally contain no image, thumbnail, file path or content URI field. */
    public boolean containsUserPixels() { return false; }

    private static <T> List<T> immutableCopy(List<T> values, String name) {
        Objects.requireNonNull(values, name);
        List<T> copy = new ArrayList<>(values.size());
        for (T value : values) {
            copy.add(Objects.requireNonNull(value, name + " entry"));
        }
        return Collections.unmodifiableList(copy);
    }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
