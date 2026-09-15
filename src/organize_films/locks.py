"""Detection of a file exclusively locked by another process.

A large video is often still being downloaded when the library is scanned.
Moving it mid-download would either fail loudly or, with a naive
copy-fallback, leave a truncated duplicate behind — the exact failure this
module exists to catch ahead of time instead of after the fact.
"""

import os
from pathlib import Path

# Windows' ERROR_SHARING_VIOLATION: another process holds the file without
# granting the share mode this attempt needs. This is exactly the failure
# `Path.rename` raises for a file a download client is still writing to.
# Public so the executor can recognize the same failure on a race-condition
# retry (a file locked after planning, before the move was attempted).
SHARING_VIOLATION_WINERROR = 32


def is_locked_for_writing(path: Path) -> bool:
    """Return whether ``path`` is held open by another process.

    A pure probe: it opens the file for read-write access and immediately
    closes it, without reading, writing, or renaming anything. Windows-only
    signal — on platforms without mandatory locking this always reports the
    file as free, since nothing prevents the move from being attempted there.

    Args:
        path: File to probe. Must exist.

    Returns:
        ``True`` when the file cannot be opened due to another process's
        lock (typically a download still in progress); ``False`` otherwise,
        including for unrelated errors, which are left for the move itself
        to report accurately.
    """
    try:
        file_descriptor = os.open(str(path), os.O_RDWR)
    except OSError as error:
        return getattr(error, "winerror", None) == SHARING_VIOLATION_WINERROR
    os.close(file_descriptor)
    return False
