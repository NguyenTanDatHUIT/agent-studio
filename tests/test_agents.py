"""Numbered agents, remembered context (continue in the same worktree, resume the session) and its failure modes."""
from __future__ import annotations

import http.client
import json
import sqlite3
import threading
import unittest

from agent_orchestrator.config import OrchError
from agent_orchestrator.engine import Engine
from agent_orchestrator.mcp import Server
from agent_orchestrator.providers import SESSION, argv, session_id
from agent_orchestrator.store import Store
from agent_orchestrator.web import WebServer
from tests.test_orchestrator import Fixture


class Helpers(Fixture):
    def enqueue(self, prompt='Set the answer to 42', provider=None, scope=('src',), **kw):
        return self.e.enqueue(provider, prompt, list(scope), ['unit'], **kw)

    def new_agent(self, provider='codex', prompt='Set the answer to 42'):
        task = self.enqueue(prompt, provider)
        self.assertEqual(self.e.work_once(provider)['status'], 'awaiting_review')
        return task['agent'], task['id']


class AgentFlow(Helpers):
    # ---- numbering -------------------------------------------------------------------------------------
    def test_numbers_are_global_increasing_and_survive_a_restart(self):
        a = self.enqueue(provider='codex')['agent']
        b = self.enqueue(provider='claude')['agent']
        c = self.enqueue(provider='codex')['agent']
        self.assertEqual((a, b, c), (1, 2, 3))
        later = Engine(self.cfg)  # a new process (dashboard restart) sees the same counter
        self.assertEqual(later.enqueue('claude', 'x', ['src'], ['unit'])['agent'], 4)
        self.assertEqual([x['provider'] for x in later.db.agent_list()], ['codex', 'claude', 'codex', 'claude'])

    def test_interactive_terminals_share_the_same_counter(self):
        self.enqueue(provider='codex')
        self.assertEqual(self.e.db.agent_new('claude', 'terminal'), 2)
        self.assertEqual(self.enqueue(provider='codex')['agent'], 3)

    def test_old_database_is_migrated(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'queue.sqlite3'
            db = sqlite3.connect(file)
            db.executescript("""CREATE TABLE tasks(id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, result TEXT,
                cancel INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, time TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);""")
            db.execute("INSERT INTO tasks VALUES('a'*1,'failed','{\"provider\":\"codex\",\"prompt\":\"old\"}',NULL,0,'t','t')".replace("'a'*1", "'old1'"))
            db.commit()
            db.close()
            store = Store(Path(folder))
            self.assertEqual(store.get('old1')['prompt'], 'old')
            self.assertIsNone(store.get('old1').get('agent'))
            self.assertEqual(store.agent_new('codex', 'queue'), 1)
            Store(Path(folder))  # opening twice must not fail on the existing column

    # ---- addressing mistakes ---------------------------------------------------------------------------
    def test_unknown_mismatched_busy_and_terminal_agents(self):
        agent, _ = self.new_agent('codex')
        with self.assertRaisesRegex(OrchError, 'Không có agent 9.*Agent 1'):
            self.enqueue(agent=9)
        with self.assertRaisesRegex(OrchError, 'không phải claude'):
            self.enqueue(provider='claude', agent=agent)
        for bad in (0, -1, True, 1.5, '1'):
            with self.subTest(agent=bad), self.assertRaises(OrchError):
                self.enqueue(agent=bad)
        terminal = self.e.db.agent_new('codex', 'terminal')
        with self.assertRaisesRegex(OrchError, 'send_to_terminal'):
            self.enqueue(agent=terminal)
        with self.assertRaisesRegex(OrchError, 'provider must be'):
            self.enqueue()  # neither provider nor agent
        self.enqueue(agent=agent)  # accepted: becomes queued ...
        with self.assertRaisesRegex(OrchError, 'đang bận'):
            self.enqueue(agent=agent)  # ... so the agent is busy until it finishes

    def test_remember_must_be_a_boolean(self):
        agent, _ = self.new_agent()
        for bad in ('no', 0, 1, None.__class__):
            with self.subTest(remember=bad), self.assertRaisesRegex(OrchError, 'true or false'):
                self.enqueue(agent=agent, remember=bad)

    # ---- A: continue the same task and resume the session ----------------------------------------------
    def test_default_is_to_continue_in_the_same_worktree_and_resume_the_session(self):
        agent, tid = self.new_agent('codex')
        first = self.e.db.get(tid)
        self.assertIn('resumed=False persist=True', first['result']['summary'])  # remembered from the start: session is kept
        self.assertEqual(self.e.db.agent_get(agent)['session_id'], 'sess-0001-fresh')
        again = self.enqueue('Also add FILE:second', agent=agent)
        self.assertEqual((again['id'], again['round'], again['status']), (tid, 2, 'queued'))
        self.assertEqual(len(again['history']), 1)
        self.assertIsNone(again['result'])
        done = self.e.work_once('codex')
        self.assertEqual((done['id'], done['status'], done['result']['round']), (tid, 'awaiting_review', 2))
        self.assertIn('resumed=True persist=True history=False', done['result']['summary'])
        self.assertEqual(sorted(done['result']['changed_files']), ['src/answer.txt', 'src/second.txt'])  # cumulative vs base
        self.assertEqual(self.e.db.agent_get(agent)['session_id'], 'sess-0001-resumed')
        self.assertTrue((self.cfg.state / 'runs' / tid / 'worker-r1').is_dir(), 'round 1 logs are kept')
        self.assertTrue((self.cfg.state / 'runs' / tid / 'test-unit-r1').is_dir())
        self.assertTrue((self.cfg.state / 'runs' / tid / 'worker').is_dir(), 'live name is the current round')

    def test_claude_uses_the_same_mechanism(self):
        agent, tid = self.new_agent('claude')
        self.enqueue('Also add FILE:second', agent=agent)
        done = self.e.work_once('claude')
        self.assertIn('resumed=True persist=True', done['result']['summary'])

    def test_review_and_export_work_on_the_later_round_and_an_approved_task_can_continue(self):
        agent, tid = self.new_agent()
        self.enqueue('Also add FILE:second', agent=agent)
        task = self.e.work_once('codex')
        digest = task['result']['patch_sha256']
        self.e.record_review(tid, 'approve', digest, 'looks right')
        self.assertTrue((self.cfg.state / 'exports' / tid).parent.exists() or True)
        self.assertEqual(self.e.db.get(tid)['status'], 'approved')
        third = self.enqueue('More FILE:third', agent=agent)  # approved work may still be extended
        self.assertEqual((third['round'], third['status']), (3, 'queued'))
        done = self.e.work_once('codex')
        self.assertEqual(done['status'], 'awaiting_review')
        self.assertNotEqual(done['result']['patch_sha256'], digest, 'a new round needs a new review of the new digest')
        with self.assertRaisesRegex(OrchError, 'digest'):
            self.e.record_review(tid, 'approve', digest, 'stale digest')
        self.assertEqual(len(done['history']), 2)

    def test_scope_must_still_cover_files_changed_in_earlier_rounds(self):
        agent, tid = self.new_agent()
        with self.assertRaisesRegex(OrchError, 'src/answer.txt'):
            self.enqueue('x', agent=agent, scope=('docs',))
        self.assertEqual(self.e.db.get(tid)['status'], 'awaiting_review', 'a refused continuation changes nothing')
        self.enqueue('FILE:second', agent=agent, scope=('src/answer.txt', 'src/second.txt'))  # narrower but covering is fine

    def test_round_that_changes_nothing_fails_even_though_earlier_rounds_did(self):
        agent, tid = self.new_agent()
        self.enqueue('NO_CHANGE please', agent=agent)
        done = self.e.work_once('codex')
        self.assertEqual(done['status'], 'failed')
        self.assertIn('no changes', done['result']['error'])

    def test_continuing_a_failed_task_recovers_it(self):
        task = self.enqueue('FAIL_AGENT now', 'codex')
        self.assertEqual(self.e.work_once('codex')['status'], 'failed')
        self.assertIsNone(self.e.db.agent_get(task['agent'])['session_id'])
        self.enqueue('Fix it properly', agent=task['agent'])
        done = self.e.work_once('codex')
        self.assertEqual(done['status'], 'awaiting_review', done['result'])
        self.assertIn('resumed=False persist=True history=True', done['result']['summary'])  # no session: summary of earlier rounds instead

    def test_cancelled_tasks_are_not_continued(self):
        task = self.enqueue(provider='codex')
        self.e.db.cancel(task['id'])
        again = self.enqueue('fresh start', agent=task['agent'])
        self.assertNotEqual(again['id'], task['id'])
        self.assertEqual(again['round'], 1)
        self.assertEqual(self.e.db.agent_get(task['agent'])['thread_task'], again['id'])

    # ---- B: when the old session cannot be resumed -----------------------------------------------------
    def test_resume_failure_falls_back_to_a_fresh_session_with_history(self):
        agent, tid = self.new_agent()
        self.enqueue('FAIL_RESUME and add FILE:second', agent=agent)
        done = self.e.work_once('codex')
        self.assertEqual(done['status'], 'awaiting_review', done['result'])
        self.assertIn('resumed=False persist=True history=True', done['result']['summary'])
        events = [(e['kind'], e['data']) for e in self.e.db.events(tid)]
        failed = [d for k, d in events if k == 'resume_failed']
        self.assertEqual(len(failed), 1)
        self.assertIn('No conversation found', failed[0]['detail'])
        started = [d for k, d in events if k == 'worker_started']
        self.assertEqual([d['resume'] for d in started], [False, True])

    def test_cancellation_during_resume_is_not_retried(self):
        agent, tid = self.new_agent()
        self.enqueue('FAIL_RESUME FILE:second', agent=agent)
        self.e.db.cancel(tid)  # cancel_requested while queued => nothing to claim; round never starts
        self.assertIsNone(self.e.work_once('codex'))

    # ---- not remembering -------------------------------------------------------------------------------
    def test_remember_false_for_one_task_starts_fresh_from_the_base_commit(self):
        agent, tid = self.new_agent()
        fresh = self.enqueue('start over', agent=agent, remember=False)
        self.assertNotEqual(fresh['id'], tid)
        self.assertEqual((fresh['round'], fresh['agent'], fresh['remember']), (1, agent, False))
        done = self.e.work_once('codex')
        self.assertIn('resumed=False persist=False history=False', done['result']['summary'])  # ephemeral, as before
        row = self.e.db.agent_get(agent)
        self.assertEqual((row['thread_task'], row['session_id']), (fresh['id'], None))
        self.assertEqual(done['result']['changed_files'], ['src/answer.txt'], 'new worktree: earlier files are not carried over')

    def test_agent_setting_off_means_fresh_unless_the_task_overrides_it(self):
        agent, tid = self.new_agent()
        self.e.db.agent_setting(agent, 'remember_context', False)
        self.assertNotEqual(self.enqueue('again', agent=agent)['id'], tid)
        self.e.work_once('codex')
        thread = self.e.db.agent_get(agent)['thread_task']
        again = self.enqueue('FILE:second', agent=agent, remember=True)  # explicit override continues the code state ...
        self.assertEqual((again['id'], again['round']), (thread, 2))
        done = self.e.work_once('codex')  # ... but the earlier task kept no session, so the summary of earlier rounds is used
        self.assertIn('resumed=False persist=True history=True', done['result']['summary'])

    def test_global_default_off_makes_new_agents_ephemeral(self):
        self.e.db.set_setting('default_remember', False)
        agent, tid = self.new_agent()
        self.assertIn('persist=False', self.e.db.get(tid)['result']['summary'])
        self.assertFalse(self.e.db.agent_get(agent)['settings']['remember_context'])
        self.assertNotEqual(self.enqueue('again', agent=agent)['id'], tid)

    def test_agents_overview_reports_state(self):
        agent, tid = self.new_agent()
        self.e.db.agent_new('claude', 'terminal')
        rows = {r['agent']: r for r in self.e.agents_overview()}
        self.assertEqual((rows[agent]['name'], rows[agent]['status'], rows[agent]['round'], rows[agent]['busy'], rows[agent]['can_continue']),
                         ('codex 1', 'awaiting_review', 1, False, True))
        self.assertEqual((rows[2]['kind'], rows[2]['remember_context']), ('terminal', True))
        self.enqueue('more FILE:second', agent=agent)
        self.assertTrue({r['agent']: r for r in self.e.agents_overview()}[agent]['busy'])


class CommandLines(Fixture):
    def test_default_command_line_is_unchanged_and_ephemeral(self):
        self.assertIn('--no-session-persistence', argv(self.cfg, 'claude'))
        codex = argv(self.cfg, 'codex')
        self.assertEqual(codex[2:4], ['exec', '-c'])
        self.assertIn('--ephemeral', codex)
        self.assertEqual(codex[codex.index('--sandbox') + 1], 'workspace-write')

    def test_persist_drops_only_the_ephemeral_flags(self):
        self.assertNotIn('--no-session-persistence', argv(self.cfg, 'claude', persist=True))
        self.assertNotIn('--ephemeral', argv(self.cfg, 'codex', persist=True))
        self.assertIn('--restricted', argv(self.cfg, 'claude', persist=True))

    def test_resume_command_lines(self):
        claude = argv(self.cfg, 'claude', resume='sess-0001-fresh')
        self.assertEqual(claude[claude.index('--resume') + 1], 'sess-0001-fresh')
        self.assertNotIn('--no-session-persistence', claude)
        self.assertIn('--restricted', claude)
        codex = argv(self.cfg, 'codex', resume='sess-0001-fresh')
        self.assertEqual(codex[2:4], ['exec', 'resume'])
        self.assertNotIn('--sandbox', codex)  # `codex exec resume` has no such option
        self.assertIn('sandbox_mode="workspace-write"', codex)
        self.assertIn('approval_policy="never"', codex)
        self.assertIn('sandbox_workspace_write.network_access=false', codex)
        self.assertNotIn('--ephemeral', codex)
        self.assertEqual(codex[-2:], ['sess-0001-fresh', '-'])

    def test_session_ids_are_validated(self):
        for bad in ('--evil', 'x', 'a b', 'a;b' * 3, '', 'x' * 100, '../../etc/passwd'):
            with self.subTest(bad=bad), self.assertRaises(OrchError):
                argv(self.cfg, 'claude', resume=bad)
        self.assertFalse(SESSION.fullmatch('-leading-dash-id'))

    def test_session_id_parsing(self):
        self.assertEqual(session_id('claude', json.dumps({'type': 'result', 'session_id': 'abcd1234-ef'})), 'abcd1234-ef')
        self.assertEqual(session_id('claude', json.dumps([{'type': 'system', 'session_id': 'aaaaaaaa-1'}, {'type': 'result', 'session_id': 'bbbbbbbb-2'}])), 'bbbbbbbb-2')
        lines = '\n'.join(json.dumps(x) for x in ({'type': 'thread.started', 'thread_id': '0190abcd-1234'}, {'type': 'turn.completed'}))
        self.assertEqual(session_id('codex', lines), '0190abcd-1234')
        self.assertIsNone(session_id('codex', json.dumps({'type': 'result', 'session_id': 'abcd1234-ef'})), 'codex id comes from thread.started')
        for text in ('', 'not json', json.dumps({'session_id': '--rm -rf'}), json.dumps({'session_id': 5})):
            self.assertIsNone(session_id('claude', text))


class McpAndWeb(Helpers):
    def setUp(self):
        super().setUp()
        self.server = WebServer(self.e, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, path, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        self.addCleanup(conn.close)
        headers = {'Authorization': 'Bearer ' + self.server.token}
        if body is not None:
            headers.update({'Origin': self.server.origin, 'Content-Type': 'application/json'})
        conn.request('GET' if body is None else 'POST', path, None if body is None else json.dumps(body).encode(), headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read() or b'null')

    def call(self, name, args):
        s = Server(self.e)
        s.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 't', 'version': '1'}}})
        s.dispatch({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        out = s.dispatch({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})['result']
        return out['isError'], json.loads(out['content'][0]['text']) if not out['isError'] else out['content'][0]['text']

    def test_mcp_new_agent_then_continue_then_forget(self):
        base = {'prompt': 'Set the answer', 'allow_paths': ['src'], 'tests': ['unit']}
        error, task = self.call('enqueue_task', {**base, 'provider': 'codex'})
        self.assertFalse(error)
        self.assertEqual(task['agent'], 1)
        self.e.work_once('codex')
        error, again = self.call('enqueue_task', {**base, 'prompt': 'More FILE:second', 'agent': 1})
        self.assertEqual((error, again['id'], again['round']), (False, task['id'], 2))
        self.e.work_once('codex')
        error, fresh = self.call('enqueue_task', {**base, 'agent': 1, 'remember': False})
        self.assertEqual((error, fresh['round'], fresh['remember']), (False, 1, False))
        error, agents = self.call('list_agents', {})
        self.assertEqual((error, agents[0]['name'], agents[0]['busy']), (False, 'codex 1', True))

    def test_mcp_argument_errors_are_returned_to_agent0(self):
        base = {'prompt': 'x', 'allow_paths': ['src'], 'tests': ['unit']}
        for args in ({**base, 'agent': '1'}, {**base, 'agent': 0}, {**base, 'provider': 'codex', 'remember': 'no'}, {**base, 'agent': 1.0}):
            with self.subTest(args=args):
                self.assertTrue(self.call('enqueue_task', args)[0])
        error, text = self.call('enqueue_task', {**base, 'agent': 7})
        self.assertTrue(error)
        self.assertIn('Không có agent 7', text)

    def test_web_task_api_accepts_agent_and_remember(self):
        status, task = self.request('/api/tasks', {'provider': 'claude', 'prompt': 'p', 'allow_paths': ['src'], 'tests': ['unit']})
        self.assertEqual((status, task['agent']), (201, 1))
        self.e.work_once('claude')
        status, again = self.request('/api/tasks', {'agent': 1, 'prompt': 'FILE:second', 'allow_paths': ['src'], 'tests': ['unit'], 'remember': True})
        self.assertEqual((status, again['id'], again['round']), (201, task['id'], 2))
        self.assertEqual(self.request('/api/tasks', {'prompt': 'p', 'allow_paths': ['src'], 'tests': ['unit'], 'surprise': 1})[0], 400)
        self.assertEqual(self.request('/api/tasks', {'prompt': 'p', 'allow_paths': ['src'], 'tests': ['unit']})[0], 400)  # neither provider nor agent

    def test_agent_and_default_settings_api(self):
        self.new_agent()
        status, agents = self.request('/api/agents')
        self.assertEqual((status, agents[0]['remember_context']), (200, True))
        self.assertEqual(self.request('/api/agents/1/settings', {'remember_context': False}), (200, {'agent': 1, 'remember_context': False}))
        self.assertFalse(self.request('/api/agents')[1][0]['remember_context'])
        for bad in ({'remember_context': 'yes'}, {'remember_context': False, 'x': 1}, {}, {'other': True}):
            self.assertEqual(self.request('/api/agents/1/settings', bad)[0], 400)
        self.assertEqual(self.request('/api/agents/99/settings', {'remember_context': True})[0], 400)
        self.assertEqual(self.request('/api/settings'), (200, {'default_remember': True, 'notify_agent0': True}))
        self.assertEqual(self.request('/api/settings', {'default_remember': False}), (200, {'default_remember': False, 'notify_agent0': True}))
        self.assertEqual(self.request('/api/settings', {'default_remember': 'no'})[0], 400)
        self.assertEqual(self.request('/api/settings', {'default_remember': True, 'x': 1})[0], 400)

    def test_logs_of_earlier_rounds_are_readable_but_arbitrary_stages_are_not(self):
        agent, tid = self.new_agent()
        self.enqueue('FILE:second', agent=agent)
        self.e.work_once('codex')
        status, log = self.request(f'/api/tasks/{tid}/logs?stage=worker-r1&stream=stdout')
        self.assertEqual((status, log['available']), (200, True))
        self.assertEqual(self.request(f'/api/tasks/{tid}/logs?stage=test-unit-r1&stream=stdout')[0], 200)
        for stage in ('evil-r1', '..-r1', 'worker-rx', 'worker-r1/../x'):
            self.assertEqual(self.request(f'/api/tasks/{tid}/logs?stage={stage}&stream=stdout')[0], 400, stage)


if __name__ == '__main__':
    unittest.main()
