"""Kiểm thử thư viện vai trò chuyên môn & mẫu bàn giao chuẩn (agent_orchestrator.roles) ở Mức 2."""
from __future__ import annotations

import http.client
import json
import threading
import unittest
from pathlib import Path

from agent_orchestrator import cli, roles, rules
from agent_orchestrator.config import OrchError
from agent_orchestrator.engine import Engine
from agent_orchestrator.mcp import Server
from agent_orchestrator.terminals import Terminals
from agent_orchestrator.web import WebServer
from tests.test_orchestrator import Fixture


class RoleCatalogTests(unittest.TestCase):
    def test_catalog_integrity_and_project_neutrality(self):
        self.assertEqual(len(roles.ROLES), 7)
        self.assertEqual(len(roles.TEMPLATES), 3)
        choices = roles.role_choices()
        self.assertEqual(len(choices), 7)
        # /api/config must never include the substring 'command' (security guard in test_web.py).
        self.assertNotIn('command', json.dumps(choices, ensure_ascii=False).lower())
        catalog = roles.catalog_with_content()
        self.assertEqual(len(catalog), 11)  # INDEX + 7 roles + 3 templates
        for item in catalog:
            self.assertTrue(item['content'].startswith('# '), item['slug'])
            self.assertLess(len(item['content']), 4000, f"{item['slug']} phải tinh gọn để tiết kiệm ngữ cảnh")
            self.assertNotIn('HIS_EMR', item['content'], 'nội dung phải trung lập dự án')

    def test_validate_and_path_safety(self):
        self.assertIsNone(roles.validate_role(None))
        self.assertIsNone(roles.validate_role(''))
        self.assertEqual(roles.validate_role('minimal-change'), 'minimal-change')
        for bad in ('unknown-role', '../INDEX', 123, ['minimal-change']):
            with self.assertRaises(OrchError):
                roles.validate_role(bad)
        with self.assertRaises(OrchError):
            roles.read_item('../../pyproject.toml')

    def test_sync_to_dir_is_idempotent_and_preserves_owner_files(self):
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix='roles-sync-'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        custom = tmp / 'coding' / 'my-custom-role.md'
        custom.parent.mkdir(parents=True, exist_ok=True)
        custom.write_text('# Vai trò riêng của chủ máy\n', encoding='utf-8')

        dest, written1 = roles.sync_to_dir(tmp)
        self.assertEqual(dest, tmp)
        self.assertEqual(len(written1), 11)
        self.assertTrue((tmp / 'INDEX.md').is_file())
        self.assertTrue((tmp / 'coding' / 'backend-architect.md').is_file())
        self.assertTrue((tmp / 'review' / 'reality-checker.md').is_file())
        self.assertTrue((tmp / 'templates' / 'escalation-handoff.md').is_file())
        self.assertTrue(custom.is_file(), 'không được xoá tệp riêng của chủ máy')

        _, written2 = roles.sync_to_dir(tmp)
        self.assertEqual(written2, [], 'nội dung không đổi thì không ghi đè lại')


class RoleIntegrationTests(Fixture):
    def test_write_generated_syncs_roles_when_enabled(self):
        terms = Terminals(self.cfg, self.e.db)
        terms.agent0_argv(session_id='sess-roles-1')
        rdir = self.cfg.state / 'prompts' / 'roles'
        self.assertTrue((rdir / 'INDEX.md').is_file())
        self.assertTrue((rdir / 'coding' / 'minimal-change.md').is_file())
        gen_text = (self.cfg.state / 'agent0-prompt.generated.md').read_text(encoding='utf-8')
        self.assertIn('### Thư viện vai trò & mẫu chuẩn', gen_text)
        self.assertIn(str(rdir), gen_text)

        # Tắt roles_enabled: không chèn mục thư viện vai trò vào prompt sinh ra
        shutil_dir = self.root / 'custom-prompts'
        rules.save(self.e.db, {'params': {'roles_enabled': False, 'prompts_dir': str(shutil_dir)}}, [self.repo])
        terms.agent0_argv(session_id='sess-roles-2')
        gen_off = (self.cfg.state / 'agent0-prompt.generated.md').read_text(encoding='utf-8')
        self.assertNotIn('### Thư viện vai trò & mẫu chuẩn', gen_off)
        self.assertFalse((shutil_dir / 'roles' / 'INDEX.md').exists())

    def test_queue_worker_role_injection_and_continuation(self):
        t1 = self.e.enqueue('codex', 'Set the answer to 42', ['src'], ['unit'], role='backend-architect')
        self.assertEqual(t1['role'], 'backend-architect')
        wp1 = Engine.worker_prompt(t1, False)
        self.assertIn('VAI TRÒ CHUYÊN MÔN (Kiến trúc & Dịch vụ Backend · `backend-architect`', wp1)
        self.assertLess(wp1.index('VAI TRÒ CHUYÊN MÔN'), wp1.index('TASK:\nSet the answer to 42'))

        done = self.e.work_once('codex')
        self.assertEqual(done['status'], 'awaiting_review')

        # Vòng 2 không truyền role -> giữ nguyên role của vòng 1
        t2 = self.e.enqueue(None, 'Keep answer at 42', ['src'], ['unit'], agent=t1['agent'])
        self.assertEqual(t2['round'], 2)
        self.assertEqual(t2['role'], 'backend-architect')
        self.assertIn('`backend-architect`', Engine.worker_prompt(t2, True))

        self.e.work_once('codex')
        # Vòng 3 đổi sang role khác -> cập nhật sang role mới
        t3 = self.e.enqueue(None, 'Verify minimal diff', ['src'], ['unit'], agent=t1['agent'], role='minimal-change')
        self.assertEqual(t3['round'], 3)
        self.assertEqual(t3['role'], 'minimal-change')
        self.assertIn('`minimal-change`', Engine.worker_prompt(t3, True))

        with self.assertRaises(OrchError):
            self.e.enqueue('codex', 'Bad role', ['src'], ['unit'], role='khong-ton-tai')

    def test_workflow_plan_step_roles(self):
        with self.assertRaises(OrchError):
            self.e.plan([{'id': 's1', 'provider': 'codex', 'role': 'sai-ten', 'prompt': 'Set 42', 'allow_paths': ['src'], 'tests': ['unit']}])

        wf = self.e.plan([
            {'id': 'code', 'provider': 'codex', 'role': 'minimal-change', 'prompt': 'Set the answer to 42', 'allow_paths': ['src'], 'tests': ['unit']},
            {'id': 'check', 'same_agent_as': 'code', 'after': ['code'], 'role': 'reality-checker', 'prompt': 'Verify 42', 'allow_paths': ['src'], 'tests': ['unit']},
        ], title='Role workflow')
        steps = {s['id']: s for s in wf['steps']}
        self.assertEqual(steps['code']['role'], 'minimal-change')
        self.assertEqual(steps['check']['role'], 'reality-checker')
        released_task = self.e.db.get(steps['code']['task_id'])
        self.assertEqual(released_task['role'], 'minimal-change')

    def test_mcp_cli_and_web_support_roles(self):
        # MCP
        mcp_srv = Server(self.e)
        out_rules = mcp_srv.call('get_orchestration_rules', {})
        self.assertEqual(len(out_rules['roles']), 7)
        self.assertTrue(out_rules['roles_dir'].endswith('roles'))
        t_mcp = mcp_srv.call('enqueue_task', {
            'provider': 'claude', 'role': 'security-auditor',
            'prompt': 'Audit src', 'allow_paths': ['src'], 'tests': ['unit'],
        })
        self.assertEqual(t_mcp['role'], 'security-auditor')

        # CLI
        import contextlib
        import io
        pfile = self.root / 'prompt.txt'
        pfile.write_text('CLI role task', encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.main([
                '--config', str(self.config_file), 'enqueue',
                '--provider', 'codex', '--role', 'frontend-ui',
                '--prompt-file', str(pfile), '--allow-path', 'src', '--test', 'unit',
            ])
        self.assertEqual(rc, 0)
        latest = self.e.db.get(self.e.db.list(limit=5)[0]['id'])
        self.assertEqual(latest['role'], 'frontend-ui')

        # Web API
        web_srv = WebServer(self.e, 0)
        th = threading.Thread(target=web_srv.serve_forever, daemon=True)
        th.start()
        try:
            def req(path, body=None):
                conn = http.client.HTTPConnection('127.0.0.1', web_srv.server_port, timeout=15)
                headers = {'Host': web_srv.authority, 'Authorization': 'Bearer ' + web_srv.token}
                if body is not None:
                    headers.update({'Origin': web_srv.origin, 'Content-Type': 'application/json'})
                conn.request('GET' if body is None else 'POST', path,
                             None if body is None else json.dumps(body).encode('utf-8'), headers)
                res = conn.getresponse()
                raw = res.read()
                conn.close()
                return res.status, json.loads(raw)

            st, cfg = req('/api/config')
            self.assertEqual(st, 200)
            self.assertEqual(len(cfg['roles']), 7)
            self.assertNotIn('command', json.dumps(cfg))

            st, created = req('/api/tasks', {
                'provider': 'codex', 'role': 'database-optimizer',
                'prompt': 'Optimize query', 'allow_paths': ['src'], 'tests': ['unit'],
            })
            self.assertEqual(st, 201)
            self.assertEqual(created['role'], 'database-optimizer')

            st, bad = req('/api/tasks', {
                'provider': 'codex', 'role': 'khong-hop-le',
                'prompt': 'Optimize query', 'allow_paths': ['src'], 'tests': ['unit'],
            })
            self.assertEqual(st, 400)

            st, rview = req('/api/orchestration-rules')
            self.assertEqual(st, 200)
            self.assertEqual(len(rview['roles']), 11)
            self.assertTrue((Path(rview['roles_dir']) / 'INDEX.md').is_file())
        finally:
            web_srv.shutdown()
            web_srv.server_close()
            web_srv.terminals.close()
            th.join(5)


if __name__ == '__main__':
    unittest.main()
