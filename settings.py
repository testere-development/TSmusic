import json
import os
import shutil
import subprocess

try:
    from jnius import autoclass
except ImportError:  # Android xaricində (kompüterdə test üçün)
    autoclass = None


LANGS = ["az", "tr", "ru", "en"]
MODES = ["dark", "light"]

DEFAULT_LANG = "az"
DEFAULT_MODE = "dark"

SETTINGS_FILENAME = "settings.json"

TEXTS = {
    "az": {
        "title": "Yükləyici",
        "hint": "Yükləmək üçün URL daxil edin",
        "download": "Yüklə",
        "empty": "Zəhmət olmasa URL daxil edin",
        "invalid": "URL düzgün deyil (http:// və ya https:// ilə başlamalıdır)",
        "downloading": "Yüklənir...",
        "converting": "Emal olunur...",
        "saving": "Yaddaşa yazılır...",
        "done": "Yükləmə tamamlandı",
        "error": "Xəta: ",
        "github": "GitHub səhifəsini aç",
        "theme": "Rejimi dəyiş",
    },
    "tr": {
        "title": "İndirici",
        "hint": "İndirmek için URL girin",
        "download": "İndir",
        "empty": "Lütfen bir URL girin",
        "invalid": "URL geçersiz (http:// veya https:// ile başlamalı)",
        "downloading": "İndiriliyor...",
        "converting": "İşleniyor...",
        "saving": "Depolamaya kaydediliyor...",
        "done": "İndirme tamamlandı",
        "error": "Hata: ",
        "github": "GitHub sayfasını aç",
        "theme": "Modu değiştir",
    },
    "ru": {
        "title": "Загрузчик",
        "hint": "Введите URL для загрузки",
        "download": "Скачать",
        "empty": "Пожалуйста, введите URL",
        "invalid": "Неверный URL (должен начинаться с http:// или https://)",
        "downloading": "Загрузка...",
        "converting": "Обработка...",
        "saving": "Сохранение в память...",
        "done": "Загрузка завершена",
        "error": "Ошибка: ",
        "github": "Открыть страницу GitHub",
        "theme": "Сменить тему",
    },
    "en": {
        "title": "Downloader",
        "hint": "Enter a URL to download",
        "download": "Download",
        "empty": "Please enter a URL",
        "invalid": "Invalid URL (must start with http:// or https://)",
        "downloading": "Downloading...",
        "converting": "Processing...",
        "saving": "Saving to storage...",
        "done": "Download complete",
        "error": "Error: ",
        "github": "Open GitHub page",
        "theme": "Toggle theme",
    },
}


class Setting:
    def __init__(self) -> None:
        # Dil və rejim (yadda saxlanılan)
        self.lang = DEFAULT_LANG
        self.mode = DEFAULT_MODE

        self.ffmpeg()
        self.load()

    # ------------------------------------------------------------------
    # FFmpeg
    # ------------------------------------------------------------------
    def ffmpeg(self):
        # Assets path
        self.assets = os.getenv("FLET_ASSETS_DIR")
        print(f"FLET_ASSETS_DIR==>{self.assets}")

        # App storage
        self.storage = os.getenv("FLET_APP_STORAGE_DATA")
        print(f"FLET_APP_STORAGE_DATA==>{self.storage}")

        # Android deyilsə (kompüterdə test), sistem ffmpeg-ini istifadə et
        if autoclass is None or not self.assets or not self.storage:
            self.ffmpeg = "ffmpeg"
            return

        # Abis
        self.build = autoclass("android.os.Build")
        self.abis = self.build.SUPPORTED_ABIS
        print(f"ABIS==>{self.abis[0]}")

        self.ffmpeg = f"{self.storage.strip()}/ffmpeg"

        # copy ffmpeg
        if "ffmpeg" not in os.listdir(self.storage):
            shutil.copy2(
                f"{self.assets.strip()}/ffmpeg/{self.abis[0].strip()}", self.ffmpeg
            )

        os.chmod(self.ffmpeg, 0o755)

        # start ffmpeg
        result = subprocess.run(
            f"{self.ffmpeg} -version", shell=True, capture_output=True, text=True
        )

        print("[FFmpeg]")
        print(result.stderr, result.stdout)

        print(os.listdir(self.assets))

        print(os.listdir(self.storage))

        print(os.listdir(f"{self.assets}/ffmpeg"))

    # ------------------------------------------------------------------
    # Dil və rejimin yadda saxlanması
    # ------------------------------------------------------------------
    def _settings_path(self) -> str:
        base = os.getenv("FLET_APP_STORAGE_DATA") or os.path.expanduser("~")
        return os.path.join(base, SETTINGS_FILENAME)

    def load(self):
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        lang = data.get("lang", DEFAULT_LANG)
        mode = data.get("mode", DEFAULT_MODE)
        self.lang = lang if lang in LANGS else DEFAULT_LANG
        self.mode = mode if mode in MODES else DEFAULT_MODE

    def save(self):
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump({"lang": self.lang, "mode": self.mode}, f)
        except Exception as e:
            print(f"Settings save error: {e}")

    def set_lang(self, lang: str):
        if lang in LANGS:
            self.lang = lang
            self.save()

    def toggle_mode(self) -> str:
        self.mode = "light" if self.mode == "dark" else "dark"
        self.save()
        return self.mode

    def t(self, key: str) -> str:
        return TEXTS[self.lang].get(key, key)
