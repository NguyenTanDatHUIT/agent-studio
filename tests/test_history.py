"""Tests for chat history and terminal resume features."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent_orchestrator.config import OrchError
from agent_orchestrator.store import Store, now


class TestConversationStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-hist-'))
        self.store = Store(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_get_conversation(self):
        conv = {
            'id': 'conv-001',
            'terminal_key': 'claude-1',
            'provider': 'claude',
            'agent_n': 1,
            'kind': 'agent',
            'cwd': str(self.tmp),
            'task_id': None,
            'session_id': 'sess-12345678',
            'title': 'Xin chào Claude',
            'started': now(),
            'last_active': now(),
            'status': 'active',
            'transcript_path': str(self.tmp / 'conv-001.log')
        }
        self.store.conversation_add(conv)
        got = self.store.conversation_get('conv-001')
        self.assertEqual(got['id'], 'conv-001')
        self.assertEqual(got['provider'], 'claude')
        self.assertEqual(got['agent_n'], 1)
        self.assertEqual(got['title'], 'Xin chào Claude')
        self.assertEqual(got['session_id'], 'sess-12345678')
        self.assertEqual(got['status'], 'active')

    def test_get_unknown_conversation(self):
        with self.assertRaises(OrchError) as ctx:
            self.store.conversation_get('non-existent')
        self.assertIn('Unknown conversation', str(ctx.exception))

    def test_update_conversation(self):
        conv = {
            'id': 'conv-002',
            'terminal_key': 'codex-2',
            'provider': 'codex',
            'kind': 'agent',
            'cwd': str(self.tmp),
            'title': 'Tiêu đề cũ',
            'status': 'active'
        }
        self.store.conversation_add(conv)
        self.store.conversation_update('conv-002', title='Tiêu đề mới', session_id='codex-sess-uuid', status='closed')
        got = self.store.conversation_get('conv-002')
        self.assertEqual(got['title'], 'Tiêu đề mới')
        self.assertEqual(got['session_id'], 'codex-sess-uuid')
        self.assertEqual(got['status'], 'closed')

    def test_update_invalid_field(self):
        conv = {
            'id': 'conv-003',
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.tmp),
            'title': 'Test'
        }
        self.store.conversation_add(conv)
        with self.assertRaises(OrchError):
            self.store.conversation_update('conv-003', malicious_col='drop table')

    def test_list_and_filters(self):
        for i in range(5):
            self.store.conversation_add({
                'id': f'conv-claude-{i}',
                'provider': 'claude',
                'kind': 'agent',
                'cwd': str(self.tmp),
                'title': f'Claude task {i}',
                'started': f'2026-11-07T0{i}:00:00Z',
                'last_active': f'2026-11-07T0{i}:00:00Z',
                'status': 'closed'
            })
        for i in range(3):
            self.store.conversation_add({
                'id': f'conv-codex-{i}',
                'provider': 'codex',
                'kind': 'agent',
                'cwd': str(self.tmp),
                'title': f'Codex feature {i}',
                'started': f'2026-11-07T1{i}:00:00Z',
                'last_active': f'2026-11-07T1{i}:00:00Z',
                'status': 'active'
            })

        all_convs = self.store.conversation_list()
        self.assertEqual(len(all_convs), 8)
        # Verify ordering: started DESC
        self.assertEqual(all_convs[0]['id'], 'conv-codex-2')

        # Limit
        limited = self.store.conversation_list(limit=3)
        self.assertEqual(len(limited), 3)

        # Provider filter
        claude_only = self.store.conversation_list(provider='claude')
        self.assertEqual(len(claude_only), 5)
        self.assertTrue(all(c['provider'] == 'claude' for c in claude_only))

        codex_only = self.store.conversation_list(provider='codex')
        self.assertEqual(len(codex_only), 3)

        # Search query
        matched = self.store.conversation_list(q='feature 1')
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]['id'], 'conv-codex-1')

    def test_list_limit_validation(self):
        for bad_limit in [0, 201, -5, '50', None, 1.5]:
            with self.assertRaises(OrchError):
                self.store.conversation_list(limit=bad_limit)

    def test_migration_idempotent(self):
        # Initializing Store multiple times on existing db should not fail
        s2 = Store(self.tmp)
        s3 = Store(self.tmp)
        conv = {
            'id': 'conv-idemp',
            'provider': 'claude',
            'kind': 'agent0',
            'cwd': str(self.tmp),
            'title': 'Agent 0 conversation'
        }
        s3.conversation_add(conv)
        self.assertEqual(s2.conversation_get('conv-idemp')['title'], 'Agent 0 conversation')

    def test_concurrent_writes(self):
        threads = []
        errors = []

        def worker(idx):
            try:
                s = Store(self.tmp)
                for j in range(10):
                    cid = f'thread-{idx}-{j}'
                    s.conversation_add({
                        'id': cid,
                        'provider': 'claude',
                        'kind': 'agent',
                        'cwd': str(self.tmp),
                        'title': f'Thread {idx} Task {j}'
                    })
                    s.conversation_update(cid, status='updated')
            except Exception as e:
                errors.append(e)

        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        total = len(self.store.conversation_list(limit=200))
        self.assertEqual(total, 40)


class TestTranscriptRecorder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-transcripts-'))
        self.log_file = self.tmp / 'test_conv.log'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_mask_secrets(self):
        from agent_orchestrator.transcripts import mask_secrets

        sample = (
            "Authorization: Bearer secret_token_value_12345\n"
            "api_key: 'my_super_secret_api_key_99'\n"
            "OPENAI_KEY = sk-proj-12345678901234567890123456\n"
            "ANTHROPIC = sk-ant-api03-abcdefghijklmnopqrstuvwxyz\n"
            "GITHUB_PAT = ghp_1234567890abcdefghijklmnopqrstuvwxyz\n"
            "Normal text: The token count is 1500 tokens in total."
        )
        masked = mask_secrets(sample)
        self.assertNotIn("secret_token_value_12345", masked)
        self.assertNotIn("my_super_secret_api_key_99", masked)
        self.assertNotIn("sk-proj-12345678901234567890123456", masked)
        self.assertNotIn("sk-ant-api03-abcdefghijklmnopqrstuvwxyz", masked)
        self.assertNotIn("ghp_1234567890abcdefghijklmnopqrstuvwxyz", masked)
        self.assertIn("[REDACTED]", masked)
        self.assertIn("The token count is 1500 tokens in total.", masked)

    def test_strip_ansi_and_clean(self):
        from agent_orchestrator.transcripts import clean_transcript_text

        text_with_ansi = "\x1b[31;1mError:\x1b[0m File not found\x07\r\nNext line"
        cleaned = clean_transcript_text(text_with_ansi)
        self.assertEqual(cleaned, "Error: File not found\nNext line")

    def test_append_transcript_entry(self):
        from agent_orchestrator.transcripts import append_transcript_entry

        append_transcript_entry(self.log_file, "Line 1\nLine 2", timestamp="2026-11-08T00:00:00Z")
        content = self.log_file.read_text(encoding='utf-8')
        self.assertIn("[2026-11-08T00:00:00Z] Line 1\n", content)
        self.assertIn("[2026-11-08T00:00:00Z] Line 2\n", content)

    def test_truncate_file_head(self):
        from agent_orchestrator.transcripts import append_transcript_entry

        # Small max file size: 2 KB, retain 1 KB
        large_chunk = ("A" * 100 + "\n") * 30  # ~3 KB
        append_transcript_entry(self.log_file, large_chunk, max_file_size=2000)
        size = self.log_file.stat().st_size
        self.assertLessEqual(size, 2048)
        content = self.log_file.read_text(encoding='utf-8')
        self.assertIn("luoc bo de giu gioi han", content)

    def test_prune_transcripts_dir(self):
        from agent_orchestrator.transcripts import append_transcript_entry

        # Total max size: 4000 bytes
        f1 = self.tmp / "f1.log"
        f2 = self.tmp / "f2.log"
        f3 = self.tmp / "f3.log"
        append_transcript_entry(f1, "1" * 1500 + "\n", max_total_size=4000)
        os.utime(f1, (1000, 1000))
        append_transcript_entry(f2, "2" * 1500 + "\n", max_total_size=4000)
        os.utime(f2, (2000, 2000))
        # Adding f3 should exceed 4000 and prune f1
        append_transcript_entry(f3, "3" * 1500 + "\n", max_total_size=4000)
        self.assertFalse(f1.exists(), "Oldest file f1 should be pruned")
        self.assertTrue(f2.exists())
        self.assertTrue(f3.exists())


class TestTerminalResumeAndTranscripts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-terms-'))
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        self.state = self.tmp / 'state'
        self.state.mkdir()

        # Minimal config
        from agent_orchestrator.config import Config
        cfg_file = self.tmp / 'config.json'
        import sys
        fake_agent = str(Path(__file__).resolve().parent / 'fake_agent.py')
        cfg_data = {
            'version': 1,
            'repo': str(self.repo),
            'state_dir': str(self.state),
            'acknowledge_local_execution': True,
            'repos': {},
            'providers': {
                'claude': {'command': [sys.executable, fake_agent]},
                'codex': {'command': [sys.executable, fake_agent]},
                'agy': {'command': [sys.executable, fake_agent]}
            },
            'tests': {}
        }
        import json
        cfg_file.write_text(json.dumps(cfg_data), encoding='utf-8')
        self.cfg = Config(cfg_file)
        self.store = Store(self.state)
        from agent_orchestrator.terminals import Terminals
        self.terminals = Terminals(self.cfg, self.store)

    def tearDown(self):
        self.terminals.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_agent0_argv_new_and_resume(self):
        # New session generates or accepts session-id
        argv_new = self.terminals.agent0_argv(session_id='sess-new-12345')
        self.assertIn('--session-id', argv_new)
        self.assertIn('sess-new-12345', argv_new)
        self.assertIn('--mcp-config', argv_new)
        self.assertIn('--strict-mcp-config', argv_new)

        # Resume session has --resume and keeps MCP config
        argv_resume = self.terminals.agent0_argv(resume='sess-resume-67890')
        self.assertIn('--resume', argv_resume)
        self.assertIn('sess-resume-67890', argv_resume)
        self.assertIn('--mcp-config', argv_resume)
        self.assertIn('--strict-mcp-config', argv_resume)

    def test_session_id_validation(self):
        for bad_id in ['--malicious-flag', 'spaces in id', 'short', 'a' * 100, None]:
            if bad_id is None:
                continue
            with self.assertRaises(OrchError):
                self.terminals.agent0_argv(resume=bad_id)
            with self.assertRaises(OrchError):
                self.terminals.agent0_argv(session_id=bad_id)

    def test_validate_cwd_security(self):
        # Allowed repo
        self.assertEqual(self.terminals.validate_cwd(self.repo), self.repo.resolve())

        # Disallowed repo
        other = self.tmp / 'other'
        other.mkdir()
        with self.assertRaises(OrchError):
            self.terminals.validate_cwd(other)

        # Worktree check
        wt = self.state / 'worktrees' / ('a' * 24)
        wt.mkdir(parents=True)
        self.assertEqual(self.terminals.validate_cwd(wt, task_id='a' * 24), wt.resolve())

        # Invalid task_id or cwd mismatch
        with self.assertRaises(OrchError):
            self.terminals.validate_cwd(wt, task_id='b' * 24)
        with self.assertRaises(OrchError):
            self.terminals.validate_cwd(other, task_id='a' * 24)

    def test_resume_missing_session_id_suggests_transcript(self):
        conv_id = 'conv-no-sess'
        self.store.conversation_add({
            'id': conv_id,
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'No session',
            'session_id': None,
            'transcript_path': str(self.state / 'transcripts' / 'test.log')
        })
        with self.assertRaises(OrchError) as ctx:
            self.terminals.resume_conversation(conv_id)
        self.assertIn('không có session ID', str(ctx.exception))
        self.assertIn('Xem lại', str(ctx.exception))

    def test_read_transcript_pagination(self):
        conv_id = 'conv-trans-paging'
        log_file = self.state / 'transcripts' / f'{conv_id}.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        lines = [f'Line {i}\n' for i in range(25)]
        log_file.write_text(''.join(lines), encoding='utf-8')

        self.store.conversation_add({
            'id': conv_id,
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'Transcript Test',
            'session_id': 'sess-12345678',
            'transcript_path': str(log_file)
        })

        # Read first 10
        r1 = self.terminals.read_transcript(conv_id, after=0, limit=10)
        self.assertEqual(len(r1['lines']), 10)
        self.assertEqual(r1['start'], 0)
        self.assertEqual(r1['next'], 10)
        self.assertEqual(r1['total'], 25)
        self.assertTrue(r1['has_more'])

        # Read next 10
        r2 = self.terminals.read_transcript(conv_id, after=r1['next'], limit=10)
        self.assertEqual(len(r2['lines']), 10)
        self.assertEqual(r2['start'], 10)
        self.assertEqual(r2['next'], 20)
        self.assertTrue(r2['has_more'])

        # Read remaining
        r3 = self.terminals.read_transcript(conv_id, after=r2['next'], limit=10)
        self.assertEqual(len(r3['lines']), 5)
        self.assertEqual(r3['next'], 25)
        self.assertFalse(r3['has_more'])

    def test_resume_already_open_session(self):
        # Create dummy session in self.terminals.sessions
        class FakeSession:
            def __init__(self, cid, sess_id):
                self.id = 'claude-1'
                self.kind = 'agent'
                self.provider = 'claude'
                self.title = 'Title'
                self.cwd = '.'
                self.alive = True
                self.exit_code = None
                self.conversation_id = cid
                self.session_id = sess_id

            def close(self):
                self.alive = False

        self.terminals.sessions['claude-1'] = FakeSession('conv-open', 'sess-12345678')
        self.store.conversation_add({
            'id': 'conv-open',
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'Already open',
            'session_id': 'sess-12345678',
            'transcript_path': str(self.state / 'transcripts' / 'open.log')
        })

        res = self.terminals.resume_conversation('conv-open')
        self.assertTrue(res.get('already_open'))
        self.assertEqual(res['id'], 'claude-1')

    def test_resume_audit_and_rate_limit(self):
        conv_id = 'conv-audit'
        self.store.conversation_add({
            'id': conv_id,
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'Audit Test',
            'session_id': 'sess-12345678',
            'transcript_path': str(self.state / 'transcripts' / 'audit.log')
        })

        import time
        # We mock open to avoid spawning real process in this rate limit test
        original_open = self.terminals.open
        try:
            self.terminals.open = lambda *a, **kw: {'id': 'claude-1'}
            res = self.terminals.resume_conversation(conv_id)
            self.assertEqual(res['id'], 'claude-1')

            # Verify audit file
            audit_file = self.state / 'terminal-audit.jsonl'
            self.assertTrue(audit_file.is_file())
            content = audit_file.read_text(encoding='utf-8')
            self.assertIn('"action": "resume"', content)
            self.assertIn('"session_id": "sess-12345678"', content)

            # Rapid second call raises rate limit error
            with self.assertRaises(OrchError) as ctx:
                self.terminals.resume_conversation(conv_id)
            self.assertIn('quá nhanh', str(ctx.exception))
        finally:
            self.terminals.open = original_open

    @unittest.skipUnless(os.name == 'nt', 'ConPTY requires Windows')
    def test_session_conpty_auto_title_and_transcript(self):
        from agent_orchestrator.terminals import Session
        import time

        conv_id = 'conv-conpty-test'
        log_file = self.state / 'transcripts' / f'{conv_id}.log'
        titles = []

        def on_title(t):
            titles.append(t)

        session = Session(
            sid='test-1',
            kind='agent',
            title='Default Title',
            argv=[os.environ['COMSPEC']],
            cwd=self.repo,
            env=dict(os.environ),
            cols=100,
            rows=30,
            conversation_id=conv_id,
            transcript_path=log_file,
            on_title=on_title
        )
        self.addCleanup(session.close)

        # Type into session
        session.write('echo AutoTitleText\r')
        deadline = time.time() + 10
        while not titles and time.time() < deadline:
            time.sleep(0.1)

        self.assertTrue(len(titles) > 0)
        self.assertIn('AutoTitleText', titles[0])

        # Verify transcript file
        deadline = time.time() + 10
        while (not log_file.exists() or b'AutoTitleText' not in log_file.read_bytes()) and time.time() < deadline:
            time.sleep(0.1)

        self.assertTrue(log_file.exists())
        text = log_file.read_text(encoding='utf-8', errors='replace')
        self.assertIn('AutoTitleText', text)

    def test_scan_codex_session_midnight_cross_day(self):
        from agent_orchestrator.terminals import scan_codex_session
        import datetime
        from datetime import timedelta

        codex_home = self.tmp / '.codex'
        now_dt = datetime.datetime.now()
        yesterday_dt = now_dt - timedelta(days=1)
        yesterday_dir = codex_home / 'sessions' / f"{yesterday_dt.year}" / f"{yesterday_dt.month:02d}" / f"{yesterday_dt.day:02d}"
        yesterday_dir.mkdir(parents=True, exist_ok=True)

        rollout_file = yesterday_dir / 'rollout-midnight.jsonl'
        sess_id = '018f1234-5678-7000-8000-000000000001'
        meta = {
            'type': 'session_meta',
            'payload': {
                'id': sess_id,
                'cwd': str(self.repo)
            }
        }
        rollout_file.write_text(json.dumps(meta) + '\n', encoding='utf-8')
        t_started = time.time()
        os.utime(rollout_file, (t_started - 1.0, t_started - 1.0))

        found = scan_codex_session(t_started, str(self.repo), timeout=1.0, codex_home=codex_home)
        self.assertEqual(found, sess_id)

    def test_scan_codex_session_multiple_sessions_picks_newest(self):
        from agent_orchestrator.terminals import scan_codex_session
        import datetime

        codex_home = self.tmp / '.codex'
        now_dt = datetime.datetime.now()
        today_dir = codex_home / 'sessions' / f"{now_dt.year}" / f"{now_dt.month:02d}" / f"{now_dt.day:02d}"
        today_dir.mkdir(parents=True, exist_ok=True)

        t_base = time.time()
        old_file = today_dir / 'rollout-1.jsonl'
        old_id = '018f1234-5678-7000-8000-000000000011'
        old_file.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': old_id, 'cwd': str(self.repo)}}) + '\n')
        os.utime(old_file, (t_base, t_base))

        new_file = today_dir / 'rollout-2.jsonl'
        new_id = '018f1234-5678-7000-8000-000000000022'
        new_file.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': new_id, 'cwd': str(self.repo)}}) + '\n')
        os.utime(new_file, (t_base + 3.0, t_base + 3.0))

        found = scan_codex_session(t_base, str(self.repo), timeout=1.0, codex_home=codex_home)
        self.assertEqual(found, new_id)

    def test_scan_codex_session_missing_fallback(self):
        from agent_orchestrator.terminals import scan_codex_session

        codex_home = self.tmp / '.codex-nonexistent'
        found = scan_codex_session(time.time(), str(self.repo), timeout=0.3, codex_home=codex_home)
        self.assertIsNone(found)



class TestWebHistoryApi(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-web-hist-'))
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        self.state = self.tmp / 'state'
        self.state.mkdir()

        from agent_orchestrator.config import Config
        cfg_file = self.tmp / 'config.json'
        import sys, json
        fake_agent = str(Path(__file__).resolve().parent / 'fake_agent.py')
        cfg_data = {
            'version': 1,
            'repo': str(self.repo),
            'state_dir': str(self.state),
            'acknowledge_local_execution': True,
            'repos': {},
            'providers': {
                'claude': {'command': [sys.executable, fake_agent]},
                'codex': {'command': [sys.executable, fake_agent]},
                'agy': {'command': [sys.executable, fake_agent]}
            },
            'tests': {}
        }
        cfg_file.write_text(json.dumps(cfg_data), encoding='utf-8')
        self.cfg = Config(cfg_file)

        from agent_orchestrator.engine import Engine
        self.engine = Engine(self.cfg)
        from agent_orchestrator.web import WebServer
        self.server = WebServer(self.engine, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.terminals.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def request(self, path, method='GET', body=None, token=True, bridge_key=None, origin=None):
        import http.client, json
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Host': self.server.authority}
        if token:
            headers['Authorization'] = f'Bearer {self.server.token}'
        if bridge_key:
            headers['X-Bridge-Key'] = bridge_key
        if origin:
            headers['Origin'] = origin
        elif method == 'POST':
            headers['Origin'] = self.server.origin
        payload = json.dumps(body).encode('utf-8') if body is not None else None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = data.decode('utf-8', 'replace')
        return res.status, parsed

    def test_conversations_api(self):
        # Unauthorized without token
        status, _ = self.request('/api/conversations', token=False)
        self.assertEqual(status, 401)

        # Empty initially
        status, data = self.request('/api/conversations')
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

        # Add conversation directly to db
        self.engine.db.conversation_add({
            'id': 'api-conv-1',
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'Hội thoại thử nghiệm',
            'session_id': 'sess-12345678',
            'transcript_path': str(self.state / 'transcripts' / 'api-conv-1.log')
        })

        status, data = self.request('/api/conversations?limit=10')
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 'api-conv-1')

        # Filter by provider
        status, data = self.request('/api/conversations?provider=codex')
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

        status, data = self.request('/api/conversations?provider=claude')
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)

        # Search q
        import urllib.parse
        status, data = self.request('/api/conversations?q=' + urllib.parse.quote('thử nghiệm'))
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)

    def test_transcript_api(self):
        cid = 'api-conv-trans'
        log_file = self.state / 'transcripts' / f'{cid}.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text('[2026-11-08T00:00:00Z] Dòng 1\n[2026-11-08T00:00:01Z] Dòng 2\n', encoding='utf-8')

        self.engine.db.conversation_add({
            'id': cid,
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'Transcript Test',
            'session_id': 'sess-12345678',
            'transcript_path': str(log_file)
        })

        status, data = self.request(f'/api/conversations/{cid}/transcript')
        self.assertEqual(status, 200)
        self.assertEqual(len(data['lines']), 2)
        self.assertEqual(data['total'], 2)
        self.assertFalse(data['has_more'])

    def _add_conv(self, cid, log_path, **extra):
        self.engine.db.conversation_add({'id': cid, 'provider': 'claude', 'kind': 'agent', 'cwd': str(self.repo),
                                         'title': 't', 'session_id': 'sess-12345678',
                                         'transcript_path': str(log_path), **extra})

    def test_delete_conversation_removes_row_and_file(self):
        root = self.state / 'transcripts'
        root.mkdir(parents=True, exist_ok=True)
        log = root / 'del-1.log'
        log.write_text('hello', encoding='utf-8')
        self._add_conv('del-1', log)
        status, _ = self.request('/api/conversations/del-1/delete', method='POST', token=False, body={})
        self.assertEqual(status, 401)
        status, _ = self.request('/api/conversations/del-1/delete', method='POST', origin='http://evil.com', body={})
        self.assertEqual(status, 403)
        self.assertTrue(log.exists())
        status, data = self.request('/api/conversations/del-1/delete', method='POST', body={})
        self.assertEqual((status, data['deleted'], data['files_removed']), (200, 1, 1))
        self.assertFalse(log.exists())
        status, _ = self.request('/api/conversations/del-1')
        self.assertEqual(status, 400)
        status, _ = self.request('/api/conversations/del-1/delete', method='POST', body={})
        self.assertEqual(status, 400)  # already gone
        audit = (self.state / 'terminal-audit.jsonl').read_text(encoding='utf-8')
        self.assertIn('"action": "delete"', audit)

    def test_delete_never_touches_files_outside_transcripts(self):
        outside = self.tmp / 'precious.txt'
        outside.write_text('keep', encoding='utf-8')
        self._add_conv('del-evil', outside)
        status, data = self.request('/api/conversations/del-evil/delete', method='POST', body={})
        self.assertEqual((status, data['files_removed']), (200, 0))
        self.assertTrue(outside.exists())

    def test_delete_refused_while_terminal_open(self):
        info = self.server.terminals.open('agent', 'claude')
        try:
            conv_id = next(iter(self.server.terminals.live_conversation_ids()))
            status, data = self.request(f'/api/conversations/{conv_id}/delete', method='POST', body={})
            self.assertEqual(status, 400)
            self.assertIn('đang mở', data['error'])
            status, data = self.request('/api/conversations/delete-all', method='POST', body={'confirm': True})
            self.assertEqual((status, data['kept_open']), (200, 1))
            self.assertEqual(self.request(f'/api/conversations/{conv_id}')[0], 200)
        finally:
            self.server.terminals.close(info['id'])

    def test_delete_all_requires_confirm(self):
        root = self.state / 'transcripts'
        root.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            log = root / f'a{i}.log'
            log.write_text('x', encoding='utf-8')
            self._add_conv(f'a{i}', log)
        self.assertEqual(self.request('/api/conversations/delete-all', method='POST', body={})[0], 400)
        self.assertEqual(self.request('/api/conversations/delete-all', method='POST', body={'confirm': 'yes'})[0], 400)
        self.assertEqual(len(self.request('/api/conversations')[1]), 3)
        status, data = self.request('/api/conversations/delete-all', method='POST', body={'confirm': True})
        self.assertEqual((status, data['deleted'], data['files_removed']), (200, 3, 3))
        self.assertEqual(self.request('/api/conversations')[1], [])

    def test_bridge_cannot_delete(self):
        for path in ('/api/bridge/conversations/x/delete', '/api/bridge/conversations/delete-all'):
            status, _ = self.request(path, method='POST', token=False, bridge_key=self.server.bridge_key, body={})
            self.assertIn(status, (401, 404))

    def test_bridge_cannot_resume(self):
        # Bridge key allows only reading or open_agent / input, never resume
        status, _ = self.request('/api/bridge/conversations/some-id/resume', method='POST',
                                 token=False, bridge_key=self.server.bridge_key, body={})
        self.assertIn(status, (401, 404))

    def test_resume_api(self):
        cid = 'api-conv-resume'
        self.engine.db.conversation_add({
            'id': cid,
            'provider': 'claude',
            'kind': 'agent',
            'cwd': str(self.repo),
            'title': 'API Resume Test',
            'session_id': 'sess-12345678',
            'transcript_path': str(self.state / 'transcripts' / 'res.log')
        })

        # Unauthorized without token
        status, _ = self.request(f'/api/conversations/{cid}/resume', method='POST', token=False, body={})
        self.assertEqual(status, 401)

        # Cross origin forbidden
        status, _ = self.request(f'/api/conversations/{cid}/resume', method='POST', origin='http://evil.com', body={})
        self.assertEqual(status, 403)

        # Mock resume_conversation
        orig_resume = self.server.terminals.resume_conversation
        try:
            self.server.terminals.resume_conversation = lambda id, cols=100, rows=30: {'id': 'claude-1', 'resumed': True}
            status, data = self.request(f'/api/conversations/{cid}/resume', method='POST', body={'cols': 80, 'rows': 24})
            self.assertEqual(status, 200)
            self.assertEqual(data.get('id'), 'claude-1')
        finally:
            self.server.terminals.resume_conversation = orig_resume




class TestAgySessionScan(unittest.TestCase):
    """agy keeps each conversation as <id>.db; the id is found from the file created after the terminal opened."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='agy-scan-'))
        self.root = self.tmp / 'conversations'
        self.root.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self, started, taken=(), **kw):
        from agent_orchestrator.terminals import scan_agy_session
        kw.setdefault('timeout', 0.3)
        kw.setdefault('interval', 0.05)
        return scan_agy_session(started, lambda: set(taken), agy_home=self.tmp, **kw)

    def test_finds_new_database_and_ignores_side_files(self):
        started = time.time()
        (self.root / 'aaaaaaaa-1111-2222-3333-444444444444.db-wal').write_text('')
        (self.root / 'bbbbbbbb-1111-2222-3333-444444444444.pb').write_text('')
        (self.root / 'cccccccc-1111-2222-3333-444444444444.db').write_text('x')
        self.assertEqual(self.scan(started), 'cccccccc-1111-2222-3333-444444444444')

    def test_ignores_databases_that_existed_before_the_terminal(self):
        (self.root / 'dddddddd-1111-2222-3333-444444444444.db').write_text('x')
        self.assertIsNone(self.scan(time.time() + 60))  # started "later" than the file was created

    def test_skips_ids_already_used_by_another_history_entry(self):
        started = time.time()
        (self.root / 'eeeeeeee-1111-2222-3333-444444444444.db').write_text('x')
        self.assertIsNone(self.scan(started, taken={'eeeeeeee-1111-2222-3333-444444444444'}))
        (self.root / 'ffffffff-1111-2222-3333-444444444444.db').write_text('x')
        self.assertEqual(self.scan(started, taken={'eeeeeeee-1111-2222-3333-444444444444'}),
                         'ffffffff-1111-2222-3333-444444444444')

    def test_earliest_created_wins_and_bad_names_are_ignored(self):
        started = time.time()
        (self.root / 'first-conversation-0001.db').write_text('x')
        time.sleep(0.05)
        (self.root / 'second-conversation-0002.db').write_text('x')
        (self.root / 'x y.db').write_text('x')  # not a valid id
        self.assertEqual(self.scan(started), 'first-conversation-0001')

    def test_waits_for_a_late_file_and_stops_when_the_terminal_closes(self):
        started = time.time()
        threading.Timer(0.2, lambda: (self.root / 'late-conversation-0003.db').write_text('x')).start()
        self.assertEqual(self.scan(started, timeout=3), 'late-conversation-0003')
        self.assertIsNone(self.scan(time.time() + 60, alive=lambda: False, timeout=5))
