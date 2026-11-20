import os

import yt_dlp

from mediastore_saver import MediaStoreError, save_media


class Download:
    def __init__(self, path) -> None:
        self.ffmpeg = path
        self.storage = os.getenv("FLET_APP_STORAGE_DATA")

    def dow(self, url: str, cohi: int):
        # cohi ==> mp3 or mp4
        if cohi == 3:
            opts = {
                "format": "bestaudio[protocol=https]/bestaudio",
                "ffmpeg_location": self.ffmpeg,
                "outtmpl": "download/%(title)s.%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "progress_hooks": [self.hook],
                "no_warnings": True,
            }

        if cohi == 4:
            opts = {
                "format": "bv*[height<=1080][protocol=https]+ba/b[height<=1080]",
                "merge_output_format": "mp4",
                "ffmpeg_location": self.ffmpeg,
                "outtmpl": "download/%(title)s.%(ext)s",
                "postprocessors": [
                    {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                ],
                "progress_hooks": [self.hook],
                "no_warnings": True,
            }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        full_pth = info["requested_downloads"][0]["filepath"]
        print(full_pth)
        self.move(full_pth)

    def hook(self, d):
        self.log = d

        if d["status"] == "downloading":
            print("yuklenir")

        elif d["status"] == "finished":
            print("Yükləndi:", d["filename"])

    def move(self, path: str):
        try:
            res = save_media(path)
            print(res)
        except MediaStoreError as e:
            print(e)

        os.remove(path)
