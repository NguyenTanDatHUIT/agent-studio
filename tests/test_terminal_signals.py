"""Signals typed into Agent 0: screen-based busy detection, error lines, batching, the
"báo hoàn thành" window button and the sent/seen bookkeeping. Quiet is a hint; these tests pin what is claimed and what is not."""
from __future__ import annotations

import json
import time
import unittest

from agent_orchestrator.config import OrchError
from agent_orchestrator.screen import Screen, bottom_lines
from agent_orchestrator.terminals import Terminals, is_terminal_spinning, terminal_error
from tests.test_interactive_idle import MockInteractiveSession
from tests.test_workflow import FakeSession, WorkflowBase


def buf(text):
    return bytearray(text.encode('utf-8'))


class ScreenModel(unittest.TestCase):
    def test_cursor_move_and_erase_replace_text(self):
        s = Screen(40, 10)
        s.feed('old line\x1b[1;1H\x1b[2Knew')
        self.assertEqual(s.lines()[0], 'new')

    def test_scrolling_keeps_the_newest_lines(self):
        s = Screen(40, 5)
        s.feed('\r\n'.join(f'line {i}' for i in range(12)))
        self.assertEqual([x for x in s.lines() if x][-1], 'line 11')

    def test_a_stale_spinner_in_the_middle_does_not_make_the_terminal_busy(self):
        # the footer at the bottom says "? for shortcuts"; an old spinner frame was the LAST thing written to the stream
        stream = '\x1b[28;1HResult\x1b[29;1H? for shortcuts\x1b[5;1H⣾ Generating...'
        self.assertEqual(bottom_lines(buf(stream), 2, 100, 30), ['Result', '? for shortcuts'])
        self.assertFalse(is_terminal_spinning(buf(stream)))

    def test_a_busy_footer_on_the_bottom_of_the_screen_is_busy(self):
        stream = '\x1b[29;1HReading file...\x1b[30;1Hesc to cancel   Gemini 4 Argon · medium'
        self.assertTrue(is_terminal_spinning(buf(stream)))

    def test_plain_streams_keep_the_old_rule(self):
        self.assertTrue(is_terminal_spinning(buf('some text\n⣾ Generating...')))
        self.assertFalse(is_terminal_spinning(buf('esc to cancel\nResult line\n> ')))


class ErrorDetection(unittest.TestCase):
    def test_network_quota_and_agent_errors(self):
        self.assertEqual(terminal_error(buf('doing...\nThere was a network issue connecting to the server\n> '))[0], 'lỗi mạng')
        self.assertEqual(terminal_error(buf('Individual quota reached. Resets in 48h\n'))[0], 'hết quota')
        self.assertEqual(terminal_error(buf('agent executor error: boom\n'))[0], 'lỗi agent')

    def test_normal_output_is_not_an_error(self):
        self.assertIsNone(terminal_error(buf('All 12 tests passed\n> \n? for shortcuts')))
        self.assertIsNone(terminal_error(bytearray()))

    def test_excerpt_is_short_and_single_line(self):
        label, excerpt = terminal_error(buf('x\nNetwork issue: ' + 'a' * 400 + '\nnext'))
        self.assertEqual(label, 'lỗi mạng')
        self.assertLessEqual(len(excerpt), 120)
        self.assertNotIn('\n', excerpt)


class FinalLine(unittest.TestCase):
    """The last line PROMPT-CHUNG.md asks for must clear an earlier "still working" line, in all three forms."""

    def kind(self, last):
        from agent_orchestrator.terminals import terminal_busy_kind
        return terminal_busy_kind(buf('Working...\nEditing files...\n' + last))

    def test_each_final_line_form_clears_the_working_marker(self):
        self.assertEqual(self.kind('Đang làm...'), 'soft', 'sanity: without a final line it still counts as working')
        for last in ('HOÀN TẤT: 3ce90872, báo cáo C:/x/BAOCAO-W2.md',
                     'HOÀN TẤT (CHƯA COMMIT): git bị chặn, lệnh commit nằm trong báo cáo C:/x/BAOCAO-W2.md',
                     'ĐANG CHỜ AGENT 0: lỗi mạng, cần chạy lại'):
            self.assertIsNone(self.kind(last), last)

    def test_a_free_text_status_is_not_a_final_line(self):
        self.assertEqual(self.kind('Phần 1/3 xong, chờ build'), 'soft')


class EchoSession(FakeSession):
    """Agent 0 stand-in that can echo what is typed into it, like a real input box does."""

    def __init__(self, echo=True):
        super().__init__()
        self.echo = echo
        self.buffer = bytearray()
        self.last_input = 0

    def write(self, data, system=False):
        super().write(data, system)
        if self.echo and data != '\r':
            self.buffer += data.encode('utf-8')


class Signals(WorkflowBase):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db, idle_debounce=0.1)
        self.agent0 = EchoSession()
        self.t.sessions['agent0'] = self.agent0
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()  # attach Agent 0

    def agy(self, n):
        s = MockInteractiveSession(f'agy-{n}', provider='agy', agent=n, cwd=self.root)
        self.t.sessions[s.id] = s
        s.write('Làm việc theo file prompt\n')
        return s

    def poll(self, wait=0.15):
        time.sleep(wait)
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()

    def lines(self):
        return [w[0] for w in self.agent0.written if w[0] != '\r']

    # ---- wording -----------------------------------------------------------------------------------------
    def test_quiet_line_does_not_claim_the_work_is_done(self):
        a = self.agy(1)
        a.emit_output('xong phần A\n')
        self.poll()
        (line,) = self.lines()
        self.assertIn('agy-1 yên lặng (chưa xác nhận đã xong)', line)
        self.assertIn('thông báo tự động của dashboard, không phải yêu cầu của người dùng', line)
        self.assertNotIn('đã xong.', line)

    def test_an_error_is_reported_as_an_error_not_as_quiet(self):
        a = self.agy(2)
        a.emit_output('There was a network issue connecting to the server\n')
        self.poll()
        (line,) = self.lines()
        self.assertIn('agy-2 có lỗi (lỗi mạng)', line)
        self.assertNotIn('yên lặng', line)

    def test_several_quiet_terminals_share_one_line(self):
        for n in (1, 3):
            self.agy(n).emit_output('xong\n')
        self.agy(4).emit_output('Individual quota reached\n')
        self.poll()
        (line,) = self.lines()
        self.assertIn('agy-1, agy-3 yên lặng', line)
        self.assertIn('agy-4 có lỗi (hết quota)', line)
        self.poll()
        self.assertEqual(len(self.lines()), 1, 'nothing is repeated')

    # ---- re-arm ------------------------------------------------------------------------------------------
    def test_bulk_output_after_an_early_notice_is_reported_again(self):
        a = self.agy(1)
        a.emit_output('xong bước 1\n')
        self.poll()
        self.assertEqual(len(self.lines()), 1)
        a.emit_output(('kết quả build dòng dài ' * 30 + '\n') * 8)  # > 4000 bytes, no spinner, no busy marker
        self.poll()
        self.assertFalse(a.idle, 'real work resumed')
        self.poll()
        self.assertEqual(len(self.lines()), 2, 'its real finish is reported')

    def test_output_after_a_resize_does_not_rearm(self):
        a = self.agy(1)
        a.emit_output('xong\n')
        self.poll()
        a.emit_output('x' * 6000 + '\n')
        a.resized_at = time.time() + 5   # the redraw came from a resize
        self.poll()
        self.assertTrue(a.idle)
        self.assertEqual(len(self.lines()), 1)

    # ---- the window button -------------------------------------------------------------------------------
    def test_button_types_one_line_into_agent0(self):
        a = self.agy(5)
        result = self.t.notify_done('agy-5')
        self.assertTrue(result['ok'])
        (line,) = self.lines()
        self.assertTrue(line.startswith('[AO] Chủ dự án xác nhận agy-5 đã hoàn thành'))
        self.assertIn('không phải thông báo tự động', line)
        self.assertEqual(self.agent0.written[-1], ('\r', True))
        audit = [json.loads(x) for x in (self.cfg.state / 'terminal-audit.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(audit[-1]['source'], 'button')
        self.assertFalse(a.idle_notified and not a.idle, 'a working agent is not marked as already notified')

    def test_button_stops_the_automatic_line_for_the_same_finish(self):
        a = self.agy(5)
        a.emit_output('xong\n')
        time.sleep(0.15)
        self.t.update_interactive_idle(a)
        self.assertTrue(a.idle and not a.idle_notified)
        self.t.notify_done('agy-5')
        self.poll()
        self.assertEqual(len(self.lines()), 1, 'only the button line, no second "yên lặng" line')

    def test_button_refuses_when_it_cannot_deliver(self):
        self.agy(5)
        self.agent0.last_input = time.time()
        with self.assertRaises(OrchError):
            self.t.notify_done('agy-5')          # someone is typing in Agent 0
        self.agent0.last_input = 0
        with self.assertRaises(OrchError):
            self.t.notify_done('agent0')         # Agent 0 itself
        with self.assertRaises(OrchError):
            self.t.notify_done('agy-99')         # unknown window
        w = self.agy(6)
        w.kind = 'worker'
        with self.assertRaises(OrchError):
            self.t.notify_done('agy-6')          # read-only queue window
        del self.t.sessions['agent0']
        with self.assertRaises(OrchError):
            self.t.notify_done('agy-5')          # Agent 0 not open
        self.assertEqual(self.agent0.written, [])

    # ---- sent / seen bookkeeping --------------------------------------------------------------------------
    def test_a_notice_that_shows_up_in_agent0_is_confirmed(self):
        self.agy(5)
        self.t.notify_done('agy-5')
        self.assertEqual(self.t.check_acks(time.time() + 1), 0, 'too early to judge')
        self.assertEqual(self.t.check_acks(time.time() + 10), 1)
        self.assertEqual(self.t.notices_unconfirmed, 0)
        audit = [json.loads(x) for x in (self.cfg.state / 'terminal-audit.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual((audit[-1]['source'], audit[-1]['seen']), ('ack', True))

    def test_a_notice_that_never_shows_up_is_counted_not_silent(self):
        self.agent0.echo = False
        self.agy(5)
        self.t.notify_done('agy-5')
        self.t.check_acks(time.time() + 10)
        self.assertEqual(self.t.notices_unconfirmed, 1)
        audit = [json.loads(x) for x in (self.cfg.state / 'terminal-audit.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertFalse(audit[-1]['seen'])

    # ---- a new Agent 0 -----------------------------------------------------------------------------------
    def test_a_terminal_that_did_work_is_reported_to_a_restarted_agent0(self):
        a = self.agy(1)
        a.emit_output('xong\n')
        self.poll()
        self.assertEqual(len(self.lines()), 1)
        fresh = EchoSession()
        self.t.sessions['agent0'] = fresh        # Agent 0 restarted: a new session object
        self.t.notify_agent0()                   # attaches the new one
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()
        self.assertIn('agy-1 yên lặng', fresh.written[0][0])


if __name__ == '__main__':
    unittest.main()
