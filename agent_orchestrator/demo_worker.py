"""Offline demonstration process. Does not import or invoke a model CLI."""
import json
import sys
from pathlib import Path

prompt = sys.stdin.read()
Path('src/answer.txt').write_text('42\n', encoding='utf-8')
print(json.dumps({'type': 'result', 'result': 'OFFLINE DEMO: set answer to 42; no model was called.'}
                 if '--print' in sys.argv else {'type': 'turn.completed'}))
