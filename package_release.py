"""Release packaging script for jBahr's Clip Generator.

Builds the standalone application using PyInstaller, bundles required companion
binaries (ffmpeg, ffprobe, yt-dlp, deno), and generates distribution archives.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import argparse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERSION = "v2.0.0"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
APP_DIST_DIR = os.path.join(DIST_DIR, "jBahrs-Clip-Generator")

COMPANION_BINARIES = ["ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe", "deno.exe"]

def clean_build_artifacts():
    print("🧹 Cleaning previous build and dist directories...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

def run_pyinstaller():
    print(f"📦 Compiling jBahr's Clip Generator with PyInstaller...")
    pyinstaller_exe = os.path.join(PROJECT_DIR, ".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    spec_file = os.path.join(PROJECT_DIR, "ClipGen.spec")
    cmd = [pyinstaller_exe, "--noconfirm", spec_file]

    ret = subprocess.call(cmd, cwd=PROJECT_DIR)
    if ret != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {ret}")
    print("✅ PyInstaller build completed successfully.")

def copy_companion_dependencies():
    print("🚚 Injecting companion binary dependencies and documentation...")
    if not os.path.exists(APP_DIST_DIR):
        raise FileNotFoundError(f"App dist directory not found: {APP_DIST_DIR}")

    # Copy external binaries
    for binary in COMPANION_BINARIES:
        src = os.path.join(PROJECT_DIR, binary)
        if os.path.exists(src):
            dst = os.path.join(APP_DIST_DIR, binary)
            shutil.copy2(src, dst)
            print(f"  + Bundled {binary} ({os.path.getsize(src):,} bytes)")
        else:
            print(f"  ⚠️ Warning: {binary} not found in project root; skipping.")

    # Copy documentation & assets
    for doc in ["readme.md", "requirements.txt", "app_icon.ico"]:
        src = os.path.join(PROJECT_DIR, doc)
        if os.path.exists(src):
            dst = os.path.join(APP_DIST_DIR, doc)
            shutil.copy2(src, dst)
            print(f"  + Copied {doc}")

def create_release_archives(version_tag):
    print("🗜️ Creating release ZIP archives...")
    release_zip_name = f"jBahrs-Clip-Generator-{version_tag}-Windows.zip"
    release_zip_path = os.path.join(DIST_DIR, release_zip_name)

    print(f"  -> Creating {release_zip_name}...")
    with zipfile.ZipFile(release_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(APP_DIST_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, DIST_DIR)
                zf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(release_zip_path) / (1024 * 1024)
    print(f"✅ Created main release package: {release_zip_path} ({zip_size_mb:.1f} MB)")

    # Create companion dependencies package
    deps_zip_name = f"jBahrs-Clip-Generator-{version_tag}-Dependencies-Windows.zip"
    deps_zip_path = os.path.join(DIST_DIR, deps_zip_name)
    with zipfile.ZipFile(deps_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for binary in COMPANION_BINARIES:
            src = os.path.join(PROJECT_DIR, binary)
            if os.path.exists(src):
                zf.write(src, binary)
    deps_size_mb = os.path.getsize(deps_zip_path) / (1024 * 1024)
    print(f"✅ Created dependencies standalone package: {deps_zip_path} ({deps_size_mb:.1f} MB)")

    return release_zip_path, deps_zip_path

def main():
    parser = argparse.ArgumentParser(description="Package jBahr's Clip Generator for release")
    parser.add_argument("--version", default=VERSION, help="Release version tag (e.g. v2.0.0)")
    parser.add_argument("--skip-compile", action="store_true", help="Skip PyInstaller compilation and only package existing dist")
    args = parser.parse_args()

    print(f"==================================================")
    print(f"🎬 Packaging jBahr's Clip Generator {args.version}")
    print(f"==================================================")

    if not args.skip_compile:
        clean_build_artifacts()
        run_pyinstaller()

    copy_companion_dependencies()
    release_zip, deps_zip = create_release_archives(args.version)

    print("\n🎉 Release packaging completed successfully!")
    print(f"Release files located in: {DIST_DIR}")
    print(f"1. {os.path.basename(release_zip)} ({os.path.getsize(release_zip) / (1024 * 1024):.1f} MB)")
    print(f"2. {os.path.basename(deps_zip)} ({os.path.getsize(deps_zip) / (1024 * 1024):.1f} MB)")

if __name__ == "__main__":
    main()
