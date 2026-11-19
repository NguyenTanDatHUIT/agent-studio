"""Local loopback bridge between Agent Studio and the Google Gemini Web browser tab."""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import OrchError, inside
from .gitops import PROTECTED, in_scope, safe_relative
from .providers import SESSION
from .transcripts import _is_slash_command, append_transcript_entry, title_from_keys

BUFFER_LIMIT = 1_000_000
MAX_READ_CHARS = 9_000        # one read_file result; the model asks for the next line range itself
MAX_FEEDBACK_CHARS = 14_000   # all tool results in one follow-up message: the Gemini composer takes far less than a full file set
MAX_FILE_BYTES = 10_000_000
DEFAULT_MAX_TURNS = 12
TAB_STALE_SECONDS = 45.0

TOOL_BLOCK_RE = re.compile(r'<<<AO_TOOL\s*(\{.*?\})\s*AO_TOOL>>>', re.DOTALL)
ANSI_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')
GEMINI_URL_CONV_RE = re.compile(r'/app/([A-Za-z0-9_-]{4,72})')

IGNORED_DIRS = {
    '.git', '.claude', '.codex', '.github', '.venv', '.runtime', '.local-run',
    '__pycache__', 'node_modules', 'bin', 'obj', 'dist', 'build'
}


def normalize_gemini_session_id(raw_id: str | None) -> str | None:
    if not raw_id or not isinstance(raw_id, str):
        return None
    cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_id.strip())
    if not cleaned:
        return None
    if len(cleaned) < 8:
        cleaned = 'gem-' + cleaned
    cleaned = cleaned[:80]
    if not cleaned[0].isalnum():
        cleaned = 'g' + cleaned[:79]
    return cleaned if SESSION.fullmatch(cleaned) else None


def extract_conv_slug_from_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    m = GEMINI_URL_CONV_RE.search(url)
    return normalize_gemini_session_id(m.group(1)) if m else None


def raw_conv_slug(session_id: str | None) -> str | None:
    if not session_id:
        return None
    return session_id[4:] if session_id.startswith('gem-') and len(session_id) > 4 else session_id


FENCE_RE = re.compile(r'```[ \t]*(?:json|ao_tool|ao-tool)?[ \t]*\r?\n(.*?)\r?\n?```', re.DOTALL | re.IGNORECASE)
ACTION_START_RE = re.compile(r'\{\s*"action"\s*:')
ABS_PATH_RE = re.compile(r'^(?:[A-Za-z]:[\\/]|[\\/]{2}|/)')
ATTEMPT_RE = re.compile(r'AO_TOOL|"action"\s*:')
PARSE_HELP = ('Không đọc được lệnh. Hãy gửi lại, mỗi lệnh là MỘT khối mã ```json chứa đúng một đối tượng JSON hợp lệ, ví dụ '
              '{"action": "read_file", "path": "docs/GEMINI-WEB.md"}. Đường dẫn tương đối so với thư mục làm việc, dùng dấu /, '
              'không dùng ổ đĩa (C:) hoặc dấu \\.')


def format_tool_results(results: list[dict], limit: int = MAX_FEEDBACK_CHARS) -> str:
    """Kết quả công cụ gửi lại cho Gemini: dòng mô tả gọn + nội dung thô (không bọc JSON/escape), tổng độ dài có trần."""
    parts, used = [], 0
    for res in results:
        meta = {k: v for k, v in res.items() if k not in ('content', 'files', 'summary')}
        head = json.dumps(meta, ensure_ascii=False)
        body = ''
        if isinstance(res.get('content'), str):
            body = res['content']
        elif isinstance(res.get('files'), list):
            body = '\n'.join(res['files'])
        room = max(0, limit - used - len(head) - 200)
        note = ''
        if len(body) > room:
            body = body[:room].rsplit('\n', 1)[0] if room else ''
            note = '\n[Đã cắt bớt vì quá dài. Hãy đọc phần còn lại bằng read_file với start_line/end_line, từng đoạn nhỏ.]'
        block = head + ('\n----- NỘI DUNG -----\n' + body + '\n----- HẾT -----' if body else '') + note
        parts.append(block)
        used += len(block)
    return '\n\n'.join(parts)


def parse_tool_calls(text: str, blocks: list | None = None) -> list[dict]:
    """Lấy các lệnh công cụ từ câu trả lời.

    Nguồn tin cậy nhất là văn bản của các khối mã (<pre>) do tiện ích gửi kèm trong `blocks`; ngoài ra nhận khối ```json trong
    chính câu trả lời và cú pháp cũ <<<AO_TOOL ... AO_TOOL>>>. Nếu thấy dấu hiệu Gemini đã cố gọi công cụ mà không đọc được lệnh
    nào, trả về một _parse_error để vòng lặp báo lỗi lại cho Gemini thay vì coi là đã xong.
    """
    text = text if isinstance(text, str) else ''
    candidates: list[str] = []
    for match in TOOL_BLOCK_RE.finditer(text):
        candidates.append(match.group(1).strip())
    for match in FENCE_RE.finditer(text):
        candidates.append(match.group(1).strip())
    for block in (blocks or []):
        if isinstance(block, str):
            candidates.append(block.strip())
    calls, seen, attempted = [], set(), bool(ATTEMPT_RE.search(text))
    for raw in candidates:
        if not raw or raw in seen or not raw.startswith('{'):
            continue
        seen.add(raw)
        if '"action"' in raw:
            attempted = True
        try:
            obj = json.loads(raw)
        except ValueError:
            if '"action"' in raw or 'AO_TOOL' in raw:
                calls.append({'action': '_parse_error', 'raw': raw[:400]})
            continue
        if isinstance(obj, dict) and isinstance(obj.get('action'), str):
            calls.append(obj)
    if not calls:
        # Fallback: the page shows a code block as plain text with decoration around it (a "JSON" label, a copy button). Find
        # the JSON objects that start with "action" wherever they are, skipping spans already consumed by an earlier object.
        decoder, pos = json.JSONDecoder(), 0
        for match in ACTION_START_RE.finditer(text):
            if match.start() < pos:
                continue
            try:
                obj, length = decoder.raw_decode(text[match.start():])
            except ValueError:
                continue
            pos = match.start() + length
            if isinstance(obj, dict) and isinstance(obj.get('action'), str):
                calls.append(obj)
    if not calls and attempted:
        calls.append({'action': '_parse_error', 'raw': text[:400]})
    return calls


def build_coding_system_prompt(cwd: str, allow_paths: list[str] | None = None, queue_mode: bool = False,
                               read_roots: list | None = None) -> str:
    roots_note = ('Ngoại lệ CHỈ ĐỌC (list_files, read_file): được dùng đường dẫn tuyệt đối trong các thư mục sau, dấu /: '
                  + ', '.join(Path(r).as_posix() for r in read_roots) + '. Không ghi được vào đó.\n') if read_roots else ''
    scope_note = (
        f"Bạn CHỈ ĐƯỢC PHÉP sửa/tạo tệp nằm trong phạm vi allow_paths: {json.dumps(allow_paths, ensure_ascii=False)}."
        if allow_paths else
        "Bạn được đọc và sửa các tệp mã nguồn trong thư mục dự án (không chạm .git, .claude, .codex, .github, .env*, CLAUDE.md)."
    )
    finish_rule = (
        'Khi đã hoàn thành toàn bộ thay đổi mã nguồn, BẮT BUỘC kết thúc bằng khối:\n'
        '```json\n'
        '{"action": "finish_task", "summary": "Tóm tắt ngắn gọn các thay đổi, rủi ro và kiểm thử"}\n'
        '```'
        if queue_mode else
        'Nếu yêu cầu cần đọc hoặc sửa mã nguồn, hãy gọi tool theo từng bước. Khi đã hoàn tất và không cần gọi thêm tool nào nữa, '
        'hãy trả lời tóm tắt bình thường (hoặc dùng action "finish_task").'
    )
    return (
        "[AGENT STUDIO - GEMINI BROWSER CODING BRIDGE]\n"
        f"Thư mục làm việc hiện tại (local): {cwd}\n"
        f"{scope_note}\n\n"
        "Bạn đang được nối trực tiếp với máy local qua Agent Studio. Khi cần khảo sát hoặc sửa tệp, hãy xuất MỘT khối mã "
        "```json cho MỖI lệnh. Bên trong khối chỉ có đúng một đối tượng JSON hợp lệ, không chú thích, không chữ nào khác.\n"
        "QUY TẮC ĐƯỜNG DẪN: luôn tương đối so với thư mục làm việc và dùng dấu / (ví dụ docs/a.md). KHÔNG dùng ổ đĩa (C:), "
        "đường dẫn tuyệt đối, dấu \\ hoặc ... Tệp nằm ngoài thư mục làm việc không đọc được.\n"
        f"{roots_note}\n"
        "1. Liệt kê tệp:\n"
        '```json\n{"action": "list_files", "subdir": ""}\n```\n\n'
        "2. Đọc tệp:\n"
        '```json\n{"action": "read_file", "path": "src/main.py", "start_line": 1, "end_line": 200}\n```\n\n'
        "3. Sửa đoạn mã xác định trong tệp (ưu tiên cho tệp dài):\n"
        '```json\n{"action": "replace_in_file", "path": "src/main.py", "search": "đoạn mã cũ chính xác", "replace": "đoạn mã mới"}\n```\n\n'
        "4. Tạo mới hoặc ghi đè tệp:\n"
        '```json\n{"action": "write_file", "path": "src/helper.py", "content": "nội dung đầy đủ của tệp"}\n```\n\n'
        f"5. Hoàn tất công việc:\n{finish_rule}\n"
        "Lưu ý: Không tự chạy git commit/push/merge. Sau mỗi lần bạn xuất lệnh, Agent Studio sẽ thực thi dưới local "
        "và trả kết quả trong khối [AO_TOOL_RESULT] ở lượt tiếp theo. Chỉ gửi lệnh khi cần; đừng giải thích dài.\n"
        "------------------------------------------------------------\n\n"
    )


class WorkspaceExecutor:
    """Thực thi thao tác tệp có kiểm soát trong `root`, tuân thủ safe_relative và allow_paths."""

    def __init__(self, root: Path | str, allow_paths: list[str] | None = None, read_only: bool = False,
                 read_roots: list[Path | str] | None = None):
        self.root = Path(root).resolve()
        if not self.root.is_dir() or self.root.is_symlink():
            raise OrchError("Workspace root is invalid")
        self.allow_paths = [safe_relative(p) for p in allow_paths] if allow_paths else None
        self.read_only = bool(read_only)
        self.changed_files: set[str] = set()
        # Owner-declared folders outside the workspace that may be READ (never written). Absolute paths only work inside them.
        self.read_roots = [Path(r).resolve() for r in (read_roots or []) if Path(r).is_dir()]

    def _resolve_safe(self, rel_path: str, for_write: bool = False) -> tuple[str, Path]:
        try:
            clean_rel = safe_relative(rel_path)
        except OrchError as exc:
            raise OrchError(f"Đường dẫn '{str(rel_path)[:120]}' không hợp lệ ({exc}). Dùng đường dẫn tương đối so với "
                            f"thư mục làm việc '{self.root.name}' và dấu '/'; tệp ngoài thư mục này không truy cập được.") from exc
        if for_write:
            if self.read_only:
                raise OrchError("Workspace này chỉ cho phép đọc (read-only)")
            if self.allow_paths is not None and not in_scope(clean_rel, self.allow_paths):
                raise OrchError(f"Out-of-scope edit blocked: '{clean_rel}' ngoài allow_paths {self.allow_paths}")
        target = (self.root / clean_rel).resolve()
        if not inside(target, self.root):
            raise OrchError(f"Path escapes workspace root: {clean_rel}")
        cur = self.root
        for part in Path(clean_rel).parts:
            cur = cur / part
            if cur.exists() and cur.is_symlink():
                raise OrchError(f"Symlink không được phép: {clean_rel}")
        return clean_rel, target

    def _resolve_read(self, raw) -> tuple[str, Path]:
        """Path for a read: relative to the workspace, or absolute inside one of the owner's read-only roots."""
        text = str(raw or '').strip()
        if not (self.read_roots and ABS_PATH_RE.match(text)):
            return self._resolve_safe(text, for_write=False)
        target = Path(text).resolve()
        for root in self.read_roots:
            if target == root or inside(target, root):
                parts = target.relative_to(root).parts
                if any(p.lower() in PROTECTED or p.lower().startswith('.env') for p in parts):
                    raise OrchError('Tệp được bảo vệ, không đọc được')
                cur = root
                for part in parts:
                    cur = cur / part
                    if cur.is_symlink():
                        raise OrchError('Symlink không được phép')
                return target.as_posix(), target
        raise OrchError(f"'{text[:120]}' không nằm trong thư mục chỉ đọc nào được phép: "
                        + ', '.join(r.as_posix() for r in self.read_roots)
                        + f". Tệp trong thư mục làm việc '{self.root.name}' dùng đường dẫn tương đối.")

    def execute(self, call: dict) -> dict:
        action = call.get('action')
        if action == '_parse_error':
            return {'ok': False, 'action': 'parse_error', 'error': PARSE_HELP + ' Nội dung nhận được: ' + str(call.get('raw', ''))[:300]}
        try:
            if action == 'list_files':
                subdir = str(call.get('subdir') or '').strip().strip('/')
                base = self.root
                if subdir and subdir != '.':
                    _, base = self._resolve_read(subdir)
                if not base.exists() or not base.is_dir():
                    return {'ok': False, 'action': action, 'error': f'Thư mục không tồn tại: {subdir}'}
                files = []
                for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                    dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS and not d.startswith('.'))
                    for fname in sorted(filenames):
                        if fname.startswith('.env') or fname.lower() in PROTECTED:
                            continue
                        fpath = Path(dirpath) / fname
                        if fpath.is_symlink():
                            continue
                        files.append(fpath.relative_to(self.root).as_posix() if inside(base, self.root) else fpath.as_posix())
                        if len(files) >= 400:
                            break
                    if len(files) >= 400:
                        break
                return {'ok': True, 'action': action, 'files': files, 'truncated': len(files) >= 400}

            if action == 'read_file':
                rel, target = self._resolve_read(call.get('path'))
                if not target.is_file():
                    return {'ok': False, 'action': action, 'path': rel, 'error': 'Tệp không tồn tại'}
                if target.stat().st_size > MAX_FILE_BYTES:
                    return {'ok': False, 'action': action, 'path': rel, 'error': 'Tệp vượt quá giới hạn 10 MB'}
                lines = target.read_text(encoding='utf-8', errors='replace').splitlines()
                start_line = max(1, int(call.get('start_line') or 1))
                end_line = min(len(lines), int(call.get('end_line') or max(len(lines), 1)))
                shown, size, truncated = [], 0, False
                for i, line in enumerate(lines[start_line - 1:end_line], start=start_line):
                    entry = f'{i}: {line}'[:2000]
                    if shown and size + len(entry) + 1 > MAX_READ_CHARS:
                        truncated = True
                        break
                    shown.append(entry)
                    size += len(entry) + 1
                last_shown = start_line + len(shown) - 1
                result = {'ok': True, 'action': action, 'path': rel, 'total_lines': len(lines),
                          'start_line': start_line, 'end_line': last_shown, 'truncated': truncated,
                          'content': '\n'.join(shown)}
                if truncated or last_shown < len(lines):
                    result['next_start_line'] = last_shown + 1
                return result

            if action == 'write_file':
                rel, target = self._resolve_safe(str(call.get('path') or ''), for_write=True)
                content = call.get('content')
                if not isinstance(content, str):
                    raise OrchError('write_file yêu cầu trường "content" kiểu chuỗi')
                encoded = content.encode('utf-8')
                if len(encoded) > MAX_FILE_BYTES:
                    raise OrchError('Nội dung ghi vượt quá 10 MB')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(encoded)
                self.changed_files.add(rel)
                return {'ok': True, 'action': action, 'path': rel, 'bytes_written': len(encoded)}

            if action == 'replace_in_file':
                rel, target = self._resolve_safe(str(call.get('path') or ''), for_write=True)
                if not target.is_file():
                    raise OrchError(f'Tệp không tồn tại: {rel}')
                search, replace = call.get('search'), call.get('replace')
                if not isinstance(search, str) or not search or not isinstance(replace, str):
                    raise OrchError('replace_in_file yêu cầu "search" (khác rỗng) và "replace" kiểu chuỗi')
                original = target.read_text(encoding='utf-8')
                norm_orig = original.replace('\r\n', '\n')
                norm_search = search.replace('\r\n', '\n')
                norm_replace = replace.replace('\r\n', '\n')
                count = norm_orig.count(norm_search)
                if count == 0:
                    raise OrchError(f'Không tìm thấy đoạn "search" trong {rel}. Hãy gọi read_file trước.')
                if count > 1:
                    raise OrchError(f'Đoạn "search" xuất hiện {count} lần trong {rel}; hãy thêm ngữ cảnh bao quanh.')
                updated = norm_orig.replace(norm_search, norm_replace, 1)
                if '\r\n' in original:
                    updated = updated.replace('\n', '\r\n')
                encoded = updated.encode('utf-8')
                if len(encoded) > MAX_FILE_BYTES:
                    raise OrchError('Tệp sau khi sửa vượt quá 10 MB')
                target.write_bytes(encoded)
                self.changed_files.add(rel)
                return {'ok': True, 'action': action, 'path': rel, 'replaced': 1}

            if action == 'finish_task':
                return {'ok': True, 'action': 'finish_task', 'summary': str(call.get('summary') or 'Hoàn thành.')[:8000]}

            return {'ok': False, 'action': str(action), 'error': f'Action không hỗ trợ: {action}'}
        except (OrchError, OSError, ValueError, TypeError) as exc:
            return {'ok': False, 'action': str(action), 'error': str(exc)[:1000]}


class BrowserBridgeSession:
    """Phiên cửa sổ CMD ảo tương thích 1:1 với Session của Terminals nhưng nối qua trình duyệt Gemini."""
    _last_created = 0.0
    _created_lock = threading.Lock()
    managed_idle = True  # Ngăn bộ quét ConPTY báo rảnh sớm khi trình duyệt đang suy nghĩ

    def __init__(self, sid: str, kind: str, title: str, cwd: Path | str, hub: 'GeminiBridgeHub',
                 conversation_id: str | None = None, transcript_path: Path | str | None = None,
                 session_id: str | None = None, on_title=None, on_exit=None, resumed: bool = False):
        self.id = sid
        self.kind = kind
        self.provider = 'gemini_web'
        self.title = title
        self.cwd = str(cwd)
        self.hub = hub
        self.conversation_id = conversation_id
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.session_id = normalize_gemini_session_id(session_id)
        self.on_title = on_title
        self.on_exit = on_exit
        self.resumed = resumed
        self.agent = None
        self.task_id = None

        self.cond = threading.Condition()
        self.lock = threading.Lock()
        self.buffer = bytearray()
        self.base = 0
        self.exit_code = None
        self.closed = False

        with BrowserBridgeSession._created_lock:
            now_t = time.time()
            BrowserBridgeSession._last_created = self.created = max(now_t, BrowserBridgeSession._last_created + 1e-6)
        self.last_output_time = self.created
        self.last_input = 0.0
        self.idle = True
        self.idle_notified = True
        self.has_active_work = False
        self.idle_reason = 'quiet'

        self.tools_enabled = True
        self.system_primed = False
        self.first_input_done = False
        self._line_chars: list[str] = []
        self.executor = WorkspaceExecutor(self.cwd, allow_paths=None, read_only=False, read_roots=self.hub.read_roots())
        self._print_banner()

    @property
    def alive(self) -> bool:
        return self.exit_code is None and not self.closed

    def _print_banner(self):
        st = self.hub.status_snapshot()
        ext_txt = (
            f"\x1b[32mĐã kết nối ({st['active_tabs']} tab Gemini)\x1b[0m"
            if st['connected'] else
            "\x1b[33mChờ kết nối Extension (bấm nút Cầu nối Gemini trên thanh công cụ để ghép đôi)\x1b[0m"
        )
        banner = (
            f"\x1b[1;36m=== {self.title} [Gemini Browser Bridge] ===\x1b[0m\r\n"
            f"\x1b[2mThư mục: {self.cwd}\x1b[0m\r\n"
            f"Extension: {ext_txt}\r\n"
            f"\x1b[2mLệnh nhanh: /help | /status | /tools on|off | /new | /clear\x1b[0m\r\n\r\n"
            f"\x1b[32mgemini-web>\x1b[0m "
        )
        self._append_raw(banner.encode('utf-8'), record_transcript=False)

    def _append_raw(self, raw: bytes, record_transcript: bool = True):
        with self.cond:
            self.buffer += raw
            if len(self.buffer) > BUFFER_LIMIT:
                drop = len(self.buffer) - BUFFER_LIMIT
                del self.buffer[:drop]
                self.base += drop
            self.last_output_time = time.time()
            self.cond.notify_all()
        if record_transcript and self.transcript_path:
            try:
                append_transcript_entry(self.transcript_path, raw.decode('utf-8', 'replace'))
            except Exception:
                pass

    def emit_line(self, text: str, color: str | None = None, prompt_after: bool = False):
        norm = str(text).replace('\r\n', '\n').replace('\r', '\n')
        out = ''.join((f'\x1b[{color}m{line}\x1b[0m' if color else line) + '\r\n' for line in norm.split('\n'))
        if prompt_after and self.alive:
            out += '\x1b[32mgemini-web>\x1b[0m '
        self._append_raw(out.encode('utf-8', 'replace'))

    def read(self, after: int, wait: float):
        with self.cond:
            if after < self.base:
                after = self.base
            if wait > 0 and self.alive and after >= self.base + len(self.buffer):
                self.cond.wait(wait)
            start = after - self.base
            return after, bytes(self.buffer[start:]), self.base + len(self.buffer), self.exit_code

    def resize(self, cols: int, rows: int):
        pass

    def _handle_slash(self, cmd_line: str):
        parts = cmd_line.strip().split()
        cmd = parts[0].lower()
        if cmd == '/help':
            self.emit_line(
                "Các lệnh nội bộ:\n"
                "  /status       Kiểm tra trạng thái kết nối Chrome/Edge Extension\n"
                "  /tools on|off Bật/tắt chế độ tự động đọc và sửa file dưới local\n"
                "  /new          Mở cuộc trò chuyện mới trên Gemini ở lượt kế tiếp\n"
                "  /clear        Xóa màn hình cửa sổ hiện tại",
                color='36', prompt_after=True
            )
        elif cmd == '/status':
            st = self.hub.status_snapshot()
            self.emit_line(
                f"Extension: {'ĐÃ KẾT NỐI' if st['connected'] else 'CHƯA KẾT NỐI'} | "
                f"Tab hoạt động: {st['active_tabs']} | Hàng đợi: {st['pending_prompts']} | "
                f"Sửa file: {'BẬT' if self.tools_enabled else 'TẮT'}",
                color='32' if st['connected'] else '33', prompt_after=True
            )
        elif cmd == '/tools':
            arg = parts[1].lower() if len(parts) > 1 else ''
            self.tools_enabled = True if arg in ('on', '1', 'true') else (False if arg in ('off', '0', 'false') else not self.tools_enabled)
            if self.tools_enabled:
                self.system_primed = False
            self.emit_line(f"Chế độ đọc/sửa file local: {'BẬT' if self.tools_enabled else 'TẮT'}", color='36', prompt_after=True)
        elif cmd == '/new':
            self.session_id = None
            self.system_primed = False
            self.emit_line("Đã đặt lại phiên: câu lệnh tới sẽ mở đoạn chat mới trên Gemini.", color='36', prompt_after=True)
        elif cmd == '/clear':
            self._append_raw(b'\x1b[2J\x1b[H\x1b[32mgemini-web>\x1b[0m ', record_transcript=False)
        else:
            self.emit_line(f"Không rõ lệnh {cmd}. Gõ /help để xem hướng dẫn.", color='33', prompt_after=True)

    def write(self, data, system: bool = False):
        if not self.alive:
            raise OrchError('Terminal has ended')
        if not isinstance(data, str):
            data = bytes(data).decode('utf-8', 'replace')
        cleaned = ANSI_RE.sub('', data)
        if not cleaned:
            return
        norm = unicodedata.normalize('NFC', cleaned)
        if not system:
            self.last_input = time.time()

        submitted_lines: list[str] = []
        echo_buf: list[str] = []
        with self.lock:
            for ch in norm:
                if ch in ('\x7f', '\x08'):
                    if self._line_chars:
                        self._line_chars.pop()
                        echo_buf.append('\b \b')
                elif ch in ('\r', '\n'):
                    echo_buf.append('\r\n')
                    line = ''.join(self._line_chars).strip()
                    self._line_chars.clear()
                    if line:
                        submitted_lines.append(line)
                    elif self.idle:
                        echo_buf.append('\x1b[32mgemini-web>\x1b[0m ')
                elif ch == '\x03':
                    self._line_chars.clear()
                    echo_buf.append('^C\r\n\x1b[33m[Đã hủy yêu cầu đang chờ]\x1b[0m\r\n\x1b[32mgemini-web>\x1b[0m ')
                    self.hub.cancel_session_prompts(self.id)
                    self.idle = True
                    self.idle_notified = True
                elif ord(ch) >= 32 or ch == '\t':
                    self._line_chars.append(ch)
                    echo_buf.append(ch)

        if echo_buf:
            self._append_raw(''.join(echo_buf).encode('utf-8', 'replace'), record_transcript=False)

        for line in submitted_lines:
            if not self.first_input_done and not _is_slash_command(line):
                typed = title_from_keys(line)
                if typed:
                    self.first_input_done = True
                    if self.on_title:
                        try:
                            self.on_title(typed)
                        except Exception:
                            pass
            if _is_slash_command(line):
                self._handle_slash(line)
                continue
            self.idle = False
            self.idle_notified = False
            self.has_active_work = True
            self.idle_reason = 'busy-marker'
            self.hub.submit_interactive_prompt(self, line)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.hub.cancel_session_prompts(self.id)
        with self.cond:
            if self.exit_code is None:
                self.exit_code = 0
            self.idle = False
            self.cond.notify_all()
        if self.on_exit:
            try:
                self.on_exit(0)
            except Exception:
                pass


class GeminiBridgeHub:
    """Bộ điều phối hàng đợi prompt/phản hồi giữa Agent Studio và Extension trình duyệt."""

    def __init__(self, cfg, terminals=None):
        self.cfg = cfg
        self.terminals = terminals
        self.key = self._load_or_create_key()
        self.cond = threading.Condition()
        self.tabs: dict[str, dict] = {}
        self.pending: list[dict] = []
        self.inflight: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}

    def _load_or_create_key(self) -> str:
        """Tải khóa ghép đôi từ state dir nếu có; nếu chưa thì tạo mới và lưu lại.
        Giúp chuỗi ghép đôi (dán vào tiện ích trình duyệt) không đổi sau mỗi lần khởi động lại."""
        key_file = self.cfg.state / 'gemini-bridge-key'
        try:
            existing = key_file.read_text(encoding='utf-8').strip()
            if len(existing) >= 16:  # sanity check – key phải đủ dài
                return existing
        except (OSError, ValueError):
            pass
        new_key = secrets.token_urlsafe(24)
        try:
            key_file.write_text(new_key, encoding='utf-8')
        except OSError:
            pass  # nếu không ghi được thì chấp nhận key tạm (không nên xảy ra)
        return new_key

    def read_roots(self) -> list[Path]:
        prov = self.cfg.data.get('providers', {}).get('gemini_web', {})
        raw = prov.get('read_roots') if isinstance(prov, dict) else None
        return [Path(r) for r in raw if isinstance(r, str)] if isinstance(raw, list) else []

    def max_turns(self) -> int:
        prov = self.cfg.data.get('providers', {}).get('gemini_web', {})
        val = prov.get('max_turns', DEFAULT_MAX_TURNS)
        return val if isinstance(val, int) and 1 <= val <= 30 else DEFAULT_MAX_TURNS

    def _prune_tabs_locked(self, now_t: float):
        for tid in [k for k, v in self.tabs.items() if now_t - v.get('last_seen', 0) > TAB_STALE_SECONDS]:
            self.tabs.pop(tid, None)

    def register_tab(self, client_id: str, tab_id: str | int | None, url: str = '', title: str = '') -> dict:
        now_t = time.time()
        key = f"{client_id}:{tab_id or 'default'}"[:120]
        with self.cond:
            self._prune_tabs_locked(now_t)
            self.tabs[key] = {
                'key': key, 'client_id': str(client_id)[:64], 'tab_id': tab_id,
                'url': str(url)[:400], 'title': str(title)[:200],
                'conv_id': extract_conv_slug_from_url(url), 'last_seen': now_t,
            }
            self.cond.notify_all()
        return self.status_snapshot()

    def status_snapshot(self) -> dict:
        now_t = time.time()
        with self.cond:
            self._prune_tabs_locked(now_t)
            tabs = list(self.tabs.values())
            prov_cfg = self.cfg.data.get('providers', {}).get('gemini_web', {})
            return {
                'enabled': bool(prov_cfg.get('enabled', False)),
                'connected': len(tabs) > 0,
                'active_tabs': len(tabs),
                'tabs': [{'tab_id': t['tab_id'], 'url': t['url'], 'title': t['title'], 'conv_id': t['conv_id']} for t in tabs[:10]],
                'pending_prompts': len(self.pending),
                'inflight_prompts': len(self.inflight),
                'max_turns': self.max_turns(),
            }

    def cancel_session_prompts(self, session_id: str):
        with self.cond:
            self.pending = [p for p in self.pending if p.get('owner_session_id') != session_id]
            for pid, item in list(self.inflight.items()):
                if item.get('owner_session_id') == session_id:
                    self.inflight.pop(pid, None)
            self.cond.notify_all()

    def submit_interactive_prompt(self, session: BrowserBridgeSession, user_text: str, turn: int = 1, is_tool_followup: bool = False):
        prompt_text = user_text
        if session.tools_enabled and not session.system_primed and not is_tool_followup:
            prompt_text = build_coding_system_prompt(session.cwd, allow_paths=None, queue_mode=False, read_roots=self.read_roots()) + "YÊU CẦU:\n" + user_text
            session.system_primed = True

        item = {
            'prompt_id': 'prm-' + uuid.uuid4().hex[:16],
            'mode': 'interactive',
            'owner_session_id': session.id,
            'session_ref': session,
            'prompt': prompt_text,
            'target_conv': raw_conv_slug(session.session_id),
            'new_chat': session.session_id is None and turn == 1 and not is_tool_followup,
            'turn': turn,
            'created': time.time(),
        }
        if not is_tool_followup:
            st = self.status_snapshot()
            msg = f"Đang gửi tới tab Gemini (lượt {turn})..." if st['connected'] else "Đã xếp hàng chờ Extension kết nối tab gemini.google.com..."
            session.emit_line(msg, color='36' if st['connected'] else '33')
        with self.cond:
            self.pending.append(item)
            self.cond.notify_all()

    def create_worker_job(self, worktree: str, allow_paths: list[str], prompt: str,
                          resume_session: str | None = None, max_turns: int | None = None) -> dict:
        wt = Path(worktree).resolve()
        if not inside(wt, self.cfg.state / 'worktrees') or wt == (self.cfg.state / 'worktrees').resolve():
            raise OrchError('Worktree phải nằm trong thư mục worktrees của Agent Studio')
        if not isinstance(allow_paths, list) or not allow_paths:
            raise OrchError('allow_paths bắt buộc cho nhiệm vụ hàng đợi')
        executor = WorkspaceExecutor(wt, allow_paths=allow_paths, read_only=False, read_roots=self.read_roots())
        job_id = 'job-' + uuid.uuid4().hex[:16]
        conv_slug = normalize_gemini_session_id(resume_session)
        job = {
            'job_id': job_id, 'status': 'running', 'worktree': str(worktree),
            'allow_paths': list(allow_paths), 'executor': executor,
            'turn': 1, 'max_turns': max_turns or self.max_turns(),
            'session_id': conv_slug, 'events': [], 'summary': '', 'error': None,
        }
        if conv_slug:
            job['events'].append({'type': 'thread.started', 'thread_id': conv_slug})
        prompt_item = {
            'prompt_id': 'prm-' + uuid.uuid4().hex[:16],
            'mode': 'worker_job', 'job_id': job_id, 'owner_session_id': job_id,
            'prompt': build_coding_system_prompt(worktree, allow_paths=allow_paths, queue_mode=True, read_roots=self.read_roots()) + prompt,
            'target_conv': raw_conv_slug(conv_slug), 'new_chat': conv_slug is None,
            'turn': 1, 'created': time.time(),
        }
        with self.cond:
            self.jobs[job_id] = job
            self.pending.append(prompt_item)
            self.cond.notify_all()
        return {'job_id': job_id, 'status': 'running'}

    def cancel_worker_job(self, job_id: str) -> dict:
        with self.cond:
            job = self.jobs.get(job_id)
            if not job:
                raise OrchError('Unknown Gemini worker job')
            job['status'] = 'cancelled'
            job['error'] = 'Cancellation requested'
            self.pending = [p for p in self.pending if p.get('job_id') != job_id]
            for pid, item in list(self.inflight.items()):
                if item.get('job_id') == job_id:
                    self.inflight.pop(pid, None)
            self.cond.notify_all()
            return self._job_public(job)

    def get_worker_job(self, job_id: str, wait: float = 0.0) -> dict:
        deadline = time.time() + max(0.0, min(wait, 10.0))
        with self.cond:
            while True:
                job = self.jobs.get(job_id)
                if not job:
                    raise OrchError('Unknown Gemini worker job')
                if job['status'] != 'running' or time.time() >= deadline:
                    return self._job_public(job)
                self.cond.wait(min(0.5, max(0.05, deadline - time.time())))

    @staticmethod
    def _job_public(job: dict) -> dict:
        return {
            'job_id': job['job_id'], 'status': job['status'], 'turn': job['turn'],
            'session_id': job['session_id'], 'changed_files': sorted(job['executor'].changed_files),
            'summary': job['summary'], 'error': job['error'], 'events': list(job['events']),
        }

    def poll_next_prompt(self, client_id: str, tab_id: str | int | None = None, url: str = '', wait: float = 8.0) -> dict | None:
        self.register_tab(client_id, tab_id, url=url)
        deadline = time.time() + max(0.0, min(float(wait), 15.0))
        with self.cond:
            while True:
                if self.pending:
                    item = self.pending.pop(0)
                    self.inflight[item['prompt_id']] = item
                    return {
                        'prompt_id': item['prompt_id'], 'prompt': item['prompt'],
                        'target_conv': item.get('target_conv'), 'new_chat': bool(item.get('new_chat')),
                        'turn': item.get('turn', 1),
                    }
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self.cond.wait(min(1.0, remaining))

    def _save_debug(self, item: dict, text: str, blocks, debug_html, url: str, error):
        """Keep the last raw reply so a bad extraction can be diagnosed. Local state folder only; overwritten each time."""
        try:
            folder = self.cfg.state / 'gemini-debug'
            folder.mkdir(parents=True, exist_ok=True)
            payload = {'time': datetime.now(timezone.utc).isoformat(), 'mode': item.get('mode'), 'turn': item.get('turn'),
                       'url': url[:300], 'error': error, 'text': text[:20000],
                       'blocks': [b[:4000] for b in (blocks or []) if isinstance(b, str)][:20],
                       'html': (debug_html or '')[:8000]}
            (folder / 'last-reply.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
        except OSError:
            pass

    def submit_reply(self, prompt_id: str, text: str, url: str = '', error: str | None = None,
                     blocks: list | None = None, debug_html: str | None = None) -> dict:
        with self.cond:
            item = self.inflight.pop(prompt_id, None)
        if item is None:
            return {'ok': False, 'ignored': True}
        blocks = blocks if isinstance(blocks, list) else None
        self._save_debug(item, text, blocks, debug_html, url, error)
        conv_id = extract_conv_slug_from_url(url)
        if item['mode'] == 'interactive':
            self._handle_interactive_reply(item, text, conv_id, error, blocks)
        elif item['mode'] == 'worker_job':
            self._handle_worker_reply(item, text, conv_id, error, blocks)
        return {'ok': True}

    def _finish_interactive_turn(self, sess: BrowserBridgeSession):
        sess.idle = True
        sess.idle_reason = 'quiet'

    def _handle_interactive_reply(self, item: dict, text: str, conv_id: str | None, error: str | None, blocks: list | None = None):
        sess: BrowserBridgeSession = item['session_ref']
        if not sess or not sess.alive:
            return
        if conv_id and conv_id != sess.session_id:
            sess.session_id = conv_id
            if self.terminals is not None and getattr(self.terminals, 'db', None) and sess.conversation_id:
                try:
                    self.terminals.db.conversation_update(
                        sess.conversation_id, session_id=conv_id,
                        last_active=datetime.now(timezone.utc).isoformat()
                    )
                except Exception:
                    pass

        if error:
            sess.emit_line(f"[Lỗi trình duyệt Gemini] {error}", color='31', prompt_after=True)
            self._finish_interactive_turn(sess)
            return

        reply_text = (text or '').strip()
        sess.emit_line("\n--- Gemini ---", color='1;34')
        sess.emit_line(reply_text or '(Trống)')

        calls = parse_tool_calls(reply_text, blocks) if sess.tools_enabled else []
        if not calls:
            sess.emit_line("[Hoàn tất lượt trả lời]", color='32', prompt_after=True)
            self._finish_interactive_turn(sess)
            return

        results, finished = [], False
        for call in calls:
            res = sess.executor.execute(call)
            results.append(res)
            act = res.get('action')
            if act == 'finish_task':
                finished = True
                sess.emit_line(f"[finish_task] {res.get('summary', '')}", color='32')
            elif res.get('ok'):
                detail = res.get('path') or f"{len(res.get('files', []))} files"
                sess.emit_line(f"  [Tool {act}] OK -> {detail}", color='36')
            else:
                sess.emit_line(f"  [Tool {act}] LỖI -> {str(res.get('error'))[:300]}", color='33')

        if finished:
            sess.emit_line("[Đã hoàn thành công việc]", color='32', prompt_after=True)
            self._finish_interactive_turn(sess)
            return

        next_turn = item.get('turn', 1) + 1
        if next_turn > self.max_turns():
            sess.emit_line(f"[Chạm trần {self.max_turns()} lượt tool liên tiếp - tạm dừng]", color='33', prompt_after=True)
            self._finish_interactive_turn(sess)
            return

        followup = (
            "[AO_TOOL_RESULT]\n"
            + format_tool_results(results)
            + "\n[/AO_TOOL_RESULT]\n"
            "Hãy tiếp tục thực hiện yêu cầu dựa trên kết quả trên. Khi xong hãy xuất khối finish_task hoặc tóm tắt."
        )
        sess.emit_line(f"Đang phản hồi kết quả tool cho Gemini (lượt {next_turn}/{self.max_turns()})...", color='2')
        self.submit_interactive_prompt(sess, followup, turn=next_turn, is_tool_followup=True)

    def _handle_worker_reply(self, item: dict, text: str, conv_id: str | None, error: str | None, blocks: list | None = None):
        job_id = item['job_id']
        with self.cond:
            job = self.jobs.get(job_id)
            if not job or job['status'] != 'running':
                return
            if conv_id and conv_id != job['session_id']:
                job['session_id'] = conv_id
                job['events'].append({'type': 'thread.started', 'thread_id': conv_id})

            if error:
                job['status'] = 'failed'
                job['error'] = f'Gemini browser bridge error: {error}'
                self.cond.notify_all()
                return

            reply_text = (text or '').strip()
            job['events'].append({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': reply_text[:8000]}})
            calls = parse_tool_calls(reply_text, blocks)

            if not calls:
                if job['executor'].changed_files:
                    job['summary'] = reply_text[-4000:] or 'Hoàn thành qua Gemini Web.'
                    job['events'].append({'type': 'turn.completed'})
                    job['status'] = 'completed'
                elif job['turn'] == 1 and job['max_turns'] >= 2:
                    job['turn'] = 2
                    self.pending.append({
                        'prompt_id': 'prm-' + uuid.uuid4().hex[:16],
                        'mode': 'worker_job', 'job_id': job_id, 'owner_session_id': job_id,
                        'prompt': (
                            "[AO_SYSTEM_NOTICE] Bạn chưa sửa tệp nào trong worktree. "
                            "Hãy xuất khối <<<AO_TOOL ... AO_TOOL>>> (read_file, replace_in_file, write_file) "
                            "trong phạm vi allow_paths rồi kết thúc bằng finish_task."
                        ),
                        'target_conv': raw_conv_slug(job['session_id']), 'new_chat': False, 'turn': 2, 'created': time.time(),
                    })
                else:
                    job['status'] = 'failed'
                    job['error'] = 'Gemini kết thúc mà không tạo thay đổi tệp nào.'
                self.cond.notify_all()
                return

            results, finish_summary = [], None
            for call in calls:
                res = job['executor'].execute(call)
                results.append(res)
                job['events'].append({
                    'type': 'item.completed',
                    'item': {'type': 'tool_result', 'text': f"[{res.get('action')}] ok={res.get('ok')} {res.get('path', res.get('error', ''))}"}
                })
                if res.get('action') == 'finish_task' and res.get('ok'):
                    finish_summary = res.get('summary')

            if finish_summary is not None:
                job['summary'] = finish_summary
                job['events'].append({'type': 'turn.completed'})
                job['status'] = 'completed'
                self.cond.notify_all()
                return

            next_turn = job['turn'] + 1
            if next_turn > job['max_turns']:
                if job['executor'].changed_files:
                    job['summary'] = f"Đạt trần {job['max_turns']} lượt; đã sửa: {', '.join(sorted(job['executor'].changed_files))}."
                    job['events'].append({'type': 'turn.completed'})
                    job['status'] = 'completed'
                else:
                    job['status'] = 'failed'
                    job['error'] = f"Vượt trần {job['max_turns']} lượt tool mà chưa hoàn tất."
                self.cond.notify_all()
                return

            job['turn'] = next_turn
            self.pending.append({
                'prompt_id': 'prm-' + uuid.uuid4().hex[:16],
                'mode': 'worker_job', 'job_id': job_id, 'owner_session_id': job_id,
                'prompt': (
                    "[AO_TOOL_RESULT]\n" + format_tool_results(results) + "\n[/AO_TOOL_RESULT]\n"
                    "Tiếp tục nhiệm vụ. Khi hoàn tất sửa đổi, hãy xuất khối finish_task."
                ),
                'target_conv': raw_conv_slug(job['session_id']), 'new_chat': False, 'turn': next_turn, 'created': time.time(),
            })
            self.cond.notify_all()


def run_worktree_via_bridge(config, worktree: Path, allow_paths: list[str], prompt: str,
                            folder: Path, timeout: int, resume: str | None = None, cancelled=lambda: False) -> dict:
    """Chạy nhiệm vụ hàng đợi (queue worktree) qua HTTP loopback tới GeminiBridgeHub."""
    folder.mkdir(parents=True, exist_ok=True)
    stdout_log, stderr_log = folder / 'stdout.log', folder / 'stderr.log'
    stdout_log.write_text('', encoding='utf-8')
    stderr_log.write_text('', encoding='utf-8')

    bridge_file = config.state / 'gemini-bridge.json'
    if not bridge_file.is_file():
        stderr_log.write_text('Chưa tìm thấy gemini-bridge.json (hãy mở Agent Studio WebServer trước).\n', encoding='utf-8')
        return {'exit_code': 1, 'reason': 'bridge_unavailable', 'elapsed_seconds': 0.0, 'stdout_bytes': 0, 'stderr_bytes': stderr_log.stat().st_size}

    try:
        info = json.loads(bridge_file.read_text(encoding='utf-8'))
        base_url = f"http://127.0.0.1:{int(info['port'])}/api/gemini-bridge"
        headers = {'X-Gemini-Bridge-Key': str(info['key']), 'Content-Type': 'application/json'}
    except (OSError, ValueError, KeyError) as exc:
        stderr_log.write_text(f'Lỗi đọc gemini-bridge.json: {exc}\n', encoding='utf-8')
        return {'exit_code': 1, 'reason': 'bridge_invalid', 'elapsed_seconds': 0.0, 'stdout_bytes': 0, 'stderr_bytes': stderr_log.stat().st_size}

    def call_bridge(path: str, payload: dict | None = None, req_timeout: float = 15.0) -> dict:
        req = urllib.request.Request(
            base_url + path,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method='GET' if payload is None else 'POST',
        )
        with urllib.request.urlopen(req, timeout=req_timeout) as resp:
            return json.loads(resp.read(4_000_000))

    started = time.monotonic()
    try:
        job_id = call_bridge('/jobs', {
            'worktree': str(worktree), 'allow_paths': list(allow_paths),
            'prompt': prompt, 'resume': resume,
        })['job_id']
    except Exception as exc:
        stderr_log.write_text(f'Không khởi tạo được job trên Gemini Bridge: {exc}\n', encoding='utf-8')
        return {'exit_code': 1, 'reason': 'bridge_error', 'elapsed_seconds': round(time.monotonic() - started, 3),
                'stdout_bytes': 0, 'stderr_bytes': stderr_log.stat().st_size}

    written_events, reason, exit_code = 0, None, 1
    while True:
        elapsed = time.monotonic() - started
        if cancelled() or elapsed >= timeout:
            try:
                call_bridge(f'/jobs/{job_id}/cancel', {})
            except Exception:
                pass
            reason = 'cancelled' if cancelled() else 'timeout'
            stderr_log.write_text('Đã hủy nhiệm vụ.\n' if reason == 'cancelled' else f'Quá hạn {timeout}s.\n', encoding='utf-8')
            break

        try:
            state = call_bridge(f'/jobs/{job_id}?wait=2', None, req_timeout=10.0)
        except Exception as exc:
            stderr_log.write_text(f'Mất kết nối Gemini Bridge: {exc}\n', encoding='utf-8')
            reason = 'bridge_lost'
            break

        events = state.get('events') or []
        if len(events) > written_events:
            with stdout_log.open('a', encoding='utf-8') as f:
                for ev in events[written_events:]:
                    f.write(json.dumps(ev, ensure_ascii=False) + '\n')
            written_events = len(events)

        st = state.get('status')
        if st == 'completed':
            exit_code = 0
            break
        if st == 'cancelled':
            reason = 'cancelled'
            break
        if st == 'failed':
            stderr_log.write_text(str(state.get('error') or 'Gemini job failed') + '\n', encoding='utf-8')
            break

    return {
        'exit_code': exit_code, 'reason': reason,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'stdout_bytes': stdout_log.stat().st_size if stdout_log.exists() else 0,
        'stderr_bytes': stderr_log.stat().st_size if stderr_log.exists() else 0,
    }
