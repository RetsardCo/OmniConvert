"""Safe subprocess runner using argument arrays, timeouts, output capture, and process cancellation."""

import subprocess
import time
import logging
import os
from typing import List, Optional, Tuple, Callable, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SubprocessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False

class SafeSubprocessRunner:
    """Executes external binaries (e.g. ffmpeg, ffprobe, libreoffice) safely."""

    def __init__(self):
        self._current_process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def run(
        self,
        args: List[str],
        timeout: Optional[float] = 300.0,
        cwd: Optional[str] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> SubprocessResult:
        """
        Execute command with argument array (never shell=True).
        Supports live cancellation via is_cancelled callback and timeout enforcement.
        """
        self._is_cancelled = False
        logger.info("Executing safe subprocess: %s", " ".join(args))

        try:
            if is_cancelled and is_cancelled():
                return SubprocessResult(returncode=-1, stdout="", stderr="", cancelled=True)

            # Creation flag to prevent popup console windows on Windows
            creationflags = 0
            try:
                creationflags = subprocess.CREATE_NO_WINDOW
            except AttributeError:
                pass

            process_env = None
            if env is not None:
                process_env = os.environ.copy()
                process_env.update(env)

            self._current_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                env=process_env,
                creationflags=creationflags
            )

            start_time = time.monotonic()
            poll_interval = 0.05
            stdout, stderr = "", ""

            while True:
                if self._is_cancelled or (is_cancelled and is_cancelled()):
                    self._is_cancelled = True
                    self._terminate_process()
                    try:
                        stdout, stderr = self._current_process.communicate(timeout=1.0)
                    except Exception:
                        pass
                    return SubprocessResult(
                        returncode=-1,
                        stdout=stdout,
                        stderr=stderr,
                        cancelled=True
                    )

                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)
                    step = min(poll_interval, remaining)
                else:
                    step = poll_interval

                try:
                    stdout, stderr = self._current_process.communicate(timeout=step)
                    break
                except subprocess.TimeoutExpired:
                    continue

            returncode = self._current_process.returncode

            if self._is_cancelled or (is_cancelled and is_cancelled()):
                return SubprocessResult(
                    returncode=-1,
                    stdout=stdout,
                    stderr=stderr,
                    cancelled=True
                )

            return SubprocessResult(
                returncode=returncode,
                stdout=stdout,
                stderr=stderr
            )

        except subprocess.TimeoutExpired:
            logger.warning("Subprocess timed out after %s seconds: %s", timeout, args)
            self._terminate_process()
            stdout, stderr = "", ""
            if self._current_process:
                try:
                    stdout, stderr = self._current_process.communicate(timeout=2.0)
                except Exception:
                    pass
            return SubprocessResult(
                returncode=-1,
                stdout=stdout,
                stderr=stderr,
                timed_out=True
            )

        except Exception as e:
            logger.error("Failed to start subprocess %s: %s", args, e)
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=str(e)
            )
        finally:
            self._current_process = None

    def cancel(self):
        """Cancel the running subprocess immediately."""
        self._is_cancelled = True
        self._terminate_process()

    def _terminate_process(self):
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=2.0)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass
