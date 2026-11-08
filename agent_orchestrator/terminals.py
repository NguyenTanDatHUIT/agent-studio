"""Real interactive terminals (Windows ConPTY) for the dashboard.

Only fixed session kinds can be started: Agent 0 (Claude Code wired to this
orchestrator's MCP) and an interactive Claude/Codex CLI inside a task worktree.
Executables come from the owner's config; the browser never supplies a command.
Output is kept in a bounded ring buffer and read by long-polling HTTP.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
import time
import unicodedata
from ctypes import wintypes
from datetime import datetime, timezone, timedelta
import uuid
from pathlib import Path

from .config import OrchError, inside
from .providers import SESSION
from .transcripts import append_transcript_entry
from .store import now

BUFFER_LIMIT = 1_000_000
MAX_SESSIONS = 12
SEND_LIMIT = 4000      # characters Agent 0 may type into one terminal per call
SEND_INTERVAL = 1.0    # minimum seconds between two sends to the same terminal
OPEN_INTERVAL = 2.0    # minimum seconds between two terminals opened by Agent 0
TASK_ID = re.compile(r'^[0-9a-f]{24}$')
STAGE = re.compile(r'^[\w.-]{1,64}$')
AGENT0_TOOLS = ['enqueue_task', 'enqueue_plan', 'list_workflows', 'cancel_workflow', 'list_repos', 'list_tasks', 'get_task', 'get_events', 'review_bundle', 'list_terminals', 'read_terminal', 'list_agents']
NOTICE_INTERVAL = 5.0  # seconds between automatic notices typed into Agent 0
TERMINAL_AGENTS = {'claude': 'Claude', 'codex': 'Codex', 'agy': 'Antigravity'}
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')
# Every C0/C1 control character except TAB and LF. This removes ESC, so text coming from a task log
# (or typed by an agent) can never inject terminal escape sequences into a dashboard terminal.
CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]')
FINAL_STATUS = {'awaiting_review', 'approved', 'changes_requested', 'failed', 'cancelled'}
OK_STATUS = {'awaiting_review', 'approved'}
STATUS_TEXT = {'awaiting_review': 'chờ review', 'approved': 'đã duyệt', 'changes_requested': 'cần chỉnh sửa',
               'failed': 'thất bại', 'cancelled': 'đã hủy'}
ACTIVE_RUNNER = {'idle', 'polling', 'busy', 'starting'}


def clean(text):
    """Plain text safe to print into a terminal: no escape sequences, CR normalised to LF."""
    return CONTROL.sub('', str(text).replace('\r\n', '\n').replace('\r', '\n'))

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
    def __init__(self, sid, kind, title, argv, cwd, env, cols=100, rows=30,
                 conversation_id=None, transcript_path=None, session_id=None,
                 on_title=None, on_exit=None, resumed=False):
        if os.name != 'nt':
            raise OrchError('Embedded terminals require Windows (ConPTY)')
        self.id, self.kind, self.title, self.cwd = sid, kind, title, str(cwd)
        self.conversation_id = conversation_id
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.session_id = session_id
        self.on_title = on_title
        self.on_exit = on_exit
        self.resumed = resumed
        self.input_accumulator = ''
        self.first_input_done = False
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
            raw_chunk = chunk.raw[:got.value]
            with self.cond:
                self.buffer += raw_chunk
                if len(self.buffer) > BUFFER_LIMIT:
                    drop = len(self.buffer) - BUFFER_LIMIT
                    del self.buffer[:drop]
                    self.base += drop
                self.cond.notify_all()
            if self.transcript_path:
                try:
                    append_transcript_entry(self.transcript_path, raw_chunk.decode('utf-8', 'replace'))
                except Exception:
                    pass

    def watch(self):
        k = self.k
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject(self.process, 0xFFFFFFFF)
        code = wintypes.DWORD()
        k.GetExitCodeProcess(self.process, ctypes.byref(code))
        time.sleep(.4)  # let conhost flush the last output before the pipe is closed
        with self.cond:
            self.exit_code = code.value
            if self.resumed and self.exit_code != 0:
                msg = b"\r\n\x1b[31;1m[AO] Khong the resume phien cu (session khong con hoac loi khoi dong).\r\nDe nghi mo 'Xem lai' de xem ban ghi man hinh truoc do.\x1b[0m\r\n"
                self.buffer += msg
            self.cond.notify_all()
        if self.on_exit:
            try:
                self.on_exit(code.value)
            except Exception:
                pass
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

    def write(self, data, system=False):
        if not self.alive or self.closed:
            raise OrchError('Terminal has ended')
        if not system:
            self.last_input = time.time()  # a person is typing: the dashboard must not interleave its own notices
            if not self.first_input_done and isinstance(data, str):
                self.input_accumulator += data
                if '\r' in self.input_accumulator or '\n' in self.input_accumulator or len(self.input_accumulator) >= 80:
                    first_line = clean(self.input_accumulator).strip().split('\n')[0].split('\r')[0][:80]
                    if first_line:
                        self.first_input_done = True
                        if self.on_title:
                            try:
                                self.on_title(first_line)
                            except Exception:
                                pass
        if isinstance(data, str):
            data = unicodedata.normalize('NFC', data)
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


class AgentView:
    """Read-only live window for one numbered queue agent ("codex 1").

    It follows the agent's current task round by round, so "codex 1, continue..." keeps printing into the same
    window. The worker itself still runs headless under the supervised runner, because the engine needs its
    structured result; this view tails the task's events and log files. It never accepts input.
    """
    kind = 'worker'

    def __init__(self, sid, row, db, state_dir, runner_state=lambda: {}):
        self.id, self.provider, self.agent = sid, row['provider'], row['n']
        self.title = f"Agent {self.agent} · {TERMINAL_AGENTS.get(self.provider, self.provider)}"
        self.db, self.state_dir, self.runner_state = db, Path(state_dir), runner_state
        self.cwd = str(self.state_dir / 'worktrees')
        self.task_id, self.round, self.idle, self.remember = None, 0, False, True
        self.cond = threading.Condition()
        self.buffer = bytearray()
        self.base = 0
        self.exit_code = None
        self.created = self.last_emit = time.time()
        self.closed = False
        self.stop = threading.Event()
        self.seq, self.offsets, self.partial = 0, {}, {}
        self.segment_done, self.started, self.hinted, self.final_seen = True, time.time(), False, False
        self.thread = threading.Thread(target=self.run, daemon=True, name=f'agent-view-{self.agent}')
        self.thread.start()

    @property
    def alive(self):
        return self.exit_code is None

    @property
    def key(self):
        return f'{self.task_id}:{self.round}'

    def emit(self, text, color=None):
        text = clean(text).rstrip('\n')
        if not text:
            return
        out = ''.join((f'\x1b[{color}m{line}\x1b[0m' if color else line) + '\r\n' for line in text.split('\n'))
        raw = out.encode('utf-8', 'replace')
        with self.cond:
            self.buffer += raw
            if len(self.buffer) > BUFFER_LIMIT:
                drop = len(self.buffer) - BUFFER_LIMIT
                del self.buffer[:drop]
                self.base += drop
            self.last_emit = time.time()
            self.cond.notify_all()
        if getattr(self, 'transcript_path', None):
            try:
                append_transcript_entry(self.transcript_path, text)
            except Exception:
                pass

    def finish(self, code):
        with self.cond:
            if self.exit_code is None:
                self.exit_code = code
            self.cond.notify_all()

    def read(self, after, wait):
        with self.cond:
            if after < self.base:
                after = self.base
            if wait > 0 and self.alive and after >= self.base + len(self.buffer):
                self.cond.wait(wait)
            start = after - self.base
            return after, bytes(self.buffer[start:]), self.base + len(self.buffer), self.exit_code

    def write(self, data):
        raise OrchError(f'Cửa sổ này chỉ để theo dõi (chỉ đọc). Giao việc cho {self.provider} {self.agent} bằng enqueue_task(agent={self.agent}).')

    def resize(self, cols, rows):
        pass

    def close(self):
        self.closed = True
        self.stop.set()
        self.finish(0)
        if threading.current_thread() is not self.thread:
            self.thread.join(3)

    # ---- following the agent --------------------------------------------------------------------------
    def run(self):
        try:
            self.follow()
        except Exception as exc:  # a mirror must never hang or crash the dashboard
            self.emit(f'✗ Không theo dõi được agent ({type(exc).__name__}). Xem tab Nhiệm vụ.', '31')
            self.finish(1)

    def follow(self):
        current, first = None, True
        while not self.stop.is_set():
            try:
                row = self.db.agent_get(self.agent)
                task = None
                if row and row['thread_task']:
                    try:
                        task = self.db.get(row['thread_task'])
                    except OrchError:
                        task = None  # the task row vanished
            except sqlite3.Error:
                self.stop.wait(1)
                continue
            if row is None:
                self.emit('✗ Agent không còn trong cơ sở dữ liệu.', '31')
                return self.finish(1)
            self.remember = row['settings'].get('remember_context', bool(self.db.setting('default_remember', True)))
            if task is None:
                if first:
                    first = False
                    self.emit(f'⏸ {self.title} chưa có task. Nhớ ngữ cảnh: {"bật" if self.remember else "tắt"}.', '2')
                self.idle = True
                self.stop.wait(.6)
                continue
            key = (task['id'], task.get('round', 1))
            if key != current:
                if first and task['status'] in FINAL_STATUS:
                    # Opened on finished work: do not replay history, just show where this agent stands.
                    self.task_id, self.round = key
                    self.cwd = str(self.state_dir / 'worktrees' / task['id'])
                    self.seq = self.db.last_event_seq(task['id'])
                    self.emit(f'⏸ {self.title} sẵn sàng. Task gần nhất {task["id"][:8]} vòng {key[1]}: '
                              f'{STATUS_TEXT.get(task["status"], task["status"])}. Nhớ ngữ cảnh: {"bật" if self.remember else "tắt"}.', '2')
                    reason = str((task.get('result') or {}).get('error') or '')[:300]
                    if reason and task['status'] in {'failed', 'cancelled'}:
                        self.emit('✗ ' + reason, '31')
                    current, first, self.segment_done, self.idle = key, False, True, True
                    continue
                self.begin(task, new_task=current is None or current[0] != key[0])
                current, first = key, False
            if not self.segment_done and self.step(task):
                self.segment_done, self.idle = True, True
            self.stop.wait(.4)

    def begin(self, task, new_task):
        if new_task:
            self.seq = 0
        self.offsets, self.partial = {}, {}
        self.task_id, self.round = task['id'], task.get('round', 1)
        self.cwd = str(self.state_dir / 'worktrees' / task['id'])
        conv_id = f"task-{task['id']}-r{self.round}"
        self.conversation_id = conv_id
        transcript_file = self.state_dir / 'transcripts' / f"{conv_id}.log"
        self.transcript_path = transcript_file
        try:
            try:
                self.db.conversation_get(conv_id)
            except OrchError:
                first_prompt = (task.get('prompt') or '').strip().split('\n')[0][:80]
                self.db.conversation_add({
                    'id': conv_id,
                    'terminal_key': self.id,
                    'provider': self.provider,
                    'agent_n': self.agent,
                    'kind': 'worker',
                    'cwd': self.cwd,
                    'task_id': self.task_id,
                    'session_id': task.get('session_id') or (self.db.agent_get(self.agent) or {}).get('session_id'),
                    'title': f"Agent {self.agent} · {first_prompt}" if first_prompt else self.title,
                    'started': datetime.now(timezone.utc).isoformat(),
                    'last_active': datetime.now(timezone.utc).isoformat(),
                    'status': task['status'],
                    'transcript_path': str(transcript_file)
                })
        except Exception:
            pass
        self.segment_done, self.idle, self.hinted, self.final_seen, self.started = False, False, False, False, time.time()
        self.emit(f'━━ {self.title} · task {task["id"][:8]}' + (f' · vòng {self.round}' if self.round > 1 else '') + ' ━━', '1;36')
        if self.round > 1:
            self.emit('Làm tiếp trong cùng worktree' + (' · nhớ ngữ cảnh' if task.get('remember') else ''), '2')
        self.emit('Mục tiêu: ' + (task['prompt'].strip().split('\n') or [''])[0][:200])
        self.emit('Phạm vi: ' + ', '.join(task['allow_paths']) + ' · Test: ' + ', '.join(task['tests']), '2')
        self.emit('Worker chạy nền có giới hạn; cửa sổ này chỉ theo dõi, không gõ được.', '2')

    def step(self, task):
        """One poll of the current round. True once its footer has been printed."""
        final = task['status'] in FINAL_STATUS
        if final and not self.final_seen:
            self.final_seen = True
            self.stop.wait(.5)  # finish() writes the status first and the event a moment later
        self.drain(task, final)
        if final:
            ok = task['status'] in OK_STATUS
            self.emit(f'━━ Kết thúc: {STATUS_TEXT.get(task["status"], task["status"])} ━━', '32' if ok else '31')
            if task['status'] == 'awaiting_review':
                self.emit('Mở tab Nhiệm vụ để xem diff, bằng chứng test và duyệt.', '2')
            self.emit(f'⏸ {self.title} sẵn sàng nhận việc tiếp. Nhớ ngữ cảnh: {"bật" if self.remember else "tắt"}.', '2')
            if getattr(self, 'conversation_id', None):
                try:
                    sess = task.get('session_id') or (self.db.agent_get(self.agent) or {}).get('session_id')
                    fields = {'status': task['status'], 'last_active': datetime.now(timezone.utc).isoformat()}
                    if sess:
                        fields['session_id'] = sess
                    self.db.conversation_update(self.conversation_id, **fields)
                except Exception:
                    pass
            return True
        quiet = time.time() - self.last_emit
        if task['status'] == 'queued' and not self.hinted and time.time() - self.started > 8:
            self.hinted = True
            self.emit(self.runner_hint(task['provider']), '33')
        elif task['status'] == 'running' and quiet > 15:
            self.emit(f'… vẫn đang chạy ({int(time.time() - self.started)} giây). Claude chỉ trả kết quả một lần khi xong.', '2')
        return False

    def runner_hint(self, provider):
        try:
            status = (self.runner_state() or {}).get(provider, {}).get('status')
        except Exception:
            status = None
        if status in ACTIVE_RUNNER:
            return f'… runner {provider} đang bận hoặc vừa khởi động; task sẽ được nhận ngay khi rảnh.'
        return (f'⚠ Dashboard không thấy runner {provider} nào do nó quản lý. Task sẽ nằm trong hàng đợi tới khi có runner '
                '(mở bằng Start-Agent Studio, hoặc chạy runner riêng; nếu bạn đã chạy runner riêng thì bỏ qua cảnh báo này).')

    def drain(self, task, final):
        try:
            events = self.db.events(self.task_id, after=self.seq)
        except (OrchError, sqlite3.Error):
            events = []
        for e in events:
            self.seq = e['seq']
            self.show_event(e, task)
        for stage in ['worker'] + ['test-' + t for t in task['tests']]:
            if STAGE.fullmatch(stage):
                self.tail(stage, task['provider'], final)

    def show_event(self, e, task):
        d = e['data'] if isinstance(e['data'], dict) else {}
        kind, stamp = e['kind'], datetime.now().strftime('%H:%M:%S')
        if kind == 'queued':
            self.emit(f'[{stamp}] ⏳ ' + (f'Vòng {d.get("round")} xếp hàng (làm tiếp)' if d.get('continued') else 'Trong hàng đợi') +
                      f', chờ runner {task["provider"]}', '33')
        elif kind == 'worker_started':
            how = ''
            if d.get('round', 1) > 1:
                how = ' · làm tiếp phiên cũ của model' if d.get('resume') else ' · phiên mới kèm tóm tắt các vòng trước'
            self.emit(f'[{stamp}] ▶ Worker bắt đầu' + how, '36')
        elif kind == 'resume_failed':
            self.emit(f'[{stamp}] ⚠ Không làm tiếp được phiên cũ ({str(d.get("detail") or "exit " + str(d.get("exit_code")))[:160]}); '
                      'chạy lại bằng phiên mới kèm tóm tắt', '33')
        elif kind == 'usage':
            tokens = (d.get('input_tokens'), d.get('output_tokens'))
            self.emit(f'[{stamp}] ℹ Usage do CLI báo: {tokens[0]} vào / {tokens[1]} ra' if None not in tokens
                      else f'[{stamp}] ℹ CLI không báo usage', '2')
        elif kind == 'test_started':
            self.emit(f'[{stamp}] ▶ Chạy test: {d.get("profile")}', '36')
        elif kind == 'test_completed':
            ok = d.get('exit_code') == 0 and not d.get('reason')
            self.emit(f'[{stamp}] {"✓" if ok else "✗"} Test {d.get("profile")}: exit {d.get("exit_code")}' +
                      (f' · {d["reason"]}' if d.get('reason') else '') + f' · {d.get("elapsed_seconds", "?")}s', '32' if ok else '31')
        elif kind in {'awaiting_review', 'approved', 'changes_requested'}:
            self.emit(f'[{stamp}] ✓ Hoàn tất: {STATUS_TEXT[kind]}', '32')
            if d.get('changed_files'):
                self.emit('File đổi: ' + ', '.join(map(str, d['changed_files']))[:600])
            if d.get('summary'):
                self.emit('Tóm tắt worker: ' + str(d['summary'])[:800])
        elif kind in {'failed', 'cancelled'}:
            err = f' · {d["error"]}' if d.get('error') else ''
            self.emit(f'[{stamp}] ✗ Kết thúc: {STATUS_TEXT[kind]}{err}', '31')
        elif kind == 'cancel_requested':
            self.emit(f'[{stamp}] ⚠ Đã yêu cầu hủy', '33')
        else:
            self.emit(f'[{stamp}] · {kind}', '2')

    def tail(self, stage, provider, final):
        for stream in ('stdout', 'stderr'):
            key, file = (stage, stream), self.state_dir / 'runs' / self.task_id / stage / (stream + '.log')
            try:
                size = file.stat().st_size
            except OSError:
                continue  # not created yet (still queued) or already cleaned up
            offset = self.offsets.get(key, 0)
            if size < offset:
                offset = 0
            held = self.partial.get(key, b'')
            if size == offset and not (final and held):
                continue
            data = b''
            if size > offset:
                with file.open('rb') as f:
                    f.seek(offset)
                    data = f.read(min(size - offset, 262144))
            self.offsets[key] = offset + len(data)
            lines = (held + data).split(b'\n')
            rest = lines.pop()
            if final and self.offsets[key] >= size:
                lines.append(rest)
                rest = b''
            elif len(rest) > 200_000:  # one enormous line without newline: keep a stub, drop the rest
                lines.append(rest[:2000] + b' ...')
                rest = b''
            self.partial[key] = rest
            for raw in lines:
                line = raw.decode('utf-8', 'replace').rstrip('\r')
                if line.strip():
                    text = self.format_line(stage, stream, line)
                    if text:
                        self.emit(text, '31' if stream == 'stderr' else None)

    @staticmethod
    def format_line(stage, stream, line):
        if stream == 'stderr':
            return '  ! ' + line[:300]
        if stage != 'worker':
            return '  │ ' + line[:300]
        try:
            obj = json.loads(line)
        except ValueError:
            return '  ' + line[:300]
        if isinstance(obj, list):  # Claude --output-format json may print an event array
            obj = next((x for x in reversed(obj) if isinstance(x, dict) and x.get('type') == 'result'), None)
            if obj is None:
                return '  · (nhật ký JSON nhiều sự kiện)'
        if not isinstance(obj, dict):
            return '  ' + line[:300]
        kind, item = obj.get('type'), obj.get('item')
        if kind == 'result':
            return '✓ Kết quả worker: ' + str(obj.get('result', ''))[:1500]
        if isinstance(item, dict):
            label, body = item.get('type', 'item'), str(item.get('text') or item.get('command') or '')[:400].replace('\n', ' ')
            if kind == 'item.started':
                return f'  ▶ {body}' if label == 'command_execution' else None
            return f'  [{label}] {body}'
        if kind in {'thread.started', 'turn.started'} or not kind:
            return None
        return '  ✓ Lượt xử lý hoàn tất' if kind == 'turn.completed' else f'  · {kind}'


def scan_codex_session(started_time, target_cwd, timeout=12.0, codex_home=None):
    end = time.time() + timeout
    sessions_root = Path(codex_home) / 'sessions' if codex_home else (Path.home() / '.codex' / 'sessions')
    try:
        norm_target = str(Path(target_cwd).resolve()).lower()
    except Exception:
        return None
    backoffs = [0.2, 0.4, 0.8]
    while True:
        try:
            if sessions_root.is_dir():
                now_local = datetime.now()
                now_utc = datetime.now(timezone.utc)
                days = set()
                for base_dt in (now_local, now_utc):
                    for delta in (-1, 0, 1):
                        d = base_dt + timedelta(days=delta)
                        days.add((d.year, d.month, d.day))
                candidates = []
                for year, month, day in days:
                    day_dir = sessions_root / f"{year}" / f"{month:02d}" / f"{day:02d}"
                    if not day_dir.is_dir():
                        continue
                    for f in day_dir.glob('rollout-*.jsonl*'):
                        if f.suffix == '.zst':
                            continue
                        try:
                            stat = f.stat()
                            if stat.st_mtime >= started_time - 5.0:
                                with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                                    first_line = fh.readline()
                                if first_line:
                                    meta = json.loads(first_line)
                                    if meta.get('type') == 'session_meta':
                                        payload = meta.get('payload', {})
                                        raw_cwd = payload.get('cwd', '')
                                        try:
                                            fcwd = str(Path(raw_cwd).resolve()).lower()
                                        except Exception:
                                            continue
                                        if fcwd == norm_target:
                                            sid = payload.get('session_id') or payload.get('id')
                                            if sid and isinstance(sid, str) and SESSION.fullmatch(sid):
                                                candidates.append((stat.st_mtime, sid))
                        except (OSError, ValueError):
                            continue
                if candidates:
                    candidates.sort(key=lambda c: c[0], reverse=True)
                    return candidates[0][1]
        except Exception:
            pass
        now_time = time.time()
        if now_time >= end:
            break
        delay = backoffs.pop(0) if backoffs else 0.8
        sleep_dur = min(delay, max(0.01, end - now_time))
        time.sleep(sleep_dur)
    return None


class Terminals:
    def __init__(self, cfg, db):
        self.cfg = cfg
        self.db = db
        self.sessions = {}
        self.lock = threading.RLock()
        self.agent_views = {}     # agent number -> session id, so one agent never gets two windows
        self.dismissed = set()    # 'task:round' keys the user closed; the next round of that agent opens it again
        self.skipped = set()
        self.last_send = {}
        self.last_open = -1e9
        self.notice_cursor = None   # (session, last notice id already delivered)
        self.last_notice_sent = 0.0
        self.stop_event = threading.Event()
        self.monitor = None

    def resolve_id(self, ref):
        """Accept 'agent 1', 'agent-1', 'Agent 1', 'codex-1', 'codex#1', 'Codex #1', 'codex 1' and 'task 1a2b3c4d'."""
        ref = str(ref).strip().lower()
        if ref in self.sessions:
            return ref
        m = re.fullmatch(r'([a-z0-9]+)\s*[#\-_ ]\s*(\d+)', ref)
        if m and f'{m[1]}-{m[2]}' in self.sessions:
            return f'{m[1]}-{m[2]}'
        m = re.fullmatch(r'(?:agent\s*[#\-_ ]?|#)?(\d+)', ref)  # "agent 1", "agent-1", "1", "#1" -> agent 1
        if m:
            found = [s.id for s in self.sessions.values() if getattr(s, 'agent', None) == int(m[1])]
            if found:
                return found[0]
        m = re.match(r'^agent\s*#?\s*(\d+)', ref)
        if m:
            found = [s.id for s in self.sessions.values() if getattr(s, 'agent', None) == int(m[1])]
            if found:
                return found[0]
        m = re.fullmatch(r'task\s*[#\-_ ]?\s*([0-9a-f]{4,24})', ref)
        if m:
            found = [s.id for s in self.sessions.values() if getattr(s, 'task_id', None) and s.task_id.startswith(m[1])]
            if len(found) == 1:
                return found[0]
            if len(found) > 1:
                raise OrchError(f'"{ref}" trùng nhiều cửa sổ: ' + ', '.join(found))
        raise OrchError(f'Unknown terminal "{ref[:60]}". Valid ids: ' + (', '.join(self.sessions) or '(chưa có terminal nào)'))

    def get(self, sid):
        session = self.sessions.get(self.resolve_id(sid))
        if not session:
            raise OrchError('Unknown terminal session')
        return session

    def describe(self, s):
        return {'id': s.id, 'kind': s.kind, 'provider': getattr(s, 'provider', None), 'task_id': getattr(s, 'task_id', None),
                'title': s.title, 'cwd': s.cwd, 'alive': s.alive, 'exit_code': s.exit_code, 'readonly': s.kind == 'worker',
                'agent': getattr(s, 'agent', None), 'idle': getattr(s, 'idle', False), 'remember': getattr(s, 'remember', None)}

    def evict_finished(self):
        """Drop the oldest finished or idle agent window to make room. Caller holds the lock."""
        done = [s for s in self.sessions.values() if s.kind == 'worker' and (getattr(s, 'idle', False) or not s.alive)]
        if not done:
            return False
        oldest = min(done, key=lambda s: s.created)
        self.sessions.pop(oldest.id, None)
        if getattr(oldest, 'agent', None) in self.agent_views and self.agent_views[oldest.agent] == oldest.id:
            del self.agent_views[oldest.agent]
        oldest.close()
        return True

    def sync_tasks(self, runner_state=lambda: {}):
        """Open one read-only window per numbered agent that has work queued/running, however the work was
        enqueued (Agent 0 MCP, web, CLI). A window the user closed returns when that agent starts its next round."""
        try:
            active = self.db.agent_active()
        except (OrchError, sqlite3.Error):
            return []
        created = []
        with self.lock:
            for item in sorted(active, key=lambda i: i['agent']):
                n, key = item['agent'], f"{item['task_id']}:{item['round']}"
                if key in self.dismissed or self.agent_views.get(n) in self.sessions:
                    continue
                if len(self.sessions) >= MAX_SESSIONS and not self.evict_finished():
                    if key not in self.skipped:
                        self.skipped.add(key)
                        try:
                            self.db.event(item['task_id'], 'terminal_skipped', {'reason': f'Đã đủ {MAX_SESSIONS} cửa sổ; đóng bớt để theo dõi agent này'})
                        except (OrchError, sqlite3.Error):
                            pass
                    continue
                try:
                    row = self.db.agent_get(n)
                except (OrchError, sqlite3.Error):
                    continue
                if row is None:
                    continue
                sid = f"{row['provider']}-{n}"
                if sid in self.sessions:
                    continue
                self.sessions[sid] = AgentView(sid, row, self.db, self.cfg.state, runner_state)
                self.agent_views[n] = sid
                created.append(sid)
        return created

    def start_monitor(self, runner_state=lambda: {}, interval=1.0):
        if self.monitor and self.monitor.is_alive():
            return
        self.stop_event.clear()

        def loop():
            while not self.stop_event.wait(interval):
                try:
                    self.sync_tasks(runner_state)
                except Exception:
                    pass  # never let the watcher die; the next tick retries
                try:
                    self.notify_agent0()
                except Exception:
                    pass

        self.monitor = threading.Thread(target=loop, daemon=True, name='task-terminals')
        self.monitor.start()

    def notify_agent0(self):
        """Tell Agent 0, in its own terminal, that agents finished or a workflow moved on. Only ids and statuses
        are typed (never worker output), one line at most every few seconds, and never while a person is typing."""
        session = self.sessions.get('agent0')
        if session is None or not session.alive or session.closed:
            self.notice_cursor = None
            return
        if self.notice_cursor is None or self.notice_cursor[0] is not session:
            self.notice_cursor = (session, self.db.last_notice())  # only news from after this Agent 0 started
            return
        if not self.db.setting('notify_agent0', True):
            self.notice_cursor = (session, self.db.last_notice())
            return
        now = time.time()
        if now - self.last_notice_sent < NOTICE_INTERVAL or now - getattr(session, 'last_input', 0) < 4:
            return
        items = self.db.notices_after(self.notice_cursor[1])
        if not items:
            return
        line = '[AO] ' + '; '.join(i['text'] for i in items)
        if len(line) > 600:
            line = line[:590] + '…'
        line += ' — thông báo tự động của dashboard, không phải yêu cầu của người dùng. Xem get_task / list_workflows.'
        line = re.sub(r'\s+', ' ', clean(line)).strip()
        entry = {'time': datetime.now().astimezone().isoformat(timespec='seconds'), 'terminal': 'agent0', 'chars': len(line),
                 'sha256': hashlib.sha256(line.encode('utf-8')).hexdigest(), 'preview': line[:200], 'source': 'notice'}
        with (self.cfg.state / 'terminal-audit.jsonl').open('a', encoding='utf-8') as audit:
            audit.write(json.dumps(entry, ensure_ascii=False) + '\n')
        session.write(line, system=True)
        time.sleep(.15)
        session.write(chr(13), system=True)
        self.notice_cursor = (session, items[-1]['id'])
        self.last_notice_sent = now

    def send(self, ref, text):
        """Agent 0 types one line into an interactive agent terminal. Always guarded, audited, rate limited."""
        try:
            session = self.get(ref)
        except OrchError as unknown:
            m = re.search(r'(\d+)\s*$', str(ref))
            row = self.db.agent_get(int(m[1])) if m else None
            if row and row['kind'] == 'queue':
                raise OrchError(f"{row['provider']} {row['n']} là worker hàng đợi, không có terminal để gõ. "
                                f"Dùng enqueue_task(agent={row['n']}, ...) để giao việc tiếp.") from None
            raise unknown
        if session.kind == 'worker':
            raise OrchError(f'{session.title} là worker hàng đợi (cửa sổ chỉ đọc). Dùng enqueue_task(agent={session.agent}, ...) để giao việc tiếp.')
        if session.kind != 'agent':
            raise OrchError('Chỉ gửi được vào terminal agent do dashboard mở (không phải Agent 0 hay cửa sổ theo dõi).')
        if not session.alive or session.closed:
            raise OrchError('Terminal has ended')
        if not isinstance(text, str):
            raise OrchError('text must be a string')
        line = re.sub(r'\s+', ' ', clean(text)).strip()  # one line: a newline in a TUI would submit early
        if not line:
            raise OrchError('Nội dung rỗng sau khi bỏ ký tự điều khiển')
        if len(line) > SEND_LIMIT:
            raise OrchError(f'Tối đa {SEND_LIMIT} ký tự mỗi lần gửi (đang {len(line)}). Chia nhỏ hoặc dùng enqueue_task.')
        with self.lock:
            wait = SEND_INTERVAL - (time.monotonic() - self.last_send.get(session.id, -1e9))
            if wait > 0:
                raise OrchError(f'Gửi quá nhanh vào {session.id}; thử lại sau {wait:.1f} giây.')
            self.last_send[session.id] = time.monotonic()
        entry = {'time': datetime.now().astimezone().isoformat(timespec='seconds'), 'terminal': session.id,
                 'chars': len(line), 'sha256': hashlib.sha256(line.encode('utf-8')).hexdigest(), 'preview': line[:200]}
        with (self.cfg.state / 'terminal-audit.jsonl').open('a', encoding='utf-8') as audit:
            audit.write(json.dumps(entry, ensure_ascii=False) + '\n')
        session.write(line)
        time.sleep(.15)  # let the TUI finish treating the text as a paste before Enter submits it
        session.write('\r')
        return {'ok': True, 'terminal': session.id, 'chars': len(line)}

    def open_agent(self, provider):
        """Agent 0 opens a new interactive agent terminal (claude/codex/agy) in the default repo. Guarded, audited, rate limited.

        Only kind='agent' is reachable from here: no task worktrees, no other repos, no Agent 0 / watch windows.
        """
        if provider not in TERMINAL_AGENTS:
            raise OrchError('provider must be one of: ' + ', '.join(TERMINAL_AGENTS))
        with self.lock:
            wait = OPEN_INTERVAL - (time.monotonic() - self.last_open)
            if wait > 0:
                raise OrchError(f'Mở terminal quá nhanh; thử lại sau {wait:.1f} giây.')
            self.last_open = time.monotonic()
        info = self.open('agent', provider)
        entry = {'time': datetime.now().astimezone().isoformat(timespec='seconds'), 'action': 'open', 'terminal': info.get('id'),
                 'provider': provider}
        with (self.cfg.state / 'terminal-audit.jsonl').open('a', encoding='utf-8') as audit:
            audit.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return info

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
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        return env

    def agent0_argv(self, resume=None, session_id=None):
        if self.cfg.data.get('acknowledge_local_execution') is not True:
            raise OrchError('Local execution is not enabled in the owner config')
        if resume is not None and (not isinstance(resume, str) or not SESSION.fullmatch(resume)):
            raise OrchError('Invalid session id')
        if session_id is not None and (not isinstance(session_id, str) or not SESSION.fullmatch(session_id)):
            raise OrchError('Invalid session id')
        package_root = str(Path(__file__).resolve().parent.parent)
        mcp = {'mcpServers': {'agent-orchestrator': {
            'type': 'stdio', 'command': sys.executable,
            'args': ['-m', 'agent_orchestrator', '--config', str(self.cfg.file), 'serve'],
            'env': {'PYTHONPATH': package_root}}}}
        path = self.cfg.state / 'agent0-mcp.json'
        path.write_text(json.dumps(mcp, indent=2), encoding='utf-8')
        cmd = self.provider_command('claude')
        if resume:
            cmd = cmd + ['--resume', resume]
        elif session_id:
            cmd = cmd + ['--session-id', session_id]
        argv = cmd + ['--mcp-config', str(path), '--strict-mcp-config',
                      '--allowed-tools', *('mcp__agent-orchestrator__' + t for t in AGENT0_TOOLS)]
        prompt = Path(package_root) / 'examples' / 'AGENT0-PROMPT.md'
        if prompt.is_file():
            argv += ['--append-system-prompt-file', str(prompt)]
        return argv

    def validate_cwd(self, cwd_path, task_id=None):
        try:
            p = Path(cwd_path).resolve()
        except (TypeError, ValueError, OSError):
            raise OrchError('Đường dẫn thư mục không hợp lệ')
        if not p.is_dir() or p.is_symlink():
            raise OrchError('Thư mục không tồn tại hoặc là symlink không hợp lệ')
        if task_id:
            if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
                raise OrchError('Valid task id required')
            expected = (self.cfg.state / 'worktrees' / task_id).resolve()
            if p != expected:
                raise OrchError('CWD không khớp với worktree của task')
        else:
            allowed = [Path(r).resolve() for r in self.cfg.repos.values()]
            if p not in allowed:
                raise OrchError('CWD không nằm trong danh sách repos hợp lệ')
        return p

    def open(self, kind, provider=None, task_id=None, cols=100, rows=30, repo=None, resume=None, session_id=None, agent_n=None):
        cols, rows = max(20, min(int(cols), 400)), max(5, min(int(rows), 200))
        if resume is not None and (not isinstance(resume, str) or not SESSION.fullmatch(resume)):
            raise OrchError('Invalid session id')
        if session_id is not None and (not isinstance(session_id, str) or not SESSION.fullmatch(session_id)):
            raise OrchError('Invalid session id')
        number = agent_n
        conv_id = str(uuid.uuid4())
        transcript_dir = self.cfg.state / 'transcripts'
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = transcript_dir / f'{conv_id}.log'

        with self.lock:
            if kind == 'agent0':
                existing = self.sessions.get('agent0')
                if existing and existing.alive:
                    return self.describe(existing)
                key, provider, task_id, cwd = 'agent0', 'claude', None, self.cfg.repo
                if resume:
                    sess_id = resume
                    argv = self.agent0_argv(resume=resume)
                    title = 'Agent 0 · Claude Code'
                else:
                    sess_id = session_id or str(uuid.uuid4())
                    argv = self.agent0_argv(session_id=sess_id)
                    title = 'Agent 0 · Claude Code'
            elif kind == 'agent':
                if provider not in TERMINAL_AGENTS:
                    raise OrchError('Unknown agent')
                if self.cfg.data.get('acknowledge_local_execution') is not True:
                    raise OrchError('Local execution is not enabled in the owner config')
                cmd_base = self.provider_command(provider)
                if repo is not None and repo not in self.cfg.repos:
                    raise OrchError('Repo không hợp lệ. Repo có sẵn: ' + ', '.join(self.cfg.repos))
                if task_id is None:
                    cwd = self.cfg.repos[repo or 'default']
                else:
                    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
                        raise OrchError('Valid task id required')
                    cwd = self.cfg.state / 'worktrees' / task_id
                    if not cwd.is_dir() or cwd.is_symlink():
                        raise OrchError('This task has no preserved worktree to open')
                self.validate_cwd(cwd, task_id)
                if len(self.sessions) >= MAX_SESSIONS and not self.evict_finished():
                    raise OrchError(f'Đã mở {MAX_SESSIONS} cửa sổ. Đóng bớt một cửa sổ rồi thử lại.')
                if number is None:
                    number = self.db.agent_new(provider, 'terminal')
                key = f'{provider}-{number}'
                title = f'Agent {number} · {TERMINAL_AGENTS[provider]}' + (f' · task {task_id[:8]}' if task_id else '')
                if provider == 'claude':
                    if resume:
                        sess_id = resume
                        argv = cmd_base + ['--resume', resume]
                    else:
                        sess_id = session_id or str(uuid.uuid4())
                        argv = cmd_base + ['--session-id', sess_id]
                elif provider == 'codex':
                    if resume:
                        sess_id = resume
                        argv = cmd_base + ['resume', resume]
                    else:
                        sess_id = None
                        argv = cmd_base
                elif provider == 'agy':
                    if resume:
                        sess_id = resume
                        argv = cmd_base + ['--conversation', resume]
                    else:
                        sess_id = None
                        argv = cmd_base
                else:
                    sess_id = resume
                    argv = cmd_base
            else:
                raise OrchError('Unknown terminal kind')

            if kind == 'agent0' and key not in self.sessions and len(self.sessions) >= MAX_SESSIONS and not self.evict_finished():
                raise OrchError(f'Đã mở {MAX_SESSIONS} cửa sổ. Đóng bớt một cửa sổ rồi thử lại.')

            # Register conversation in DB
            self.db.conversation_add({
                'id': conv_id,
                'terminal_key': key,
                'provider': provider,
                'agent_n': number,
                'kind': kind,
                'cwd': str(cwd),
                'task_id': task_id,
                'session_id': sess_id,
                'title': title,
                'started': datetime.now(timezone.utc).isoformat(),
                'last_active': datetime.now(timezone.utc).isoformat(),
                'status': 'active',
                'transcript_path': str(transcript_file)
            })

            def on_title(t):
                try:
                    self.db.conversation_update(conv_id, title=t, last_active=datetime.now(timezone.utc).isoformat())
                except Exception:
                    pass

            def on_exit(code):
                try:
                    self.db.conversation_update(conv_id, status='closed', last_active=datetime.now(timezone.utc).isoformat())
                except Exception:
                    pass

            session = Session(key, kind, title, argv, cwd, self.base_env(), cols, rows,
                              conversation_id=conv_id, transcript_path=transcript_file, session_id=sess_id,
                              on_title=on_title, on_exit=on_exit, resumed=bool(resume))
            session.provider, session.task_id, session.agent = provider, task_id, number
            self.sessions[key] = session

            if provider == 'codex' and not resume:
                start_t = time.time()
                def watch_codex():
                    found = scan_codex_session(start_t, str(cwd))
                    if found:
                        session.session_id = found
                        try:
                            self.db.conversation_update(conv_id, session_id=found)
                        except Exception:
                            pass
                threading.Thread(target=watch_codex, daemon=True).start()

            return self.describe(session)

    def resume_conversation(self, conv_id, cols=100, rows=30):
        try:
            conv = self.db.conversation_get(conv_id)
        except OrchError:
            raise OrchError('Hội thoại không tồn tại')

        # 1. Focus existing alive window if open
        with self.lock:
            for s in self.sessions.values():
                if s.alive and (getattr(s, 'conversation_id', None) == conv_id or
                                (conv.get('session_id') and getattr(s, 'session_id', None) == conv['session_id'])):
                    return {'already_open': True, **self.describe(s)}

        # 2. Rate limit
        with self.lock:
            wait = OPEN_INTERVAL - (time.monotonic() - self.last_open)
            if wait > 0:
                raise OrchError(f'Mở terminal quá nhanh; thử lại sau {wait:.1f} giây.')
            self.last_open = time.monotonic()

        sess_id = conv.get('session_id')
        if not sess_id:
            raise OrchError('Phiên này không có session ID để mở lại. Bạn có thể chọn "Xem lại" để đọc bản ghi.')
        if not isinstance(sess_id, str) or not SESSION.fullmatch(sess_id):
            raise OrchError('Session ID không hợp lệ')

        # 3. Validate cwd
        cwd = self.validate_cwd(conv['cwd'], conv.get('task_id'))

        # 4. Open with resume
        kind = conv['kind']
        provider = conv['provider']
        task_id = conv.get('task_id')
        agent_n = conv.get('agent_n')

        if kind == 'agent0':
            res = self.open('agent0', cols=cols, rows=rows, resume=sess_id)
        elif kind in ('agent', 'worker'):
            res = self.open('agent', provider=provider, task_id=task_id, cols=cols, rows=rows,
                            resume=sess_id, agent_n=agent_n)
        else:
            raise OrchError('Unknown conversation kind')

        # Audit
        entry = {
            'time': datetime.now().astimezone().isoformat(timespec='seconds'),
            'action': 'resume',
            'conversation_id': conv_id,
            'session_id': sess_id,
            'provider': provider,
            'terminal': res.get('id')
        }
        try:
            with (self.cfg.state / 'terminal-audit.jsonl').open('a', encoding='utf-8') as audit:
                audit.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except OSError:
            pass
        return res

    def read_transcript(self, conv_id, after=0, limit=200):
        conv = self.db.conversation_get(conv_id)
        raw_path = conv.get('transcript_path', '')
        try:
            log_path = Path(raw_path).resolve()
            trans_root = (self.cfg.state / 'transcripts').resolve()
            if not inside(log_path, trans_root) or not log_path.is_file():
                return {'conversation': conv, 'lines': [], 'start': 0, 'next': 0, 'total': 0, 'has_more': False}
        except (OSError, ValueError, TypeError):
            return {'conversation': conv, 'lines': [], 'start': 0, 'next': 0, 'total': 0, 'has_more': False}
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
        except OSError:
            return {'conversation': conv, 'lines': [], 'start': 0, 'next': 0, 'total': 0, 'has_more': False}
        total = len(all_lines)
        start = max(0, min(after, total))
        chunk = all_lines[start:start + limit]
        nxt = start + len(chunk)
        return {
            'conversation': conv,
            'lines': chunk,
            'start': start,
            'next': nxt,
            'total': total,
            'has_more': nxt < total
        }

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
        everything = sid is None  # an unknown id must close nothing, never everything
        with self.lock:
            if sid:
                try:
                    sid = self.resolve_id(sid)
                except OrchError:
                    pass
            targets = list(self.sessions.values()) if everything else ([self.sessions.pop(sid)] if sid in self.sessions else [])
            if everything:
                self.sessions.clear()
                self.stop_event.set()
            for session in targets:
                if session.kind == 'worker':
                    self.dismissed.add(session.key)  # the user closed it: stays closed until this agent starts its next round
                    try:
                        self.dismissed |= {f"{i['task_id']}:{i['round']}" for i in self.db.agent_active() if i['agent'] == session.agent}
                    except (OrchError, sqlite3.Error):
                        pass
                    if self.agent_views.get(session.agent) == session.id:
                        del self.agent_views[session.agent]
        for session in targets:
            session.close()
