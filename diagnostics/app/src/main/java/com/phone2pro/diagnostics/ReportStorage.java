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

    static Uri saveJsonReport(Context context, String json) throws IOException {
        ContentResolver resolver = context.getContentResolver();
        String stamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());

        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, "phone2pro-capabilities-" + stamp + ".json");
        values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
        values.put(MediaStore.Downloads.RELATIVE_PATH, REPORT_FOLDER);
        values.put(MediaStore.Downloads.IS_PENDING, 1);

        Uri collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
        Uri uri = resolver.insert(collection, values);
        if (uri == null) {
            throw new IOException("MediaStore refused to create the report entry");
        }

        boolean complete = false;
        try (OutputStream stream = resolver.openOutputStream(uri, "w")) {
            if (stream == null) {
                throw new IOException("Unable to open the report output stream");
            }
            stream.write(json.getBytes(StandardCharsets.UTF_8));
            complete = true;
        } finally {
            if (!complete) {
                resolver.delete(uri, null, null);
            }
        }

        values.clear();
        values.put(MediaStore.Downloads.IS_PENDING, 0);
        resolver.update(uri, values, null, null);
        return uri;
    }
}
