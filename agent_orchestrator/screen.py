"""Minimal terminal screen model: rebuilds what a TUI (agy, Claude Code) shows NOW from its raw byte stream.

A full-screen TUI redraws regions with cursor moves, so the last line of the byte stream is often a stale footer rather
than the last line on screen. This tiny emulator replays the tail of the stream into a rows x cols grid (cursor moves,
erase line/display, scrolling) so callers can look at the bottom of the real screen. It is an approximation, not a
terminal: colours, wide-character widths and alternate-screen details are ignored. Standard library only.
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r'\x1b\[([0-?]*)[ -/]*([@-~])|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][0-2AB]|\x1b([78=>DEHMc])|([\x00-\x1f])|([^\x00-\x1f\x1b]+)')


def _ints(params, default):
    out = []
    for part in params.replace('?', '').split(';'):
        try:
            out.append(int(part))
        except ValueError:
            out.append(default)
    return out or [default]


class Screen:
    def __init__(self, cols=100, rows=30):
        self.cols = max(20, min(int(cols), 400))
        self.rows = max(5, min(int(rows), 200))
        self.grid = [[' '] * self.cols for _ in range(self.rows)]
        self.x = self.y = 0
        self.saved = (0, 0)

    def _scroll(self):
        del self.grid[0]
        self.grid.append([' '] * self.cols)

    def _lf(self):
        if self.y >= self.rows - 1:
            self._scroll()
        else:
            self.y += 1

    def _put(self, text):
        for ch in text:
            if self.x >= self.cols:
                self.x = 0
                self._lf()
            self.grid[self.y][self.x] = ch
            self.x += 1

    def _csi(self, params, final):
        p = _ints(params, 0)
        n = p[0] if p[0] > 0 else 1
        if final == 'A':
            self.y = max(0, self.y - n)
        elif final in 'Be':
            self.y = min(self.rows - 1, self.y + n)
        elif final in 'Ca':
            self.x = min(self.cols - 1, self.x + n)
        elif final == 'D':
            self.x = max(0, self.x - n)
        elif final == 'E':
            self.y, self.x = min(self.rows - 1, self.y + n), 0
        elif final == 'F':
            self.y, self.x = max(0, self.y - n), 0
        elif final == 'G':
            self.x = max(0, min(self.cols - 1, n - 1))
        elif final == 'd':
            self.y = max(0, min(self.rows - 1, n - 1))
        elif final in 'Hf':
            row = p[0] if p[0] > 0 else 1
            col = (p[1] if len(p) > 1 and p[1] > 0 else 1)
            self.y, self.x = max(0, min(self.rows - 1, row - 1)), max(0, min(self.cols - 1, col - 1))
        elif final == 'J':
            mode = p[0]
            if mode == 2 or mode == 3:
                self.grid = [[' '] * self.cols for _ in range(self.rows)]
            elif mode == 0:
                self.grid[self.y][self.x:] = [' '] * (self.cols - self.x)
                for r in range(self.y + 1, self.rows):
                    self.grid[r] = [' '] * self.cols
            elif mode == 1:
                self.grid[self.y][:self.x + 1] = [' '] * (self.x + 1)
                for r in range(self.y):
                    self.grid[r] = [' '] * self.cols
        elif final == 'K':
            mode = p[0]
            if mode == 0:
                self.grid[self.y][self.x:] = [' '] * (self.cols - self.x)
            elif mode == 1:
                self.grid[self.y][:self.x + 1] = [' '] * (self.x + 1)
            elif mode == 2:
                self.grid[self.y] = [' '] * self.cols
        elif final == 'X':
            for i in range(self.x, min(self.cols, self.x + n)):
                self.grid[self.y][i] = ' '
        elif final == 's':
            self.saved = (self.x, self.y)
        elif final == 'u':
            self.x, self.y = self.saved
        elif final == 'S':
            for _ in range(n):
                self._scroll()
        # everything else (colours m, modes h/l, cursor style, reports) does not change the visible text

    def feed(self, text):
        for m in _TOKEN.finditer(text):
            if m.group(2):
                self._csi(m.group(1) or '', m.group(2))
            elif m.group(3):
                code = m.group(3)
                if code == '7':
                    self.saved = (self.x, self.y)
                elif code == '8':
                    self.x, self.y = self.saved
                elif code == 'M':
                    self.y = max(0, self.y - 1)
                elif code == 'D':
                    self._lf()
                elif code == 'E':
                    self._lf()
                    self.x = 0
                elif code == 'c':
                    self.grid = [[' '] * self.cols for _ in range(self.rows)]
                    self.x = self.y = 0
            elif m.group(4):
                c = m.group(4)
                if c == '\r':
                    self.x = 0
                elif c == '\n':
                    self._lf()
                elif c == '\b':
                    self.x = max(0, self.x - 1)
                elif c == '\t':
                    self.x = min(self.cols - 1, (self.x // 8 + 1) * 8)
            elif m.group(5):
                self._put(m.group(5))

    def lines(self):
        """Visible lines, right-stripped; blank lines kept so callers can pick the bottom non-empty ones."""
        return [''.join(row).rstrip() for row in self.grid]


def screen_lines(buffer, cols=100, rows=30, tail_bytes=12000):
    """Lines of the screen after replaying the last `tail_bytes` of `buffer` (bytes/bytearray)."""
    if not buffer:
        return []
    text = bytes(buffer[-tail_bytes:]).decode('utf-8', 'replace')
    screen = Screen(cols, rows)
    screen.feed(text)
    return screen.lines()


def bottom_lines(buffer, count=2, cols=100, rows=30):
    """The last `count` non-empty lines on the rebuilt screen (oldest first)."""
    lines = [line for line in screen_lines(buffer, cols, rows) if line.strip()]
    return lines[-count:]
