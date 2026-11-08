from __future__ import annotations

import json
import os
from pathlib import Path


class OrchError(Exception):
    pass


def inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def command(value):
    """Only owner-configured argv; never command strings or Windows shell shims."""
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or '\x00' in x for x in value):
        raise OrchError("Command must be a nonempty array of strings")
    exe = Path(value[0])
    if not exe.is_absolute() or not exe.is_file():
        raise OrchError("Executable must be an existing absolute file path")
    if exe.suffix.lower() in {'.cmd', '.bat', '.ps1', '.sh'} or exe.stem.lower() in {
        'cmd', 'powershell', 'pwsh', 'bash', 'sh', 'wsl', 'cscript', 'wscript'}:
        raise OrchError("Shells and script shims are forbidden; use a native executable or node.exe + CLI JS")
    return value


class Config:
    def __init__(self, filename):
        self.file = Path(filename).resolve()
        try:
            self.data = json.loads(self.file.read_text(encoding='utf-8-sig'))
            self.repo = Path(self.data['repo']).resolve(strict=True)
            self.state = Path(self.data['state_dir']).resolve()
        except (OSError, ValueError, KeyError) as exc:
            raise OrchError(f"Invalid configuration: {exc}") from exc
        if not self.repo.is_dir() or inside(self.state, self.repo) or inside(self.repo, self.state):
            raise OrchError("Repository and state directory must be disjoint")
        if inside(self.file, self.repo):
            raise OrchError("Owner configuration must live outside the repository")
        # Optional extra repositories an agent may work in. Owner-declared names only; a task never supplies a path.
        extra = self.data.get('repos', {})
        if not isinstance(extra, dict) or len(extra) > 20:
            raise OrchError("repos must be an object of at most 20 name -> absolute path entries")
        self.repos = {'default': self.repo}
        for name, value in extra.items():
            if not isinstance(name, str) or not name.isidentifier() or name == 'default' or not isinstance(value, str):
                raise OrchError("Repo names must be identifiers (not 'default') with string paths")
            try:
                folder = Path(value).resolve(strict=True)
            except OSError as exc:
                raise OrchError(f"Repo {name}: {exc}") from exc
            if not folder.is_dir() or inside(self.state, folder) or inside(folder, self.state) or inside(self.file, folder):
                raise OrchError(f"Repo {name} must be a folder disjoint from the state directory and the config file")
            self.repos[name] = folder
        if self.data.get('version') != 1:
            raise OrchError("Unsupported config version")
        if not isinstance(self.data.get('providers', {}), dict) or not isinstance(self.data.get('tests', {}), dict):
            raise OrchError("providers and tests must be objects")
        names = self.data.get('agent_env_allow', [])
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.isidentifier() for n in names):
            raise OrchError("agent_env_allow must contain environment variable names")
        if type(self.data.get('acknowledge_local_execution', False)) is not bool:
            raise OrchError("acknowledge_local_execution must be a boolean")
        self.timeout = self.data.get('timeout_seconds', 900)
        self.output_limit = self.data.get('output_limit_bytes', 8_000_000)
        if type(self.timeout) is not int or not 1 <= self.timeout <= 86400:
            raise OrchError("timeout_seconds must be 1..86400")
        if type(self.output_limit) is not int or not 1024 <= self.output_limit <= 100_000_000:
            raise OrchError("output_limit_bytes must be 1024..100000000")
        for provider in self.data.get('providers', {}).values():
            if not isinstance(provider, dict):
                raise OrchError("Provider must be an object")
            if provider.get('command'):
                command(provider['command'])
                entry = provider['command']
                # Keep the owner-provided prefix to an executable or interpreter + script.
                # Runtime flags are always supplied by our adapter, never by a task.
                if len(entry) > 2 or (len(entry) == 2 and
                    (not Path(entry[1]).is_absolute() or not Path(entry[1]).is_file() or Path(entry[1]).suffix.lower() not in {'.js', '.py'})):
                    raise OrchError("Provider command must be executable alone or interpreter + absolute .js/.py entrypoint")
            if set(provider) - {'command', 'model'}:
                raise OrchError("Provider supports only command and model; no arbitrary extra flags")
        for name, argv in self.data.get('tests', {}).items():
            if not name.isidentifier():
                raise OrchError("Test names must be identifiers")
            command(argv)
        for folder in ('worktrees', 'runs', 'exports', 'empty-hooks'):
            if not inside(self.state / folder, self.state):
                raise OrchError("State subdirectory escapes state root")
        self.state.mkdir(parents=True, exist_ok=True)
        for name in ('worktrees', 'runs', 'exports'):
            (self.state / name).mkdir(exist_ok=True)

    def environment(self, agent=False):
        # No inherited GIT_*, PYTHONPATH, NODE_OPTIONS or unrelated API credentials.
        names = {'PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
                 'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'LANG', 'LC_ALL',
                 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'SYSTEMDRIVE'}
        if agent:
            names |= set(self.data.get('agent_env_allow', []))
        env = {k: v for k, v in os.environ.items() if k.upper() in {n.upper() for n in names}}
        env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': os.devnull, 'PYTHONUTF8': '1',
                    'PYTHONDONTWRITEBYTECODE': '1'})
        return env

    def execution_allowed(self):
        if self.data.get('acknowledge_local_execution') is not True:
            raise OrchError("Execution disabled. Owner must set acknowledge_local_execution=true; read SECURITY.md")


def template(repo: str, state: str):
    return {'version': 1, 'repo': str(Path(repo).resolve()),
            'state_dir': str(Path(state).resolve()), 'base_ref': 'HEAD',
            'acknowledge_local_execution': False, 'timeout_seconds': 900,
            'output_limit_bytes': 8_000_000, 'agent_env_allow': [],
            'providers': {'claude': {'command': [], 'model': None},
                          'codex': {'command': [], 'model': None},
                          'agy': {'command': [], 'model': None}}, 'tests': {}}
