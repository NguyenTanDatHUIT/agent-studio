"""Prompt chung (PROMPT-CHUNG.md) và quy tắc điều phối phải thật sự đến được agent:
 - dòng giao việc ĐẦU TIÊN cho cửa sổ agent mới bị công cụ chặn nếu không trỏ tới tệp chung;
 - "những điều không được bỏ" đứng đầu prompt của Agent 0;
 - khi chủ máy đổi quy tắc, Agent 0 đang chạy được báo một lần; đọc `get_orchestration_rules` thì được ghi nhận là đã nhận."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from agent_orchestrator import rules, terminals
from agent_orchestrator.config import OrchError
from agent_orchestrator.mcp import Server
from agent_orchestrator.terminals import Terminals
from tests.test_interactive_idle import MockInteractiveSession
from tests.test_terminal_signals import EchoSession
from tests.test_workflow import WorkflowBase


class CommonBase(WorkflowBase):
    def params(self):
        return rules.load(self.e.db)['params']

    def make_common(self, text='quy định chung'):
        folder = rules.prompts_dir(self.cfg, self.params())
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'PROMPT-CHUNG.md'
        path.write_text(text, encoding='utf-8')
        return path


class Settings(CommonBase):
    def test_new_params_are_validated(self):
        abs_path = str(self.root / 'x' / 'PROMPT-CHUNG.md')
        out = rules.validate({'params': {'common_prompt_file': abs_path, 'common_prompt_enforce': False}})
        self.assertEqual(out['params']['common_prompt_file'], abs_path)
        self.assertFalse(out['params']['common_prompt_enforce'])
        self.assertEqual(rules.validate({'params': {'common_prompt_file': '  '}})['params']['common_prompt_file'], '')
        for bad in ({'common_prompt_file': 'tuong-doi.md'}, {'common_prompt_file': 'a\x00b'}, {'common_prompt_file': 5},
                    {'common_prompt_enforce': 'true'}):
            with self.assertRaises(OrchError):
                rules.validate({'params': bad})

    def test_common_prompt_is_found_only_when_it_exists_and_is_enforced(self):
        self.assertIsNone(rules.common_prompt(self.cfg, self.params()), 'no file, nothing to enforce')
        path = self.make_common()
        self.assertEqual(rules.common_prompt(self.cfg, self.params()), path)
        other = self.root / 'khac.md'
        other.write_text('x', encoding='utf-8')
        self.assertEqual(rules.common_prompt(self.cfg, {**self.params(), 'common_prompt_file': str(other)}), other)
        self.assertIsNone(rules.common_prompt(self.cfg, {**self.params(), 'common_prompt_file': str(self.root / 'khong-co.md')}))
        self.assertIsNone(rules.common_prompt(self.cfg, {**self.params(), 'common_prompt_enforce': False}))

    def test_path_match_ignores_case_and_slash_direction(self):
        self.assertTrue(rules.mentions_path(r'Đọc C:\AgentControl\Prompts\prompt-chung.md rồi làm', 'C:/agentcontrol/prompts/PROMPT-CHUNG.md'))
        self.assertFalse(rules.mentions_path('Đọc PROMPT-CHUNG.md rồi làm', 'C:/a/PROMPT-CHUNG.md'), 'a bare name is not the path')


class TopBlock(CommonBase):
    def test_block_leads_the_generated_prompt_once_and_names_the_common_file(self):
        path = self.make_common()
        core = self.root / 'core.md'
        core.write_text('LOI-CORE-PROMPT\n', encoding='utf-8')
        out = rules.write_generated(self.cfg, self.e.db, core)
        text = out.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('## Những điều không được bỏ'))
        self.assertEqual(text.count('## Những điều không được bỏ'), 1)
        self.assertLess(text.index('## Những điều không được bỏ'), text.index('LOI-CORE-PROMPT'))
        self.assertIn(str(path), text.split('LOI-CORE-PROMPT')[0])
        self.assertIn('BẮT BUỘC đọc và làm theo', text)

    def test_rules_read_through_the_tool_also_start_with_the_block(self):
        self.make_common()
        markdown = rules.current(self.cfg, self.e.db)[1]
        self.assertTrue(markdown.startswith('## Những điều không được bỏ'))

    def test_without_a_common_file_the_block_has_no_first_line_demand(self):
        markdown = rules.current(self.cfg, self.e.db)[1]
        self.assertTrue(markdown.startswith('## Những điều không được bỏ'))
        self.assertNotIn('LẦN ĐẦU', markdown.split('### Ràng buộc chung')[0])
        self.assertIn('yên lặng', markdown)
        self.assertIn('HOÀN TẤT (CHƯA COMMIT)', markdown)

    def test_stored_digest_covers_the_block(self):
        before = rules.digest(rules.current(self.cfg, self.e.db)[1])
        self.make_common()
        self.assertNotEqual(before, rules.digest(rules.current(self.cfg, self.e.db)[1]))


@mock.patch.object(terminals, 'SEND_INTERVAL', 0)
class FirstLineGate(CommonBase):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db, idle_debounce=0.1)

    def window(self, n=1, **attrs):
        s = MockInteractiveSession(f'agy-{n}', provider='agy', agent=n, cwd=self.root)
        for key, value in attrs.items():
            setattr(s, key, value)
        self.t.sessions[s.id] = s
        return s

    def sent(self, s):
        return [w[0] for w in s.written if w[0] != '\r']

    def test_nothing_is_enforced_while_there_is_no_common_file(self):
        s = self.window()
        self.t.send('agy-1', 'Đọc PROMPT-A.md và làm')
        self.assertEqual(self.sent(s), ['Đọc PROMPT-A.md và làm'])

    def test_first_line_without_the_path_is_refused_with_the_exact_wording_to_use(self):
        path = self.make_common()
        s = self.window()
        with self.assertRaises(OrchError) as raised:
            self.t.send('agy-1', 'Đọc PROMPT-A.md và làm đúng theo đó')
        self.assertIn(str(path), str(raised.exception))
        self.assertIn('BẮT BUỘC đọc và làm theo', str(raised.exception))
        self.assertEqual(self.sent(s), [], 'nothing reached the terminal')
        self.assertFalse(getattr(s, 'briefed', False))

    def test_first_line_with_the_path_passes_and_later_lines_are_free(self):
        path = self.make_common()
        s = self.window()
        self.t.send('agy-1', f'BẮT BUỘC đọc và làm theo {str(path).replace("/", chr(92)).upper()} trước, rồi đọc PROMPT-A.md và làm.')
        self.assertTrue(s.briefed)
        self.t.send('agy-1', 'Sửa nhỏ: dòng 59 dùng DateTime.UtcNow, đổi sang tham số.')
        self.assertEqual(len(self.sent(s)), 2)

    def test_slash_commands_and_resumed_windows_are_not_blocked(self):
        self.make_common()
        fresh = self.window(1)
        self.t.send('agy-1', '/add-dir C:\\CongViec\\itc-git\\HIS_EMR')
        self.assertEqual(len(self.sent(fresh)), 1)
        self.assertFalse(getattr(fresh, 'briefed', False), 'a slash command does not count as the brief')
        resumed = self.window(2, resumed=True)
        self.t.send('agy-2', 'Làm tiếp việc đang dở')
        self.assertEqual(len(self.sent(resumed)), 1)

    def test_the_owner_can_switch_enforcement_off(self):
        self.make_common()
        rules.save(self.e.db, {'params': {'common_prompt_enforce': False}})
        s = self.window()
        self.t.send('agy-1', 'Đọc PROMPT-A.md và làm')
        self.assertEqual(len(self.sent(s)), 1)

    def test_an_unreadable_rules_setting_never_blocks_sending(self):
        self.make_common()
        s = self.window()
        with mock.patch.object(rules, 'load', side_effect=OrchError('hỏng')):
            self.t.send('agy-1', 'Đọc PROMPT-A.md và làm')
        self.assertEqual(len(self.sent(s)), 1)


class RulesChangedNotice(CommonBase):
    def setUp(self):
        super().setUp()
        self.t = Terminals(self.cfg, self.e.db, idle_debounce=0.1)
        self.agent0 = EchoSession()
        self.t.sessions['agent0'] = self.agent0
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()  # attach

    def digest(self):
        return rules.digest(rules.current(self.cfg, self.e.db)[1])

    def lines(self):
        return [w[0] for w in self.agent0.written if w[0] != '\r']

    def poll(self):
        self.t.last_notice_sent = 0.0
        self.t.notify_agent0()

    def test_agent0_is_told_once_when_the_owner_changes_the_rules(self):
        rules.save(self.e.db, {'params': {'max_fix_rounds': 5}})
        self.assertTrue(self.t.rules_changed(self.digest()))
        self.poll()
        (line,) = self.lines()
        self.assertIn('Quy tắc điều phối của chủ máy vừa đổi', line)
        self.assertIn('get_orchestration_rules', line)
        self.assertIn(self.digest(), line)
        self.assertFalse(self.t.rules_changed(self.digest()), 'the same version is not announced twice')
        self.poll()
        self.assertEqual(len(self.lines()), 1)

    def test_nothing_is_typed_when_agent0_already_has_that_version(self):
        self.e.db.set_setting(rules.APPLIED_KEY, self.digest())
        self.assertFalse(self.t.rules_changed(self.digest()))
        self.poll()
        self.assertEqual(self.lines(), [])

    def test_a_notice_queued_before_agent0_restarted_is_dropped_when_the_new_one_has_the_version(self):
        rules.save(self.e.db, {'params': {'max_fix_rounds': 6}})
        self.t.rules_changed(self.digest())
        self.e.db.set_setting(rules.APPLIED_KEY, self.digest())   # Agent 0 restarted with it, or called the tool
        self.poll()
        self.assertEqual(self.lines(), [])

    def test_reading_the_rules_through_mcp_marks_them_as_received(self):
        rules.save(self.e.db, {'params': {'max_fix_rounds': 7}})
        self.assertNotEqual(self.e.db.setting(rules.APPLIED_KEY, None), self.digest())
        out = Server(self.e).call('get_orchestration_rules', {})
        self.assertEqual(out['digest'], self.digest())
        self.assertEqual(self.e.db.setting(rules.APPLIED_KEY, None), self.digest())
        self.assertTrue(out['rules_markdown'].startswith('## Những điều không được bỏ'))


class RepoCopies(unittest.TestCase):
    """Hai bản chép PROMPT-CHUNG.md trong repo chỉ để lưu lịch sử; bản chuẩn nằm ngoài repo. Chúng không được lệch nhau."""

    ROOT = Path(__file__).resolve().parent.parent

    def read(self, rel):
        return (self.ROOT / rel).read_text(encoding='utf-8').replace('\r\n', '\n')

    def test_the_two_repo_copies_are_identical(self):
        self.assertEqual(self.read('docs/PROMPT-CHUNG.md'), self.read('NhatKyCongViec/promt/PROMPT-CHUNG.md'),
                         'chạy tools/Sync-PromptChung.ps1 để đồng bộ với bản chuẩn')

    def test_the_copy_states_all_three_final_line_forms(self):
        text = self.read('docs/PROMPT-CHUNG.md')
        for form in ('HOÀN TẤT: <hash commit cuối>', 'HOÀN TẤT (CHƯA COMMIT):', 'ĐANG CHỜ AGENT 0: <lý do>'):
            self.assertIn(form, text)


if __name__ == '__main__':
    unittest.main()
