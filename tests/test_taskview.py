"""Agent watch windows, terminal id resolution and Agent 0 terminal input: normal paths and failure cases."""
from __future__ import annotations

import http.client
import json
import os
import threading
import time
import unittest

from agent_orchestrator import terminals
from agent_orchestrator.config import OrchError
from agent_orchestrator.mcp import Server
from agent_orchestrator.terminals import Terminals, clean
from agent_orchestrator.web import WebServer
from tests.test_orchestrator import Fixture


class Stub:
    """Stands in for an interactive ConPTY session."""

    def __init__(self, sid, kind='agent', alive=True):
        self.id, self.kind, self.title, self.cwd = sid, kind, sid, '.'
        self.provider, self.task_id, self.closed = sid.split('-')[0], None, False
        self.agent = int(sid.split('-')[1]) if '-' in sid and sid.split('-')[1].isdigit() else None
        self.exit_code = None if alive else 0
        self.written, self.created = [], time.time()
        self.cond = threading.Condition()
        self.buffer = bytearray()

    @property
    def alive(self):
        return self.exit_code is None

    def write(self, data):
        self.written.append(data)

    def close(self):
        self.closed = True


def wait_for(predicate, seconds=15):
    end = time.time() + seconds
    while time.time() < end:
        if predicate():
            return True
        time.sleep(.05)
    return predicate()


def raw_of(view):
    return view.read(0, 0)[1].decode('utf-8', 'replace')


def text_of(view):
    return terminals.ANSI.sub('', raw_of(view)).replace('\r\n', '\n')


class IdResolution(Fixture):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db)
        self.t.sessions.update({'codex-1': Stub('codex-1'), 'claude-2': Stub('claude-2')})

    def test_all_spellings_reach_the_same_terminal(self):
        for ref in ('codex-1', 'codex#1', 'Codex #1', 'codex 1', 'agent 1', 'Agent 1', 'agent-1', '  CODEX#1 ', 'codex_1', '1', '#1'):
            with self.subTest(ref=ref):
                self.assertEqual(self.t.resolve_id(ref), 'codex-1')
        self.assertEqual(self.t.resolve_id('Claude #2'), 'claude-2')
        self.assertEqual(self.t.resolve_id('Agent 2'), 'claude-2')
        self.assertEqual(self.t.resolve_id('2'), 'claude-2')

    def test_unknown_reference_lists_valid_ids(self):
        for ref in ('codex#9', 'nope', '', 'agy-1', 'task zzzz', '9'):
            with self.subTest(ref=ref), self.assertRaises(OrchError) as raised:
                self.t.resolve_id(ref)
            self.assertIn('codex-1', str(raised.exception))

    def test_unknown_id_never_closes_everything(self):
        self.t.close('does-not-exist')
        self.assertEqual(set(self.t.sessions), {'codex-1', 'claude-2'})
        self.t.close('codex#1')
        self.assertEqual(set(self.t.sessions), {'claude-2'})

    def test_task_prefix_must_be_unique(self):
        for sid, tid in (('codex-8', 'aaaa1111' + '0' * 16), ('codex-9', 'aaaa2222' + '0' * 16)):
            view = Stub(sid, 'worker')
            view.task_id = tid
            self.t.sessions[sid] = view
        self.assertEqual(self.t.resolve_id('task aaaa1111'), 'codex-8')
        with self.assertRaises(OrchError):
            self.t.resolve_id('task aaaa')


class SendGuards(Fixture):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db)
        self.codex = self.t.sessions['codex-1'] = Stub('codex-1')
        self.t.sessions['agent0'] = Stub('agent0', 'agent0')
        self.t.sessions['claude-5'] = Stub('claude-5', 'worker')
        for _ in range(5):  # numbers 1..5 belong to the stubs, so a real queue agent gets 6
            self.e.db.agent_new('codex', 'terminal')

    def test_sends_text_then_enter_and_writes_audit(self):
        result = self.t.send('Codex #1', 'fix the bug in src/app.py')
        self.assertEqual(self.codex.written, ['fix the bug in src/app.py', '\r'])
        self.assertEqual(result['terminal'], 'codex-1')
        audit = [json.loads(x) for x in (self.cfg.state / 'terminal-audit.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual((audit[0]['terminal'], audit[0]['chars']), ('codex-1', 25))
        self.assertIn('sha256', audit[0])

    def test_escape_sequences_and_newlines_are_neutralised(self):
        self.t.send('codex-1', 'line one\nline two\r\n\x1b[2J\x1b]0;pwn\x07 \u009b31m done\t!')
        sent = self.codex.written[0]
        for forbidden in ('\x1b', '\n', '\r', '\x07', '\u009b'):
            self.assertNotIn(forbidden, sent)
        self.assertTrue(sent.startswith('line one line two'))

    def test_refused_targets(self):
        for ref in ('agent0', 'claude-5'):
            with self.subTest(ref=ref), self.assertRaises(OrchError):
                self.t.send(ref, 'hello')
        self.assertEqual(self.t.sessions['agent0'].written, [])
        self.assertEqual(self.t.sessions['claude-5'].written, [])

    def test_queue_agents_are_pointed_to_enqueue_task(self):
        with self.assertRaisesRegex(OrchError, r'enqueue_task\(agent=5'):
            self.t.send('claude 5', 'hello')  # a worker window exists
        n = self.e.db.agent_new('codex', 'queue')  # no window open for this one
        with self.assertRaisesRegex(OrchError, rf'codex {n} là worker hàng đợi.*enqueue_task\(agent={n}'):
            self.t.send(f'codex {n}', 'hello')
        with self.assertRaisesRegex(OrchError, 'Unknown terminal'):
            self.t.send('codex 99', 'hello')

    def test_ended_terminal_is_refused(self):
        self.codex.exit_code = 0
        with self.assertRaisesRegex(OrchError, 'ended'):
            self.t.send('codex-1', 'hello')
        self.codex.exit_code, self.codex.closed = None, True
        with self.assertRaisesRegex(OrchError, 'ended'):
            self.t.send('codex-1', 'hello')

    def test_bad_text(self):
        for bad in ('', '   ', '\x1b\x07\x00', None, 42, ['x']):
            with self.subTest(bad=bad), self.assertRaises(OrchError):
                self.t.send('codex-1', bad)
        with self.assertRaisesRegex(OrchError, '4000'):
            self.t.send('codex-1', 'x' * (terminals.SEND_LIMIT + 1))
        self.assertEqual(self.codex.written, [])

    @unittest.skipUnless(os.name == 'nt', 'ConPTY is Windows only')
    def test_text_sent_to_a_real_conpty_is_typed_and_submitted(self):
        session = terminals.Session('codex-1', 'agent', 'Codex 1', [os.environ['COMSPEC']], os.getcwd(), dict(os.environ), 100, 30)
        session.provider, session.task_id, session.agent = 'codex', None, 1
        self.t.sessions['codex-1'] = session
        self.addCleanup(session.close)
        self.t.send('Codex #1', 'echo marker-' + '4242')
        seen, offset = '', 0
        end = time.time() + 15
        while seen.count('marker-4242') < 2 and time.time() < end:  # once as typed echo, once as the command's output
            _, data, offset, _ = session.read(offset, 1)
            seen += data.decode('utf-8', 'replace')
        self.assertGreaterEqual(seen.count('marker-4242'), 2, seen[-300:])

    def test_rate_limit_per_terminal(self):
        self.t.send('codex-1', 'first')
        with self.assertRaisesRegex(OrchError, 'quá nhanh'):
            self.t.send('codex-1', 'second')
        self.t.sessions['claude-2'] = other = Stub('claude-2')
        self.t.send('claude-2', 'independent')  # another terminal is not throttled
        self.assertEqual(other.written, ['independent', '\r'])
        self.t.last_send['codex-1'] -= terminals.SEND_INTERVAL + 1
        self.t.send('codex-1', 'later')


class AgentWatch(Fixture):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db)
        self.addCleanup(self.t.close)

    def view(self, agent):
        return self.t.sessions[self.t.agent_views[agent]]

    def event_rows(self):
        with self.e.db.connect() as db:
            return [dict(r) for r in db.execute('SELECT task_id,kind FROM events')]

    def started(self, provider='codex', **kw):
        """Enqueue, open the window, return (agent number, task id, view)."""
        task = self.e.enqueue(provider, 'Set the answer to 42', ['src'], ['unit'], **kw)
        self.t.sync_tasks()
        return task['agent'], task['id'], self.view(task['agent'])

    def test_agent0_style_enqueue_opens_exactly_one_window_named_after_the_agent(self):
        """Agent 0 says 'create a new codex agent to fix this': enqueue_task through MCP must show a window."""
        task = Server(self.e).call('enqueue_task', {'provider': 'codex', 'prompt': 'Fix src/answer.txt',
                                                    'allow_paths': ['src'], 'tests': ['unit']})
        self.assertEqual(self.t.sync_tasks(), ['codex-1'])
        self.assertEqual(self.t.sync_tasks(), [])  # polling again must not duplicate
        info = self.t.describe(self.view(1))
        self.assertEqual((info['kind'], info['provider'], info['agent'], info['readonly'], info['title']),
                         ('worker', 'codex', 1, True, 'Agent 1 · Codex'))
        self.assertTrue(wait_for(lambda: 'Mục tiêu: Fix src/answer.txt' in text_of(self.view(1))))
        self.assertEqual(self.t.resolve_id('codex 1'), 'codex-1')
        self.assertEqual(task['agent'], 1)

    def test_window_stays_open_and_idle_after_the_task_finishes(self):
        agent, tid, view = self.started()
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.assertTrue(wait_for(lambda: view.idle and 'Kết thúc: chờ review' in text_of(view)))
        body = text_of(view)
        self.assertTrue(view.alive, 'an agent window does not end with its task')
        for expected in ('Trong hàng đợi', 'Worker bắt đầu', 'Chạy test: unit', 'Test unit: exit 0', 'sẵn sàng nhận việc tiếp', 'Nhớ ngữ cảnh: bật'):
            self.assertIn(expected, body)
        self.assertEqual(self.t.sync_tasks(), [])

    def test_next_round_prints_into_the_same_window(self):
        agent, tid, view = self.started()
        self.e.work_once('codex')
        self.assertTrue(wait_for(lambda: view.idle))
        self.e.enqueue(None, 'Also add FILE:second', ['src'], ['unit'], agent=agent)
        self.assertTrue(wait_for(lambda: not view.idle))
        self.e.work_once('codex')
        self.assertTrue(wait_for(lambda: view.idle and text_of(view).count('Kết thúc: chờ review') == 2))
        body = text_of(view)
        for expected in ('vòng 2', 'Làm tiếp trong cùng worktree · nhớ ngữ cảnh', 'Vòng 2 xếp hàng (làm tiếp)', 'làm tiếp phiên cũ của model'):
            self.assertIn(expected, body)
        self.assertEqual(len(self.t.agent_views), 1)

    def test_resume_failure_is_visible(self):
        agent, tid, view = self.started()
        self.e.work_once('codex')
        self.e.enqueue(None, 'FAIL_RESUME and FILE:second', ['src'], ['unit'], agent=agent)
        self.e.work_once('codex')
        self.assertTrue(wait_for(lambda: 'Không làm tiếp được phiên cũ' in text_of(view)))
        self.assertIn('chạy lại bằng phiên mới kèm tóm tắt', text_of(view))

    def test_cancelled_task_is_reported_and_the_window_stays(self):
        agent, tid, view = self.started('claude')
        self.assertTrue(wait_for(lambda: 'Mục tiêu:' in text_of(view)))
        self.e.db.cancel(tid)
        self.assertTrue(wait_for(lambda: view.idle and 'Kết thúc: đã hủy' in text_of(view)))
        self.assertTrue(view.alive)

    def test_failed_task_shows_the_reason(self):
        agent, tid, view = self.started()
        self.e.db.claim('codex')
        self.e.db.finish(tid, 'failed', {'error': 'Worker produced no changes'})
        self.assertTrue(wait_for(lambda: view.idle))
        self.assertIn('Worker produced no changes', text_of(view))

    def test_closed_window_stays_closed_for_that_round_and_returns_with_the_next(self):
        agent, tid, view = self.started()
        self.t.close('codex 1')
        self.assertNotIn('codex-1', self.t.sessions)
        self.assertEqual(self.t.sync_tasks(), [])
        self.assertEqual(self.t.sync_tasks(), [])
        self.assertIn(f'{tid}:1', self.t.dismissed)
        self.e.work_once('codex')
        self.e.enqueue(None, 'FILE:second', ['src'], ['unit'], agent=agent)
        self.assertEqual(self.t.sync_tasks(), ['codex-1'], 'a new round opens the window again')

    def test_window_is_read_only(self):
        agent, tid, view = self.started()
        with self.assertRaisesRegex(OrchError, rf'chỉ đọc.*enqueue_task\(agent={agent}\)'):
            view.write('rm -rf /')
        view.resize(80, 24)  # harmless no-op

    def test_opening_on_finished_work_does_not_replay_history(self):
        task = self.e.enqueue('codex', 'Set the answer', ['src'], ['unit'])
        self.e.work_once('codex')
        self.e.enqueue(None, 'FILE:second', ['src'], ['unit'], agent=task['agent'])  # active again
        self.e.work_once('codex')  # ... and finished before any window existed
        view = AgentWatch.attach(self, task['agent'])
        self.assertTrue(wait_for(lambda: 'sẵn sàng' in text_of(view)))
        self.assertNotIn('Chạy test', text_of(view))
        self.assertTrue(view.idle)
        self.e.enqueue(None, 'FILE:third', ['src'], ['unit'], agent=task['agent'])
        self.assertTrue(wait_for(lambda: 'vòng 3' in text_of(view)))

    def attach(self, agent):
        row = self.e.db.agent_get(agent)
        view = terminals.AgentView(f"{row['provider']}-{agent}", row, self.e.db, self.cfg.state)
        self.addCleanup(view.close)
        return view

    def test_log_text_cannot_inject_terminal_escape_sequences(self):
        agent, tid, view = self.started()
        folder = self.cfg.state / 'runs' / tid / 'worker'
        folder.mkdir(parents=True)
        (folder / 'stdout.log').write_bytes(
            b'before \x1b[2J\x1b]0;PWNED-TITLE\x07 \xc2\x9b31m after\nsecond \xff\xfe broken utf8\n')
        self.assertTrue(wait_for(lambda: 'broken utf8' in raw_of(view)))
        raw = raw_of(view)
        for forbidden in ('\x1b[2J', '\x1b]0;', '\x07', '\u009b'):
            self.assertNotIn(forbidden, raw)

    def test_partial_line_waits_for_newline_and_is_flushed_at_the_end(self):
        agent, tid, view = self.started()
        folder = self.cfg.state / 'runs' / tid / 'test-unit'
        folder.mkdir(parents=True)
        log = folder / 'stdout.log'
        log.write_bytes(b'half a li')
        time.sleep(1.2)
        self.assertNotIn('half a li', text_of(view))
        with log.open('ab') as f:
            f.write(b'ne\nunfinished tail')
        self.assertTrue(wait_for(lambda: 'half a line' in text_of(view)))
        self.assertNotIn('unfinished tail', text_of(view))
        self.e.db.claim('codex')
        self.e.db.finish(tid, 'failed', {'error': 'x'})
        self.assertTrue(wait_for(lambda: 'unfinished tail' in text_of(view)))

    def test_codex_json_lines_are_summarised_not_dumped(self):
        agent, tid, view = self.started()
        folder = self.cfg.state / 'runs' / tid / 'worker'
        folder.mkdir(parents=True)
        lines = [{'type': 'thread.started'},
                 {'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'pytest -q'}},
                 {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Đã sửa xong'}},
                 {'type': 'turn.completed', 'usage': {'input_tokens': 1}}]
        (folder / 'stdout.log').write_text('\n'.join(json.dumps(x) for x in lines) + '\n', encoding='utf-8')
        self.assertTrue(wait_for(lambda: 'Lượt xử lý hoàn tất' in text_of(view)))
        body = text_of(view)
        self.assertIn('▶ pytest -q', body)
        self.assertIn('[agent_message] Đã sửa xong', body)
        self.assertNotIn('thread.started', body)
        self.assertNotIn('"item"', body)

    def test_claude_single_json_result_is_shown_as_text(self):
        agent, tid, view = self.started('claude')
        folder = self.cfg.state / 'runs' / tid / 'worker'
        folder.mkdir(parents=True)
        (folder / 'stdout.log').write_text(json.dumps([{'type': 'system'}, {'type': 'result', 'result': 'Sửa xong file'}]) + '\n', encoding='utf-8')
        self.assertTrue(wait_for(lambda: 'Kết quả worker: Sửa xong file' in text_of(view)))

    def test_runner_hint_depends_on_runner_state(self):
        self.e.enqueue('codex', 'x', ['src'], ['unit'])
        view = self.t.sessions[self.t.sync_tasks(lambda: {})[0]]
        self.assertIn('⚠', view.runner_hint('codex'))
        view.runner_state = lambda: {'codex': {'status': 'busy'}}
        self.assertNotIn('⚠', view.runner_hint('codex'))
        view.runner_state = lambda: 1 / 0  # a broken status source must not break the window
        self.assertIn('⚠', view.runner_hint('codex'))

    def test_window_cap_evicts_idle_windows_and_reports_when_full(self):
        old = terminals.MAX_SESSIONS
        terminals.MAX_SESSIONS = 2
        self.addCleanup(setattr, terminals, 'MAX_SESSIONS', old)
        first, second, third = (self.e.enqueue('codex', 'x', ['src'], ['unit']) for _ in range(3))
        self.assertEqual(len(self.t.sync_tasks()), 2)
        self.assertEqual(self.t.sync_tasks(), [])
        self.assertIn(third['id'], {e['task_id'] for e in self.event_rows() if e['kind'] == 'terminal_skipped'})
        self.e.db.cancel(first['id'])  # its window goes idle, which frees a slot for the waiting agent
        self.assertTrue(wait_for(lambda: self.view(first['agent']).idle))
        self.assertEqual(self.t.sync_tasks(), [f"codex-{third['agent']}"])
        self.assertNotIn(f"codex-{first['agent']}", self.t.sessions)

    def test_vanished_task_or_agent_does_not_hang_the_window(self):
        agent, tid, view = self.started()
        with self.e.db.connect() as db:
            db.execute('DELETE FROM tasks WHERE id=?', (tid,))
        time.sleep(1)
        self.assertTrue(view.alive)  # the agent still exists; it just has nothing to show
        with self.e.db.connect() as db:
            db.execute('DELETE FROM agents WHERE n=?', (agent,))
        self.assertTrue(wait_for(lambda: not view.alive))
        self.assertIn('không còn', text_of(view))

    def test_background_monitor_opens_windows_by_itself(self):
        self.t.start_monitor(interval=.1)
        task = self.e.enqueue('codex', 'x', ['src'], ['unit'])
        self.assertTrue(wait_for(lambda: task['agent'] in self.t.agent_views))
        self.t.close()  # stops the monitor too
        self.assertTrue(wait_for(lambda: not self.t.monitor.is_alive()))

    def test_enqueue_error_lists_available_profiles(self):
        with self.assertRaisesRegex(OrchError, 'Available profiles: unit'):
            self.e.enqueue('codex', 'x', ['src'], ['nope'])

    def test_clean_strips_every_control_character_but_keeps_text(self):
        self.assertEqual(clean('a\x1b[31mb\x07c\x00d\u009be\r\nf\rg\th'), 'a[31mbcde\nf\ng\th')


class BridgeRoutes(Fixture):
    def setUp(self):
        super().setUp()
        self.e.db.agent_new('codex', 'terminal')  # the stub below is "codex 1", so queue agents start at 2
        self.server = WebServer(self.e, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.key = {'X-Bridge-Key': self.server.bridge_key, 'Authorization': ''}
        self.codex = self.server.terminals.sessions['codex-1'] = Stub('codex-1')

    def stop_server(self):
        self.server.terminals.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        self.addCleanup(conn.close)
        defaults = {'Authorization': 'Bearer ' + self.server.token}
        if body is not None:
            defaults.update({'Origin': self.server.origin, 'Content-Type': 'application/json'})
        defaults.update(headers or {})
        conn.request('GET' if body is None else 'POST', path, None if body is None else json.dumps(body).encode(), defaults)
        response = conn.getresponse()
        data = response.read()
        return response.status, json.loads(data) if data.startswith(b'{') or data.startswith(b'[') else data, response

    def post(self, path, body, headers=None):
        return self.request(path, body, self.key if headers is None else headers)

    def test_input_requires_the_bridge_key(self):
        self.assertEqual(self.post('/api/bridge/terminals/codex-1/input', {'text': 'hi'}, {'Authorization': ''})[0], 401)
        self.assertEqual(self.post('/api/bridge/terminals/codex-1/input', {'text': 'hi'}, {'X-Bridge-Key': 'wrong', 'Authorization': ''})[0], 401)
        self.assertEqual(self.codex.written, [])

    def test_dashboard_token_alone_cannot_use_the_bridge(self):
        self.assertEqual(self.post('/api/bridge/terminals/codex-1/input', {'text': 'hi'}, {})[0], 401)
        self.assertEqual(self.codex.written, [])

    def test_bridge_stays_read_only_except_input(self):
        self.assertEqual(self.post('/api/bridge/terminals', {'x': 1})[0], 401)
        self.assertEqual(self.post('/api/bridge/terminals/codex-1', {'x': 1})[0], 401)
        # Agent 0 may only close a terminal it opened itself; codex-1 was not (its window must stay)
        self.assertEqual(self.post('/api/bridge/terminals/codex-1/close', {})[0], 400)
        self.assertIn('codex-1', self.server.terminals.sessions)

    def test_open_terminal_requires_key_and_only_a_known_provider(self):
        url = '/api/bridge/terminals/open'
        self.assertEqual(self.post(url, {'provider': 'codex'}, {})[0], 401)
        self.assertEqual(self.post(url, {'provider': 'codex'}, {'X-Bridge-Key': 'wrong', 'Authorization': ''})[0], 401)
        self.assertEqual(self.post(url, {})[0], 400)
        self.assertEqual(self.post(url, {'provider': 'bash'})[0], 400)
        self.assertEqual(self.post(url, {'provider': 'codex', 'task_id': 'x' * 24})[0], 400)  # no worktrees via the bridge
        self.assertEqual(self.post(url, {'provider': 'codex', 'kind': 'agent0'})[0], 400)

    def test_open_terminal_opens_audits_and_rate_limits(self):
        opened = []
        self.server.terminals.open = lambda kind, provider=None, **kw: opened.append((kind, provider, kw)) or {'id': 'agy-3', 'agent': 3}
        status, data, _ = self.post('/api/bridge/terminals/open', {'provider': 'agy'})
        self.assertEqual((status, data['id']), (200, 'agy-3'))
        self.assertEqual(opened, [('agent', 'agy', {})])
        audit = (self.cfg.state / 'terminal-audit.jsonl').read_text(encoding='utf-8')
        self.assertIn('"action": "open"', audit)
        self.assertEqual(self.post('/api/bridge/terminals/open', {'provider': 'agy'})[0], 400)  # too fast
        self.assertEqual(len(opened), 1)

    def test_input_validation(self):
        url = '/api/bridge/terminals/codex-1/input'
        self.assertEqual(self.post(url, {})[0], 400)
        self.assertEqual(self.post(url, {'text': 'hi', 'cols': 5})[0], 400)
        self.assertEqual(self.post(url, {'text': 123})[0], 400)
        self.assertEqual(self.post(url, {'text': ''})[0], 400)
        self.assertEqual(self.codex.written, [])

    def test_percent_encoded_hash_id_and_bare_number_are_delivered(self):
        status, data, _ = self.post('/api/bridge/terminals/codex%231/input', {'text': 'fix this'})
        self.assertEqual((status, data['terminal']), (200, 'codex-1'))
        self.assertEqual(self.codex.written, ['fix this', '\r'])
        self.server.terminals.last_send.clear()
        self.assertEqual(self.post('/api/bridge/terminals/1/input', {'text': 'again'})[0], 200)

    def test_unknown_terminal_error_names_valid_ids(self):
        status, data, _ = self.post('/api/bridge/terminals/codex%239/input', {'text': 'hi'})
        self.assertEqual(status, 400)
        self.assertIn('codex-1', data['error'])

    def test_agent_window_listing_is_flagged_read_only_and_refuses_input(self):
        task = self.e.enqueue('codex', 'x', ['src'], ['unit'])
        sid = f"codex-{task['agent']}"
        self.assertEqual(self.server.terminals.sync_tasks(), [sid])
        rows = {r['id']: r for r in self.request('/api/terminals')[1]}
        self.assertTrue(rows[sid]['readonly'])
        self.assertEqual(rows[sid]['agent'], task['agent'])
        self.assertFalse(rows['codex-1']['readonly'])
        status, data, _ = self.post(f'/api/bridge/terminals/{sid}/input', {'text': 'hi'})
        self.assertEqual(status, 400)
        self.assertIn('enqueue_task', data['error'])

    def test_browser_stream_delivers_the_agent_window_and_rejects_typing(self):
        import base64
        task = self.e.enqueue('codex', 'x', ['src'], ['unit'])
        sid = self.server.terminals.sync_tasks()[0]
        status, data, _ = self.request(f'/api/terminals/stream?c={sid}:0&wait=5')
        self.assertEqual(status, 200)
        self.assertTrue(data[sid]['alive'])
        self.assertIn('task ' + task['id'][:8], base64.b64decode(data[sid]['data']).decode('utf-8'))
        status, data, _ = self.request(f'/api/terminals/{sid}/input', {'data': 'rm something\r'})
        self.assertEqual(status, 400)
        self.assertIn('chỉ đọc', data['error'])

    def test_closing_an_agent_window_through_the_dashboard_api(self):
        task = self.e.enqueue('codex', 'x', ['src'], ['unit'])
        sid = self.server.terminals.sync_tasks()[0]
        self.assertEqual(self.request(f'/api/terminals/{sid}/close', {})[0], 200)
        self.assertNotIn(sid, {r['id'] for r in self.request('/api/terminals')[1]})
        self.assertEqual(self.server.terminals.sync_tasks(), [])
        self.assertIn(f"{task['id']}:1", self.server.terminals.dismissed)

    def test_mcp_tool_uses_the_bridge_and_reports_dashboard_reasons(self):
        (self.cfg.state / 'terminal-bridge.json').write_text(
            json.dumps({'port': self.server.server_port, 'key': self.server.bridge_key}), encoding='utf-8')
        s = Server(self.e)
        self.assertEqual(s.call('send_to_terminal', {'terminal_id': 'Codex #1', 'text': 'fix src/app.py'})['terminal'], 'codex-1')
        self.assertEqual(self.codex.written, ['fix src/app.py', '\r'])
        self.codex.buffer = bytearray("line 1\n⣷ Generating...\nDone!\n".encode('utf-8'))
        read_clean = s.call('read_terminal', {'terminal_id': 'codex-1', 'clean': True})
        self.assertNotIn("Generating", read_clean['text'])
        self.assertIn("Done!", read_clean['text'])
        with self.assertRaisesRegex(OrchError, 'Unknown terminal'):
            s.call('read_terminal', {'terminal_id': 'codex#7'})
        with self.assertRaisesRegex(OrchError, 'quá nhanh'):
            s.call('send_to_terminal', {'terminal_id': 'codex-1', 'text': 'again'})

    def test_mcp_tool_without_dashboard_says_so(self):
        bridge = self.cfg.state / 'terminal-bridge.json'
        if bridge.exists():
            bridge.unlink()
        with self.assertRaisesRegex(OrchError, 'unavailable'):
            Server(self.e).call('send_to_terminal', {'terminal_id': 'codex-1', 'text': 'hi'})
        bridge.write_text(json.dumps({'port': 1, 'key': 'x'}), encoding='utf-8')  # stale file left by a crashed dashboard
        with self.assertRaisesRegex(OrchError, 'unavailable'):
            Server(self.e).call('send_to_terminal', {'terminal_id': 'codex-1', 'text': 'hi'})


if __name__ == '__main__':
    unittest.main()
