import os
import shutil
import threading
import uuid

import yt_dlp

from mediastore_saver import MediaStoreError, save_media


class DownloadCancelled(Exception):
    """İstifadəçi yükləməni ləğv etdi."""


# ---------- ffmpeg proseslərini thread-ə görə izləmək ----------
# Ləğv edəndə yalnız həmin yükləməyə aid ffmpeg prosesi öldürülsün deyə
# yt-dlp-nin Popen-ini izləyən alt-sinif ilə əvəz edirik.
_local = threading.local()

try:
    import yt_dlp.postprocessor.ffmpeg as _ffmpeg_mod
    from yt_dlp.utils import Popen as _YPopen

    class _TrackedPopen(_YPopen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            procs = getattr(_local, "procs", None)
            if procs is not None:
                procs.append(self)

    _ffmpeg_mod.Popen = _TrackedPopen
except Exception:  # yt-dlp versiyası fərqlidirsə, ffmpeg yalnız hook-larda yoxlanır
    pass


def _kill_procs(procs):
    for p in list(procs):
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass


def _prefer_jpg_thumbnails(info):
    """Kapak üçün yalnız jpg variantlarını saxla: webp→jpg çevirməsi lazım olmasın.
    jpg yoxdursa siyahı dəyişmir (çevirmə ehtiyat variant kimi qalır)."""
    thumbs = info.get("thumbnails") or []
    jpgs = [
        t
        for t in thumbs
        if (t.get("url") or "").split("?")[0].lower().endswith((".jpg", ".jpeg"))
    ]
    if jpgs:
        info["thumbnails"] = jpgs


class Download:
    def __init__(self, path) -> None:
        self.ffmpeg = path
        self.storage = os.getenv("FLET_APP_STORAGE_DATA")

    def dow(self, url: str, cohi: int, on_progress=None, cancel_event=None):
        """
        cohi: 3 = mp3, 4 = mp4
        on_progress(d): yt-dlp progress dict-i ilə çağırılır (thread-safe olmalıdır)
        cancel_event: threading.Event; set olunarsa yükləmə tam dayandırılır
        """
        cancel_event = cancel_event or threading.Event()

        # Hər yükləmə üçün ayrıca qovluq: paralel yükləmələr qarışmasın,
        # ləğv edəndə yarımçıq (.part) fayllar asanlıqla silinsin.
        workdir = os.path.join("download", uuid.uuid4().hex)
        os.makedirs(workdir, exist_ok=True)
        outtmpl = os.path.join(workdir, "%(title)s.%(ext)s")

        def check():
            if cancel_event.is_set():
                raise DownloadCancelled()

        def hook(d):
            check()
            if on_progress:
                on_progress(d)

        def pp_hook(d):
            check()

        common = {
            "ffmpeg_location": self.ffmpeg,
            "outtmpl": outtmpl,
            "progress_hooks": [hook],
            "postprocessor_hooks": [pp_hook],
            "no_warnings": True,
            "noplaylist": True,
            # Şəbəkə donanda da hook-a çatıb ləğv yoxlanılsın
            "socket_timeout": 10,
            "retries": 3,
        }

        if cohi == 3:
            opts = {
                **common,
                "format": "bestaudio[protocol=https]/bestaudio",
                # Kapak şəkli yüklənir, mp3-ün içinə yerləşdirilir və
                # ayrıca şəkil faylı qalmır (qovluq sonda silinir)
                "writethumbnail": True,
                "postprocessors": [
                    # webp → jpg (mp3 üçün uyğun format)
                    {
                        "key": "FFmpegThumbnailsConvertor",
                        "format": "jpg",
                        "when": "before_dl",
                    },
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                    # Ad, müəllif və s. məlumat teqləri
                    {"key": "FFmpegMetadata", "add_metadata": True},
                    # Kapak şəklini mp3-ə yerləşdirir və şəkil faylını silir
                    {"key": "EmbedThumbnail", "already_have_thumbnail": False},
                ],
            }
        elif cohi == 4:
            opts = {
                **common,
                "format": "bv*[height<=1080][protocol=https]+ba/b[height<=1080]",
                "merge_output_format": "mp4",
                "postprocessors": [
                    {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                ],
            }
        else:
            raise ValueError("Yanlış format")

        # Bu thread-in ffmpeg proseslərini toplayırıq
        procs = []
        _local.procs = procs

        # Ləğv edilən kimi işləyən ffmpeg-i dərhal öldürən izləyici
        done = threading.Event()

        def watcher():
            while not done.is_set():
                if cancel_event.wait(0.2):
                    _kill_procs(procs)
                    # ffmpeg sonradan başlasa da öldürülsün
                    while not done.is_set():
                        _kill_procs(procs)
                        done.wait(0.2)
                    return

        threading.Thread(target=watcher, daemon=True).start()

        try:
            check()
            with yt_dlp.YoutubeDL(opts) as ydl:
                if cohi == 3:
                    # Əvvəl məlumatı al, kapakları jpg ilə məhdudlaşdır, sonra yüklə
                    info = ydl.extract_info(url, download=False)
                    check()
                    _prefer_jpg_thumbnails(info)
                    info = ydl.process_ie_result(info, download=True)
                else:
                    info = ydl.extract_info(url, download=True)

            check()

            full_pth = info["requested_downloads"][0]["filepath"]
            self.move(full_pth)

        except DownloadCancelled:
            raise
        except Exception as e:
            # Ləğv səbəbindən yaranan istənilən xəta (məs. öldürülən ffmpeg)
            if cancel_event.is_set():
                raise DownloadCancelled() from e
            raise
        finally:
            done.set()
            _kill_procs(procs)
            _local.procs = None
            shutil.rmtree(workdir, ignore_errors=True)

    def move(self, path: str):
        try:
            res = save_media(path)
            print(res)
        except MediaStoreError as e:
            print(e)

        if os.path.exists(path):
            os.remove(path)
