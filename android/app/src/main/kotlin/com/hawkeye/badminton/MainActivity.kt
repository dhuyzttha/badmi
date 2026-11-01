package com.hawkeye.badminton

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.hawkeye.badminton/file_picker"
    private var pendingResult: MethodChannel.Result? = null

    // Modern Android Photo Picker (Backwards-compatible down to Android 4.4 via Google Play Services)
    private lateinit var pickMediaLauncher: ActivityResultLauncher<PickVisualMediaRequest>
    // Fallback Storage Access Framework (SAF)
    private lateinit var safPickerLauncher: ActivityResultLauncher<Intent>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Photo Picker Launcher (Safest for Android 13+ / MIUI / HyperOS)
        pickMediaLauncher = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            handleSelectedUri(uri)
        }

        // 2. Storage Access Framework Fallback
        safPickerLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK && result.data != null) {
                val uri = result.data?.data
                handleSelectedUri(uri)
            } else {
                pendingResult?.success(null)
                pendingResult = null
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "pickVideoSafe" -> {
                    if (pendingResult != null) {
                        result.error("BUSY", "Another file picking session is active", null)
                        return@setMethodCallHandler
                    }
                    pendingResult = result
                    launchSafeVideoPicker()
                }
                "getCacheDirectory" -> {
                    result.success(applicationContext.cacheDir.absolutePath)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }

    private fun launchSafeVideoPicker() {
        try {
            // Android 13+ or devices with PhotoPicker extension
            if (ActivityResultContracts.PickVisualMedia.isPhotoPickerAvailable(this)) {
                pickMediaLauncher.launch(
                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                )
            } else {
                // Storage Access Framework (SAF) - avoids MIUI intent crashes
                val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "video/*"
                    putExtra(Intent.EXTRA_LOCAL_ONLY, true)
                }
                safPickerLauncher.launch(intent)
            }
        } catch (e: Exception) {
            // Extreme fallback if manufacturer stripped picker
            try {
                val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                    type = "video/*"
                }
                safPickerLauncher.launch(intent)
            } catch (fallbackEx: Exception) {
                pendingResult?.error("PICKER_ERROR", fallbackEx.localizedMessage, null)
                pendingResult = null
            }
        }
    }

    /**
     * Copies the content URI stream directly into context.cacheDir.
     * This avoids FileUriExposedException and MIUI / HyperOS Scoped Storage Permission Denial!
     */
    private fun handleSelectedUri(uri: Uri?) {
        if (uri == null) {
            pendingResult?.success(null)
            pendingResult = null
            return
        }

        val callback = pendingResult
        pendingResult = null

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val originalName = queryFileName(uri) ?: "badminton_video_${System.currentTimeMillis()}.mp4"
                val safeFileName = "cached_" + originalName.replace("[^a-zA-Z0-9._-]".toRegex(), "_")
                val targetFile = File(applicationContext.cacheDir, safeFileName)

                // Copy stream in buffered 64KB chunks
                applicationContext.contentResolver.openInputStream(uri)?.use { input ->
                    FileOutputStream(targetFile).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        var bytesRead: Int
                        while (input.read(buffer).also { bytesRead = it } != -1) {
                            output.write(buffer, 0, bytesRead)
                        }
                        output.flush()
                    }
                } ?: throw IllegalStateException("Failed to open input stream for URI: $uri")

                withContext(Dispatchers.Main) {
                    callback?.success(targetFile.absolutePath)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    callback?.error("COPY_FAILED", "Failed to cache video file: ${e.message}", null)
                }
            }
        }
    }

    private fun queryFileName(uri: Uri): String? {
        var name: String? = null
        try {
            contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (nameIndex != -1 && cursor.moveToFirst()) {
                    name = cursor.getString(nameIndex)
                }
            }
        } catch (_: Exception) {}
        return name
    }
}
