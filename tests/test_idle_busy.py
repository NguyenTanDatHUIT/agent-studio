"""'agy đã xong' must not fire while the agent is still running a long tool, nor re-fire because the browser sent focus reports."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from agent_orchestrator import terminals
from agent_orchestrator.terminals import Session, Terminals, terminal_looks_busy
from tests.test_interactive_idle import MockInteractiveSession
from tests.test_workflow import FakeSession, WorkflowBase

RUNNING = '● Ran 5 commands (+2 · docker exec a16b-pg ...)\n○ Running (cd C:/x/Source/NET8) (ctrl+o to expand)\n? for shortcuts'
FINISHED = '○ Running (cd C:/x)\n● Ran (cd C:/x)\nĐã sửa xong, 3 test đạt.\n> \n? for shortcuts'


class BusyMarkers(unittest.TestCase):
    def busy(self, text):
        return terminal_looks_busy(bytearray(text.encode('utf-8')))

    def test_a_tool_that_is_still_running_is_busy(self):
        self.assertTrue(self.busy(RUNNING))
        self.assertTrue(self.busy('● Bash(dotnet test)\n  ⎿  Running… (4m 12s)'))     # claude
        self.assertTrue(self.busy('● Ran (a)\n○ Running (b)'))                    # a second tool started after the first ended

    def test_animated_status_lines_are_left_to_the_spinner_check(self):
        # they redraw every second, so the quiet-time rule already covers them; a stale one must not mean "busy" forever
        self.assertFalse(self.busy('• Working (12s • esc to interrupt)'))
        self.assertFalse(self.busy('esc to cancel   Gemini 3.8 Flash\nResult line\n> '))

    def test_finished_output_is_not_busy(self):
        self.assertFalse(self.busy(FINISHED))
        self.assertFalse(self.busy('✻ Baked for 14s · done 10:39 PM'))           # claude
        self.assertFalse(self.busy(''))
        self.assertFalse(self.busy('just some ordinary output\n> '))

    def test_ansi_and_spinner_frames_do_not_hide_the_marker(self):
        self.assertTrue(self.busy('\x1b[2J\x1b[H⣾ ○ \x1b[1mRunning (cd C:/x)\x1b[0m ⣽'))


class SilentToolRun(WorkflowBase):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db, idle_debounce=0.1)
        self.agent0 = FakeSession()
        self.t.sessions['agent0'] = self.agent0
        self.t.last_notice_sent = 0.0
        self.agy = MockInteractiveSession('agy-1', provider='agy', agent=1, cwd=self.root)
        self.t.sessions['agy-1'] = self.agy
        self.t.notify_agent0()                      # attach Agent 0
        self.agy.write('Làm A1.6b theo file prompt\n')

    def poll(self, wait=0.15):
        time.sleep(wait)
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()

    def test_quiet_while_a_long_command_runs_is_not_reported(self):
        self.agy.emit_output(RUNNING)
        self.poll()
        self.poll()
        self.assertEqual(self.agent0.written, [])
        self.assertFalse(self.agy.idle)

    def test_it_is_reported_once_the_command_has_finished(self):
        self.agy.emit_output(RUNNING)
        self.poll()
        self.assertEqual(self.agent0.written, [])
        self.agy.emit_output(FINISHED)
        self.poll()
        self.assertEqual(len(self.agent0.written), 2)
        self.assertIn('agy-1 đã xong', self.agent0.written[0][0])

    def test_a_stale_busy_marker_cannot_silence_a_terminal_forever(self):
        self.agy.emit_output(RUNNING)
        with mock.patch.object(terminals, 'IDLE_BUSY_CAP', 0.05):
            self.poll()
        self.assertEqual(len(self.agent0.written), 2)


class RealSessionInput(unittest.TestCase):
    """Uses a real ConPTY session: what the browser's terminal sends about focus must not count as work."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='idle-input-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.session = Session(sid='s1', kind='agent', title='T', argv=[os.environ['COMSPEC']], cwd=self.tmp,
                               env=dict(os.environ), cols=100, rows=30)
        self.addCleanup(self.session.close)
        self.session.idle, self.session.idle_notified, self.session.has_active_work, self.session.last_input = True, True, False, 0.0

    def test_focus_mouse_and_cursor_reports_do_not_rearm_the_notice(self):
        esc = chr(27)
        for report in (esc + '[I', esc + '[O', esc + '[<0;12;5M', esc + '[24;80R'):
            self.session.write(report)
        self.assertEqual((self.session.idle, self.session.idle_notified, self.session.has_active_work, self.session.last_input),
                         (True, True, False, 0.0))

    def test_typing_and_enter_do_rearm_it(self):
        self.session.write('echo hi')
        self.assertEqual((self.session.idle, self.session.idle_notified, self.session.has_active_work), (False, False, True))
        self.session.idle, self.session.idle_notified, self.session.has_active_work = True, True, False
        self.session.write(chr(13))                         # a bare Enter is a real action (e.g. answering a prompt)
        self.assertEqual((self.session.idle, self.session.idle_notified, self.session.has_active_work), (False, False, True))

    def test_slash_commands_do_not_arm_the_finished_notice(self):
        for cmd in ('/clear', '/model gpt', '/compact'):
            self.session.write(cmd)
            self.session.write(chr(13))
            self.assertEqual((self.session.idle, self.session.idle_notified, self.session.has_active_work), (True, True, False), cmd)
        self.session.write('/clear' + chr(13) + 'fix bug')   # a task typed after a command still counts
        self.assertTrue(self.session.has_active_work)

    def test_a_report_glued_to_typing_still_counts_as_typing(self):
        self.session.write(chr(27) + '[Iecho x')
        self.assertTrue(self.session.has_active_work)

    def test_the_title_logic_still_ignores_reports(self):
        titles = []
        self.session.on_title = titles.append
        self.session.write(chr(27) + '[O' + chr(27) + '[I')
        self.session.write('echo done' + chr(13))
        self.assertEqual(titles, ['echo done'])


if __name__ == '__main__':
    unittest.main()
