from __future__ import annotations

import http.client
import json
import os
import threading
import time
import unittest
import urllib.parse

from tests.test_orchestrator import Fixture
from agent_orchestrator.web import WebServer


class WebTests(Fixture):
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

    def request(self, path, body=None, headers=None, method=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        self.addCleanup(conn.close)
        defaults = {'Authorization': 'Bearer ' + self.server.token}
        if body is not None:
            defaults.update({'Origin': self.server.origin, 'Content-Type': 'application/json'})
        defaults.update(headers or {})
        conn.request(method or ('GET' if body is None else 'POST'), path,
                     None if body is None else json.dumps(body).encode(), defaults)
        response = conn.getresponse()
        data = response.read()
        parsed = json.loads(data) if response.getheader('Content-Type', '').startswith('application/json') else data
        return response.status, parsed, response

    def test_static_assets_and_security_headers(self):
        for path in ('/', '/app.js', '/style.css', '/icons.js'):
            status, data, response = self.request(path, headers={'Authorization': ''})
            self.assertEqual(status, 200)
            self.assertTrue(data)
            self.assertEqual(response.getheader('Cache-Control'), 'no-store')
            self.assertEqual(response.getheader('X-Frame-Options'), 'DENY')
        self.assertEqual(self.request('/../../README.md')[0], 404)

    def test_token_host_and_origin_guards(self):
        self.assertEqual(self.request('/api/config', headers={'Authorization': ''})[0], 401)
        self.assertEqual(self.request('/api/config', headers={'Host': 'evil.test'})[0], 403)
        self.assertEqual(self.request('/api/config', headers={'Origin': 'https://evil.test'})[0], 403)
        self.assertEqual(self.request('/api/config', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request('/api/tasks', {}, {'Origin': ''})[0], 403)
        self.assertEqual(self.request('/api/tasks', {}, {'Content-Type': 'text/plain'})[0], 400)

    def test_config_excludes_credentials_and_commands(self):
        status, config, _ = self.request('/api/config')
        self.assertEqual(status, 200)
        self.assertEqual(config['tests'], ['unit'])
        self.assertEqual(config['providers'], {'claude': True, 'codex': True})
        self.assertNotIn('command', json.dumps(config))
        self.assertNotIn(self.server.token, json.dumps(config))

    def test_runner_status_is_authenticated_and_read_only(self):
        status, report, _ = self.request('/api/runners')
        self.assertEqual(status, 200)
        self.assertEqual(report, {'managed': False, 'providers': {}})
        self.assertEqual(self.request('/api/runners', headers={'Authorization': ''})[0], 401)
        self.assertEqual(self.request('/api/runners', {})[0], 404)

    def test_queue_list_cancel_and_activity(self):
        status, task, _ = self.request('/api/tasks', {'provider': 'codex', 'prompt': 'Set answer',
                                                     'allow_paths': ['src'], 'tests': ['unit']})
        self.assertEqual(status, 201)
        task_id = task['id']
        self.assertEqual(self.request('/api/tasks')[1][0]['id'], task_id)
        self.assertEqual(self.request('/api/tasks/' + task_id)[1]['status'], 'queued')
        self.assertEqual(self.request('/api/tasks/' + task_id + '/cancel', {})[1]['status'], 'cancelled')
        self.assertTrue(self.request('/api/activity')[1])
        self.assertTrue(self.request('/api/tasks/' + task_id + '/events')[1])

    def test_validation_and_no_arbitrary_execution_endpoint(self):
        payload = {'provider': 'codex', 'prompt': 'Set answer', 'allow_paths': ['../x'], 'tests': ['unit']}
        self.assertEqual(self.request('/api/tasks', payload)[0], 400)
        payload['allow_paths'] = ['src']
        payload['command'] = 'whoami'
        self.assertEqual(self.request('/api/tasks', payload)[0], 400)
        self.assertEqual(self.request('/api/exec', {'command': 'whoami'})[0], 404)
        self.assertEqual(self.request('/api/tasks', ['not an object'])[0], 400)
        self.assertEqual(self.request('/api/tasks', {'prompt': 'x' * 200001})[0], 413)

    def test_logs_are_bounded_and_paths_are_restricted(self):
        task_id = self.add()
        folder = self.cfg.state / 'runs' / task_id / 'worker'
        folder.mkdir(parents=True)
        (folder / 'stdout.log').write_bytes(b'x' * 70000 + b'end')
        base = '/api/tasks/' + task_id
        status, log, _ = self.request(base + '/logs')
        self.assertEqual(status, 200)
        self.assertEqual(len(log['text']), 65536)
        self.assertTrue(log['truncated'])
        self.assertTrue(log['text'].endswith('end'))
        self.assertFalse(self.request(base + '/logs?stream=stderr')[1]['available'])
        self.assertEqual(self.request(base + '/logs?stage=../../..')[0], 400)
        self.assertEqual(self.request(base + '/logs?stream=../../..')[0], 400)
        self.assertEqual(self.request('/api/tasks/../../logs')[0], 404)

    def test_review_export_download_full_flow(self):
        task_id = self.completed()
        base = '/api/tasks/' + task_id
        self.assertEqual(self.request(base + '/export', {})[0], 400)
        status, bundle, _ = self.request(base + '/review')
        self.assertEqual(status, 200)
        self.assertIn('+42', bundle['diff'])
        self.assertIn(b'+42', self.request(base + '/diff')[1])
        review = {'verdict': 'approve', 'patch_sha256': 'wrong', 'notes': 'Reviewed changes'}
        self.assertEqual(self.request(base + '/review', review)[0], 400)
        review['patch_sha256'] = bundle['patch_sha256']
        self.assertEqual(self.request(base + '/review', review)[1]['status'], 'approved')
        self.assertEqual(self.request(base + '/export', {})[0], 200)
        status, patch, response = self.request(base + '/download/patch')
        self.assertEqual(status, 200)
        self.assertIn(b'+42', patch)
        self.assertIn('changes.patch', response.getheader('Content-Disposition'))
        manifest = json.loads(self.request(base + '/download/manifest')[1])
        self.assertEqual(manifest['patch_sha256'], bundle['patch_sha256'])
        (self.e.git.path(task_id) / 'src/answer.txt').write_text('changed')
        self.assertEqual(self.request(base + '/download/patch')[0], 400)

    def test_request_changes_does_not_rerun_worker(self):
        task_id = self.completed()
        base = '/api/tasks/' + task_id
        bundle = self.request(base + '/review')[1]
        response = self.request(base + '/review', {'verdict': 'request_changes',
                                'patch_sha256': bundle['patch_sha256'], 'notes': 'Add edge case coverage'})
        self.assertEqual(response[1]['status'], 'changes_requested')
        self.assertEqual(self.request(base + '/download/patch')[0], 400)
        self.assertEqual(len(self.e.db.list()), 1)

    def test_repo_and_browse_endpoints(self):
        status, data, _ = self.request('/api/browse')
        self.assertEqual(status, 200)
        self.assertIn('dirs', data)

        status, data, _ = self.request('/api/browse?path=' + urllib.parse.quote(str(self.e.cfg.repo)))
        self.assertEqual(status, 200)
        self.assertIn('dirs', data)

        status, data, _ = self.request('/api/repo/folders')
        self.assertEqual(status, 200)
        self.assertIn('folders', data)

        status, data, _ = self.request('/api/repo', {'path': 'C:/NonExistentPathXYZ123'})
        self.assertEqual(status, 400)

        status, data, _ = self.request('/api/repo', {'path': str(self.e.cfg.repo)})
        self.assertEqual(status, 200)
        self.assertEqual(data['ok'], True)


class TerminalTests(WebTests):
    def test_terminal_routes_are_authenticated_and_fixed_kinds_only(self):
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'agent0'}, {'Authorization': ''})[0], 401)
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'shell'})[0], 400)
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'agent0', 'command': 'cmd'})[0], 400)
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'worker', 'task_id': '../x'})[0], 400)
        self.assertEqual(self.request('/api/terminals/nope/output')[0], 400)

    @unittest.skipUnless(os.name == 'nt', 'ConPTY is Windows only')
    def test_conpty_session_roundtrip(self):
        from agent_orchestrator.terminals import Session
        session = Session('t', 'x', 't', [os.environ['COMSPEC']], os.getcwd(), dict(os.environ), 100, 30)
        self.addCleanup(session.close)
        offset = 0
        deadline = time.time() + 15
        seen = b''
        session.write('echo roundtrip-ok\r')
        while b'roundtrip-ok' not in seen and time.time() < deadline:
            _, data, offset, _ = session.read(offset, 1)
            seen += data
        self.assertIn(b'roundtrip-ok', seen)
        session.write('exit\r')
        deadline = time.time() + 10
        while session.alive and time.time() < deadline:
            time.sleep(.2)
        self.assertFalse(session.alive)

    def test_bridge_is_read_only_and_key_protected(self):
        key = {'X-Bridge-Key': self.server.bridge_key, 'Authorization': ''}
        self.assertEqual(self.request('/api/bridge/terminals', headers={'Authorization': ''})[0], 401)
        self.assertEqual(self.request('/api/bridge/terminals', headers={'X-Bridge-Key': 'wrong', 'Authorization': ''})[0], 401)
        status, data, _ = self.request('/api/bridge/terminals', headers=key)
        self.assertEqual((status, data), (200, []))
        self.assertEqual(self.request('/api/bridge/terminals/nope', headers=key)[0], 400)

    def test_agent_kind_requires_known_provider(self):
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'agent', 'provider': 'bash'})[0], 400)
        self.assertEqual(self.request('/api/terminals/open', {'kind': 'agent'})[0], 400)
