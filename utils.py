import os
import sys
import re
import subprocess
import time
import queue
import threading
from typing import List, Optional, Callable, Tuple, Set

def redact_sensitive(text: str) -> str:
    """Redacts Discord webhook URLs and API keys from logs and display."""
    if not isinstance(text, str):
        return text
    # Redact Discord webhook tokens: https://discord.com/api/webhooks/<id>/<token>
    text = re.sub(
        r'https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/(\d+)/[A-Za-z0-9_-]+',
        r'https://discord.com/api/webhooks/\1/[REDACTED]',
        text
    )
    # Redact OpenAI keys
    text = re.sub(r'sk-[A-Za-z0-9_-]{20,}', '[REDACTED_API_KEY]', text)
    # Redact Anthropic keys
    text = re.sub(r'sk-ant-[A-Za-z0-9_-]{20,}', '[REDACTED_API_KEY]', text)
    # Redact Google AI Studio keys
    text = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_API_KEY]', text)
    return text

_ACTIVE_PROCESSES: Set[subprocess.Popen] = set()
_PROCESS_LOCK = threading.Lock()

def register_process(proc: subprocess.Popen) -> None:
    """Registers an active subprocess for lifecycle tracking."""
    if proc is not None:
        with _PROCESS_LOCK:
            _ACTIVE_PROCESSES.add(proc)

def unregister_process(proc: subprocess.Popen) -> None:
    """Unregisters a finished subprocess."""
    if proc is not None:
        with _PROCESS_LOCK:
            _ACTIVE_PROCESSES.discard(proc)

def kill_process_tree(proc: subprocess.Popen) -> None:
    """Terminates a process and all its child processes on Windows or POSIX."""
    if proc is None:
        return
    try:
        proc.terminate()
    except Exception:
        pass

    if os.name == 'nt' and hasattr(proc, 'pid') and proc.pid:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except Exception:
            pass

def cleanup_all_processes() -> None:
    """Terminates all currently registered active subprocesses."""
    with _PROCESS_LOCK:
        procs = list(_ACTIVE_PROCESSES)
    for p in procs:
        try:
            if p.poll() is None:
                kill_process_tree(p)
        except Exception:
            pass

def _reader_thread(stream, q: queue.Queue) -> None:
    """Reads lines from a stream and puts them into a queue."""
    try:
        for line in iter(stream.readline, ""):
            q.put(line)
    except Exception:
        pass
    finally:
        q.put(None)  # Sentinel to indicate EOF


def run_subprocess_command(
    cmd: List[str],
    logger_callback: Optional[Callable[[str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    cwd: Optional[str] = None
) -> int:
    """
    Runs a subprocess command, configuring startupinfo to hide windows on Windows.
    Optionally logs output line-by-line via logger_callback and supports cancellation.
    Returns the exit code of the process.
    """
    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO()  # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE  # type: ignore

    try:
        # We redirect stderr to stdout to capture everything in one stream.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            startupinfo=startupinfo,
            bufsize=1,
            universal_newlines=True,
            cwd=cwd
        )
        register_process(process)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        if logger_callback:
            logger_callback(f"❌ Failed to start subprocess: {e}")
        return -1

    try:
        q: queue.Queue = queue.Queue()
        t = threading.Thread(target=_reader_thread, args=(process.stdout, q), daemon=True)
        t.start()

        cancelled = False
        while True:
            # Check cancellation
            if is_cancelled and is_cancelled():
                cancelled = True
                if logger_callback:
                    logger_callback("🛑 Cancellation requested. Terminating subprocess...")
                kill_process_tree(process)
                # Give it a moment to terminate gracefully, then kill if necessary
                for _ in range(20):
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                else:
                    try:
                        process.kill()
                    except Exception:
                        pass
                break

            # Check queue for new lines
            try:
                line = q.get_nowait()
                if line is None:
                    # Sentinel reached, end of stream
                    break
                
                # Forward the line to the logger callback if registered
                if logger_callback:
                    logger_callback(line)
            except queue.Empty:
                # Check if process has terminated
                if process.poll() is not None:
                    # Process exited but queue might still have data; check one last time.
                    time.sleep(0.05)
                    while not q.empty():
                        line = q.get()
                        if line is not None and logger_callback:
                            logger_callback(line)
                    break
                time.sleep(0.1)

        t.join(timeout=1.0)
        
        if cancelled:
            return -1

        try:
            process.wait(timeout=5)
        except Exception:
            pass

        return process.returncode if process.returncode is not None else 0
    finally:
        unregister_process(process)

def run_subprocess_binary(
    cmd: List[str],
    cwd: Optional[str] = None
) -> Tuple[int, bytes, bytes]:
    """
    Runs a subprocess command that produces binary output, configuring startupinfo
    to hide windows on Windows.
    Returns a tuple of (returncode, stdout_bytes, stderr_bytes).
    """
    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO()  # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE  # type: ignore

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            cwd=cwd
        )
        register_process(process)
        try:
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        finally:
            unregister_process(process)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return -1, b"", str(e).encode()


def ensure_app_dir_in_path() -> None:
    """
    Ensures the application's root directory (and executable directory if frozen)
    is present at the front of os.environ["PATH"].
    This ensures bundled/local binaries like ffmpeg.exe and yt-dlp.exe can be
    discovered by subprocess calls regardless of the current working directory.
    """
    dirs_to_add = []
    if getattr(sys, 'frozen', False):
        dirs_to_add.append(os.path.dirname(sys.executable))

    # Path of this file (utils.py is at the root of the project)
    dirs_to_add.append(os.path.dirname(os.path.abspath(__file__)))

    current_path = os.environ.get("PATH", "")
    existing_paths = [os.path.normcase(os.path.normpath(p)) for p in current_path.split(os.pathsep) if p]

    entries_to_prepend = []
    for d in dirs_to_add:
        norm_d = os.path.normcase(os.path.normpath(d))
        if norm_d and norm_d not in existing_paths and os.path.exists(d):
            entries_to_prepend.append(os.path.abspath(d))
            existing_paths.insert(0, norm_d)

    if entries_to_prepend:
        os.environ["PATH"] = os.pathsep.join(entries_to_prepend) + os.pathsep + current_path


# Ensure application directory is in PATH as soon as utils is loaded
ensure_app_dir_in_path()

