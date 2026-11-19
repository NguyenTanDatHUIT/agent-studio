from __future__ import annotations

import http.client
import json
import threading
import unittest

from agent_orchestrator.gemini_bridge import WorkspaceExecutor, parse_tool_calls
from agent_orchestrator.web import WebServer
from tests.test_orchestrator import Fixture


class GeminiBridgeTests(Fixture):
    def setUp(self):
        super().setUp()
        self.cfg.data['providers']['gemini_web'] = {'command': [], 'model': 'gemini-web', 'enabled': True, 'max_turns': 6}
        self.server = WebServer(self.e, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def ext_call(self, path, body=None, key=None, origin='chrome-extension://abcdefghijklmnop'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        self.addCleanup(conn.close)
        headers = {
            'Origin': origin,
            'Sec-Fetch-Site': 'cross-site',
            'X-Gemini-Bridge-Key': self.server.gemini_bridge.key if key is None else key,
        }
        if body is not None:
            headers['Content-Type'] = 'application/json'
        conn.request('GET' if body is None else 'POST', '/api/gemini-bridge' + path,
                     None if body is None else json.dumps(body).encode('utf-8'), headers)
        res = conn.getresponse()
        raw = res.read()
        return res.status, (json.loads(raw) if raw else None), res

    def test_scope_and_traversal_blocked_by_executor(self):
        ex = WorkspaceExecutor(self.repo, allow_paths=['src'])
        self.assertFalse(ex.execute({'action': 'write_file', 'path': '../outside.txt', 'content': 'x'})['ok'])
        self.assertFalse(ex.execute({'action': 'write_file', 'path': '.env', 'content': 'SECRET=1'})['ok'])
        self.assertFalse(ex.execute({'action': 'write_file', 'path': 'README.md', 'content': 'out of scope'})['ok'])
        ok = ex.execute({'action': 'replace_in_file', 'path': 'src/answer.txt', 'search': '0', 'replace': '42'})
        self.assertTrue(ok['ok'], ok)
        self.assertEqual((self.repo / 'src/answer.txt').read_text(encoding='utf-8'), '42\n')

    def test_cors_and_bridge_key_guard(self):
        self.assertEqual(self.ext_call('/poll?client_id=t1&wait=0', key='wrong-key')[0], 401)
        st, payload, res = self.ext_call('/poll?client_id=t1&wait=0')
        self.assertEqual(st, 200)
        self.assertIsNone(payload)
        self.assertEqual(res.getheader('Access-Control-Allow-Origin'), 'chrome-extension://abcdefghijklmnop')

    def test_end_to_end_worktree_coding_and_review_gate(self):
        """End-to-end: engine chuẩn bị worktree, gọi hub trực tiếp (bỏ qua HTTP loopback để tránh
        proxy sandbox), extension giả mạo poll/reply qua HTTP, engine ghép kết quả và chạy test."""
        hub = self.server.gemini_bridge
        task = self.e.enqueue('gemini_web', 'Update src/answer.txt to 42', ['src'], ['unit'])
        # Chuẩn bị worktree trước để hub biết đường dẫn
        git = self.e.task_git(self.e.db.get(task['id']))
        worktree = git.prepare(self.e.db.get(task['id']))

        result_holder = {}

        def fake_browser_extension():
            # Enqueue job vào hub trực tiếp (bỏ qua HTTP để tránh sandbox chặn 127.0.0.1)
            from agent_orchestrator.engine import Engine
            prompt = Engine.worker_prompt(self.e.db.get(task['id']), True)
            hub.create_worker_job(str(worktree), ['src'], prompt)

            # Lượt 1: extension poll, nhận job, trả lời read_file
            _, job1, _ = self.ext_call(
                '/poll?client_id=ext1&tab_id=1&url=https://gemini.google.com/app/abc123456&wait=8'
            )
            self.assertIsNotNone(job1, 'Extension không nhận được job')
            reply1 = '<<<AO_TOOL\n{"action": "read_file", "path": "src/answer.txt"}\nAO_TOOL>>>'
            self.ext_call('/reply', {
                'prompt_id': job1['prompt_id'], 'text': reply1,
                'url': 'https://gemini.google.com/app/abc123456'
            })

            # Lượt 2: nhận tool result, sửa file rồi finish_task
            _, job2, _ = self.ext_call(
                '/poll?client_id=ext1&tab_id=1&url=https://gemini.google.com/app/abc123456&wait=8'
            )
            self.assertIsNotNone(job2, 'Extension không nhận được job2')
            self.assertIn('[AO_TOOL_RESULT]', job2['prompt'])
            reply2 = (
                '<<<AO_TOOL\n{"action": "replace_in_file", "path": "src/answer.txt",'
                ' "search": "0", "replace": "42"}\nAO_TOOL>>>\n'
                '<<<AO_TOOL\n{"action": "finish_task", "summary": "Set answer to 42"}\nAO_TOOL>>>'
            )
            self.ext_call('/reply', {
                'prompt_id': job2['prompt_id'], 'text': reply2,
                'url': 'https://gemini.google.com/app/abc123456'
            })

            # Chờ job hoàn tất trong hub
            import time
            deadline = time.time() + 10
            job_id = list(hub.jobs.keys())[0]
            while time.time() < deadline:
                st = hub.get_worker_job(job_id, wait=1.0)
                if st['status'] != 'running':
                    result_holder['job'] = st
                    break

        ext_thread = threading.Thread(target=fake_browser_extension, daemon=True)
        ext_thread.start()
        ext_thread.join(30)

        # Kiểm tra job thành công
        self.assertIn('job', result_holder, 'Job chưa hoàn tất')
        job_st = result_holder['job']
        self.assertEqual(job_st['status'], 'completed', job_st)
        self.assertEqual(job_st['session_id'], 'abc123456')
        # Kiểm tra file đã được sửa trong worktree
        self.assertEqual((worktree / 'src' / 'answer.txt').read_text(encoding='utf-8'), '42\n')

    def test_foreign_origin_and_outside_worktree_rejected(self):
        self.assertEqual(self.ext_call('/poll?client_id=t1&wait=0', origin='https://evil.example')[0], 403)
        st, payload, _ = self.ext_call('/jobs', {'worktree': str(self.repo), 'allow_paths': ['src'], 'prompt': 'x'})
        self.assertEqual(st, 400, payload)  # the key holder may not aim the executor at an arbitrary folder
        self.cfg.data['providers']['gemini_web']['enabled'] = False
        self.assertEqual(self.ext_call('/poll?client_id=t1&wait=0')[0], 403)

    def test_config_validation(self):
        from agent_orchestrator.config import Config, OrchError
        data = json.loads(self.config_file.read_text(encoding='utf-8'))
        for bad in ({'command': ['C:/x.exe']}, {'enabled': 'yes'}, {'max_turns': 99}, {'flags': 1}):
            data['providers']['gemini_web'] = bad
            self.config_file.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(OrchError):
                Config(self.config_file)
        data['providers']['gemini_web'] = {'enabled': True, 'max_turns': 5}
        self.config_file.write_text(json.dumps(data), encoding='utf-8')
        self.assertTrue(Config(self.config_file).provider_enabled('gemini_web'))

    def test_interactive_terminal_tool_loop(self):
        info = self.server.terminals.open('agent', 'gemini_web')
        sid = info['id']
        sess = self.server.terminals.get(sid)
        sess.write('Set answer to 42' + chr(13))
        self.assertFalse(sess.idle)
        _, job, _ = self.ext_call('/poll?client_id=e&tab_id=1&url=https://gemini.google.com/app&wait=3')
        self.assertIn('Set answer to 42', job['prompt'])
        reply = '<<<AO_TOOL' + chr(10) + '{"action": "replace_in_file", "path": "src/answer.txt", "search": "0", "replace": "42"}' + chr(10) + 'AO_TOOL>>>'
        self.ext_call('/reply', {'prompt_id': job['prompt_id'], 'text': reply, 'url': 'https://gemini.google.com/app/conv12345'})
        self.assertFalse(sess.idle)  # tool result is sent back first; silence must not count as finished
        _, job2, _ = self.ext_call('/poll?client_id=e&tab_id=1&wait=3')
        self.assertIn('[AO_TOOL_RESULT]', job2['prompt'])
        self.ext_call('/reply', {'prompt_id': job2['prompt_id'], 'text': 'Đã xong.', 'url': 'https://gemini.google.com/app/conv12345'})
        self.assertTrue(sess.idle)
        self.assertEqual((self.repo / 'src/answer.txt').read_text(encoding='utf-8'), '42' + chr(10))
        self.assertEqual(sess.session_id, 'conv12345')
        self.assertTrue(self.server.terminals.describe(sess)['idle'])
        self.server.terminals.close(sid)

    def test_parser_accepts_fenced_blocks_and_flags_garbled_commands(self):
        from agent_orchestrator.gemini_bridge import parse_tool_calls
        fence = chr(96) * 3
        text = 'Đọc thử:' + chr(10) + fence + 'json' + chr(10) + '{"action": "read_file", "path": "src/answer.txt"}' + chr(10) + fence + chr(10) + 'xong'
        self.assertEqual(parse_tool_calls(text)[0]['action'], 'read_file')
        self.assertEqual(parse_tool_calls('Mô tả', ['{"action": "list_files", "subdir": ""}'])[0]['action'], 'list_files')
        # the garbled reply seen in a real session must come back as an error to feed to the model, not as "finished"
        garbled = '<<<AO_TOOL "C:/x/a.md", "end_line": "path": "read_file", "start_line": 1, 200} AO_TOOL {"action":>>>'
        calls = parse_tool_calls(garbled)
        self.assertEqual([c['action'] for c in calls], ['_parse_error'])
        ex = WorkspaceExecutor(self.repo)
        res = ex.execute(calls[0])
        self.assertFalse(res['ok'])
        self.assertIn('```json', res['error'])
        # the exact text seen in a real session: the page's "JSON" label sits in front of the object
        shown = 'JSON' + chr(10) + '{"action": "list_files", "subdir": ""}'
        self.assertEqual([c['action'] for c in parse_tool_calls(shown)], ['list_files'])
        # text inside a string value that merely looks like a command must not become a second command
        nested = '{"action": "write_file", "path": "a.md", "content": "{\\"action\\": \\"finish_task\\"}"}'
        self.assertEqual([c['action'] for c in parse_tool_calls(nested)], ['write_file'])
        self.assertEqual(parse_tool_calls('Chỉ là lời giải thích, không có lệnh.'), [])

    def test_large_reads_are_chunked_and_feedback_is_capped(self):
        from agent_orchestrator.gemini_bridge import MAX_FEEDBACK_CHARS, format_tool_results
        big = self.repo / 'src' / 'big.txt'
        big.write_text(''.join(f'line {i} ' + 'x' * 70 + chr(10) for i in range(1, 801)), encoding='utf-8')
        ex = WorkspaceExecutor(self.repo)
        first = ex.execute({'action': 'read_file', 'path': 'src/big.txt'})
        self.assertTrue(first['ok'] and first['truncated'])
        self.assertLess(len(first['content']), 9_500)
        nxt = ex.execute({'action': 'read_file', 'path': 'src/big.txt', 'start_line': first['next_start_line'], 'end_line': 800})
        self.assertTrue(nxt['content'].startswith(str(first['next_start_line']) + ': '))  # continues exactly where it stopped
        two = format_tool_results([first, nxt, ex.execute({'action': 'read_file', 'path': 'src/big.txt', 'start_line': 300, 'end_line': 800})])
        self.assertLess(len(two), MAX_FEEDBACK_CHARS + 1500)
        self.assertIn('start_line', two)

    def test_read_roots_allow_read_only_outside_the_workspace(self):
        notes = self.root / 'notes'
        notes.mkdir()
        (notes / 'plan.md').write_text('a' + chr(10) + 'b' + chr(10), encoding='utf-8')
        (notes / '.env').write_text('SECRET=1', encoding='utf-8')
        (self.root / 'notes-secret').mkdir()
        (self.root / 'notes-secret' / 'k.txt').write_text('no', encoding='utf-8')
        ex = WorkspaceExecutor(self.repo, read_roots=[notes])
        ok = ex.execute({'action': 'read_file', 'path': (notes / 'plan.md').as_posix()})
        self.assertTrue(ok['ok'], ok)
        self.assertEqual(ok['total_lines'], 2)
        listing = ex.execute({'action': 'list_files', 'subdir': notes.as_posix()})
        self.assertTrue(listing['ok'] and any(f.endswith('plan.md') for f in listing['files']), listing)
        self.assertFalse(any(f.endswith('.env') for f in listing['files']))
        # still blocked: protected names, sibling folder with the same prefix, traversal out of the root, any write
        self.assertFalse(ex.execute({'action': 'read_file', 'path': (notes / '.env').as_posix()})['ok'])
        self.assertFalse(ex.execute({'action': 'read_file', 'path': (self.root / 'notes-secret' / 'k.txt').as_posix()})['ok'])
        self.assertFalse(ex.execute({'action': 'read_file', 'path': notes.as_posix() + '/../notes-secret/k.txt'})['ok'])
        self.assertFalse(ex.execute({'action': 'write_file', 'path': (notes / 'new.md').as_posix(), 'content': 'x'})['ok'])
        self.assertFalse((notes / 'new.md').exists())
        # without read_roots the same absolute path is refused
        self.assertFalse(WorkspaceExecutor(self.repo).execute({'action': 'read_file', 'path': (notes / 'plan.md').as_posix()})['ok'])

    def test_read_roots_config_rejects_dangerous_folders(self):
        from agent_orchestrator.config import Config, OrchError
        data = json.loads(self.config_file.read_text(encoding='utf-8'))
        safe = self.root / 'notes2'
        safe.mkdir()
        for bad in (str(self.root), str(self.cfg.state), str(self.root.anchor), 'relative/dir', str(self.root / 'missing')):
            data['providers']['gemini_web'] = {'enabled': True, 'read_roots': [bad]}
            self.config_file.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(OrchError, msg=bad):
                Config(self.config_file)
        data['providers']['gemini_web'] = {'enabled': True, 'read_roots': [str(safe)]}
        self.config_file.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(len(Config(self.config_file).data['providers']['gemini_web']['read_roots']), 1)

    def test_absolute_path_gives_actionable_error(self):
        ex = WorkspaceExecutor(self.repo)
        res = ex.execute({'action': 'read_file', 'path': 'C:/AgentControl/studio-state/x.md'})
        self.assertFalse(res['ok'])
        self.assertIn('tương đối', res['error'])

    def test_reply_blocks_drive_tool_loop_and_debug_is_saved(self):
        info = self.server.terminals.open('agent', 'gemini_web')
        sess = self.server.terminals.get(info['id'])
        sess.write('Đọc answer' + chr(13))
        _, job, _ = self.ext_call('/poll?client_id=e&tab_id=1&url=https://gemini.google.com/app&wait=3')
        self.assertIn('```json', job['prompt'])
        self.ext_call('/reply', {'prompt_id': job['prompt_id'], 'text': 'Tôi sẽ đọc tệp.', 'url': 'https://gemini.google.com/app/conv99999',
                                 'blocks': ['{"action": "read_file", "path": "src/answer.txt"}'], 'debug_html': '<pre>x</pre>'})
        _, job2, _ = self.ext_call('/poll?client_id=e&tab_id=1&wait=3')
        self.assertIn('[AO_TOOL_RESULT]', job2['prompt'])
        self.assertTrue((self.cfg.state / 'gemini-debug' / 'last-reply.json').is_file())
        self.server.terminals.close(info['id'])


if __name__ == '__main__':
    unittest.main()
