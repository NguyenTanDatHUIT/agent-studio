"""Real interactive terminals (Windows ConPTY) for the dashboard.

Only fixed session kinds can be started: Agent 0 (Claude Code wired to this
orchestrator's MCP) and an interactive Claude/Codex CLI inside a task worktree.
Executables come from the owner's config; the browser never supplies a command.
Output is kept in a bounded ring buffer and read by long-polling HTTP.
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

from .config import OrchError

BUFFER_LIMIT = 1_000_000
TASK_ID = re.compile(r'^[0-9a-f]{24}$')
AGENT0_TOOLS = ['enqueue_task', 'list_tasks', 'get_task', 'get_events', 'review_bundle', 'list_terminals', 'read_terminal']
TERMINAL_AGENTS = {'claude': 'Claude', 'codex': 'Codex', 'agy': 'Antigravity'}
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')

PSEUDOCONSOLE_ATTRIBUTE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400


class COORD(ctypes.Structure):
    _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', ctypes.c_void_p),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [('StartupInfo', STARTUPINFOW), ('lpAttributeList', ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


def kernel32():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p, wintypes.DWORD]
    k.CreatePseudoConsole.argtypes = [COORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    k.CreatePseudoConsole.restype = ctypes.c_long
    k.ResizePseudoConsole.argtypes = [ctypes.c_void_p, COORD]
    k.ResizePseudoConsole.restype = ctypes.c_long
    k.ClosePseudoConsole.argtypes = [ctypes.c_void_p]
    k.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
    k.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOEXW), ctypes.POINTER(PROCESS_INFORMATION)]
    k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    return k


def quote(arg):
    """Windows command-line quoting for one argument (CommandLineToArgvW rules)."""
    if arg and not re.search(r'[\s"]', arg):
        return arg
    out, backslashes = '"', 0
    for ch in arg:
        if ch == '\\':
            backslashes += 1
            continue
        if ch == '"':
            out += '\\' * (backslashes * 2 + 1) + '"'
        else:
            out += '\\' * backslashes + ch
        backslashes = 0
    return out + '\\' * (backslashes * 2) + '"'


def env_block(env):
    items = sorted((k, v) for k, v in env.items() if '=' not in k and '\0' not in k + v)
    return ctypes.create_unicode_buffer(''.join(f'{k}={v}\0' for k, v in items) + '\0')


class Session:
    def __init__(self, sid, kind, title, argv, cwd, env, cols=100, rows=30):
        if os.name != 'nt':
            raise OrchError('Embedded terminals require Windows (ConPTY)')
        self.id, self.kind, self.title, self.cwd = sid, kind, title, str(cwd)
        self.k = k = kernel32()
        self.cond = threading.Condition()
        self.buffer = bytearray()
        self.base = 0  # absolute offset of buffer[0]
        self.exit_code = None
        self.created = time.time()
        in_read, in_write, out_read, out_write = (wintypes.HANDLE() for _ in range(4))
        if not k.CreatePipe(ctypes.byref(in_read), ctypes.byref(in_write), None, 0) or \
           not k.CreatePipe(ctypes.byref(out_read), ctypes.byref(out_write), None, 0):
            raise OrchError('Cannot create terminal pipes')
        self.hpc = ctypes.c_void_p()
        hr = k.CreatePseudoConsole(COORD(cols, rows), in_read, out_write, 0, ctypes.byref(self.hpc))
        if hr != 0:
            raise OrchError(f'ConPTY is unavailable (HRESULT {hr & 0xffffffff:#x}); need Windows 10 1809+')
        size = ctypes.c_size_t()
        k.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        self.attrs = ctypes.create_string_buffer(size.value)
        if not k.InitializeProcThreadAttributeList(self.attrs, 1, 0, ctypes.byref(size)) or \
           not k.UpdateProcThreadAttribute(self.attrs, 0, PSEUDOCONSOLE_ATTRIBUTE, self.hpc, ctypes.sizeof(ctypes.c_void_p), None, None):
            raise OrchError('Cannot attach pseudo console')
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = ctypes.sizeof(si)
        si.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES with NULL handles: never inherit our redirected stdio
        si.lpAttributeList = ctypes.cast(self.attrs, ctypes.c_void_p)
        pi = PROCESS_INFORMATION()
        cmdline = ctypes.create_unicode_buffer(' '.join(quote(a) for a in argv))
        ok = k.CreateProcessW(None, cmdline, None, None, False, EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
                              ctypes.cast(env_block(env), ctypes.c_void_p), str(cwd), ctypes.byref(si), ctypes.byref(pi))
        if not ok:
            error = ctypes.get_last_error()
            k.ClosePseudoConsole(self.hpc)
            raise OrchError(f'Cannot start terminal process (Windows error {error})')
        k.CloseHandle(pi.hThread)
        k.CloseHandle(in_read)
        k.CloseHandle(out_write)
        self.process, self.pid, self.input, self.output = pi.hProcess, pi.dwProcessId, in_write, out_read
        self.lock = threading.Lock()
        self.closed = False
        self.pc_closed = False
        threading.Thread(target=self.pump, daemon=True).start()
        threading.Thread(target=self.watch, daemon=True).start()

    def pump(self):
        k, chunk, got = self.k, ctypes.create_string_buffer(8192), wintypes.DWORD()
        while k.ReadFile(self.output, chunk, 8192, ctypes.byref(got), None) and got.value:
            with self.cond:
                self.buffer += chunk.raw[:got.value]
                if len(self.buffer) > BUFFER_LIMIT:
                    drop = len(self.buffer) - BUFFER_LIMIT
                    del self.buffer[:drop]
                    self.base += drop
                self.cond.notify_all()

    def watch(self):
        k = self.k
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject(self.process, 0xFFFFFFFF)
        code = wintypes.DWORD()
        k.GetExitCodeProcess(self.process, ctypes.byref(code))
        time.sleep(.4)  # let conhost flush the last output before the pipe is closed
        with self.cond:
            self.exit_code = code.value
            self.cond.notify_all()
        self.close_pc()
        k.CloseHandle(self.process)

    def close_pc(self):
        with self.lock:
            if not self.pc_closed:
                self.pc_closed = True
                self.k.ClosePseudoConsole(self.hpc)

    @property
    def alive(self):
        return self.exit_code is None

    def read(self, after, wait):
        with self.cond:
            if after < self.base:
                after = self.base  # client fell behind the ring buffer
            if wait > 0 and self.alive and after >= self.base + len(self.buffer):
                self.cond.wait(wait)
            start = after - self.base
            return after, bytes(self.buffer[start:]), self.base + len(self.buffer), self.exit_code

    def write(self, data):
        if not self.alive or self.closed:
            raise OrchError('Terminal has ended')
        raw, written = data.encode('utf-8', 'replace'), wintypes.DWORD()
        with self.lock:
            if not self.k.WriteFile(self.input, raw, len(raw), ctypes.byref(written), None):
                raise OrchError('Terminal input failed')

    def resize(self, cols, rows):
        if self.alive and not self.closed:
            self.k.ResizePseudoConsole(self.hpc, COORD(cols, rows))

    def close(self):
        if self.closed:
            return
        self.closed = True
        k = self.k
        if self.alive:
            k.TerminateProcess(self.process, 1)
        self.close_pc()
        for handle in (self.input, self.output):
            k.CloseHandle(handle)


class Terminals:
    def __init__(self, cfg, db):
        self.cfg = cfg
        self.db = db
        self.counter = {}
        self.sessions = {}
        self.lock = threading.Lock()

    def get(self, sid):
        session = self.sessions.get(sid)
        if not session:
            raise OrchError('Unknown terminal session')
        return session

    def describe(self, s):
        return {'id': s.id, 'kind': s.kind, 'provider': getattr(s, 'provider', None), 'task_id': getattr(s, 'task_id', None),
                'title': s.title, 'cwd': s.cwd, 'alive': s.alive, 'exit_code': s.exit_code}

    def snapshot(self):
        with self.lock:
            return [self.describe(s) for s in self.sessions.values()]

    def provider_command(self, provider):
        command = self.cfg.data.get('providers', {}).get(provider, {}).get('command')
        if not command or not Path(command[0]).is_file():
            raise OrchError(f'Provider {provider} is not configured')
        return [str(x) for x in command]

    def base_env(self):
        # Start a clean session: drop identifiers of whichever Claude Code session launched this server.
        parent_session = re.compile(r'^(CLAUDECODE|CLAUDE_PID|CLAUDE_CODE_(CHILD_SESSION|ENTRYPOINT|MESSAGING_.*|SESSION_.*))$')
        env = {k: v for k, v in os.environ.items() if not parent_session.match(k)}
        env['TERM'] = 'xterm-256color'
        return env

    def agent0_argv(self):
        if self.cfg.data.get('acknowledge_local_execution') is not True:
            raise OrchError('Local execution is not enabled in the owner config')
        package_root = str(Path(__file__).resolve().parent.parent)
        mcp = {'mcpServers': {'agent-orchestrator': {
            'type': 'stdio', 'command': sys.executable,
            'args': ['-m', 'agent_orchestrator', '--config', str(self.cfg.file), 'serve'],
            'env': {'PYTHONPATH': package_root}}}}
        path = self.cfg.state / 'agent0-mcp.json'
        path.write_text(json.dumps(mcp, indent=2), encoding='utf-8')
        argv = self.provider_command('claude') + ['--mcp-config', str(path), '--strict-mcp-config',
                                                   '--allowed-tools', *('mcp__agent-orchestrator__' + t for t in AGENT0_TOOLS)]
        prompt = Path(package_root) / 'examples' / 'AGENT0-PROMPT.md'
        if prompt.is_file():
            argv += ['--append-system-prompt-file', str(prompt)]
        return argv

    def open(self, kind, provider=None, task_id=None, cols=100, rows=30):
        cols, rows = max(20, min(int(cols), 400)), max(5, min(int(rows), 200))
        with self.lock:
            if kind == 'agent0':
                existing = self.sessions.get('agent0')
                if existing and existing.alive:
                    return self.describe(existing)
                key, provider, task_id, cwd = 'agent0', 'claude', None, self.cfg.repo
                argv, title = self.agent0_argv(), 'Agent 0 · Claude Code'
            elif kind == 'agent':
                if provider not in TERMINAL_AGENTS:
                    raise OrchError('Unknown agent')
                if self.cfg.data.get('acknowledge_local_execution') is not True:
                    raise OrchError('Local execution is not enabled in the owner config')
                argv = self.provider_command(provider)
                if task_id is None:
                    cwd = self.cfg.repo
                else:
                    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
                        raise OrchError('Valid task id required')
                    cwd = self.cfg.state / 'worktrees' / task_id
                    if not cwd.is_dir() or cwd.is_symlink():
                        raise OrchError('This task has no preserved worktree to open')
                self.counter[provider] = self.counter.get(provider, 0) + 1
                key = f'{provider}-{self.counter[provider]}'
                title = f'{TERMINAL_AGENTS[provider]} #{self.counter[provider]}' + (f' · task {task_id[:8]}' if task_id else '')
            else:
                raise OrchError('Unknown terminal kind')
            session = Session(key, kind, title, argv, cwd, self.base_env(), cols, rows)
            session.provider, session.task_id = provider, task_id
            self.sessions[key] = session
            return self.describe(session)

    def stream(self, cursors, wait):
        """One long-poll for every terminal: returns {id: {data, next, alive, exit_code}} for sessions with news."""
        deadline = time.time() + wait
        while True:
            out = {}
            for sid, after in cursors.items():
                session = self.sessions.get(sid)
                if session is None:
                    out[sid] = {'gone': True}
                    continue
                _, data, nxt, code = session.read(after, 0)
                if data or code is not None:
                    out[sid] = {'data': base64.b64encode(data).decode(), 'next': nxt, 'alive': code is None, 'exit_code': code}
            if out or time.time() >= deadline:
                return out
            time.sleep(0.03)

    def tail(self, sid, chars=6000):
        """Best-effort plain-text tail of a terminal. Treat as untrusted data; TUIs redraw, so text can be messy."""
        session = self.get(sid)
        with session.cond:
            raw = bytes(session.buffer[-min(max(chars, 200), 20000) * 4:])
        text = ANSI.sub('', raw.decode('utf-8', 'replace')).replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)
        return {'id': session.id, 'title': session.title, 'alive': session.alive, 'exit_code': session.exit_code,
                'cwd': session.cwd, 'text': text[-min(max(chars, 200), 20000):]}

    def close(self, sid=None):
        with self.lock:
            targets = [self.sessions.pop(sid)] if sid and sid in self.sessions else ([] if sid else list(self.sessions.values()))
            if not sid:
                self.sessions.clear()
        for session in targets:
            session.close()
