"""Workflows (steps with dependencies), several repositories, and automatic notices to Agent 0."""
from __future__ import annotations

import json
import os
import subprocess
import time
import unittest

from agent_orchestrator.config import Config, OrchError
from agent_orchestrator.engine import Busy, Engine
from agent_orchestrator.mcp import Server
from agent_orchestrator.terminals import Terminals
from tests.test_orchestrator import PYTHON, Fixture


def step(key, scope, **kw):
    return {'id': key, 'prompt': f'FILE:{key}', 'allow_paths': [scope], 'tests': ['ok'], **kw}


class WorkflowBase(Fixture):
    def setUp(self):
        super().setUp()
        data = json.loads(self.config_file.read_text(encoding='utf-8'))
        data['tests']['ok'] = [PYTHON, '-c', 'pass']
        other = self.root / 'other repo'
        other.mkdir()
        self.other = other
        for args in (('init', '-b', 'main'), ('config', 'user.email', 'a@b.invalid'), ('config', 'user.name', 'T')):
            self.run_git(other, *args)
        (other / 'src').mkdir()
        (other / 'src/answer.txt').write_text('0\n', encoding='utf-8')
        self.run_git(other, 'add', '.')
        self.run_git(other, 'commit', '-m', 'base')
        data['repos'] = {'other': str(other)}
        self.config_file.write_text(json.dumps(data), encoding='utf-8')
        self.cfg = Config(self.config_file)
        self.e = Engine(self.cfg)

    def run_git(self, cwd, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        r = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, *args], cwd=cwd, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def states(self, wf):
        return {s['id']: s['status'] for s in self.e.workflow(wf['id'])['steps']}


class WorkflowFlow(WorkflowBase):
    def test_fan_out_then_join_on_the_first_agent(self):
        wf = self.e.plan([
            step('a', 'src/a.txt', provider='codex'),
            step('b', 'src/b.txt', provider='claude'),
            step('c', 'src/c.txt', same_agent_as='a', after=['a', 'b']),
        ], title='demo')
        self.assertEqual(self.states(wf), {'a': 'released', 'b': 'released', 'c': 'waiting'})
        agent_a = wf['steps'][0]['agent']
        self.assertEqual(wf['steps'][2]['agent'], agent_a)
        self.assertNotEqual(wf['steps'][1]['agent'], agent_a)
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['c'], 'waiting', 'must wait for b too')
        self.assertEqual(self.e.work_once('claude')['status'], 'awaiting_review')
        self.e.release_ready()
        self.assertEqual(self.states(wf), {'a': 'done', 'b': 'done', 'c': 'released'})
        third = self.e.workflow(wf['id'])['steps'][2]
        task = self.e.db.get(third['task_id'])
        self.assertEqual(task['round'], 2, 'the same agent continues its own worktree')
        self.assertIn('KẾT QUẢ CÁC BƯỚC TRƯỚC', task['prompt'])
        self.assertIn('src/a.txt', task['allow_paths'], 'earlier changes stay in scope for the continued round')
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.e.release_ready()
        self.assertEqual(self.e.workflow(wf['id'])['state'], 'done')
        texts = [n['text'] for n in self.e.db.notices_after(0)]
        self.assertTrue(any('hoàn tất' in t for t in texts), texts)

    def test_require_approval_waits_for_the_review(self):
        wf = self.e.plan([step('a', 'src/a.txt', provider='codex'), step('b', 'src/b.txt', provider='codex', after=['a'])], require_approval=True)
        self.e.work_once('codex')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'waiting')
        task_id = wf['steps'][0]['task_id']
        bundle = self.e.review_bundle(task_id)
        self.e.record_review(task_id, 'approve', bundle['patch_sha256'], 'looks fine')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'released')

    def test_failed_dependency_blocks_and_recovers(self):
        wf = self.e.plan([{**step('a', 'src/a.txt', provider='codex'), 'prompt': 'FAIL_AGENT'},
                          step('b', 'src/b.txt', provider='claude', after=['a'])])
        self.assertEqual(self.e.work_once('codex')['status'], 'failed')
        self.e.release_ready()
        self.assertEqual(self.states(wf), {'a': 'released', 'b': 'blocked'})
        self.assertTrue(any('bị chặn' in n['text'] for n in self.e.db.notices_after(0)))
        agent = wf['steps'][0]['agent']  # Agent 0 fixes the failed step by giving it more work
        self.e.enqueue(None, 'FILE:a', ['src/a.txt'], ['ok'], agent=agent)
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'waiting')
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'released')

    def test_busy_agent_makes_the_step_wait(self):
        first = self.e.enqueue('codex', 'FILE:x', ['src/x.txt'], ['ok'])
        wf = self.e.plan([step('a', 'src/a.txt', provider='claude'), step('b', 'src/b.txt', agent=first['agent'], after=['a'])])
        self.e.work_once('claude')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'waiting', 'agent still has queued work')
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.e.release_ready()
        self.assertEqual(self.states(wf)['b'], 'released')

    def test_cancel_workflow(self):
        wf = self.e.plan([step('a', 'src/a.txt', provider='codex'), step('b', 'src/b.txt', provider='codex', after=['a'])])
        out = self.e.cancel_workflow(wf['id'])
        self.assertEqual(out['state'], 'cancelled')
        self.assertEqual(self.states(wf), {'a': 'released', 'b': 'cancelled'})
        self.assertEqual(self.e.db.get(wf['steps'][0]['task_id'])['status'], 'cancelled')

    def test_plan_is_rejected_before_anything_is_created(self):
        bad = {
            'cycle': [step('a', 'src/a.txt', provider='codex', after=['b']), step('b', 'src/b.txt', provider='codex', after=['a'])],
            'unknown dependency': [step('a', 'src/a.txt', provider='codex', after=['zzz'])],
            'parallel scopes overlap': [step('a', 'src/a.txt', provider='codex'), step('b', 'src', provider='claude')],
            'same agent unchained': [step('a', 'src/a.txt', provider='codex'), step('b', 'src/b.txt', same_agent_as='a')],
            'two agent selectors': [step('a', 'src/a.txt', provider='codex', agent=1)],
            'no agent selector': [step('a', 'src/a.txt')],
            'unknown test': [{**step('a', 'src/a.txt', provider='codex'), 'tests': ['nope']}],
            'unknown repo': [step('a', 'src/a.txt', provider='codex', repo='nowhere')],
            'duplicate id': [step('a', 'src/a.txt', provider='codex'), step('a', 'src/b', provider='claude')],
            'unknown agent': [step('a', 'src/a.txt', agent=99)],
            'extra key': [{**step('a', 'src/a.txt', provider='codex'), 'command': 'rm -rf /'}],
            'empty': [],
        }
        for name, steps in bad.items():
            with self.subTest(name), self.assertRaises(OrchError):
                self.e.plan(steps)
        self.assertEqual(self.e.db.agent_list(), [], 'a rejected plan must not allocate agents')
        self.assertEqual(self.e.db.list(), [])
        self.assertEqual(self.e.db.wf_list(), [])

    def test_busy_agent_rejects_an_immediate_step(self):
        first = self.e.enqueue('codex', 'FILE:x', ['src/x.txt'], ['ok'])
        with self.assertRaises(Busy):
            self.e.plan([step('a', 'src/a.txt', agent=first['agent'])])

    def test_mcp_tools(self):
        server = Server(self.e)
        out = server.call('enqueue_plan', {'steps': [step('a', 'src/a.txt', provider='codex')], 'title': 't'})
        self.assertEqual(out['state'], 'running')
        self.assertEqual(server.call('list_workflows', {})[0]['id'], out['id'])
        self.assertEqual({r['name'] for r in server.call('list_repos', {})}, {'default', 'other'})
        self.assertEqual(server.call('cancel_workflow', {'workflow_id': out['id']})['state'], 'cancelled')


class Repos(WorkflowBase):
    def test_agent_is_bound_to_its_repo(self):
        task = self.e.enqueue('codex', 'Set the answer to 42', ['src'], ['ok'], repo='other')
        self.assertEqual(task['repo'], 'other')
        self.assertEqual(self.e.work_once('codex')['status'], 'awaiting_review')
        self.assertTrue((self.cfg.state / 'worktrees' / task['id'] / 'src/answer.txt').read_text().startswith('42'))
        self.assertEqual(self.git('status', '--porcelain'), '', 'the main repo is untouched')
        agent = task['agent']
        with self.assertRaisesRegex(OrchError, 'gắn với repo other'):
            self.e.enqueue(None, 'x', ['src'], ['ok'], agent=agent, repo='default')
        again = self.e.enqueue(None, 'Set the answer to 42 again', ['src'], ['ok'], agent=agent)
        self.assertEqual((again['repo'], again['round']), ('other', 2))
        self.assertEqual({a['agent']: a['repo'] for a in self.e.agents_overview()}[agent], 'other')

    def test_repo_names_come_only_from_the_owner_config(self):
        for bad in ('../x', str(self.other), 'nowhere', 5):
            with self.subTest(bad=bad), self.assertRaises(OrchError):
                self.e.enqueue('codex', 'x', ['src'], ['ok'], repo=bad)

    def test_config_rejects_bad_repos(self):
        data = json.loads(self.config_file.read_text(encoding='utf-8'))
        for repos in ({'default': str(self.other)}, {'bad name': str(self.other)}, {'x': str(self.root / 'missing')},
                      {'x': str(self.cfg.state)}, {'x': 5}, []):
            data['repos'] = repos
            self.config_file.write_text(json.dumps(data), encoding='utf-8')
            with self.subTest(repos=repos), self.assertRaises(OrchError):
                Config(self.config_file)


class FakeSession:
    alive, closed, last_input = True, False, 0

    def __init__(self):
        self.written = []

    def write(self, data, system=False):
        self.written.append((data, system))


class Notices(WorkflowBase):
    def terminals(self):
        t = Terminals(self.cfg, self.e.db)
        t.sessions['agent0'] = FakeSession()
        return t

    def test_task_outcomes_become_notices_without_worker_text(self):
        self.e.enqueue('codex', 'FAIL_AGENT with secret text', ['src'], ['ok'])
        self.e.work_once('codex')
        (text,) = [n['text'] for n in self.e.db.notices_after(0)]
        self.assertIn('failed', text)
        self.assertNotIn('secret', text)

    def test_agent0_hears_only_news_from_after_it_started(self):
        t = self.terminals()
        self.e.enqueue('codex', 'FILE:old', ['src'], ['ok'])
        self.e.work_once('codex')           # finished before Agent 0 attached
        t.notify_agent0()                   # first look: sets the cursor, sends nothing
        self.assertEqual(t.sessions['agent0'].written, [])
        self.e.enqueue('claude', 'FILE:new', ['src'], ['ok'])
        self.e.work_once('claude')
        t.last_notice_sent = 0
        t.notify_agent0()
        written = t.sessions['agent0'].written
        self.assertEqual(len(written), 2)
        self.assertTrue(written[0][0].startswith('[AO] Agent 2 (claude)'))
        self.assertNotIn('Agent 1 (codex)', written[0][0])
        self.assertEqual(written[1][0], '\r')
        self.assertTrue(all(system for _, system in written))
        t.last_notice_sent = 0
        t.notify_agent0()
        self.assertEqual(len(t.sessions['agent0'].written), 2, 'delivered once')

    def test_not_while_typing_rate_limited_and_switchable(self):
        t = self.terminals()
        t.notify_agent0()
        self.e.enqueue('codex', 'FILE:a', ['src'], ['ok'])
        self.e.work_once('codex')
        t.sessions['agent0'].last_input = time.time()
        t.notify_agent0()
        self.assertEqual(t.sessions['agent0'].written, [], 'a person is typing')
        t.sessions['agent0'].last_input = 0
        t.last_notice_sent = time.time()
        t.notify_agent0()
        self.assertEqual(t.sessions['agent0'].written, [], 'rate limited')
        self.e.db.set_setting('notify_agent0', False)
        t.last_notice_sent = 0
        t.notify_agent0()
        self.assertEqual(t.sessions['agent0'].written, [], 'switched off')
        self.e.db.set_setting('notify_agent0', True)
        t.notify_agent0()
        self.assertEqual(t.sessions['agent0'].written, [], 'what happened while off is dropped, not replayed')


if __name__ == '__main__':
    unittest.main()
