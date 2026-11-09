"""Agent 0 must follow the repo the dashboard uses, and must delegate instead of spawning agents in its own terminal."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_orchestrator.config import Config, OrchError
from agent_orchestrator.store import Store
from agent_orchestrator.terminals import AGENT0_DENIED, Terminals


class RepoSwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='repo-switch-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('AGENT_STUDIO_REPO', None)
        self.repo_a, self.repo_b, self.state = self.tmp / 'a', self.tmp / 'b', self.tmp / 'state'
        for folder in (self.repo_a, self.repo_b):
            folder.mkdir()
        fake = str(Path(__file__).resolve().parent / 'fake_agent.py')
        self.cfg_file = self.tmp / 'owner.json'
        self.cfg_file.write_text(json.dumps({
            'version': 1, 'repo': str(self.repo_a), 'state_dir': str(self.state), 'acknowledge_local_execution': True,
            'providers': {'claude': {'command': [sys.executable, fake]}}, 'tests': {}}), encoding='utf-8')

    def test_environment_override_moves_the_default_repo_without_touching_the_file(self):
        before = self.cfg_file.read_text(encoding='utf-8')
        os.environ['AGENT_STUDIO_REPO'] = str(self.repo_b)
        cfg = Config(self.cfg_file)
        self.assertEqual((cfg.repo, cfg.repos['default']), (self.repo_b.resolve(), self.repo_b.resolve()))
        self.assertEqual(self.cfg_file.read_text(encoding='utf-8'), before)
        os.environ.pop('AGENT_STUDIO_REPO')
        self.assertEqual(Config(self.cfg_file).repo, self.repo_a.resolve())

    def test_a_bad_override_is_an_error_not_a_silent_fallback(self):
        os.environ['AGENT_STUDIO_REPO'] = str(self.tmp / 'missing')
        with self.assertRaises(OrchError):
            Config(self.cfg_file)

    def test_the_override_still_obeys_the_repo_and_state_separation_rule(self):
        os.environ['AGENT_STUDIO_REPO'] = str(self.state)       # a repo inside/equal to the state dir is refused
        self.state.mkdir()
        with self.assertRaises(OrchError):
            Config(self.cfg_file)

    def agent0_args(self):
        cfg = Config(self.cfg_file)
        terms = Terminals(cfg, Store(self.state))
        argv = terms.agent0_argv(session_id='sess-12345678')
        mcp = json.loads((self.state / 'agent0-mcp.json').read_text(encoding='utf-8'))
        return cfg, terms, argv, mcp['mcpServers']['agent-orchestrator']['env']

    def test_agent0_mcp_gets_the_current_repo_and_follows_a_switch(self):
        cfg, terms, argv, env = self.agent0_args()
        self.assertEqual(env['AGENT_STUDIO_REPO'], str(self.repo_a.resolve()))
        cfg.repo = self.repo_b.resolve()                         # what POST /api/repo does in memory
        argv = terms.agent0_argv(session_id='sess-12345678')
        env = json.loads((self.state / 'agent0-mcp.json').read_text(encoding='utf-8'))['mcpServers']['agent-orchestrator']['env']
        self.assertEqual(env['AGENT_STUDIO_REPO'], str(self.repo_b.resolve()))

    def test_agent0_cannot_spawn_agents_in_its_own_terminal(self):
        _, _, argv, _ = self.agent0_args()
        denied = argv[argv.index('--disallowed-tools') + 1:]
        for tool in ('Agent', 'Task', 'Workflow', 'Bash(claude:*)', 'Bash(codex:*)', 'Bash(agy:*)'):
            self.assertIn(tool, denied)
        self.assertEqual(denied[:len(AGENT0_DENIED)], AGENT0_DENIED)
        # the orchestrator's own tools stay available and are not in the deny list
        allowed = argv[argv.index('--allowed-tools') + 1:argv.index('--disallowed-tools')]
        self.assertIn('mcp__agent-orchestrator__enqueue_task', allowed)
        self.assertFalse(any(t.startswith('mcp__') for t in denied))

    def test_prompt_tells_agent0_to_delegate_and_report_tool_errors(self):
        text = (Path(__file__).resolve().parent.parent / 'examples' / 'AGENT0-PROMPT.md').read_text(encoding='utf-8')
        self.assertIn('không tự làm thay agent', text)
        self.assertIn('nói rõ lỗi cho người dùng', text)


if __name__ == '__main__':
    unittest.main()
