package com.phone2pro.diagnostics;

import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Size;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class MediaInterop {
    private static final String PREFS = "media_interop";
    private static final String KEY_LATEST_URI = "latest_uri";
    private static final String PHOTO_ALBUM = Environment.DIRECTORY_DCIM + "/Phone2Pro Camera";
    private static final String REPORT_FOLDER = Environment.DIRECTORY_DOWNLOADS + "/Phone2Pro Diagnostics";

    private MediaInterop() {
    }

    static Uri saveJpeg(Context context, Bitmap bitmap) throws IOException {
        ContentResolver resolver = context.getContentResolver();
        String stamp = new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(new Date());
        ContentValues values = new ContentValues();
        values.put(MediaStore.Images.Media.DISPLAY_NAME, "P2P_" + stamp + ".jpg");
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
        values.put(MediaStore.Images.Media.RELATIVE_PATH, PHOTO_ALBUM);
        values.put(MediaStore.Images.Media.DATE_TAKEN, System.currentTimeMillis());
        values.put(MediaStore.Images.Media.IS_PENDING, 1);

        Uri collection = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
        Uri uri = resolver.insert(collection, values);
        if (uri == null) {
            throw new IOException("MediaStore refused to create the JPEG entry");
        }

        boolean complete = false;
        try (OutputStream stream = resolver.openOutputStream(uri, "w")) {
            if (stream == null || !bitmap.compress(Bitmap.CompressFormat.JPEG, 95, stream)) {
                throw new IOException("Unable to encode the JPEG");
            }
            complete = true;
        } finally {
            if (!complete) {
                resolver.delete(uri, null, null);
            }
        }

        values.clear();
        values.put(MediaStore.Images.Media.IS_PENDING, 0);
        resolver.update(uri, values, null, null);
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_LATEST_URI, uri.toString())
                .apply();
        return uri;
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

    static Uri getLatestPhotoUri(Context context) {
        String raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(KEY_LATEST_URI, null);
        return raw == null ? null : Uri.parse(raw);
    }

    static Bitmap loadThumbnail(Context context, Uri uri, int pixels) throws IOException {
        return context.getContentResolver().loadThumbnail(uri, new Size(pixels, pixels), null);
    }

    static void clearLatestPhoto(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .remove(KEY_LATEST_URI)
                .apply();
    }

    static void openInDefaultViewer(Context context, Uri uri) {
        Intent view = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "image/jpeg")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        view.setClipData(ClipData.newRawUri("Phone2Pro photo", uri));
        try {
            context.startActivity(view);
        } catch (ActivityNotFoundException firstFailure) {
            Intent gallery = new Intent(Intent.ACTION_VIEW)
                    .setDataAndType(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, "image/*");
            context.startActivity(gallery);
        }
    }
}
