Testere Downloader
A lightweight media downloader with a simple Flet interface. Choose an
output format, paste a media URL, and start downloading.
Features
- MP3 and MP4 output options
- Download progress indicator
- Sequential downloads: a second download cannot start while the
  current one is running
- URL field is cleared as soon as the download starts
- Light and dark themes
- Multiple language options provided by the project settings
- GitHub shortcut in the application interface
- Uses the project's Download class and FFmpeg configuration
Requirements
- Python 3.10 or newer
- Flet
- yt-dlp
- FFmpeg
- Project modules: settings.py and download.py (or dowload.py,
  if that is the filename used)
The exact dependencies and Android build configuration are defined in
pyproject.toml.
Project structure
A typical layout:
project/
├── pyproject.toml
├── README.md
└── src/
    ├── main.py
    ├── settings.py
    ├── download.py
    └── assets/
        └── icon.png
Adjust this structure to match the actual project. The application entry
point and asset paths must match your Flet configuration.
Run locally
For a project managed with uv:
uv sync
uv run flet run
If you use another environment or package manager, install the
dependencies and run the Flet application with the equivalent commands.
Build for Android
With the Flet CLI and Android build requirements installed:
flet build apk
The current Android settings in the supplied pyproject.toml are:
- min_sdk_version = 24
- target_sdk_version = 28
- target_arch = ["arm64-v8a", "armeabi-v7a"]
- split_per_abi = false
Change these values in pyproject.toml if your build requirements
change.
How to use
1. Open the application.
2. Select MP3 or MP4.
3. Paste a valid http:// or https:// media URL.
4. Press the download button.
5. Wait for the download and any required conversion to finish.
6. Start another download after the current one completes.
Notes
- The interface allows only one download at a time.
- Download and conversion behavior depends on the implementation of
  the project's Download class and its FFmpeg setup.
- Make sure FFmpeg is available at the path configured in
  settings.py.
- Download only content you have the right to access and save. Respect
  the source service's terms and applicable copyright laws.
License
No license has been specified yet. Add a LICENSE file before
publishing if you want to define how others may use, modify, and
distribute this project.
Testere Development
GitHub
