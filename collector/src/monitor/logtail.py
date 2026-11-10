"""Thread-safe incremental reader for append-only logs with rotation support."""

import os
from pathlib import Path
from threading import Lock


class LogTail:
    """Read complete new lines while tracking inode replacement and truncation.

    By default existing content is skipped on process start: the collector cannot
    claim a rate for historical log lines without knowing their collection window.
    """

    def __init__(self, path: Path, start_at_end: bool = True) -> None:
        self.path = Path(path)
        self._start_at_end = start_at_end
        self._lock = Lock()
        self._identity: tuple[int, int] | None = None
        self._offset = 0
        self._pending = b""
        self._seen_file = False
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            return
        self._identity = (stat.st_dev, stat.st_ino)
        self._offset = stat.st_size if start_at_end else 0
        self._seen_file = True

    def read_new_lines(self) -> list[str]:
        with self._lock:
            with self.path.open("rb") as stream:
                file_stat = os.fstat(stream.fileno())
                identity = (file_stat.st_dev, file_stat.st_ino)

                if identity != self._identity:
                    self._identity = identity
                    self._offset = (
                        file_stat.st_size
                        if not self._seen_file and self._start_at_end
                        else 0
                    )
                    self._pending = b""
                    self._seen_file = True
                elif file_stat.st_size < self._offset:
                    self._offset = 0
                    self._pending = b""

                stream.seek(self._offset)
                chunk = stream.read()
                self._offset = stream.tell()

            complete = self._pending + chunk
            parts = complete.split(b"\n")
            self._pending = parts.pop()
            return [part.rstrip(b"\r").decode("utf-8", errors="replace") for part in parts]
