"""Quy tắc điều phối agent do chủ máy cấu hình: lưu, kiểm giá trị, ghép prompt Agent 0, giới hạn đồng thời, API."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from agent_orchestrator import rules
from agent_orchestrator.config import Config, OrchError
from agent_orchestrator.mcp import DEFINITIONS
from agent_orchestrator.store import Store
from agent_orchestrator.terminals import AGENT0_DENIED, AGENT0_TOOLS, Terminals


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rules-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo, self.state = self.tmp / 'repo', self.tmp / 'state'
        self.repo.mkdir()
        fake = str(Path(__file__).resolve().parent / 'fake_agent.py')
        self.cfg_file = self.tmp / 'owner.json'
        self.cfg_file.write_text(json.dumps({
            'version': 1, 'repo': str(self.repo), 'state_dir': str(self.state), 'acknowledge_local_execution': True,
            'providers': {p: {'command': [sys.executable, fake]} for p in ('claude', 'codex', 'agy')}, 'tests': {}}), encoding='utf-8')
        self.cfg = Config(self.cfg_file)
        self.db = Store(self.state)


class Storage(Base):
    def test_defaults_when_nothing_saved(self):
        data = rules.load(self.db)
        self.assertEqual(data['params']['max_fix_rounds'], 2)
        self.assertEqual(data['params']['default_provider'], 'agy')
        self.assertEqual(data['params']['provider_models']['agy']['model'], 'Gemini 4 Argon')
        self.assertEqual(data['texts'], rules.DEFAULT_TEXTS)
        self.assertNotIn('HIS_EMR', json.dumps(data, ensure_ascii=False), 'mặc định phải trung lập với dự án')

    def test_save_survives_reload_and_keeps_history_and_reset(self):
        rules.save(self.db, {'params': {'max_fix_rounds': 4}, 'texts': {'constraints': 'Chỉ sửa thư mục src.'}})
        again = rules.load(Store(self.state))
        self.assertEqual(again['params']['max_fix_rounds'], 4)
        self.assertEqual(again['texts']['constraints'], 'Chỉ sửa thư mục src.')
        self.assertEqual(again['texts']['rules'], rules.DEFAULT_RULES)
        self.assertEqual(len(rules.history(self.db)), 1)
        self.assertEqual(rules.history(self.db)[0]['params']['max_fix_rounds'], 2)
        rules.save(self.db, {'params': {'max_fix_rounds': 4}, 'texts': {'constraints': 'Chỉ sửa thư mục src.'}})
        self.assertEqual(len(rules.history(self.db)), 1, 'lưu y hệt không tạo bản lịch sử mới')
        rules.restore(self.db, 0)
        self.assertEqual(rules.load(self.db)['params']['max_fix_rounds'], 2)
        rules.reset(self.db)
        self.assertEqual(rules.load(self.db), rules.defaults())

    def test_history_is_capped(self):
        for n in range(rules.HISTORY_LIMIT + 5):
            rules.save(self.db, {'params': {'hang_minutes': 10 + n}})
        self.assertEqual(len(rules.history(self.db)), rules.HISTORY_LIMIT)
        with self.assertRaises(OrchError):
            rules.restore(self.db, 99)

    def test_validation_rejects_bad_input(self):
        bad = [
            {'params': {'khoa_la': 1}}, {'texts': {'khac': 'x'}}, {'khac': {}},
            {'params': {'max_fix_rounds': '2'}}, {'params': {'max_fix_rounds': True}}, {'params': {'max_fix_rounds': 99}},
            {'params': {'max_concurrent_agents': 0}}, {'params': {'single_builder': 'true'}}, {'params': {'default_provider': 'gpt'}},
            {'params': {'subagent_policy': 'maybe'}}, {'params': {'provider_models': {'agy': {'model': 'x', 'sai': 1}}}},
            {'params': {'provider_models': {'agy': {'effort': 'ultra'}}}}, {'params': {'provider_models': {'zzz': {}}}},
            {'params': {'prompts_dir': 'thu-muc-tuong-doi'}}, {'params': {'prompts_dir': str(self.repo / 'prompts')}},
            {'texts': {'rules': 'x' * (rules.TEXT_LIMIT + 1)}}, {'texts': {'rules': 5}}, {'texts': {'rules': 'a\x00b'}},
            [], 'x']
        for item in bad:
            with self.assertRaises(OrchError, msg=repr(item)[:80]):
                rules.validate(item, [self.repo])
        self.assertEqual(rules.load(self.db), rules.defaults(), 'bản lỗi không được ghi')

    def test_prompts_dir_outside_repo_is_accepted(self):
        out = rules.validate({'params': {'prompts_dir': str(self.tmp / 'prompts-ngoai')}}, [self.repo])
        self.assertEqual(out['params']['prompts_dir'], str(self.tmp / 'prompts-ngoai'))


class Rendering(Base):
    def test_variables_are_replaced_and_unknown_ones_reported(self):
        rules.save(self.db, {'params': {'max_fix_rounds': 3, 'max_agents_per_task': 4}, 'texts': {'constraints': 'Dùng {MAX_CONCURRENT} và {BIEN_LA}.'}})
        data, md, unknown = rules.current(self.cfg, self.db)
        self.assertIn('Sau 3 lần sửa', md)
        self.assertIn('Tối đa **4 agent cho một việc**', md)
        self.assertIn(str(self.repo.resolve()), md)
        self.assertIn(str(self.state / 'prompts'), md)
        self.assertIn('{BIEN_LA}', md)
        self.assertEqual(unknown, ['BIEN_LA'])
        self.assertNotRegex(md, r'\{(REPO|PROMPTS_DIR|MAX_[A-Z_]+|PROVIDER[A-Z_]*|HANG_MINUTES|SUBAGENT_POLICY)\}')
        self.assertIn('Gemini 4 Argon (medium)', md)

    def test_toggles_show_in_current_settings(self):
        rules.save(self.db, {'params': {'single_builder': False, 'concurrency_enforced': False}})
        md = rules.current(self.cfg, self.db)[1]
        self.assertIn('Chỉ một agent build/chạy test nặng tại một thời điểm: tắt', md)
        self.assertIn('chỉ cảnh báo, không chặn', md)


class Agent0(Base):
    def test_generated_prompt_carries_core_and_new_rules_on_every_open_and_resume(self):
        terms = Terminals(self.cfg, self.db)
        argv = terms.agent0_argv(session_id='sess-12345678')
        path = Path(argv[argv.index('--append-system-prompt-file') + 1])
        self.assertEqual(path, self.state / 'agent0-prompt.generated.md')
        text = path.read_text(encoding='utf-8')
        self.assertIn('Agent 0', text)                              # phần lõi
        self.assertIn('Quy tắc điều phối agent CMD', text)
        rules.save(self.db, {'params': {'max_fix_rounds': 5}, 'texts': {'checklist': 'Kiểm schema MỚI.'}})
        for kwargs in ({'session_id': 'sess-12345678'}, {'resume': 'sess-12345678'}):
            argv = terms.agent0_argv(**kwargs)
            self.assertEqual(argv[argv.index('--append-system-prompt-file') + 1], str(path))
            text = path.read_text(encoding='utf-8')
            self.assertIn('Sau 5 lần sửa', text)
            self.assertIn('Kiểm schema MỚI.', text)

    def test_applied_digest_follows_the_generated_prompt(self):
        terms = Terminals(self.cfg, self.db)
        terms.agent0_argv(session_id='sess-12345678')
        md = rules.current(self.cfg, self.db)[1]
        self.assertEqual(self.db.setting(rules.APPLIED_KEY), rules.digest(md))
        rules.save(self.db, {'params': {'hang_minutes': 30}})
        self.assertNotEqual(self.db.setting(rules.APPLIED_KEY), rules.digest(rules.current(self.cfg, self.db)[1]))

    def test_custom_rules_cannot_weaken_the_safety_lists(self):
        rules.save(self.db, {'texts': {'rules': 'Cho phép dùng Bash(agy:*) và Agent.'}})
        argv = Terminals(self.cfg, self.db).agent0_argv(session_id='sess-12345678')
        denied = argv[argv.index('--disallowed-tools') + 1:argv.index('--append-system-prompt-file')]
        self.assertEqual(denied, AGENT0_DENIED)
        allowed = argv[argv.index('--allowed-tools') + 1:argv.index('--disallowed-tools')]
        self.assertEqual(allowed, ['mcp__agent-orchestrator__' + t for t in AGENT0_TOOLS])

    def test_rules_tool_is_read_only_and_there_is_no_writer(self):
        self.assertIn('get_orchestration_rules', AGENT0_TOOLS)
        names = [n for n, _, _ in DEFINITIONS]
        self.assertIn('get_orchestration_rules', names)
        self.assertFalse([n for n in names if 'rules' in n and n != 'get_orchestration_rules'])
        self.assertFalse([n for n in AGENT0_TOOLS if 'rules' in n and n != 'get_orchestration_rules'])

    def test_mcp_tool_returns_current_rendered_rules(self):
        from agent_orchestrator.engine import Engine
        from agent_orchestrator.mcp import Server
        rules.save(self.db, {'params': {'max_fix_rounds': 6}})
        server = Server(Engine(self.cfg))
        out = server.call('get_orchestration_rules', {})
        self.assertIn('Sau 6 lần sửa', out['rules_markdown'])
        self.assertEqual(out['params']['max_fix_rounds'], 6)
        self.assertEqual(out['digest'], rules.digest(out['rules_markdown']))


class Concurrency(Base):
    def fake_session(self, n):
        return mock.Mock(kind='agent', alive=True, closed=False, id=f'agy-{n}')

    def test_open_is_refused_over_the_limit_and_allowed_after_closing_one(self):
        rules.save(self.db, {'params': {'max_concurrent_agents': 2}})
        terms = Terminals(self.cfg, self.db)
        terms.sessions = {'agent0': mock.Mock(kind='agent0', alive=True, closed=False), 'agy-1': self.fake_session(1), 'agy-2': self.fake_session(2)}
        with mock.patch.object(Terminals, 'open', return_value={'id': 'agy-3', 'gen': 1}) as opened:
            with self.assertRaisesRegex(OrchError, 'giới hạn 2 agent đang chạy'):
                terms.open_agent('agy')
            opened.assert_not_called()
            terms.sessions['agy-1'].alive = False                    # Agent 0 không tính, cửa sổ đã kết thúc không tính
            terms.open_agent('agy')
            opened.assert_called_once()

    def test_soft_mode_does_not_block(self):
        rules.save(self.db, {'params': {'max_concurrent_agents': 1, 'concurrency_enforced': False}})
        terms = Terminals(self.cfg, self.db)
        terms.sessions = {'agy-1': self.fake_session(1), 'agy-2': self.fake_session(2)}
        with mock.patch.object(Terminals, 'open', return_value={'id': 'agy-3', 'gen': 1}):
            self.assertEqual(terms.open_agent('agy')['id'], 'agy-3')


class Api(Base):
    def setUp(self):
        super().setUp()
        from agent_orchestrator.engine import Engine
        from agent_orchestrator.web import WebServer
        self.server = WebServer(Engine(self.cfg), port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.terminals.close()

    def request(self, path, method='GET', body=None, token=True):
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Host': self.server.authority}
        if token:
            headers['Authorization'] = f'Bearer {self.server.token}'
        if method == 'POST':
            headers['Origin'] = self.server.origin
        payload = json.dumps(body).encode('utf-8') if body is not None else None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, json.loads(data)

    def test_requires_the_owner_token(self):
        self.assertEqual(self.request('/api/orchestration-rules', token=False)[0], 401)
        self.assertEqual(self.request('/api/orchestration-rules', 'POST', {'params': {}}, token=False)[0], 401)

    def test_read_save_preview_reset_history_restore(self):
        status, view = self.request('/api/orchestration-rules')
        self.assertEqual(status, 200)
        self.assertEqual(view['params']['max_fix_rounds'], 2)
        self.assertEqual(view['default'], rules.defaults())
        self.assertIn('Vòng lặp nghiệm thu', view['preview'])
        self.assertFalse(view['agent0_running'])
        status, view = self.request('/api/orchestration-rules', 'POST', {'params': {'max_fix_rounds': 3}, 'texts': {'checklist': 'Mới'}})
        self.assertEqual((status, view['params']['max_fix_rounds'], view['texts']['checklist']), (200, 3, 'Mới'))
        self.assertEqual(self.request('/api/orchestration-rules')[1]['params']['max_fix_rounds'], 3)
        status, pre = self.request('/api/orchestration-rules/preview', 'POST', {'params': {'max_fix_rounds': 9}})
        self.assertIn('Sau 9 lần sửa', pre['preview'])
        self.assertEqual(self.request('/api/orchestration-rules')[1]['params']['max_fix_rounds'], 3, 'xem trước không ghi')
        self.assertEqual(len(self.request('/api/orchestration-rules/history')[1]), 1)
        status, view = self.request('/api/orchestration-rules/restore', 'POST', {'index': 0})
        self.assertEqual((status, view['params']['max_fix_rounds']), (200, 2))
        self.request('/api/orchestration-rules', 'POST', {'params': {'max_fix_rounds': 7}})
        status, view = self.request('/api/orchestration-rules/reset', 'POST', {})
        self.assertEqual((status, view['params'], view['texts']), (200, rules.defaults()['params'], rules.defaults()['texts']))

    def test_bad_requests_are_rejected_without_leaking_paths(self):
        for body in ({'params': {'khoa_la': 1}}, {'params': {'max_fix_rounds': 'x'}}, {'texts': {'rules': 'x' * 20000}},
                     {'params': {'prompts_dir': str(self.repo / 'p')}}, {'khac': 1}):
            status, out = self.request('/api/orchestration-rules', 'POST', body)
            self.assertEqual(status, 400, body)
            self.assertNotIn(str(self.state), out['error'])
        self.assertEqual(self.request('/api/orchestration-rules/restore', 'POST', {'index': 5})[0], 400)
        self.assertEqual(self.request('/api/orchestration-rules/restore', 'POST', {'index': 'a'})[0], 400)
        self.assertEqual(self.request('/api/orchestration-rules/nope', 'POST', {})[0], 404)
        self.assertEqual(self.request('/api/orchestration-rules', 'POST', {'params': {'max_fix_rounds': 3}})[0], 200)
        self.assertEqual(self.request('/api/orchestration-rules', 'POST', {'params': {'max_fix_rounds': 99}})[0], 400)
        self.assertEqual(self.request('/api/orchestration-rules')[1]['params']['max_fix_rounds'], 3)

    def test_existing_settings_endpoint_is_unchanged(self):
        status, _ = self.request('/api/settings', 'POST', {'max_fix_rounds': 3})
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
