"""Early report then real finish; agy working lines; stale spinner; many terminals (see logs/ao-thong-bao-sai.md)."""
from __future__ import annotations

import time
from unittest import mock

from agent_orchestrator import terminals
from agent_orchestrator.terminals import Terminals, terminal_looks_busy
from tests.test_interactive_idle import MockInteractiveSession
from tests.test_workflow import FakeSession, WorkflowBase


def busy(text):
    return terminal_looks_busy(bytearray(text.encode('utf-8')))


class AgySignalsAndRearm(WorkflowBase):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db, idle_debounce=0.1)
        self.agent0 = FakeSession()
        self.t.sessions['agent0'] = self.agent0
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()

    def add(self, n):
        a = MockInteractiveSession(f'agy-{n}', provider='agy', agent=n, cwd=self.root)
        self.t.sessions[a.id] = a
        a.write('lam viec\n')
        return a

    def poll(self, wait=0.15):
        time.sleep(wait)
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()

    def test_agy_working_lines_are_busy(self):
        for text in ('Spawned 2 subagents\nĐang chờ 2 subagent hoàn tất', '● dotnet build ... running', 'Editing files...', 'x\n1 task(s)'):
            self.assertTrue(busy(text), text)
        self.assertFalse(busy('Working...\nHOÀN TẤT: abc123'))

    def test_subagent_wait_is_not_reported_early(self):
        a = self.add(1)
        a.emit_output('Spawned 2 subagents\nĐang chờ 2 subagent hoàn tất')
        self.poll()
        self.assertEqual(self.agent0.written, [])

    def test_resumed_terminal_is_reported_again_when_it_really_finishes(self):
        a = self.add(1)
        a.emit_output('cho lenh')                      # quiet, no marker: reported early
        self.poll()
        self.assertEqual(len(self.agent0.written), 2)
        a.emit_output('● dotnet build ... running\n' + 'x' * 300 + '\nWorking...')   # it resumes by itself
        self.poll(0.05)
        self.assertFalse(a.idle)
        self.assertFalse(a.idle_notified)
        a.emit_output('\nHOÀN TẤT: abc123')
        self.poll()
        self.assertEqual(len(self.agent0.written), 4)

    def test_tiny_redraw_after_idle_does_not_repeat_the_notice(self):
        a = self.add(1)
        a.emit_output('xong')
        self.poll()
        a.emit_output('\x1b[?25h ⣾ Generating...')
        self.poll()
        self.assertEqual(len(self.agent0.written), 2)

    def test_stale_spinner_line_does_not_silence_a_terminal_forever(self):
        a = self.add(1)
        a.emit_output('ket qua\n⣾ Generating... esc to cancel')
        with mock.patch.object(terminals, 'SPINNER_QUIET_CAP', 0.05):
            self.poll()
        self.assertEqual(len(self.agent0.written), 2)
        self.assertEqual(a.idle_reason, 'quiet')

    def test_a_broken_terminal_does_not_block_the_others(self):
        bad = self.add(1)
        good = self.add(2)
        good.emit_output('xong')
        bad.emit_output('xong')
        orig = self.t.update_interactive_idle

        def boom(s, now=None):
            if s is bad:
                raise RuntimeError('x')
            return orig(s, now)

        with mock.patch.object(self.t, 'update_interactive_idle', boom):
            self.poll()
        self.assertEqual(len(self.agent0.written), 2)
        self.assertIn('agy-2 đã xong', self.agent0.written[0][0])
