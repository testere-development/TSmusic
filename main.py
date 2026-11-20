import inspect
import threading
import urllib.parse

import flet as ft

from settings import LANGS, Setting

try:
    from download import Download
except ImportError:
    from dowload import Download  # Faylın adı dowload.py olarsa

ICONS = getattr(ft, "Icons", None) or ft.icons
Button = getattr(ft, "Button", None) or ft.ElevatedButton

GITHUB_URL = "https://github.com/testere-development"

# Download.dow(url, cohi): 3 = MP3, 4 = MP4
FORMATS = {"MP3": 3, "MP4": 4}


def main(page: ft.Page):
    setting = Setting()
    dl = Download(setting.ffmpeg)

    state = {
        "format": "MP3",
        "downloading": False,
    }

    page.title = "Testere Downloader"
    page.padding = 16
    page.spacing = 10

    # ---------- URL açmaq ----------
    url_launcher = None
    if not hasattr(page, "launch_url") and hasattr(ft, "UrlLauncher"):
        url_launcher = ft.UrlLauncher()
        try:
            page.services.append(url_launcher)
        except Exception:
            pass

    async def open_github(e):
        if url_launcher is not None:
            result = url_launcher.launch_url(GITHUB_URL)
        else:
            result = page.launch_url(GITHUB_URL)

        if inspect.isawaitable(result):
            await result

    # ---------- Controls ----------
    logo = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ICONS.CODE, size=25),
                ft.Text("Testere", weight=ft.FontWeight.BOLD, size=16),
            ],
            spacing=6,
        ),
        on_click=open_github,
        ink=True,
        border_radius=8,
        padding=6,
        tooltip="GitHub",
    )

    theme_btn = ft.IconButton(
        icon=ICONS.LIGHT_MODE,
        icon_size=22,
        tooltip="Theme",
    )

    lang_buttons = {}
    for code in LANGS:
        lang_buttons[code] = ft.TextButton(
            content=code.upper(),
            on_click=lambda e, c=code: change_lang(c),
        )

    format_buttons = {}
    for name in FORMATS:
        format_buttons[name] = ft.TextButton(
            content=name,
            on_click=lambda e, n=name: change_format(n),
        )

    title = ft.Text(size=23, weight=ft.FontWeight.BOLD)

    url_input = ft.TextField(
        prefix_icon=ICONS.LINK,
        expand=True,
        on_submit=lambda e: start_download(e),
        text_size=14,
    )

    download_btn = Button(
        content=setting.t("download"),
        icon=ICONS.DOWNLOAD,
        expand=True,
        height=50,
        on_click=lambda e: start_download(e),
    )

    progress = ft.ProgressBar(visible=False, value=None)
    status = ft.Text(size=13)

    # ---------- UI ----------
    def style_selected(btn, selected):
        btn.style = ft.ButtonStyle(
            bgcolor="#3B82F6" if selected else None,
            color="#FFFFFF" if selected else None,
            padding=ft.Padding(left=12, top=6, right=12, bottom=6),
        )

    def refresh_ui():
        title.value = setting.t("title")
        url_input.label = setting.t("hint")
        download_btn.content = setting.t("download")
        logo.tooltip = setting.t("github")
        theme_btn.tooltip = setting.t("theme")
        theme_btn.icon = (
            ICONS.LIGHT_MODE if setting.mode == "dark" else ICONS.DARK_MODE
        )

        page.theme_mode = (
            ft.ThemeMode.DARK if setting.mode == "dark" else ft.ThemeMode.LIGHT
        )

        for code, btn in lang_buttons.items():
            style_selected(btn, code == setting.lang)

        for name, btn in format_buttons.items():
            style_selected(btn, name == state["format"])

        page.update()

    def change_lang(code):
        setting.set_lang(code)
        status.value = ""
        refresh_ui()

    def change_format(name):
        # Format yükləmə zamanı dəyişdirilməsin
        if state["downloading"]:
            return
        state["format"] = name
        refresh_ui()

    def toggle_theme(e):
        setting.toggle_mode()
        refresh_ui()

    theme_btn.on_click = toggle_theme

    def set_status(message, error=False):
        status.value = message
        status.color = "#EF4444" if error else None
        page.update()

    # ---------- Yükləmə progress hook ----------
    original_hook = dl.hook

    def progress_hook(data):
        original_hook(data)

        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes") or 0

            if total:
                progress.value = downloaded / total

            page.update()

        elif data.get("status") == "finished":
            progress.value = None
            set_status(setting.t("converting"))

    dl.hook = progress_hook

    # ---------- Ardıcıl yükləmə ----------
    def start_download(e=None):
        # Birinci yükləmə bitmədən ikinci başlamasın
        if state["downloading"]:
            return

        url = (url_input.value or "").strip()

        if not url:
            set_status(setting.t("empty"), True)
            return

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            set_status(setting.t("invalid"), True)
            return

        selected_format = state["format"]
        cohi = FORMATS[selected_format]

        # Kilidi thread başlamazdan əvvəl aktiv et
        state["downloading"] = True

        # Düyməyə basılan kimi URL input-dan silinsin
        url_input.value = ""

        download_btn.disabled = True
        progress.visible = True
        progress.value = None

        # Format seçimini də yükləmə bitənədək bağla
        for btn in format_buttons.values():
            btn.disabled = True

        set_status(setting.t("downloading"))
        page.update()

        def worker():
            try:
                dl.dow(url, cohi)
                progress.value = 1
                set_status(setting.t("done"))

            except Exception as ex:
                set_status(setting.t("error") + str(ex), True)

            finally:
                state["downloading"] = False
                download_btn.disabled = False
                progress.visible = False

                for btn in format_buttons.values():
                    btn.disabled = False

                page.update()

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Layout ----------
    top_bar = ft.Row(
        [logo, theme_btn],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    lang_row = ft.Row(
        list(lang_buttons.values()),
        spacing=5,
        run_spacing=5,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    format_row = ft.Row(
        list(format_buttons.values()),
        spacing=6,
        run_spacing=6,
        wrap=True,
    )

    body = ft.Column(
        [
            top_bar,
            lang_row,
            ft.Container(height=6),
            title,
            format_row,
            url_input,
            download_btn,
            progress,
            status,
        ],
        spacing=12,
        expand=True,
    )

    safe_area = getattr(ft, "SafeArea", None)
    page.add(safe_area(content=body) if safe_area else body)

    refresh_ui()


if __name__ == "__main__":
    runner = getattr(ft, "run", None) or ft.app
    runner(main)
