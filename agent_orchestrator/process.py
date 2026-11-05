"""Bounded process IO; shell=False; process-tree timeout/cancellation.

The Windows Job Object is lifecycle control, NOT a security sandbox.
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time

from .config import OrchError, command


class Job:
    def __init__(self, process):
        self.handle = None
        if os.name != 'nt':
            return
        import ctypes as c
        from ctypes import wintypes as w

        class BASIC(c.Structure):
            _fields_ = [('ProcessTime', c.c_int64), ('JobTime', c.c_int64),
                        ('LimitFlags', w.DWORD), ('MinWS', c.c_size_t), ('MaxWS', c.c_size_t),
                        ('ActiveProcessLimit', w.DWORD), ('Affinity', c.c_size_t),
                        ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]

        class IO(c.Structure):
            _fields_ = [(n, c.c_uint64) for n in ('ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes', 'OtherBytes')]

        class EXTENDED(c.Structure):
            _fields_ = [('Basic', BASIC), ('Io', IO), ('ProcessMemoryLimit', c.c_size_t),
                        ('JobMemoryLimit', c.c_size_t), ('PeakProcessMemoryUsed', c.c_size_t),
                        ('PeakJobMemoryUsed', c.c_size_t)]

        k = c.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.CloseHandle.argtypes = [w.HANDLE]
        self.k = k
        handle = k.CreateJobObjectW(None, None)
        info = EXTENDED()
        info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not handle or not k.SetInformationJobObject(handle, 9, c.byref(info), c.sizeof(info)) or not k.AssignProcessToJobObject(handle, int(process._handle)):
            if handle:
                k.CloseHandle(handle)
            process.kill()
            process.wait()
            raise OrchError("Cannot attach Windows Job Object; refusing unsupervised execution")
        self.handle = handle

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


def run(argv, cwd, env, timeout, limit, output_dir, stdin='', cancelled=lambda: False):
    command(argv)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    exceeded = threading.Event()
    sizes = [0, 0]
    errors = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    p = subprocess.Popen(argv, cwd=cwd, env=env, shell=False, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=flags, start_new_session=os.name != 'nt')
    job = Job(p)

    def drain(pipe, filename, index):
        try:
            with (output_dir / filename).open('wb') as f:
                while block := pipe.read1(8192):
                    remaining = max(0, limit - sizes[index])
                    f.write(block[:remaining])
                    f.flush()
                    sizes[index] += len(block)
                    if sizes[index] > limit:
                        exceeded.set()
        except Exception as exc:
            errors.append(str(exc))
            exceeded.set()
        finally:
            pipe.close()

    def feed():
        try:
            p.stdin.write(stdin.encode('utf-8'))
            p.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    threads = [threading.Thread(target=drain, args=(p.stdout, 'stdout.log', 0), daemon=True),
               threading.Thread(target=drain, args=(p.stderr, 'stderr.log', 1), daemon=True),
               threading.Thread(target=feed, daemon=True)]
    for thread in threads:
        thread.start()
    reason = None
    try:
        while p.poll() is None:
            if cancelled():
                reason = 'cancelled'
            elif exceeded.is_set():
                reason = 'output_limit'
            elif time.monotonic() - started > timeout:
                reason = 'timeout'
            if reason:
                break
            time.sleep(.05)
    finally:
        # Close the Job even on normal exit: detached children must not survive.
        if os.name == 'nt':
            job.close()
        else:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        p.wait()
        for thread in threads:
            thread.join(timeout=5)
        if any(t.is_alive() for t in threads):
            reason = reason or 'io_incomplete'
    if exceeded.is_set():
        reason = reason or 'output_limit'
    return {'exit_code': p.returncode, 'reason': reason, 'elapsed_seconds': round(time.monotonic()-started, 3),
            'stdout_bytes': sizes[0], 'stderr_bytes': sizes[1], 'io_errors': errors}
