#!/usr/bin/env python3
"""The orthogonality index writer lock: `refresh.lock` in the index directory (re-exported by `_archstate`).

Taken with O_CREAT|O_EXCL and holding "pid timestamp host". It is broken when older than LOCK_STALE_SECONDS,
the fallback, or at once when its holder ran on this host and no longer runs: a closed session, `-p`
teardown, Ctrl+C or a hook timeout can kill a background refresh mid-pass, and nothing else would clear
its lock for ten minutes. A pid that now names a process started after the lock was taken was reused, so
that lock is orphaned too. A lock from another host, or in the older "pid timestamp" form, is judged by
age alone. A live holder touches the lock at every batch commit, so a long pass is never taken for stale,
and releases only a lock it still owns.

Liveness: `os.kill(pid, 0)` and /proc on POSIX (macOS has no /proc, so a live pid there counts as the
holder). On Windows, OpenProcess, GetExitCodeProcess and GetProcessTimes through ctypes: os.kill(pid, 0)
would send CTRL_C_EVENT there, and any other signal value terminates the process.
"""
import os
import socket
import time

LOCK_NAME = "refresh.lock"
LOCK_STALE_SECONDS = 600
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_INVALID_PARAMETER = 87
STILL_ACTIVE = 259
FILETIME_EPOCH = 116444736000000000  # 100-ns intervals between 1601-01-01 and 1970-01-01
_WINDOWS = {}


def acquire_lock(directory):
    """True when this process now holds the writer lock (a stale or orphaned lock is broken first)."""
    path = os.path.join(directory, LOCK_NAME)
    os.makedirs(directory, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ("%d %f %s" % (os.getpid(), time.time(), _host())).encode("utf-8"))
            os.close(fd)
            return True
        except OSError:
            if not _break_stale(path):
                return False
    return False


def _break_stale(path):
    try:
        if time.time() - os.path.getmtime(path) < LOCK_STALE_SECONDS and not orphaned(path):
            return False
        os.remove(path)
        return True
    except OSError:
        return False


def release_lock(directory):
    """Remove the lock unless another writer took it over (after breaking this process's lock as stale)."""
    path = os.path.join(directory, LOCK_NAME)
    holder = _holder(path)
    if holder is None or holder[0] == os.getpid():
        try:
            os.remove(path)
        except OSError:
            pass


def touch_lock(directory):
    """Move the lock's mtime to now, so a holder that is still working is never taken for stale."""
    try:
        os.utime(os.path.join(directory, LOCK_NAME), None)
    except OSError:
        pass


def lock_held(directory):
    """True while a live writer holds the lock (a stale or orphaned lock is not held)."""
    path = os.path.join(directory, LOCK_NAME)
    try:
        return time.time() - os.path.getmtime(path) < LOCK_STALE_SECONDS and not orphaned(path)
    except OSError:
        return False


def _host():
    try:
        return socket.gethostname() or "-"
    except OSError:
        return "-"


def _holder(path):
    """(pid, timestamp, host) of a lock file; None when unreadable or in the older "pid timestamp" form."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            parts = handle.read().split(" ", 2)
        return (int(parts[0]), float(parts[1]), parts[2].strip()) if len(parts) == 3 else None
    except (OSError, ValueError):
        return None


def orphaned(path):
    """True when the lock's holder ran on this host and is gone, or its pid now names a newer process."""
    holder = _holder(path)
    if holder is None or holder[2] != _host() or holder[0] == os.getpid():
        return False
    started = process_started(holder[0])
    return started is None or started > holder[1] + 1.0


def process_started(pid):
    """Epoch seconds process `pid` started; 0.0 when it runs but its start is unknown; None when it does not run."""
    if os.name == "nt":
        return _windows_started(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except OSError:
        return 0.0
    return _proc_started(pid)


def _proc_started(pid):
    """From /proc/<pid>/stat (field 22: clock ticks after boot); None for a zombie; 0.0 without /proc."""
    try:
        with open("/proc/%d/stat" % pid, encoding="ascii", errors="replace") as handle:
            fields = handle.read().rsplit(")", 1)[1].split()
        with open("/proc/stat", encoding="ascii", errors="replace") as handle:
            boot = next(float(line.split()[1]) for line in handle if line.startswith("btime "))
        return None if fields[0] == "Z" else boot + int(fields[19]) / float(os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError, StopIteration):
        return 0.0


def _kernel32():
    """(kernel32, ctypes, wintypes) with argument types declared, so a 64-bit HANDLE is never truncated."""
    if not _WINDOWS:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        _WINDOWS.update(kernel32=kernel32, ctypes=ctypes, wintypes=wintypes)
    return _WINDOWS["kernel32"], _WINDOWS["ctypes"], _WINDOWS["wintypes"]


def _windows_started(pid):
    kernel32, ctypes, wintypes = _kernel32()
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None if ctypes.get_last_error() == ERROR_INVALID_PARAMETER else 0.0
    try:
        code, times = wintypes.DWORD(), [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return 0.0
        if code.value != STILL_ACTIVE:
            return None
        if not kernel32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            return 0.0
        return ((times[0].dwHighDateTime << 32) + times[0].dwLowDateTime - FILETIME_EPOCH) / 1e7
    finally:
        kernel32.CloseHandle(handle)
