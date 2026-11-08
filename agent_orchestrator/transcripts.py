"""Transcript recorder for interactive and worker agent sessions.

Records plain-text (clean, ANSI-stripped, secret-redacted) logs with timestamps
under state/transcripts/<conversation_id>.log.
Enforces per-file size limits (truncating the head) and total directory limits (deleting oldest).
"""
from __future__ import annotations

import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

# Max size per transcript file: 5 MB
MAX_TRANSCRIPT_FILE_SIZE = 5 * 1024 * 1024
# Truncation target when a file exceeds MAX_TRANSCRIPT_FILE_SIZE: retain last 4 MB
RETAIN_TRANSCRIPT_FILE_SIZE = 4 * 1024 * 1024
# Max total size of all transcripts in the directory: 100 MB
MAX_TRANSCRIPTS_TOTAL_SIZE = 100 * 1024 * 1024

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')
CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]')

SECRET_PATTERNS = [
    # Bearer tokens
    (re.compile(r'(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]{8,}'), r'\1[REDACTED]'),
    # Key-value secret assignments: api_key="...", password: '...', etc.
    (re.compile(r'(?i)\b(api[_-]?key|token|secret|password|passwd|authorization)\b(\s*[:=]\s*["\']?)[a-zA-Z0-9_\-\.]{8,}(["\']?)'),
     r'\1\2[REDACTED]\3'),
    # Known API key prefixes
    (re.compile(r'\b(sk-ant-[a-zA-Z0-9_\-]{16,})\b'), '[REDACTED]'),
    (re.compile(r'\b(sk-[a-zA-Z0-9_\-]{20,})\b'), '[REDACTED]'),
    (re.compile(r'\b(gh[pousr]_[a-zA-Z0-9]{20,})\b'), '[REDACTED]'),
]

_DIR_LOCK = threading.Lock()


def strip_ansi(text: str) -> str:
    """Strip all ANSI escape sequences."""
    return ANSI.sub('', text)


def clean_transcript_text(text: str) -> str:
    """Normalize newlines, strip ANSI and control characters."""
    text = strip_ansi(str(text))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return CONTROL.sub('', text)


def title_from_keys(keys: str, limit: int = 80):
    """The first line a person typed, as it would look on screen.

    Raw keystrokes contain escape sequences (xterm focus reports ESC[I / ESC[O, arrows, bracketed paste) and
    corrections (Backspace/DEL, sent by Vietnamese IMEs while composing). Replay them instead of storing them.
    Returns None until a non-empty line has been entered.
    """
    import unicodedata
    line = []
    for ch in strip_ansi(str(keys)):
        if ch in (chr(0x7f), chr(8)):  # DEL / Backspace
            if line:
                line.pop()
        elif ch in (chr(13), chr(10)):  # Enter
            if ''.join(line).strip():
                break
            line.clear()
        elif ch == chr(9):  # Tab
            line.append(' ')
        elif ord(ch) >= 32 and not 0x7f <= ord(ch) <= 0x9f:
            line.append(ch)
    text = unicodedata.normalize('NFC', ''.join(line))
    text = ' '.join(text.split())
    return text[:limit] or None


_LEFTOVER_FOCUS = re.compile(r'^(?:\[[IO])+')


def clean_title(title):
    """Titles saved by older versions may start with the leftovers of focus reports (\"[O[I...\")."""
    if not isinstance(title, str):
        return title
    return _LEFTOVER_FOCUS.sub('', title).strip()


def mask_secrets(text: str) -> str:
    """Redact tokens, API keys, passwords and bearer credentials from text."""
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_for_transcript(text: str) -> str:
    """Full sanitization: strip ANSI, clean control characters, and mask secrets."""
    return mask_secrets(clean_transcript_text(text))


def prune_transcripts_dir(dir_path: Path, max_total_size: int = MAX_TRANSCRIPTS_TOTAL_SIZE) -> None:
    """Delete oldest transcript files when total directory size exceeds max_total_size."""
    if not dir_path.is_dir():
        return
    with _DIR_LOCK:
        try:
            files = []
            total_size = 0
            for entry in dir_path.glob('*.log'):
                try:
                    stat = entry.stat()
                    files.append((stat.st_mtime, stat.st_size, entry))
                    total_size += stat.st_size
                except OSError:
                    continue
            if total_size <= max_total_size:
                return
            # Sort oldest first
            files.sort(key=lambda x: x[0])
            for _, size, path in files:
                if total_size <= max_total_size:
                    break
                try:
                    path.unlink(missing_ok=True)
                    total_size -= size
                except OSError:
                    continue
        except OSError:
            pass


def truncate_file_head(file_path: Path, retain_size: int = RETAIN_TRANSCRIPT_FILE_SIZE) -> None:
    """Drop the head of a file, keeping the most recent retain_size bytes."""
    try:
        size = file_path.stat().st_size
        if size <= retain_size:
            return
        with open(file_path, 'rb') as f:
            f.seek(size - retain_size)
            # Find next newline to keep line boundaries clean
            chunk = f.read(4096)
            nl_pos = chunk.find(b'\n')
            if nl_pos != -1:
                f.seek(size - retain_size + nl_pos + 1)
            else:
                f.seek(size - retain_size)
            content = f.read()
        with open(file_path, 'wb') as f:
            f.write(b'[... noi dung cu da duoc luoc bo de giu gioi han 5 MB ...]\n')
            f.write(content)
    except OSError:
        pass


def append_transcript_entry(
    file_path: Path | str,
    text: str,
    timestamp: str | None = None,
    max_file_size: int = MAX_TRANSCRIPT_FILE_SIZE,
    max_total_size: int = MAX_TRANSCRIPTS_TOTAL_SIZE,
    retain_size: int | None = None,
) -> None:
    """Append sanitized, timestamped lines to a transcript file.

    Guarantees size limits per file and total directory size.
    Uses tightest permissions on Windows.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_for_transcript(text).rstrip('\n')
    if not sanitized:
        return

    ts = timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds')
    lines = [f'[{ts}] {line}\n' for line in sanitized.split('\n')]
    payload = ''.join(lines).encode('utf-8')

    try:
        # Secure file open with tight permissions (0o600)
        flags = os.O_CREAT | os.O_WRONLY | os.O_APPEND
        fd = os.open(path, flags, 0o600)
        try:
            with open(fd, 'ab', closefd=False) as f:
                f.write(payload)
        finally:
            os.close(fd)

        # Check file size limit
        try:
            if path.stat().st_size > max_file_size:
                target_retain = retain_size if retain_size is not None else int(max_file_size * 0.8)
                truncate_file_head(path, target_retain)
        except OSError:
            pass

        # Check directory total size limit periodically
        prune_transcripts_dir(path.parent, max_total_size)
    except OSError:
        pass
