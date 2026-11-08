from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import uuid
from pathlib import Path, PurePosixPath

from .config import OrchError, inside

ID = re.compile(r'^[0-9a-f]{24}$')
PROTECTED = {'.git', '.claude', '.codex', '.github', '.mcp.json', '.gitmodules',
             '.gitattributes', '.gitignore', 'agents.md', 'claude.md'}


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or any(ord(c) < 32 for c in value):
        raise OrchError("Scope must be a plain repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {'.', '..'} for p in value.split('/')):
        raise OrchError("Absolute paths, traversal and empty-root scopes are forbidden")
    if any(p.lower() in PROTECTED or p.lower().startswith('.env') for p in path.parts):
        raise OrchError("Protected configuration/secret path")
    return path.as_posix().rstrip('/')


def in_scope(path, scopes):
    safe_relative(path)
    return any(path == s or path.startswith(s + '/') for s in scopes)


class Git:
    def __init__(self, config, repo=None):
        self.cfg = config
        self.repo = Path(repo or config.repo).resolve()
        self.exe = shutil.which('git')
        if not self.exe:
            raise OrchError("Git not found")
        self.hooks = config.state / 'empty-hooks'
        self.hooks.mkdir(exist_ok=True)
        try:
            top = Path(self.text(self.repo, 'rev-parse', '--show-toplevel')).resolve()
            if top != self.repo and not inside(self.repo, top):
                raise OrchError("repo must be inside a Git repository")
            self.git_root = top
        except OrchError:
            self.git_root = self.repo

    def call(self, cwd, *args, data=None, env=None):
        argv = [self.exe, '--no-optional-locks', '-c', f'core.hooksPath={self.hooks}',
                '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
                '-c', 'core.autocrlf=false', '-c', 'core.quotePath=false', '-c', 'core.pager=cat', *args]
        e = self.cfg.environment()
        if env:
            e.update(env)
        try:
            r = subprocess.run(argv, cwd=cwd, input=data, capture_output=True, timeout=60, env=e,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OrchError(f"Git command failed: {exc}") from exc
        if r.returncode:
            raise OrchError('Git: ' + r.stderr.decode('utf-8', 'replace')[:2000])
        return r.stdout

    def text(self, cwd, *args, **kwargs):
        return self.call(cwd, *args, **kwargs).decode('utf-8', 'strict').strip()

    def resolve_base(self):
        ref = self.cfg.data.get('base_ref', 'HEAD')
        if not isinstance(ref, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', ref) or ref.startswith('-') or '..' in ref:
            raise OrchError("Invalid base_ref")
        return self.text(self.git_root, 'rev-parse', '--verify', ref + '^{commit}')

    def protected_refs(self):
        # Detection only; linked worktrees share Git metadata, not an isolation boundary.
        return self.text(self.git_root, 'for-each-ref', '--format=%(refname) %(objectname)',
                         'refs/heads/main', 'refs/heads/master')

    def path(self, task_id):
        if not ID.fullmatch(task_id):
            raise OrchError("Invalid task id")
        path = self.cfg.state / 'worktrees' / task_id
        if not inside(path, self.cfg.state / 'worktrees') or path.is_symlink():
            raise OrchError("Unsafe worktree path")
        return path

    def prepare(self, task):
        path = self.path(task['id'])
        if path.exists():
            raise OrchError("Worktree already exists; no automatic reuse or deletion")
        keys = self.text(self.git_root, 'config', '--local', '--includes', '--name-only', '--list')
        if any(key.lower().startswith('filter.') for key in keys.splitlines()):
            # Checkout itself can execute smudge/process filters, before the worker starts.
            raise OrchError("Repository-local Git filters unsupported; use a trusted plain-byte repository")
        self.call(self.git_root, 'worktree', 'add', '-b', 'orch/' + task['id'], str(path), task['base'])
        self.verify(task)
        return path

    def verify(self, task):
        path = self.path(task['id'])
        if path.is_symlink() or not path.is_dir():
            raise OrchError("Missing or unsafe worktree")
        if Path(self.text(path, 'rev-parse', '--show-toplevel')).resolve() != path.resolve():
            raise OrchError("Worktree root changed")
        common = self.text(path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        expected = self.text(self.git_root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        if Path(common).resolve() != Path(expected).resolve():
            raise OrchError("Git common directory changed")
        if self.text(path, 'rev-parse', 'HEAD') != task['base'] or self.text(path, 'symbolic-ref', 'HEAD') != 'refs/heads/orch/' + task['id']:
            raise OrchError("Worker changed HEAD/branch; manual inspection required")
        if self.protected_refs() != task['protected_refs']:
            raise OrchError("Protected branch changed; manual inspection required")
        return path

    def snapshot(self, task):
        path = self.verify(task)
        # Reject symlinks, junctions and submodules, including ignored paths.
        count = 0
        for root, dirs, files in os.walk(path, followlinks=False):
            for name in dirs + files:
                item = Path(root) / name
                if item == path / '.git':
                    continue
                count += 1
                if count > 100000:
                    raise OrchError("Worktree exceeds 100000 entries")
                info = item.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise OrchError("Symlinks/reparse points are unsupported")
                if item.is_dir() and (item / '.git').exists():
                    raise OrchError("Nested repositories/submodules unsupported")
        index = self.cfg.state / 'runs' / ('index-' + uuid.uuid4().hex)
        env = {'GIT_INDEX_FILE': str(index)}
        try:
            self.call(path, 'read-tree', task['base'], env=env)
            tracked = self.call(path, 'ls-files', '-z', env=env).split(b'\0')
            others = self.call(path, 'ls-files', '--others', '--exclude-standard', '-z', env=env).split(b'\0')
            entries, total = [], 0
            for raw in sorted(set(tracked + others) - {b''}):
                rel = raw.decode('utf-8', 'strict')
                if any(ord(c) < 32 for c in rel) or '\\' in rel or ':' in rel:
                    raise OrchError("Unsupported filename")
                file = path / rel
                if not inside(file, path):
                    raise OrchError("File escapes worktree")
                if not file.exists():
                    entries.append(b'0 ' + b'0'*len(task['base']) + b'\t' + raw + b'\0')
                    continue
                if not file.is_file():
                    raise OrchError("Only regular files supported; no submodules")
                total += file.stat().st_size
                if file.stat().st_size > 10_000_000 or total > 50_000_000:
                    raise OrchError("Snapshot limit: 10MB/file, 50MB total")
                blob = self.text(path, 'hash-object', '-w', '--no-filters', '--stdin', data=file.read_bytes())
                # Preserve tracked executable bits on Windows. New files are regular 100644.
                mode = '100644'
                stage = self.text(path, 'ls-files', '--stage', '--', rel, env=env)
                if stage:
                    mode = stage.split(' ', 1)[0]
                elif os.name != 'nt' and file.stat().st_mode & stat.S_IXUSR:
                    mode = '100755'
                if mode not in {'100644', '100755'}:
                    raise OrchError("Unsupported Git file mode")
                entries.append(mode.encode() + b' ' + blob.encode() + b'\t' + raw + b'\0')
            self.call(path, 'update-index', '-z', '--index-info', data=b''.join(entries), env=env)
            tree = self.text(path, 'write-tree', env=env)
            changed = self.call(path, 'diff-tree', '--no-commit-id', '--name-only', '--no-renames', '-r', '-z', task['base'], tree).split(b'\0')
            names = [r.decode('utf-8') for r in changed if r]
            for name in names:
                if not in_scope(name, task['allow_paths']):
                    raise OrchError(f"Out-of-scope edit: {name}")
            return {'tree': tree, 'changed_files': names}
        finally:
            index.unlink(missing_ok=True)
            Path(str(index) + '.lock').unlink(missing_ok=True)

    def patch(self, task, tree):
        return self.call(self.path(task['id']), 'diff', '--binary', '--no-ext-diff', '--no-textconv',
                         '--no-renames', task['base'], tree, '--')
