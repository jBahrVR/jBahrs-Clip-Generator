import os
import subprocess
import time
import queue
import threading
from typing import List, Optional, Callable, Tuple

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
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        if logger_callback:
            logger_callback(f"❌ Failed to start subprocess: {e}")
        return -1

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
            process.terminate()
            # Give it a moment to terminate gracefully, then kill if necessary
            for _ in range(20):
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            else:
                process.kill()
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
    return process.returncode

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
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return -1, b"", str(e).encode()

