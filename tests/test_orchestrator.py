from __future__ import annotations

import concurrent.futures
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_orchestrator.config import Config, OrchError, command, template
from agent_orchestrator.engine import Engine, task_lock
from agent_orchestrator.gitops import safe_relative
from agent_orchestrator.mcp import Server, serve
from agent_orchestrator.process import run
from agent_orchestrator.providers import argv, usage

PYTHON = str(Path(sys.executable).resolve())
FAKE = str(Path(__file__).with_name('fake_agent.py').resolve())


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent orch test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo with spaces'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Offline Test')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/answer.txt').write_text('0\n', encoding='utf-8')
        (self.repo / 'test_check.py').write_text(
            "from pathlib import Path\nassert Path('src/answer.txt').read_text() == '42\\n'\n", encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        self.main_head = self.git('rev-parse', 'main')
        data = template(str(self.repo), str(self.root / 'state'))
        data.update({'acknowledge_local_execution': True, 'timeout_seconds': 10})
        data['providers'] = {p: {'command': [PYTHON, FAKE], 'model': None} for p in ('claude', 'codex')}
        data['tests'] = {'unit': [PYTHON, 'test_check.py']}
        self.config_file = self.root / 'owner.json'
        self.config_file.write_text(json.dumps(data), encoding='utf-8')
        self.cfg = Config(self.config_file)
        self.e = Engine(self.cfg)

    def git(self, *args):
        env = os.environ.copy()
        # Independent fixture Git setup, with hooks/system/global config disabled.
        for k in list(env):
            if k.startswith('GIT_'):
                del env[k]
        env['GIT_CONFIG_GLOBAL'] = os.devnull
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        r = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, *args],
                           cwd=self.repo, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def add(self, provider='codex', prompt='Set the answer to 42'):
        return self.e.enqueue(provider, prompt, ['src'], ['unit'])['id']

    def completed(self, provider='codex'):
        task_id = self.add(provider)
        result = self.e.work_once(provider)
        self.assertEqual(result['status'], 'awaiting_review', result)
        return task_id


class UnitTests(unittest.TestCase):
    def test_scope_rejects_traversal_and_protected(self):
        for path in ('../src', '/tmp', 'C:/x', 'src/../x', '.', 'src\\x', '.claude/settings.json',
                     '.env.local', 'src/.env', '.github/workflows/x', 'src\nfile', 'src/./x'):
            with self.subTest(path=path), self.assertRaises(OrchError):
                safe_relative(path)
        self.assertEqual(safe_relative('src/module.py'), 'src/module.py')

    def test_command_rejects_strings_and_shims(self):
        with self.assertRaises(OrchError):
            command('echo bad')
        with self.assertRaises(OrchError):
            command(['relative.exe'])
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'tool.cmd'
            script.touch()
            with self.assertRaises(OrchError):
                command([str(script)])

    def test_usage_does_not_estimate(self):
        result = usage('codex', 'plain response, approximately 100 tokens')
        self.assertIsNone(result['input_tokens'])
        self.assertIsNone(result['cost_usd'])
        self.assertEqual(result['source'], 'unavailable')
        self.assertEqual(usage('codex', '{"type":"turn.completed"}')['source'], 'unavailable')

    def test_usage_only_terminal_not_double_count(self):
        text = '\n'.join(json.dumps(x) for x in [
            {'type': 'item.completed', 'usage': {'input_tokens': 100}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 4, 'cached_input_tokens': 7}}])
        self.assertEqual(usage('codex', text)['input_tokens'], 10)
        self.assertEqual(usage('codex', text)['cached_input_tokens'], 7)
        self.assertIsNone(usage('codex', text)['cost_usd'])

    def test_usage_partial_metrics_stay_unknown(self):
        result = usage('codex', '{"type":"turn.completed","usage":{"output_tokens":4}}')
        self.assertIsNone(result['input_tokens'])
        self.assertEqual(result['output_tokens'], 4)

    def test_claude_usage_preserves_cache_and_error(self):
        result = usage('claude', json.dumps({'type': 'result', 'is_error': True,
                                            'usage': {'input_tokens': 2, 'cache_read_input_tokens': 9},
                                            'total_cost_usd': .01}))
        self.assertEqual(result['cache_read_input_tokens'], 9)
        self.assertTrue(result['reported_error'])


class IntegrationTests(Fixture):
    def test_codex_full_flow_preserves_main_and_real_index(self):
        task_id = self.completed()
        bundle = self.e.review_bundle(task_id)
        self.assertIn('+42', bundle['diff'])
        self.assertEqual(bundle['changed_files'], ['src/answer.txt'])
        self.assertEqual(self.e.db.get(task_id)['result']['usage']['input_tokens'], 10)
        with self.assertRaises(OrchError):
            self.e.export(task_id)
        self.e.record_review(task_id, 'approve', bundle['patch_sha256'], 'Inspected diff and passing test.')
        export = self.e.export(task_id)
        self.assertTrue(Path(export['patch']).is_file())
        self.assertEqual(self.git('rev-parse', 'main'), self.main_head)
        self.assertEqual((self.repo / 'src/answer.txt').read_text(), '0\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.e.git.text(self.e.git.path(task_id), 'diff', '--cached', '--name-only'), '')

    def test_claude_full_flow(self):
        task_id = self.completed('claude')
        result = self.e.db.get(task_id)['result']
        self.assertEqual(result['usage']['cost_usd'], .001)
        args = argv(self.cfg, 'claude')
        self.assertIn('--restricted', args)
        self.assertNotIn('Bash', args[args.index('--tools')+1])
        self.assertNotIn('--dangerously-skip-permissions', args)

    def test_scope_violation_fails_before_tests(self):
        task_id = self.add(prompt='BAD_SCOPE')
        result = self.e.work_once()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Out-of-scope', result['result']['error'])
        self.assertEqual(result['result']['tests'], [])

    def test_worker_failure_is_logged(self):
        task_id = self.add(prompt='FAIL_AGENT')
        result = self.e.work_once()
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(result['result']['usage']['input_tokens'])
        self.assertTrue(self.e.db.events(task_id))

    def test_changed_after_test_invalidates_review(self):
        task_id = self.completed()
        bundle = self.e.review_bundle(task_id)
        (self.e.git.path(task_id) / 'src/answer.txt').write_text('999\n')
        with self.assertRaisesRegex(OrchError, 'changed after tests'):
            self.e.record_review(task_id, 'approve', bundle['patch_sha256'], 'reviewed')

    def test_wrong_digest_rejected(self):
        task_id = self.completed()
        with self.assertRaisesRegex(OrchError, 'digest'):
            self.e.record_review(task_id, 'approve', 'bad', 'reviewed')

    def test_cancel_queued_never_claimed(self):
        task_id = self.add()
        self.e.db.cancel(task_id)
        self.assertIsNone(self.e.work_once())
        self.assertEqual(self.e.db.get(task_id)['status'], 'cancelled')

    def test_atomic_claim_between_threads(self):
        ids = {self.add() for _ in range(8)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            claimed = list(pool.map(lambda _: self.e.db.claim(), range(12)))
        claimed = [x for x in claimed if x]
        self.assertEqual(len(set(claimed)), 8)
        self.assertEqual(set(claimed), ids)

    def test_two_real_runner_processes(self):
        ids = {self.add('claude'), self.add('codex')}
        cmd = [PYTHON, '-m', 'agent_orchestrator', '--config', str(self.config_file), 'worker', '--once']
        processes = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        outputs = [p.communicate(timeout=60) for p in processes]
        for p, output in zip(processes, outputs):
            self.assertEqual(p.returncode, 0, output)
        self.assertEqual({json.loads(o[0])['id'] for o in outputs}, ids)
        for task_id in ids:
            self.assertEqual(self.e.db.get(task_id)['status'], 'awaiting_review')

    def test_approval_export_rechecks_content(self):
        task_id = self.completed()
        digest = self.e.review_bundle(task_id)['patch_sha256']
        self.e.record_review(task_id, 'approve', digest, 'reviewed')
        (self.e.git.path(task_id) / 'src/answer.txt').write_text('43\n')
        with self.assertRaises(OrchError):
            self.e.export(task_id)

    def test_tests_may_not_change_sources(self):
        script = self.root / 'mutate.py'
        script.write_text("from pathlib import Path\nPath('src/answer.txt').write_text('mutated')\n")
        self.cfg.data['tests']['unit'] = [PYTHON, str(script)]
        self.add()
        result = self.e.work_once()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Tests modified', result['result']['error'])

    def test_test_failure_blocks_review(self):
        script = self.root / 'fail.py'
        script.write_text('raise SystemExit(8)\n')
        self.cfg.data['tests']['unit'] = [PYTHON, str(script)]
        task_id = self.add()
        result = self.e.work_once()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['result']['tests'][0]['exit_code'], 8)
        with self.assertRaises(OrchError):
            self.e.review_bundle(task_id)

    def test_disabled_by_default(self):
        self.cfg.data['acknowledge_local_execution'] = False
        task_id = self.add()
        with self.assertRaises(OrchError):
            self.e.work_once()
        self.assertEqual(self.e.db.get(task_id)['status'], 'queued')

    def test_task_lock_released_and_abandon(self):
        task_id = self.add()
        self.e.db.claim()
        with task_lock(self.cfg, task_id):
            with self.assertRaises(OrchError):
                self.e.abandon(task_id)
        self.assertEqual(self.e.abandon(task_id)['status'], 'failed')

    def test_config_and_input_guards(self):
        with self.assertRaises(OrchError):
            self.e.enqueue('codex', 'hi', ['src'], ['unknown'])
        with self.assertRaises(OrchError):
            self.e.enqueue('codex', 'hi', ['src'], [])
        with self.assertRaises(OrchError):
            self.e.git.path('../bad')
        self.cfg.data['state_dir'] = str(self.repo / 'state')
        self.config_file.write_text(json.dumps(self.cfg.data))
        with self.assertRaises(OrchError):
            Config(self.config_file)

    def test_provider_cannot_inject_bypass_flags(self):
        self.cfg.data['providers']['codex']['command'] = [PYTHON, FAKE, '--dangerously-bypass-approvals-and-sandbox']
        self.config_file.write_text(json.dumps(self.cfg.data))
        with self.assertRaisesRegex(OrchError, 'Provider command'):
            Config(self.config_file)

    def test_deleted_and_untracked_files_are_in_patch(self):
        task_id = self.add()
        task = self.e.db.get(task_id)
        path = self.e.git.prepare(task)
        (path / 'src/answer.txt').unlink()
        (path / 'src/new.txt').write_text('new content\n')
        snap = self.e.git.snapshot(task)
        self.assertEqual(set(snap['changed_files']), {'src/answer.txt', 'src/new.txt'})
        patch = self.e.git.patch(task, snap['tree'])
        self.assertIn(b'new content', patch)
        self.assertIn(b'deleted file mode', patch)

    def test_git_hooks_are_disabled(self):
        hooks = self.repo / '.git/hooks'
        marker = self.root / 'hook-fired'
        hook = hooks / 'post-checkout'
        hook.write_text('#!/bin/sh\nprintf unsafe > "' + marker.as_posix() + '"\n', encoding='utf-8')
        hook.chmod(0o755)
        task_id = self.add()
        self.e.git.prepare(self.e.db.get(task_id))
        self.assertFalse(marker.exists())

    def test_checkout_filters_rejected_before_execution(self):
        self.git('config', 'filter.demo.smudge', 'unexpected-command')
        task_id = self.add()
        with self.assertRaisesRegex(OrchError, 'filters unsupported'):
            self.e.git.prepare(self.e.db.get(task_id))
        self.assertFalse(self.e.git.path(task_id).exists())

    def test_protected_branch_move_blocks_review(self):
        task_id = self.completed()
        tree = self.git('rev-parse', 'main^{tree}')
        new_commit = self.git('commit-tree', tree, '-p', self.main_head, '-m', 'Moved main')
        self.git('update-ref', 'refs/heads/main', new_commit)
        with self.assertRaisesRegex(OrchError, 'Protected branch'):
            self.e.review_bundle(task_id)

    def test_commit_by_worker_detected(self):
        task_id = self.add()
        task = self.e.db.get(task_id)
        path = self.e.git.prepare(task)
        self.e.git.call(path, '-c', 'user.email=test@example.invalid', '-c', 'user.name=Test',
                        'commit', '--allow-empty', '-m', 'Unexpected worker commit')
        with self.assertRaisesRegex(OrchError, 'changed HEAD'):
            self.e.git.snapshot(task)


class ProcessTests(unittest.TestCase):
    def execute(self, source, timeout=3, limit=4096, cancelled=lambda: False):
        with tempfile.TemporaryDirectory(prefix='process test ') as folder:
            path = Path(folder)
            script = path / 'child.py'
            script.write_text(source, encoding='utf-8')
            return run([PYTHON, str(script)], path, os.environ.copy(), timeout, limit, path / 'logs', cancelled=cancelled)

    def test_timeout(self):
        result = self.execute('import time\ntime.sleep(30)', timeout=.2)
        self.assertEqual(result['reason'], 'timeout')

    def test_output_bound(self):
        result = self.execute("print('x'*100000)", limit=1024)
        self.assertEqual(result['reason'], 'output_limit')
        self.assertGreater(result['stdout_bytes'], 1024)

    def test_cancellation(self):
        result = self.execute('import time\ntime.sleep(30)', cancelled=lambda: True)
        self.assertEqual(result['reason'], 'cancelled')

    def test_literal_shell_characters(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            script = path / 'echo.py'
            script.write_text('import sys\nprint(sys.argv[1])')
            marker = path / 'pwned'
            value = f'hello & echo unsafe > "{marker}"'
            result = run([PYTHON, str(script), value], path, os.environ.copy(), 5, 4096, path / 'logs')
            self.assertEqual(result['exit_code'], 0)
            self.assertFalse(marker.exists())
            self.assertIn(value, (path / 'logs/stdout.log').read_text())

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object lifecycle')
    def test_job_closes_grandchild_process(self):
        # A delayed side effect must not happen after parent timeout.
        import time
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            marker = path / 'grandchild-survived'
            grandchild = path / 'grandchild.py'
            grandchild.write_text('import time\nfrom pathlib import Path\ntime.sleep(1.5)\nPath(' + repr(str(marker)) + ').touch()\n')
            parent = path / 'parent.py'
            parent.write_text('import subprocess,sys,time\nsubprocess.Popen([sys.executable,' + repr(str(grandchild)) + '])\ntime.sleep(30)\n')
            result = run([PYTHON, str(parent)], path, os.environ.copy(), .5, 4096, path / 'logs')
            self.assertEqual(result['reason'], 'timeout')
            time.sleep(2)
            self.assertFalse(marker.exists())


class MCPTests(Fixture):
    def ready(self):
        s = Server(self.e)
        init = s.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-11-25', 'clientInfo': {'name': 'test', 'version': '1'}, 'capabilities': {}}})
        self.assertEqual(init['result']['protocolVersion'], '2025-03-26')
        s.dispatch({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        return s

    def test_lifecycle_and_tools(self):
        s = Server(self.e)
        self.assertEqual(s.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['error']['code'], -32002)
        s = self.ready()
        tools = s.dispatch({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['result']['tools']
        self.assertEqual(len(tools), 17)
        self.assertFalse(any('merge' in t['name'] for t in tools))

    def test_tool_validation_and_enqueue(self):
        s = self.ready()
        bad = s.dispatch({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
            'name': 'list_tasks', 'arguments': {'limit': True}}})
        self.assertTrue(bad['result']['isError'])
        good = s.dispatch({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
            'name': 'enqueue_task', 'arguments': {'provider': 'claude', 'prompt': 'Update answer', 'allow_paths': ['src'], 'tests': ['unit']}}})
        self.assertFalse(good['result']['isError'])
        self.assertNotIn('prompt', json.loads(good['result']['content'][0]['text']))

    def test_malformed_tool_names_and_unknown_fields(self):
        s = self.ready()
        for value in (None, {}, [], 8):
            with self.subTest(value=value):
                response = s.dispatch({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': value}})
                self.assertEqual(response['error']['code'], -32602)
        response = s.dispatch({'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {
            'name': 'list_tasks', 'arguments': {'command': 'bad'}}})
        self.assertTrue(response['result']['isError'])

    def test_stdio_parse_error_and_notifications(self):
        reader = io.BytesIO(b'bad json\n{"jsonrpc":"2.0","method":"notifications/cancelled"}\n{"jsonrpc":"2.0","id":3,"method":"ping"}\n')
        writer = io.StringIO()
        serve(self.e, reader, writer)
        lines = [json.loads(x) for x in writer.getvalue().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]['error']['code'], -32700)
        self.assertEqual(lines[1]['id'], 3)

    def test_actual_stdio_process(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
        p = subprocess.run([PYTHON, '-m', 'agent_orchestrator', '--config', str(self.config_file), 'serve'],
                           input=''.join(json.dumps(m) + '\n' for m in messages), capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        output = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(output), 2)
        self.assertEqual(len(output[1]['result']['tools']), 17)


if __name__ == '__main__':
    unittest.main()
