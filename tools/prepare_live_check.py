"""Create a tiny persistent Git repo with a real failing functional test.

No CLI inference here. Use the printed config with doctor/web to run a real task.
"""
import json
import argparse
import subprocess
import sys
from pathlib import Path

from agent_orchestrator.config import Config, template
from agent_orchestrator.engine import Engine
from agent_orchestrator.readiness import discover


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enqueue', action='store_true', help='Queue a new real-model task if none is pending')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / '.local-run/live-check'
    repo = root / 'repo'
    repo.mkdir(parents=True, exist_ok=True)
    def git(*args):
        subprocess.run(['git', '-c', 'core.hooksPath=' + str(root / 'empty-hooks'), *args],
                       cwd=repo, check=True, capture_output=True)
    (root / 'empty-hooks').mkdir(exist_ok=True)
    if not (repo / '.git').exists():
        git('init', '-b', 'main')
        (repo / 'calculator.py').write_text('def add(a, b):\n    return a - b\n', encoding='utf-8')
        (repo / 'check.py').write_text('from calculator import add\nassert add(2, 3) == 5\nassert add(-1, 1) == 0\nassert add(0, 0) == 0\nprint("3 functional checks passed")\n', encoding='utf-8')
        git('add', 'calculator.py', 'check.py')
        git('-c', 'user.name=Agent Studio Validation', '-c', 'user.email=validation@example.invalid',
            'commit', '-m', 'Local live-check baseline')
    config = root / 'owner.json'
    if not config.exists():
        data = template(str(repo), str(root / 'state'))
        for name, executable in discover().items():
            data['providers'][name]['command'] = executable
        data.update(acknowledge_local_execution=True, timeout_seconds=120, agent_env_allow=['CODEX_HOME'])
        data['tests'] = {'functional': [sys.executable, '-B', '-c', "import os,runpy,sys; sys.path.insert(0,os.getcwd()); runpy.run_path('check.py',run_name='__main__')"]}
        config.write_text(json.dumps(data, indent=2), encoding='utf-8')
    engine = Engine(Config(config))
    pending = any(row['status'] in {'queued', 'running'} for row in engine.db.list())
    if not engine.db.list() or (args.enqueue and not pending):
        task = engine.enqueue('codex', 'Fix add(a,b) in calculator.py so it returns the sum. Only edit calculator.py. Do not run tests, commit, or invoke other agents.', ['calculator.py'], ['functional'])
        print('Enqueued:', task['id'])
    print('Config:', config)


if __name__ == '__main__':
    main()
