# Contributing to jBahr's Clip Generator

Welcome! This document provides instructions for setting up the development environment, understanding the application's architecture, running tests, and compiling/packaging the application.

---

## 🛠️ Local Environment Setup

The application is written in **Python 3.12+** and uses **CustomTkinter** for its graphical user interface.

### 1. Prerequisites
Ensure you have the following installed on your machine:
* **Python 3.12 or newer**
* **Git**
* **NVIDIA CUDA Toolkit** (Optional, but highly recommended for GPU-accelerated local transcription via Whisper and torch).

### 2. Setting Up the Virtual Environment
Clone the repository and set up a Python virtual environment:

```powershell
# Clone the repository
git clone https://github.com/jBahrVR/jBahrs-Clip-Generator.git
cd jBahrs-Clip-Generator

# Create a virtual environment named '.venv'
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (CMD):
.\.venv\Scripts\activate.bat
# On Unix/macOS:
source .venv/bin/activate
```

### 3. Installing Dependencies
Install all required packages listed in the `requirements.txt` manifest:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> If you plan to run local GPU-accelerated transcriptions, ensure that the PyTorch version installed matches your CUDA version. See the [PyTorch Get Started](https://pytorch.org/get-started/locally/) guide for custom pip installation strings if CUDA acceleration is not working out-of-the-box.

### 4. Binary Dependencies (FFmpeg & yt-dlp)
The application relies on external executables (`ffmpeg.exe` and `yt-dlp.exe`) to download streams, extract audio, and cut videos.
* **Startup Bootstrapper:** On startup, `app.py` checks if these binaries exist in the application folder. If they are missing, a progress dialog automatically runs to download them.
* **Manual Override:** You can manually place current Windows executables (`ffmpeg.exe` and `yt-dlp.exe`) in the project root directory.

---

## 🏗️ Codebase Architecture

```mermaid
graph TD
    A[app.py - CTk UI & Scheduler] --> B[watcher.py - Stream Monitor]
    A --> C[editor.py - Clip Cutter & AI Client]
    A --> D[config_manager.py - Settings JSON]
    C --> E[Whisper - Local Transcription]
    C --> F[Google GenAI / Anthropic / OpenAI]
    C --> G[FFmpeg - Audio & Video Processing]
```

### File Map
* **[app.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/app.py)**: The main entry point. Houses the CustomTkinter GUI layout, tab definitions (Manual Clipper, Clip Gallery, Scheduler, Prompts, Settings), background watcher scheduler thread, and key validation endpoints. Also includes the binary bootstrap downloader logic.
* **[editor.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/editor.py)**: The processing engine. Contains functions to extract audio via FFmpeg, invoke local Whisper models, calculate RMS loudness peaks, run combat spike detection heuristics, prompt the AI engine, parse clips, and run final FFmpeg render clips with vertical video cropping and stabilization.
* **[watcher.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/watcher.py)**: A background monitor helper that checks YouTube/Twitch channels for new streams and triggers automated clipper pipelines.
* **[config_manager.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/config_manager.py)**: Manages loading, saving, and defaulting application configurations in `%APPDATA%\jBahrsClipGenerator\config.json`.

---

## 🧪 Running Unit & Integration Tests

The repository includes a suite of unit tests for key application components.

### Running the Test Suite
Ensure your virtual environment is active and run the tests:

```powershell
python -m unittest discover -p "test_*.py"
```

### Test Files
* **[test_app.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/test_app.py)**: Tests GUI configuration validation logic, including parsing YouTube video IDs from URLs.
* **[test_config_manager.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/test_config_manager.py)**: Verifies file configuration loading, saving, defaults, and directory paths.
* **[test_editor.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/test_editor.py)**: Tests video-to-audio extraction parameters, Whisper arguments translation, and AI clip retrieval processing.
* **[test_watcher.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/test_watcher.py)**: Exercises Lookback check windows and scheduler intervals.

---

## 📦 Compilation & Packaging (PyInstaller)

To bundle the application into a standalone Windows distribution with all companion dependencies:

### 1. Automated Release Packaging
Run the automated packaging script inside your virtual environment:

```powershell
python package_release.py --version v2.0.0
```

This automated script:
1. Compiles the application using the [`ClipGen.spec`](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/ClipGen.spec) PyInstaller specification.
2. Injects the companion binary dependencies (`ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, `deno.exe`) and assets into the output bundle.
3. Generates complete, portable release archives in `dist/`:
   - `jBahrs-Clip-Generator-v2.0.0-Windows.zip` (full portable standalone application)
   - `jBahrs-Clip-Generator-v2.0.0-Dependencies-Windows.zip` (standalone companion binaries)

### 2. Building Setup Installer (Inno Setup)
To build a Windows `Setup.exe` installer, compile the provided Inno Setup script with the Inno Setup Compiler:
```powershell
iscc installer.iss
```

### 3. Automated GitHub Actions Releases
Whenever a git release tag (`v*`) is pushed to GitHub, `.github/workflows/release.yml` automatically compiles the application, runs tests, and publishes the release assets directly to GitHub Releases.
