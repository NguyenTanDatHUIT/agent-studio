"""Local CLI discovery and bounded, non-inference readiness checks."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .config import OrchError, command


REQUIRED = {
    'codex': ['--json', '--ephemeral', '--ignore-user-config', '--ignore-rules', '--sandbox'],
    'claude': ['--restricted', '--permission-prompts', '--strict-mcp-config', '--no-session-persistence'],
}


def discover():
    user = Path(os.environ.get('USERPROFILE') or Path.home())
    npm = Path(os.environ.get('APPDATA', str(user / 'AppData/Roaming'))) / 'npm/node_modules'
    candidates = {
        'codex': [shutil.which('codex.exe'),
                  *sorted((user / '.codex/packages/app-server-daemon/releases').glob('*/bin/codex.exe'), reverse=True),
                  npm / '@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'],
        'claude': [shutil.which('claude.exe'), user / '.local/bin/claude.exe',
                   npm / '@anthropic-ai/claude-code/bin/claude.exe'],
    }
    found = {}
    for name, paths in candidates.items():
        for path in paths:
            if path:
                try:
                    found[name] = command([str(Path(path).resolve())])
                    break
                except (OSError, ValueError, OrchError):
                    continue
        if name not in found and shutil.which('node'):
            script = npm / ('@openai/codex/bin/codex.js' if name == 'codex' else '@anthropic-ai/claude-code/cli.js')
            try:
                if script.is_file():
                    found[name] = [str(Path(shutil.which('node')).resolve()), str(script)]
            except OSError:
                pass
    return found


def probe(config, provider, check_auth=False):
    settings = config.data.get('providers', {}).get(provider, {})
    base = settings.get('command')
    result = {'configured': bool(base), 'compatible': False, 'authenticated': None}
    if not base:
        result['error'] = 'CLI not configured. Install it or set providers.' + provider + '.command.'
        return result
    env = config.environment(agent=True)
    def call(args):
        completed = subprocess.run(command(base) + args, env=env, capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', timeout=15,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return completed.returncode, completed.stdout + '\n' + completed.stderr
    try:
        code, version = call(['--version'])
        result['version'] = next((line for line in version.splitlines() if line and not line.startswith('WARNING:')), '')[:200]
        code, help_text = call(['exec', '--help'] if provider == 'codex' else ['--help'])
        result['missing_flags'] = [flag for flag in REQUIRED[provider] if flag not in help_text]
        result['compatible'] = code == 0 and not result['missing_flags']
        if check_auth and result['compatible']:
            code, status = call(['login', 'status'] if provider == 'codex' else ['auth', 'status'])
            result['authenticated'] = code == 0
            # Never return raw authentication output, which differs across CLI versions.
            if code:
                result['error'] = 'Authentication check failed. Run the CLI login/status command in your terminal.'
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result['error'] = str(exc)[:1000]
    return result
