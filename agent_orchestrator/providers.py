from __future__ import annotations

import json
import re

from .config import OrchError, command

SESSION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{7,79}$')


def argv(config, provider, persist=False, resume=None):
    """Worker command line.

    Default (persist=False): ephemeral, nothing saved, exactly as before.
    persist=True: the CLI keeps its session so a later round can continue it.
    resume=<session id>: continue that session (implies persist). Codex `exec resume` has no --sandbox
    option, so the identical policy is passed as -c sandbox_mode; if it were ignored the CLI falls back to
    its read-only default, which fails safe ("no changes") rather than widening access.
    """
    settings = config.data.get('providers', {}).get(provider, {})
    base = command(settings.get('command', []))
    if resume is not None and (not isinstance(resume, str) or not SESSION.fullmatch(resume)):
        raise OrchError("Invalid session id")
    persist = persist or resume is not None
    if provider == 'claude':
        args = ['--restricted', '--print', '--output-format', 'json',
                '--permission-mode', 'acceptEdits', '--permission-prompts', 'none',
                '--tools', 'Read,Edit,Write,Glob,Grep', '--strict-mcp-config',
                '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands']
        if not persist:
            args.append('--no-session-persistence')
        if resume:
            args += ['--resume', resume]
    elif provider == 'codex':
        args = ['exec'] + (['resume'] if resume else []) + ['-c', 'windows.sandbox="elevated"', '--json']
        if not persist:
            args.append('--ephemeral')
        args += ['--ignore-user-config', '--ignore-rules']
        args += ['-c', 'sandbox_mode="workspace-write"'] if resume else ['--sandbox', 'workspace-write']
        args += ['-c', 'approval_policy="never"',
                 '-c', 'sandbox_workspace_write.network_access=false',
                 '-c', 'sandbox_workspace_write.writable_roots=[]',
                 '-c', 'mcp_servers={}']
    else:
        raise OrchError("Unknown provider")
    model = settings.get('model')
    if model:
        if not isinstance(model, str) or model.startswith('-'):
            raise OrchError("Invalid model")
        args += ['--model', model]
    if provider == 'codex':
        args += ([resume] if resume else []) + ['-']
    return base + args


def events_of(text):
    """Every JSON event in a CLI output: one document (object or array) or JSON lines."""
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except ValueError:
        events = []
        for line in text.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events


def session_id(provider, text):
    """The CLI's own session/thread id, so the next round can resume it. None when not reported."""
    found = None
    for event in events_of(text):
        if not isinstance(event, dict):
            continue
        value = event.get('session_id') if provider == 'claude' else (
            event.get('thread_id') if event.get('type') == 'thread.started' else None)
        if isinstance(value, str) and SESSION.fullmatch(value):
            found = value
    return found


def usage(provider, text):
    """Parse reported terminal events only. Missing metrics stay null, never estimates."""
    events = events_of(text)
    terminal = next((e for e in reversed(events) if isinstance(e, dict) and
                     e.get('type') in ({'result'} if provider == 'claude' else {'turn.completed'})), None)
    raw = terminal.get('usage') if terminal else None
    def metric(key):
        val = raw.get(key) if isinstance(raw, dict) else None
        return val if type(val) in (int, float) and val >= 0 else None
    cost = terminal.get('total_cost_usd') if terminal and provider == 'claude' else None
    return {'source': 'cli_reported' if isinstance(raw, dict) else 'unavailable',
            'input_tokens': metric('input_tokens'), 'output_tokens': metric('output_tokens'),
            'cached_input_tokens': metric('cached_input_tokens'),
            'cache_read_input_tokens': metric('cache_read_input_tokens'),
            'cache_creation_input_tokens': metric('cache_creation_input_tokens'),
            'cost_usd': cost if type(cost) in (int, float) and cost >= 0 else None,
            'raw_usage': raw if isinstance(raw, dict) else None,
            'terminal_seen': terminal is not None,
            'reported_error': bool(terminal.get('is_error')) if terminal else False}


def summary(provider, text):
    try:
        data = json.loads(text)
        if provider == 'claude' and isinstance(data, dict):
            return str(data.get('result', ''))[:12000]
    except ValueError:
        pass
    messages = []
    for line in text.splitlines():
        try:
            item = json.loads(line).get('item', {})
            if item.get('type') == 'agent_message':
                messages.append(str(item.get('text', '')))
        except (ValueError, AttributeError):
            pass
    return '\n'.join(messages)[-12000:]
