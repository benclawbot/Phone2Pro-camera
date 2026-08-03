package com.phone2pro.diagnostics;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

final class FullSpecificationRunner {
    interface ProgressListener {
        void onProgress(String message);
    }

    private final Context context;
    private final ProgressListener progressListener;

    FullSpecificationRunner(Context context, ProgressListener progressListener) {
        this.context = context.getApplicationContext();
        this.progressListener = progressListener;
    }

    JSONObject run() throws Exception {
        long started = SystemClock.elapsedRealtime();
        progress("Collecting public Camera2 capabilities…");
        JSONObject root = new PlatformCapabilityReporter(context).build();
        root.put("schemaVersion", 3);
        root.put("selectedProfile", CameraJson.object(
                "id", "full-camera-platform-specification",
                "label", "Full camera platform specification",
                "capturesOrPersistsImages", false,
                "networkUsed", false
        ));
        root.put("diagnosticsApp", appInfo());

        JSONObject specification = new JSONObject();
        specification.put("schemaVersion", 1);
        specification.put("startedAtElapsedRealtimeMillis", started);
        specification.put("privacy", CameraJson.object(
                "allProcessingOnDevice", true,
                "networkAccessRequired", false,
                "photographsPersisted", false,
                "rawFramePayloadsIncludedInJson", false,
                "note", "The capture trace drains YUV buffers and records metadata only."
        ));

        JSONObject openModule = module("cameraOpen", () -> {
            progress("Probing public, hidden and system-only camera IDs…");
            try (CameraOpenDiagnostics diagnostics = new CameraOpenDiagnostics(context)) {
                return diagnostics.run();
            }
        });
        specification.put("cameraOpen", openModule);

        JSONObject sessionModule = module("sessionMatrix", () -> {
            progress("Testing public stream and capture-session combinations…");
            try (SessionMatrixDiagnostics diagnostics =
                         new SessionMatrixDiagnostics(context)) {
                return diagnostics.run();
            }
        });
        specification.put("sessionMatrix", sessionModule);

        JSONObject vendorModule = module("vendorMetadata", () -> {
            progress("Inventorying MediaTek, Nothing and Android metadata keys…");
            try (VendorTagDiagnostics diagnostics = new VendorTagDiagnostics(context)) {
                return diagnostics.run();
            }
        });
        specification.put("vendorMetadata", vendorModule);

        JSONObject sensorModule = module("sensorProfiles", () -> {
            progress("Collecting sensor calibration, timing and optical metadata…");
            return new SensorProfileDiagnostics(context).run();
        });
        specification.put("sensorProfiles", sensorModule);

        JSONObject captureModule = module("captureTrace", () -> {
            progress("Recording one metadata-complete capture and an 8-frame YUV burst…");
            try (CaptureTraceDiagnostics diagnostics =
                         new CaptureTraceDiagnostics(context)) {
                return diagnostics.run();
            }
        });
        specification.put("captureTrace", captureModule);

        progress("Classifying the observed routing and privilege boundary…");
        JSONObject route = RouteClassificationDiagnostics.classify(
                root,
                data(openModule),
                data(captureModule),
                data(vendorModule)
        );
        specification.put("routeClassification", route);
        specification.put("moduleSummary", summarizeModules(specification));
        specification.put(
                "finishedAtElapsedRealtimeMillis",
                SystemClock.elapsedRealtime()
        );
        specification.put(
                "durationMillis",
                SystemClock.elapsedRealtime() - started
        );
        root.put("fullCameraPlatformSpecification", specification);
        progress("Saving the complete JSON specification…");
        return root;
    }

    private JSONObject module(String name, CheckedSupplier supplier) {
        long started = SystemClock.elapsedRealtime();
        JSONObject wrapper = new JSONObject();
        CameraJson.put(wrapper, "name", name);
        CameraJson.put(wrapper, "startedAtElapsedRealtimeMillis", started);
        try {
            JSONObject data = supplier.get();
            CameraJson.put(wrapper, "status", "complete");
            CameraJson.put(wrapper, "data", data);
        } catch (Throwable error) {
            CameraJson.put(wrapper, "status", "error");
            CameraJson.put(wrapper, "error", CameraJson.error(error));
        }
        CameraJson.put(
                wrapper,
                "durationMillis",
                SystemClock.elapsedRealtime() - started
        );
        return wrapper;
    }

    @SuppressWarnings("deprecation")
    private JSONObject appInfo() {
        JSONObject result = new JSONObject();
        CameraJson.put(result, "packageName", context.getPackageName());
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(
                    context.getPackageName(),
                    0
            );
            CameraJson.put(result, "versionName", info.versionName);
            CameraJson.put(result, "longVersionCode", info.getLongVersionCode());
            CameraJson.put(result, "firstInstallTime", info.firstInstallTime);
            CameraJson.put(result, "lastUpdateTime", info.lastUpdateTime);
        } catch (Throwable error) {
            CameraJson.put(result, "packageInfoError", CameraJson.error(error));
        }
        return result;
    }

    private static JSONObject data(JSONObject wrapper) {
        JSONObject data = wrapper.optJSONObject("data");
        return data == null ? new JSONObject() : data;
    }

    private static JSONArray summarizeModules(JSONObject specification) {
        JSONArray summary = new JSONArray();
        String[] names = {
                "cameraOpen",
                "sessionMatrix",
                "vendorMetadata",
                "sensorProfiles",
                "captureTrace"
        };
        for (String name : names) {
            JSONObject module = specification.optJSONObject(name);
            if (module == null) {
                continue;
            }
            summary.put(CameraJson.object(
                    "name", name,
                    "status", module.optString("status", "missing"),
                    "durationMillis", module.optLong("durationMillis", -1),
                    "error", module.opt("error") == null
                            ? JSONObject.NULL
                            : module.opt("error")
            ));
        }
        return summary;
    }

    private void progress(String message) {
        if (progressListener != null) {
            progressListener.onProgress(message);
        }
    }

    @FunctionalInterface
    private interface CheckedSupplier {
        JSONObject get() throws Exception;
    }
}
