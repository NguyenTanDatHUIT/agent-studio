"""Offline CLI double. Never uses real credentials or model calls."""
import json
import pathlib
import sys

prompt = sys.stdin.read()
if 'FAIL_AGENT' in prompt:
    print('simulated failure', file=sys.stderr)
    raise SystemExit(3)
if 'BAD_SCOPE' in prompt:
    pathlib.Path('outside.txt').write_text('unexpected', encoding='utf-8')
else:
    pathlib.Path('src/answer.txt').write_text('42\n', encoding='utf-8')
if '--print' in sys.argv:
    print(json.dumps({'type': 'result', 'is_error': False, 'result': 'Updated answer.',
                      'usage': {'input_tokens': 10, 'output_tokens': 4}, 'total_cost_usd': .001}))
else:
    print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Updated answer.'}}))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 4}}))
