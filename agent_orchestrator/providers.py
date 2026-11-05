from __future__ import annotations

import json

from .config import OrchError, command


def argv(config, provider):
    settings = config.data.get('providers', {}).get(provider, {})
    base = command(settings.get('command', []))
    if provider == 'claude':
        args = ['--restricted', '--print', '--output-format', 'json',
                '--permission-mode', 'acceptEdits', '--permission-prompts', 'none',
                '--tools', 'Read,Edit,Write,Glob,Grep', '--strict-mcp-config',
                '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands',
                '--no-session-persistence']
    elif provider == 'codex':
        args = ['exec', '--json', '--ephemeral', '--ignore-user-config', '--ignore-rules',
                '--sandbox', 'workspace-write', '-c', 'approval_policy="never"',
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
        args += ['-']
    return base + args


def usage(provider, text):
    """Parse reported terminal events only. Missing metrics stay null, never estimates."""
    events = []
    try:
        parsed = json.loads(text)
        events = parsed if isinstance(parsed, list) else [parsed]
    except ValueError:
        for line in text.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
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
