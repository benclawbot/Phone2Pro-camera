package com.phone2pro.diagnostics;

import org.json.JSONArray;
import org.json.JSONObject;

final class RouteClassificationDiagnostics {
    private RouteClassificationDiagnostics() {
    }

    static JSONObject classify(
            JSONObject platform,
            JSONObject cameraOpen,
            JSONObject captureTrace,
            JSONObject vendorTags
    ) {
        JSONObject result = new JSONObject();
        JSONArray evidence = new JSONArray();
        JSONArray openableNonPublic = new JSONArray();
        JSONArray systemOnlyCandidates = new JSONArray();

        JSONArray probes = cameraOpen.optJSONArray("probes");
        if (probes != null) {
            for (int index = 0; index < probes.length(); index++) {
                JSONObject probe = probes.optJSONObject(index);
                if (probe == null) {
                    continue;
                }
                String id = probe.optString("cameraId", "");
                boolean publicId = probe.optBoolean("publiclyListed", false);
                String outcome = probe.optString("openOutcome", "");
                String errorText = probe.toString().toLowerCase();
                if (!publicId && "opened".equals(outcome)) {
                    openableNonPublic.put(id);
                }
                if (!publicId && (errorText.contains("system only")
                        || errorText.contains("system-only")
                        || errorText.contains("system_camera"))) {
                    systemOnlyCandidates.put(id);
                }
            }
        }

        JSONObject traceResult = captureTrace
                .optJSONObject("singleCapture");
        JSONObject resultMetadata = traceResult == null
                ? null
                : traceResult.optJSONObject("result");
        JSONArray resultKeys = resultMetadata == null
                ? null
                : resultMetadata.optJSONArray("keys");
        Object activePhysicalId = null;
        Object focalLength = null;
        if (resultKeys != null) {
            for (int index = 0; index < resultKeys.length(); index++) {
                JSONObject key = resultKeys.optJSONObject(index);
                if (key == null) {
                    continue;
                }
                String name = key.optString("name", "");
                if ("android.logicalMultiCamera.activePhysicalId".equals(name)) {
                    activePhysicalId = key.opt("value");
                } else if ("android.lens.focalLength".equals(name)) {
                    focalLength = key.opt("value");
                }
            }
        }

        int vendorCount = countVendorKeys(vendorTags);
        CameraJson.put(result, "openableNonPublicIds", openableNonPublic);
        CameraJson.put(result, "systemOnlyCandidateIds", systemOnlyCandidates);
        CameraJson.put(result, "activePhysicalIdInPublicCapture",
                activePhysicalId == null ? JSONObject.NULL : activePhysicalId);
        CameraJson.put(result, "focalLengthInPublicCapture",
                focalLength == null ? JSONObject.NULL : focalLength);
        CameraJson.put(result, "vendorKeyCount", vendorCount);

        String classification;
        int confidence;
        String reason;
        String nextAction;

        if (openableNonPublic.length() > 0) {
            classification = "non-public-camera-openable-by-diagnostics-app";
            confidence = 4;
            reason = "At least one camera ID absent from the public list opened successfully for the ordinary diagnostics package.";
            nextAction = "Capture characteristics and controlled optical outputs from each openable non-public ID, then map them to physical sensors.";
            evidence.put("A non-public CameraDevice reached onOpened().");
        } else if (systemOnlyCandidates.length() > 0) {
            classification = "system-camera-boundary-confirmed";
            confidence = 4;
            reason = "CameraService recognizes non-public IDs as system-only while rejecting the ordinary diagnostics caller.";
            nextAction = "Trace Nothing Camera package grants and stock CameraManager.openCamera calls. If stock opens these IDs, implement separate ordinary and privileged backends.";
            evidence.put("Non-public IDs were recognized but rejected with system-only language.");
        } else if (activePhysicalId != null && activePhysicalId != JSONObject.NULL) {
            classification = "public-logical-camera-active-physical-id-observed";
            confidence = 3;
            reason = "The public capture result reports an active physical camera ID.";
            nextAction = "Run controlled zoom and session-parameter experiments and verify optical outputs before treating the reported physical ID as selectable.";
            evidence.put("android.logicalMultiCamera.activePhysicalId was non-null.");
        } else if (vendorCount > 0) {
            classification = "public-camera-with-vendor-surface";
            confidence = 3;
            reason = "The ordinary application can enumerate a substantial vendor metadata surface, but this run did not establish auxiliary optical routing.";
            nextAction = "Compare exact stock Expert request/session values against this inventory and test only evidence-backed route discriminators.";
            evidence.put("Vendor characteristics, requests, results or session keys were visible.");
        } else {
            classification = "public-camera-only";
            confidence = 2;
            reason = "Only the public camera route was observed and no auxiliary routing discriminator was captured.";
            nextAction = "Collect stock-camera Java/native traces and provider metadata before concluding where auxiliary routing occurs.";
        }

        CameraJson.put(result, "classification", classification);
        CameraJson.put(result, "confidence", confidence);
        CameraJson.put(result, "reason", reason);
        CameraJson.put(result, "nextAction", nextAction);
        CameraJson.put(result, "evidence", evidence);
        CameraJson.put(result, "scope",
                "This classifier describes what the ordinary diagnostics application observed. It does not infer the stock app's internal route without stock-process traces.");
        CameraJson.put(result, "platformSchemaVersion", platform.optInt("schemaVersion", -1));
        return result;
    }

    private static int countVendorKeys(JSONObject vendorTags) {
        int count = 0;
        JSONArray cameras = vendorTags.optJSONArray("cameras");
        if (cameras == null) {
            return count;
        }
        for (int cameraIndex = 0; cameraIndex < cameras.length(); cameraIndex++) {
            JSONObject camera = cameras.optJSONObject(cameraIndex);
            if (camera == null) {
                continue;
            }
            count += countVendor(camera.optJSONArray("characteristics"));
            count += countVendor(camera.optJSONArray("requestKeys"));
            count += countVendor(camera.optJSONArray("resultKeys"));
            count += countVendor(camera.optJSONArray("sessionKeys"));
            count += countVendor(camera.optJSONArray("physicalRequestKeys"));
        }
        return count;
    }

    private static int countVendor(JSONArray entries) {
        if (entries == null) {
            return 0;
        }
        int count = 0;
        for (int index = 0; index < entries.length(); index++) {
            JSONObject entry = entries.optJSONObject(index);
            if (entry != null && entry.optBoolean("vendor", false)) {
                count++;
            }
        }
        return count;
    }
}
