package com.phone2pro.diagnostics;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class ReportStorage {
    private static final String REPORT_FOLDER =
            Environment.DIRECTORY_DOWNLOADS + "/Phone2Pro Diagnostics";

    private ReportStorage() {
    }

    static Uri saveJsonReport(Context context, String profileLabel, String json) throws IOException {
        return save(
                context,
                MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                "phone2pro-" + profileLabel + "-" + timestamp() + ".json",
                "application/json",
                REPORT_FOLDER,
                json.getBytes(StandardCharsets.UTF_8)
        );
    }

    private static Uri save(
            Context context,
            Uri collection,
            String displayName,
            String mimeType,
            String relativePath,
            byte[] bytes
    ) throws IOException {
        ContentResolver resolver = context.getContentResolver();
        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, displayName);
        values.put(MediaStore.MediaColumns.MIME_TYPE, mimeType);
        values.put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath);
        values.put(MediaStore.MediaColumns.IS_PENDING, 1);

        Uri uri = resolver.insert(collection, values);
        if (uri == null) {
            throw new IOException("MediaStore refused to create " + displayName);
        }

        boolean complete = false;
        try (OutputStream stream = resolver.openOutputStream(uri, "w")) {
            if (stream == null) {
                throw new IOException("Unable to open output stream for " + displayName);
            }
            stream.write(bytes);
            complete = true;
        } finally {
            if (!complete) {
                resolver.delete(uri, null, null);
            }
        }

        values.clear();
        values.put(MediaStore.MediaColumns.IS_PENDING, 0);
        resolver.update(uri, values, null, null);
        return uri;
    }

    private static String timestamp() {
        return new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(new Date());
    }
}
