from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import Config, OrchError, template
from .engine import Engine
from .mcp import serve


def parser():
    p = argparse.ArgumentParser(description='Claude/Codex worktree orchestrator. No merge/push commands.')
    p.add_argument('--config', default='orchestrator.json', help='Owner-controlled JSON outside repository')
    sub = p.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init', help='Create config; never overwrites an existing file')
    init.add_argument('--repo', required=True)
    init.add_argument('--state-dir', required=True)
    init.add_argument('--detect-providers', action='store_true', help='Discover native CLI executables')
    init.add_argument('--test-profile', action='append', default=[], metavar='NAME=JSON_ARGV')
    init.add_argument('--enable-execution', action='store_true', help='Enable trusted local execution; see SECURITY.md')
    doctor = sub.add_parser('doctor', help='Inspect configuration; probes never call a model')
    doctor.add_argument('--probe', action='store_true', help='Check installed CLI versions and required flags')
    doctor.add_argument('--check-auth', action='store_true', help='Also query login status; never return credentials')
    add = sub.add_parser('enqueue')
    add.add_argument('--provider', choices=['claude', 'codex'], help='Start a NEW numbered agent of this provider')
    add.add_argument('--agent', type=int, help='Give more work to this numbered agent (continues its task when it remembers context)')
    add.add_argument('--remember', choices=['yes', 'no'], help='Override the agent remember-context setting for this task only')
    add.add_argument('--repo', help='Name of an owner-configured repo (default: the main repo); new agents only')
    add.add_argument('--prompt-file', required=True)
    add.add_argument('--allow-path', action='append', required=True)
    add.add_argument('--test', action='append', required=True)
    sub.add_parser('list')
    worker = sub.add_parser('worker', help='Separate foreground runner; use two terminals for concurrency')
    worker.add_argument('--provider', choices=['claude', 'codex'])
    worker.add_argument('--once', action='store_true')
    worker.add_argument('--poll-seconds', type=float, default=2)
    sub.add_parser('serve', help='MCP stdio; stdout is reserved for JSON-RPC')
    web = sub.add_parser('web', help='Local web dashboard; runners remain separate processes')
    web.add_argument('--port', type=int, default=8765)
    web.add_argument('--demo', action='store_true', help='Disposable offline demo; no model calls')
    web.add_argument('--open', action='store_true', help='Open the dashboard in the default browser')
    web.add_argument('--run-workers', action='store_true', help='Run configured providers with the web server; stop together')
    for name in ('show', 'events', 'cancel', 'review', 'export', 'abandon'):
        cmd = sub.add_parser(name)
        cmd.add_argument('task_id')
    review = sub.add_parser('record-review')
    review.add_argument('task_id')
    review.add_argument('--verdict', choices=['approve', 'request_changes'], required=True)
    review.add_argument('--patch-sha256', required=True)
    review.add_argument('--notes-file', required=True)
    return p


def main(argv=None):
    # MCP uses UTF-8 even when Windows redirects stdout through a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    args = parser().parse_args(argv)
    try:
        if args.action == 'web' and args.demo:
            if args.run_workers:
                raise OrchError('--run-workers requires a real config; cannot combine with --demo')
            from .demo import serve_demo
            serve_demo(args.port, open_browser=args.open)
            return 0
        if args.action == 'init':
            target = Path(args.config).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            data = template(args.repo, args.state_dir)
            if args.detect_providers:
                from .readiness import discover
                for name, executable in discover().items():
                    data['providers'][name]['command'] = executable
            for profile in args.test_profile:
                name, separator, value = profile.partition('=')
                if not separator or not name.isidentifier():
                    raise OrchError('Test profile must be NAME=JSON_ARGV')
                from .config import command
                data['tests'][name] = command(json.loads(value))
            data['acknowledge_local_execution'] = args.enable_execution
            # Validate before writing. The config file need not exist yet.
            repo, state = Path(data['repo']), Path(data['state_dir'])
            if not repo.is_dir() or target.is_relative_to(repo) or state.is_relative_to(repo) or repo.is_relative_to(state):
                raise OrchError('Config/state must be outside the repository, and paths must be disjoint')
            with target.open('x', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            output = {'config': str(target), 'execution_enabled': args.enable_execution,
                      'providers': {p: bool(v['command']) for p, v in data['providers'].items()}}
        else:
            cfg = Config(args.config)
            engine = Engine(cfg)
            if args.action == 'serve':
                serve(engine)
                return 0
            if args.action == 'web':
                from .web import serve_web
                serve_web(engine, args.port, run_workers=args.run_workers, open_browser=args.open)
                return 0
            if args.action == 'doctor':
                output = {'repo': str(cfg.repo), 'state': str(cfg.state), 'base_commit': engine.git.resolve_base(),
                          'execution_enabled': cfg.data.get('acknowledge_local_execution') is True,
                          'providers_configured': {k: bool(v.get('command')) for k, v in cfg.data.get('providers', {}).items()},
                          'tests': list(cfg.data.get('tests', {})), 'python': sys.version,
                          'warning': 'Native execution is not a VM boundary. See SECURITY.md. No paid CLI invoked.'}
                if args.probe or args.check_auth:
                    from .readiness import probe
                    output['provider_checks'] = {p: probe(cfg, p, args.check_auth) for p in ('claude', 'codex')}
            elif args.action == 'enqueue':
                output = engine.enqueue(args.provider, Path(args.prompt_file).read_text(encoding='utf-8-sig'), args.allow_path, args.test,
                                       agent=args.agent, remember=None if args.remember is None else args.remember == 'yes', repo=args.repo)
            elif args.action == 'list':
                output = engine.db.list()
            elif args.action == 'worker':
                if not .1 <= args.poll_seconds <= 60:
                    raise OrchError('poll-seconds must be .1..60')
                while True:
                    output = engine.work_once(args.provider)
                    if output is not None:
                        print(json.dumps({'id': output['id'], 'status': output['status']}, ensure_ascii=False), flush=True)
                    if args.once:
                        return 1 if output and output['status'] == 'failed' else 0
                    if output is None:
                        time.sleep(args.poll_seconds)
            elif args.action == 'show':
                output = engine.db.get(args.task_id)
            elif args.action == 'events':
                output = engine.db.events(args.task_id)
            elif args.action == 'cancel':
                output = engine.db.cancel(args.task_id)
            elif args.action == 'review':
                output = engine.review_bundle(args.task_id, max_chars=100000)
            elif args.action == 'record-review':
                output = engine.record_review(args.task_id, args.verdict, args.patch_sha256,
                                              Path(args.notes_file).read_text(encoding='utf-8-sig'))
            elif args.action == 'export':
                output = engine.export(args.task_id)
            elif args.action == 'abandon':
                output = engine.abandon(args.task_id)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except KeyboardInterrupt:
        print('Stopped. Running task may need CLI abandon after checking process termination.', file=sys.stderr)
        return 130
    except (OrchError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
