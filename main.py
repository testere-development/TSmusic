import base64
import inspect
import threading
import time
import urllib.parse

import flet as ft

from settings import LANGS, Setting

try:
    from download import Download, DownloadCancelled
except ImportError:
    from dowload import Download, DownloadCancelled  # Faylın adı dowload.py olarsa

ICONS = getattr(ft, "Icons", None) or ft.icons
Button = getattr(ft, "Button", None) or ft.ElevatedButton

GITHUB_URL = "https://github.com/testere-development"

# Download.dow(url, cohi): 3 = MP3, 4 = MP4
FORMATS = {"MP3": 3, "MP4": 4}
FORMAT_ICONS = {"MP3": ICONS.MUSIC_NOTE, "MP4": ICONS.VIDEOCAM}

# Eyni anda neçə yükləmə işləsin (qalanları növbədə gözləyir)
MAX_PARALLEL = 3

MB = 1024 * 1024

# ---------- Rənglər ----------
PRIMARY = "#3B82F6"
ACCENT = "#8B5CF6"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"

# GitHub loqosu (Octicons "mark-github"), rəng sonradan əvəz olunur
GITHUB_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="COLOR">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 '
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15"
    "-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51"
    "-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 "
    "0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82"
    ".44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54"
    ".73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42"
    '-3.58-8-8-8z"/></svg>'
)


def github_logo(color, size=28):
    """GitHub SVG loqosu; Flet versiyasından asılı olmayaraq təhlükəsiz yaradılır."""
    svg = GITHUB_SVG.replace("COLOR", color)
    b64 = base64.b64encode(svg.encode()).decode()
    for kwargs in ({"src_base64": b64}, {"src": svg.encode()}, {"src": b64}):
        try:
            return ft.Image(width=size, height=size, fit=ft.BoxFit.CONTAIN, **kwargs)
        except (TypeError, AttributeError):
            try:
                return ft.Image(width=size, height=size, **kwargs)
            except Exception:
                continue
    return ft.Icon(ICONS.CODE, size=size)


# settings.py-də olmayan yeni mətnlər
EXTRA = {
    "cancel": {"az": "Ləğv et", "tr": "İptal", "en": "Cancel", "ru": "Отмена"},
    "queued": {"az": "Növbədə", "tr": "Sırada", "en": "Queued", "ru": "В очереди"},
    "cancelled": {
        "az": "Ləğv edildi",
        "tr": "İptal edildi",
        "en": "Cancelled",
        "ru": "Отменено",
    },
}


def main(page: ft.Page):
    setting = Setting()
    dl = Download(setting.ffmpeg)

    state = {"format": "MP3", "counter": 0}
    tasks = []  # yaradılma sırası ilə bütün yükləmələr
    sem = threading.Semaphore(MAX_PARALLEL)

    page.title = "Testere Downloader"
    page.padding = 16
    page.spacing = 10
    page.theme = ft.Theme(color_scheme_seed=PRIMARY)
    page.dark_theme = ft.Theme(color_scheme_seed=PRIMARY)

    def tx(key):
        """Əvvəl EXTRA-dan, yoxdursa settings-dən tərcümə."""
        if key in EXTRA:
            return EXTRA[key].get(setting.lang) or EXTRA[key]["en"]
        return setting.t(key)

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
    # GitHub loqosu: tema dəyişəndə rəngi də dəyişir
    logo_holder = ft.Container(content=github_logo("#111827"))

    logo = ft.Container(
        content=ft.Row(
            [
                logo_holder,
                ft.Text("Testere", weight=ft.FontWeight.BOLD, size=18),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=open_github,
        ink=True,
        border_radius=12,
        padding=ft.Padding(left=8, top=6, right=12, bottom=6),
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
            icon=FORMAT_ICONS[name],
            on_click=lambda e, n=name: change_format(n),
        )

    title = ft.Text(size=26, weight=ft.FontWeight.BOLD, color="#FFFFFF")

    url_input = ft.TextField(
        prefix_icon=ICONS.LINK,
        expand=True,
        on_submit=lambda e: start_download(e),
        text_size=14,
        border=ft.OutlineInputBorder(border_radius=14),
        filled=True,
    )

    download_btn = Button(
        content=setting.t("download"),
        icon=ICONS.DOWNLOAD,
        expand=True,
        height=52,
        on_click=lambda e: start_download(e),
        style=ft.ButtonStyle(
            bgcolor=PRIMARY,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )

    status = ft.Text(size=13)

    # Yükləmələrin siyahısı (sıra ilə, ən yenisi aşağıda)
    downloads_list = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # ---------- UI ----------
    pill = ft.RoundedRectangleBorder(radius=20)

    def style_format(btn, selected):
        btn.style = ft.ButtonStyle(
            bgcolor=PRIMARY if selected else None,
            color="#FFFFFF" if selected else None,
            shape=pill,
            padding=ft.Padding(left=16, top=8, right=16, bottom=8),
        )

    def style_lang(btn, selected):
        # Gradient başlığın üstündə: seçilən ağ, qalanları şəffaf
        btn.style = ft.ButtonStyle(
            bgcolor="#FFFFFF" if selected else None,
            color=PRIMARY if selected else "#FFFFFF",
            shape=pill,
            padding=ft.Padding(left=12, top=4, right=12, bottom=4),
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
        logo_holder.content = github_logo(
            "#F3F4F6" if setting.mode == "dark" else "#111827"
        )

        for code, btn in lang_buttons.items():
            style_lang(btn, code == setting.lang)

        for name, btn in format_buttons.items():
            style_format(btn, name == state["format"])

        for t in tasks:
            t.cancel_btn.tooltip = tx("cancel")
            render_task(t)

        page.update()

    def change_lang(code):
        setting.set_lang(code)
        status.value = ""
        refresh_ui()

    def change_format(name):
        # Yükləmə zamanı da dəyişmək olar: hər yükləmə öz formatını saxlayır
        state["format"] = name
        refresh_ui()

    def toggle_theme(e):
        setting.toggle_mode()
        refresh_ui()

    theme_btn.on_click = toggle_theme

    def set_status(message, error=False):
        status.value = message
        status.color = DANGER if error else None
        page.update()

    # ---------- Bir yükləmə sətri ----------
    class Task:
        def __init__(self, number, url, fmt):
            self.number = number
            self.url = url
            self.fmt = fmt
            self.cohi = FORMATS[fmt]
            self.cancel = threading.Event()

            self.name = url  # title məlum olanda dəyişəcək
            self.state = "queued"  # queued/downloading/converting/done/error/cancelled
            self.downloaded = 0
            self.total = 0
            self.error = ""
            self.last_ui = 0.0

            self.badge = ft.Container(
                content=ft.Icon(FORMAT_ICONS[fmt], color="#FFFFFF", size=22),
                width=44,
                height=44,
                border_radius=22,
                bgcolor=PRIMARY if fmt == "MP3" else ACCENT,
                alignment=ft.Alignment(0, 0),
            )
            self.name_text = ft.Text(
                weight=ft.FontWeight.BOLD,
                size=14,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
            self.info_text = ft.Text(size=12, expand=True)
            self.bar = ft.ProgressBar(value=None, bar_height=6, color=PRIMARY)
            self.cancel_btn = ft.IconButton(
                icon=ICONS.CLOSE,
                icon_size=20,
                icon_color=DANGER,
                tooltip=tx("cancel"),
                on_click=lambda e: cancel_task(self),
            )
            self.card = ft.Card(
                content=ft.Container(
                    padding=12,
                    border_radius=16,
                    content=ft.Row(
                        [
                            self.badge,
                            ft.Column(
                                [
                                    self.name_text,
                                    self.bar,
                                    ft.Row(
                                        [self.info_text],
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=6,
                                expand=True,
                            ),
                            self.cancel_btn,
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    def size_text(t):
        if t.total:
            pct = t.downloaded / t.total * 100
            return f"{t.downloaded / MB:.1f} / {t.total / MB:.1f} MB  ({pct:.0f}%)"
        if t.downloaded:
            return f"{t.downloaded / MB:.1f} MB"
        return ""

    def render_task(t):
        t.name_text.value = f"#{t.number}  {t.name}"

        if t.state == "queued":
            t.info_text.value = tx("queued")
            t.info_text.color = None
            t.bar.value = None
            t.bar.color = PRIMARY
            t.cancel_btn.visible = True

        elif t.state == "downloading":
            sz = size_text(t)
            t.info_text.value = sz or tx("downloading")
            t.info_text.color = None
            t.bar.value = (t.downloaded / t.total) if t.total else None
            t.bar.color = PRIMARY
            t.cancel_btn.visible = True

        elif t.state == "converting":
            sz = size_text(t)
            t.info_text.value = f"{tx('converting')}  {sz}".strip()
            t.info_text.color = None
            t.bar.value = None
            t.bar.color = ACCENT
            t.cancel_btn.visible = True

        elif t.state == "done":
            sz = f"{t.total / MB:.1f} MB" if t.total else ""
            t.info_text.value = f"{tx('done')}  {sz}".strip()
            t.info_text.color = SUCCESS
            t.bar.value = 1
            t.bar.color = SUCCESS
            t.cancel_btn.visible = False

        elif t.state == "cancelled":
            t.info_text.value = tx("cancelled")
            t.info_text.color = WARNING
            t.bar.value = 0
            t.bar.color = WARNING
            t.cancel_btn.visible = False

        elif t.state == "error":
            t.info_text.value = tx("error") + t.error
            t.info_text.color = DANGER
            t.bar.value = 0
            t.bar.color = DANGER
            t.cancel_btn.visible = False

    def cancel_task(t):
        if t.state in ("done", "error", "cancelled"):
            return
        # Thread növbəti progress hook-da (və ya gözləmə zamanı) dayanacaq
        t.cancel.set()
        t.state = "cancelled"

        # Ləğv edilən kart dərhal ekrandan silinir, yer tutmur
        if t.card in downloads_list.controls:
            downloads_list.controls.remove(t.card)
        if t in tasks:
            tasks.remove(t)
        page.update()

    # ---------- Paralel yükləmə ----------
    def make_hook(t):
        def on_progress(d):
            status_ = d.get("status")

            info = d.get("info_dict") or {}
            if info.get("title"):
                t.name = info["title"]

            if status_ == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                t.downloaded = d.get("downloaded_bytes") or 0
                if total:
                    t.total = total
                t.state = "downloading"

                # UI-ni çox tez-tez yeniləməyək
                now = time.monotonic()
                if now - t.last_ui >= 0.25:
                    t.last_ui = now
                    render_task(t)
                    page.update()

            elif status_ == "finished":
                # Audio+video ayrı yüklənəndə hər biri üçün "finished" gəlir
                t.downloaded = d.get("total_bytes") or t.downloaded
                if t.downloaded and t.downloaded > t.total:
                    t.total = t.downloaded
                t.state = "converting"
                render_task(t)
                page.update()

        return on_progress

    def run_task(t):
        # Boş yer gözlə, amma gözləyərkən də ləğv edilə bilsin
        acquired = False
        while not t.cancel.is_set():
            if sem.acquire(timeout=0.3):
                acquired = True
                break

        if not acquired:
            t.state = "cancelled"
            render_task(t)
            page.update()
            return

        try:
            if t.cancel.is_set():
                t.state = "cancelled"
            else:
                t.state = "downloading"
                render_task(t)
                page.update()

                dl.dow(t.url, t.cohi, on_progress=make_hook(t), cancel_event=t.cancel)
                t.state = "done"

        except DownloadCancelled:
            t.state = "cancelled"

        except Exception as ex:
            t.error = str(ex)
            t.state = "error"

        finally:
            sem.release()
            render_task(t)
            page.update()

    def start_download(e=None):
        url = (url_input.value or "").strip()

        if not url:
            set_status(setting.t("empty"), True)
            return

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            set_status(setting.t("invalid"), True)
            return

        state["counter"] += 1
        t = Task(state["counter"], url, state["format"])
        tasks.append(t)

        # Düyməyə basılan kimi URL input təmizlənsin
        url_input.value = ""
        status.value = ""

        downloads_list.controls.append(t.card)
        render_task(t)
        page.update()

        threading.Thread(target=run_task, args=(t,), daemon=True).start()

    # ---------- Layout ----------
    top_bar = ft.Row(
        [logo, theme_btn],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    lang_row = ft.Row(
        list(lang_buttons.values()),
        spacing=4,
        run_spacing=4,
        wrap=True,
    )

    # Gradient başlıq: ad + dil seçimi
    hero = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ICONS.CLOUD_DOWNLOAD, color="#FFFFFF", size=30),
                        title,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                lang_row,
            ],
            spacing=10,
        ),
        padding=20,
        border_radius=20,
        gradient=ft.LinearGradient(colors=[PRIMARY, ACCENT]),
    )

    format_row = ft.Row(
        list(format_buttons.values()),
        spacing=8,
        run_spacing=8,
        wrap=True,
    )

    # Giriş kartı: format + link + düymə
    input_card = ft.Card(
        content=ft.Container(
            padding=16,
            border_radius=16,
            content=ft.Column(
                [
                    format_row,
                    ft.Row([url_input]),
                    ft.Row([download_btn]),
                    status,
                ],
                spacing=12,
            ),
        )
    )

    body = ft.Column(
        [
            top_bar,
            hero,
            input_card,
            downloads_list,
        ],
        spacing=12,
        expand=True,
    )

    safe_area = getattr(ft, "SafeArea", None)
    page.add(safe_area(content=body, expand=True) if safe_area else body)

    refresh_ui()


if __name__ == "__main__":
    runner = getattr(ft, "run", None) or ft.app
    runner(main)
