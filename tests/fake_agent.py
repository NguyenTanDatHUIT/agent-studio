"""Offline CLI double. Never uses real credentials or model calls.

It reports a session id the way the real CLIs do (Claude: session_id in the result; Codex: thread.started),
echoes how it was invoked in its summary so tests can see resume/persistence flags, and fails on request.
"""
import json
import pathlib
import re
import sys

prompt = sys.stdin.read()
args = sys.argv[1:]
resumed = '--resume' in args or 'resume' in args
persist = '--no-session-persistence' not in args and '--ephemeral' not in args
session = 'sess-0001-' + ('resumed' if resumed else 'fresh')
# Markers are read from the current instruction only, not from the EARLIER ROUNDS summary.
instruction = prompt.split('FOLLOW-UP INSTRUCTION:')[-1]
if 'FAIL_RESUME' in instruction and resumed:
    print('No conversation found with session ID', file=sys.stderr)
    raise SystemExit(1)
if 'FAIL_AGENT' in instruction:
    print('simulated failure', file=sys.stderr)
    raise SystemExit(3)
note = f"resumed={resumed} persist={persist} history={'EARLIER ROUNDS' in prompt}"
src = pathlib.Path('src')
if 'BAD_SCOPE' in instruction:
    pathlib.Path('outside.txt').write_text('unexpected', encoding='utf-8')
elif 'NO_CHANGE' in instruction:
    pass
elif re.search(r'FILE:(\w+)', instruction):
    (src / (re.search(r'FILE:(\w+)', instruction).group(1) + '.txt')).write_text('1\n', encoding='utf-8')
else:
    (src / 'answer.txt').write_text('42\n', encoding='utf-8')
if '--print' in args:
    print(json.dumps({'type': 'result', 'is_error': False, 'result': 'Updated answer. ' + note, 'session_id': session,
                      'usage': {'input_tokens': 10, 'output_tokens': 4}, 'total_cost_usd': .001}))
else:
    print(json.dumps({'type': 'thread.started', 'thread_id': session}))
    print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Updated answer. ' + note}}))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 4}}))
