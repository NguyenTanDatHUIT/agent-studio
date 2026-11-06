"""Disposable offline workspace for trying the dashboard without model accounts."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import Config, template
from .engine import Engine
from .web import serve_web


def serve_demo(port=8765, open_browser=False):
    with tempfile.TemporaryDirectory(prefix='agent-studio-offline-') as folder:
        root = Path(folder)
        repo = root / 'OFFLINE-DEMO'
        repo.mkdir()
        data = template(str(repo), str(root / 'state'))
        data.update({'demo': True, 'acknowledge_local_execution': True})
        data['providers'] = {p: {'command': [str(Path(sys.executable).resolve()),
                               str(Path(__file__).with_name('demo_worker.py').resolve())], 'model': None}
                             for p in ('claude', 'codex')}
        data['tests'] = {'unit': [str(Path(sys.executable).resolve()), 'test_check.py']}
        config = root / 'config.json'
        config.write_text(json.dumps(data), encoding='utf-8')
        cfg = Config(config)
        for args in [('init', '-b', 'main'), ('config', 'user.name', 'Offline Demo'),
                     ('config', 'user.email', 'offline@example.invalid')]:
            subprocess.run(['git', '-c', 'core.hooksPath=' + str(root / 'no-hooks'), *args],
                           cwd=repo, env=cfg.environment(), check=True, capture_output=True)
        (repo / 'src').mkdir()
        (repo / 'src/answer.txt').write_text('0\n', encoding='utf-8')
        (repo / 'test_check.py').write_text("from pathlib import Path\nassert Path('src/answer.txt').read_text() == '42\\n'\n", encoding='utf-8')
        for args in [('add', '.'), ('commit', '-m', 'Offline demonstration baseline')]:
            subprocess.run(['git', '-c', 'core.hooksPath=' + str(root / 'no-hooks'), *args],
                           cwd=repo, env=cfg.environment(), check=True, capture_output=True)
        engine = Engine(cfg)
        engine.enqueue('codex', '[OFFLINE DEMO] Đổi giá trị thành 42 và chạy test', ['src'], ['unit'])
        engine.work_once('codex')
        engine.enqueue('claude', '[OFFLINE DEMO] Nhiệm vụ trong hàng đợi', ['src'], ['unit'])
        print('OFFLINE DEMO: disposable data; no Claude/Codex model calls. Queue has no active runner.', flush=True)
        serve_web(engine, port, open_browser=open_browser)
