import json
import threading
import time
from unittest.mock import patch

from agent_orchestrator.config import OrchError
from agent_orchestrator.process import run
from agent_orchestrator.readiness import probe
from agent_orchestrator.runners import Runners
from tests.test_orchestrator import Fixture, PYTHON


class ReadinessTests(Fixture):
    def test_missing_and_incompatible_provider(self):
        self.cfg.data['providers']['claude']['command'] = []
        self.assertFalse(probe(self.cfg, 'claude')['configured'])
        script = self.root / 'old_cli.py'
        script.write_text("print('old-cli 1.0')\n", encoding='utf-8')
        self.cfg.data['providers']['codex']['command'] = [PYTHON, str(script)]
        report = probe(self.cfg, 'codex', True)
        self.assertFalse(report['compatible'])
        self.assertIn('--ignore-user-config', report['missing_flags'])
        self.assertIsNone(report['authenticated'])

    def test_probe_does_not_return_auth_output(self):
        script = self.root / 'cli.py'
        script.write_text("import sys\nprint('--json --ephemeral --ignore-user-config --ignore-rules --sandbox' if '--help' in sys.argv else 'PRIVATE_AUTH_VALUE')\n", encoding='utf-8')
        self.cfg.data['providers']['codex']['command'] = [PYTHON, str(script)]
        report = probe(self.cfg, 'codex', True)
        self.assertTrue(report['authenticated'])
        self.assertNotIn('PRIVATE_AUTH_VALUE', json.dumps({k: v for k, v in report.items() if k != 'version'}))

    def test_managed_runner_processes_queue_and_stops(self):
        self.cfg.data['providers']['claude']['command'] = []
        task_id = self.add()
        with patch('agent_orchestrator.runners.probe', return_value={'compatible': True}):
            runners = Runners(self.cfg).start()
        try:
            deadline = time.monotonic() + 20
            while self.e.db.get(task_id)['status'] in {'queued', 'running'} and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertEqual(self.e.db.get(task_id)['status'], 'awaiting_review')
        finally:
            runners.close()
        self.assertEqual(runners.snapshot()['codex']['status'], 'stopped')
        self.assertTrue(all(not t.is_alive() for t in runners.threads))

    def test_managed_shutdown_cancels_active_child(self):
        script = self.root / 'slow_cli.py'
        script.write_text('import time\nprint("started", flush=True)\ntime.sleep(30)\n', encoding='utf-8')
        self.cfg.data['providers'] = {'codex': {'command': [PYTHON, str(script)]}}
        task_id = self.add()
        with patch('agent_orchestrator.runners.probe', return_value={'compatible': True}):
            runners = Runners(self.cfg).start()
        try:
            deadline = time.monotonic() + 15
            log = self.cfg.state / 'runs' / task_id / 'worker/stdout.log'
            while not log.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(log.exists())
        finally:
            runners.close()
        task = self.e.db.get(task_id)
        self.assertEqual(task['status'], 'cancelled', task)
        self.assertEqual(task['result']['worker']['reason'], 'cancelled')

    def test_runner_refuses_disabled_or_incompatible_execution(self):
        self.cfg.data['acknowledge_local_execution'] = False
        with self.assertRaises(OrchError):
            Runners(self.cfg).start()
        self.cfg.data['acknowledge_local_execution'] = True
        with patch('agent_orchestrator.runners.probe', return_value={'compatible': False}):
            with self.assertRaises(OrchError):
                Runners(self.cfg).start()

    def test_log_streams_before_child_exits(self):
        script = self.root / 'stream.py'
        script.write_text('import time\nprint("live output", flush=True)\ntime.sleep(10)\n', encoding='utf-8')
        logs = self.root / 'stream-logs'
        stop = threading.Event()
        result = []
        thread = threading.Thread(target=lambda: result.append(run([PYTHON, str(script)], self.repo,
                                  self.cfg.environment(), 15, 4096, logs, cancelled=stop.is_set)))
        thread.start()
        try:
            deadline = time.monotonic() + 5
            file = logs / 'stdout.log'
            while time.monotonic() < deadline and (not file.exists() or not file.read_bytes()):
                time.sleep(.05)
            self.assertTrue(thread.is_alive())
            self.assertIn(b'live output', file.read_bytes())
        finally:
            stop.set()
            thread.join(10)
        self.assertEqual(result[0]['reason'], 'cancelled')
