"""
mediastore_saver.py - başqa layihələrdə import edib istifadə üçün modul.

Android 10+ üçün MediaStore ilə mp4/mp3 saxlayır.
- İcazə (permission) lazım deyil
- Kivy və Flet-dən asılı deyil (yalnız pyjnius)
- mp4 -> Movies, mp3 -> Music

İstifadə:
    from mediastore_saver import save_media, MediaStoreError

    try:
        res = save_media("/yol/video.mp4")
        print(res)            # {'uri': 'content://...', 'folder': 'Movies', 'name': 'video.mp4'}
    except MediaStoreError as e:
        print(e)

pyproject.toml / requirements:  pyjnius
"""

import os

__all__ = ["save_media", "is_supported", "MediaStoreError"]

# uzantı -> (MIME, kolleksiya, Environment qovluq adı)
_TYPES = {
    ".mp4": ("video/mp4", "video", "DIRECTORY_MOVIES"),
    ".mp3": ("audio/mpeg", "audio", "DIRECTORY_MUSIC"),
}


class MediaStoreError(Exception):
    """MediaStore əməliyyatı zamanı xəta."""


def is_supported() -> bool:
    """Android 10+ üzərində işləyirsə True qaytarır."""
    try:
        from jnius import autoclass

        return autoclass("android.os.Build$VERSION").SDK_INT >= 29
    except Exception:
        return False


def save_media(src_path: str, display_name: str | None = None) -> dict:
    """
    mp4/mp3 faylını MediaStore ilə sürətli saxlayır.

    src_path     - mənbə faylın tam yolu
    display_name - yeni ad (verilməsə mənbə adı istifadə olunur)

    Qaytarır: {'uri': str, 'folder': str, 'name': str}
    Xəta olarsa MediaStoreError atır.
    """
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in _TYPES:
        raise MediaStoreError("Yalnız .mp4 və .mp3 dəstəklənir")
    if not os.path.isfile(src_path):
        raise MediaStoreError(f"Fayl tapılmadı: {src_path}")

    try:
        from jnius import autoclass
    except ImportError:
        raise MediaStoreError("pyjnius tapılmadı (yalnız Android-də işləyir)")

    if autoclass("android.os.Build$VERSION").SDK_INT < 29:
        raise MediaStoreError("Android 10 (API 29) və yuxarı lazımdır")

    mime, kind, dir_attr = _TYPES[ext]
    name = display_name or os.path.basename(src_path)
    if not name.lower().endswith(ext):
        name += ext

    ActivityThread = autoclass("android.app.ActivityThread")
    ContentValues = autoclass("android.content.ContentValues")
    MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
    Environment = autoclass("android.os.Environment")
    Integer = autoclass("java.lang.Integer")
    FileInputStream = autoclass("java.io.FileInputStream")
    FileUtils = autoclass("android.os.FileUtils")

    if kind == "video":
        collection = autoclass("android.provider.MediaStore$Video$Media")
    else:
        collection = autoclass("android.provider.MediaStore$Audio$Media")

    folder = getattr(Environment, dir_attr)
    resolver = (
        ActivityThread.currentApplication().getApplicationContext().getContentResolver()
    )

    values = ContentValues()
    values.put(MediaColumns.DISPLAY_NAME, name)
    values.put(MediaColumns.MIME_TYPE, mime)
    values.put(MediaColumns.RELATIVE_PATH, folder)
    values.put(MediaColumns.IS_PENDING, Integer.valueOf(1))

    uri = resolver.insert(collection.EXTERNAL_CONTENT_URI, values)
    if uri is None:
        raise MediaStoreError("MediaStore insert uğursuz oldu")

    in_stream = FileInputStream(src_path)
    out_stream = resolver.openOutputStream(uri)
    try:
        FileUtils.copy(in_stream, out_stream)
    except Exception as e:
        resolver.delete(uri, None, None)
        raise MediaStoreError(f"Yazma xətası: {e}")
    finally:
        in_stream.close()
        if out_stream is not None:
            out_stream.close()

    done = ContentValues()
    done.put(MediaColumns.IS_PENDING, Integer.valueOf(0))
    resolver.update(uri, done, None, None)

    return {"uri": uri.toString(), "folder": folder, "name": name}
