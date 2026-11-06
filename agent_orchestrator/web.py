"""Authenticated loopback dashboard, backed by the same Engine as CLI/MCP."""
from __future__ import annotations

import base64
import hmac
import json
import os
import time
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .config import OrchError, inside
from .terminals import TERMINAL_AGENTS, Terminals
from .engine import task_lock
from .gitops import ID

ASSETS = Path(__file__).with_name('web_assets')


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def agent0_status(state_dir):
    try:
        data = json.loads((Path(state_dir) / 'agent0-presence.json').read_text(encoding='utf-8'))
        return {'connected': pid_alive(data.get('pid')), 'client': data.get('client'), 'last_tool': data.get('last_tool'),
                'idle_seconds': max(0, int(time.time() - float(data.get('last_seen', 0))))}
    except (OSError, ValueError, TypeError):
        return {'connected': False, 'client': None, 'last_tool': None, 'idle_seconds': None}


class WebServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128  # many short-lived loopback connections (terminal input, polling)

    def __init__(self, engine, port=8765):
        if type(port) is not int or not 0 <= port <= 65535:
            raise OrchError('Port must be 0..65535')
        self.engine = engine
        self.runners = None
        self.terminals = Terminals(engine.cfg, engine.db)
        self.token = secrets.token_urlsafe(32)
        self.bridge_key = secrets.token_urlsafe(24)  # read-only key for the local MCP process (Agent 0)
        super().__init__(('127.0.0.1', port), Handler)
        self.authority = f'127.0.0.1:{self.server_port}'
        self.origin = 'http://' + self.authority


class Handler(BaseHTTPRequestHandler):
    server_version = 'AgentStudio'

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # Never log credentials, task text or model output.

    def reply(self, status, body, mime='application/json; charset=utf-8', filename=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, mutation):
        self.close_connection = True
        try:
            if self.headers.get('Host') != self.server.authority:
                return self.reply(403, {'error': 'Invalid Host'})
            origin = self.headers.get('Origin')
            if (origin and origin != self.server.origin) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': 'Cross-origin access denied'})
            url = urlsplit(self.path)
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/icons.js': ('icons.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8'),
                      '/vendor/xterm.js': ('vendor/xterm.js', 'text/javascript; charset=utf-8'),
                      '/vendor/addon-fit.js': ('vendor/addon-fit.js', 'text/javascript; charset=utf-8'),
                      '/vendor/xterm.css': ('vendor/xterm.css', 'text/css; charset=utf-8')}
            if not mutation and url.path in static:
                name, mime = static[url.path]
                return self.reply(200, (ASSETS / name).read_bytes(), mime)
            if url.path.startswith('/api/bridge/'):
                if mutation or not hmac.compare_digest(self.headers.get('X-Bridge-Key', '').encode(), self.server.bridge_key.encode()):
                    return self.reply(401, {'error': 'Bridge key required'})
                terminals, parts = self.server.terminals, url.path.strip('/').split('/')
                if parts == ['api', 'bridge', 'terminals']:
                    return self.reply(200, terminals.snapshot())
                if len(parts) == 4 and parts[2] == 'terminals':
                    return self.reply(200, terminals.tail(parts[3], int(parse_qs(url.query).get('chars', ['6000'])[0])))
                return self.reply(404, {'error': 'Route not found'})
            expected = ('Bearer ' + self.server.token).encode()
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected):
                return self.reply(401, {'error': 'Mở liên kết Dashboard có token trong terminal máy chủ.'})
            body = {}
            if mutation:
                if origin != self.server.origin:
                    return self.reply(403, {'error': 'Same-origin POST required'})
                if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    return self.reply(400, {'error': 'JSON body required'})
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 200_000:
                    return self.reply(413, {'error': 'Request body limit: 200 KB'})
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise OrchError('Incomplete request body')
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise OrchError('JSON object required')
            self.route(url.path, parse_qs(url.query), body, mutation)
        except (OrchError, ValueError, TypeError, KeyError) as exc:
            self.reply(400, {'error': str(exc)[:2000]})
        except sqlite3.Error:
            self.reply(503, {'error': 'Queue temporarily unavailable; retry shortly.'})
        except ConnectionError:
            pass  # browser navigated away or aborted a long-poll
        except OSError:
            self.reply(400, {'error': 'Local file unavailable. Check state and permissions.'})
        except Exception:
            self.reply(500, {'error': 'Internal dashboard error. Check local state.'})

    def route(self, path, query, body, mutation):
        e = self.server.engine
        if path == '/api/runners' and not mutation:
            return self.reply(200, {'managed': self.server.runners is not None,
                                   'providers': self.server.runners.snapshot() if self.server.runners else {}})
        if path == '/api/terminals' and not mutation:
            return self.reply(200, self.server.terminals.snapshot())
        if path == '/api/terminals/open' and mutation:
            if not set(body) <= {'kind', 'provider', 'task_id', 'cols', 'rows'} or 'kind' not in body:
                raise OrchError('Expected kind, optional provider, task_id, cols and rows')
            return self.reply(200, self.server.terminals.open(body['kind'], body.get('provider'), body.get('task_id'), body.get('cols', 100), body.get('rows', 30)))
        if path == '/api/terminals/stream' and not mutation:
            cursors = {}
            for item in query.get('c', [''])[0].split(',')[:40]:
                sid, _, after = item.partition(':')
                if sid and after.isdigit():
                    cursors[sid] = int(after)
            return self.reply(200, self.server.terminals.stream(cursors, min(float(query.get('wait', ['0'])[0]), 8)))
        if path.startswith('/api/terminals/'):
            parts = path.split('/')
            if len(parts) == 5 and parts[4] in {'output', 'input', 'resize', 'close'}:
                session = self.server.terminals.get(parts[3])
                if parts[4] == 'output' and not mutation:
                    after, data, nxt, code = session.read(int(query.get('after', ['0'])[0]), min(float(query.get('wait', ['0'])[0]), 8))
                    return self.reply(200, {'start': after, 'next': nxt, 'data': base64.b64encode(data).decode(), 'alive': code is None, 'exit_code': code})
                if mutation and parts[4] == 'input' and set(body) == {'data'} and isinstance(body['data'], str) and len(body['data']) <= 100_000:
                    session.write(body['data'])
                    return self.reply(200, {'ok': True})
                if mutation and parts[4] == 'resize' and set(body) == {'cols', 'rows'}:
                    session.resize(max(20, min(int(body['cols']), 400)), max(5, min(int(body['rows']), 200)))
                    return self.reply(200, {'ok': True})
                if mutation and parts[4] == 'close' and not body:
                    self.server.terminals.close(parts[3])
                    return self.reply(200, {'ok': True})
            return self.reply(404, {'error': 'Route or arguments not supported'})
        if path == '/api/agent0' and not mutation:
            return self.reply(200, agent0_status(e.cfg.state))
        if path == '/api/config' and not mutation:
            return self.reply(200, {'repo': str(e.cfg.repo), 'base_ref': e.cfg.data.get('base_ref', 'HEAD'),
                                   'demo': e.cfg.data.get('demo') is True,
                                   'execution_enabled': e.cfg.data.get('acknowledge_local_execution') is True,
                                   'providers': {k: bool(v.get('command')) for k, v in e.cfg.data.get('providers', {}).items() if k in {'claude', 'codex'}},
                                   'terminal_agents': [k for k in TERMINAL_AGENTS if e.cfg.data.get('providers', {}).get(k, {}).get('command')],
                                   'tests': list(e.cfg.data.get('tests', {}))})
        if path == '/api/tasks':
            if mutation:
                if set(body) != {'provider', 'prompt', 'allow_paths', 'tests'}:
                    raise OrchError('Expected provider, prompt, allow_paths and tests')
                return self.reply(201, e.enqueue(**body))
            return self.reply(200, [e.db.get(row['id']) for row in e.db.list(limit=200)])
        if path == '/api/activity' and not mutation:
            with e.db.connect() as db:
                rows = db.execute('SELECT seq,task_id,time,kind FROM events ORDER BY seq DESC LIMIT 40').fetchall()
            return self.reply(200, [dict(row) for row in rows])
        parts = path.strip('/').split('/')
        if len(parts) < 3 or parts[:2] != ['api', 'tasks'] or not ID.fullmatch(parts[2]):
            return self.reply(404, {'error': 'Route not found'})
        task_id = parts[2]
        task = e.db.get(task_id)
        action = '/'.join(parts[3:])
        if not mutation:
            if not action:
                return self.reply(200, task)
            if action == 'events':
                after = int(query.get('after', ['0'])[0])
                if after < 0:
                    raise OrchError('Invalid event cursor')
                return self.reply(200, e.db.events(task_id, after=after))
            if action == 'review':
                return self.reply(200, e.review_bundle(task_id, max_chars=100000))
            if action == 'diff':
                with task_lock(e.cfg, task_id):
                    _, patch = e._validated(e.db.get(task_id))
                return self.reply(200, patch, 'text/plain; charset=utf-8', 'changes.patch')
            if action == 'logs':
                stage = query.get('stage', ['worker'])[0]
                stream = query.get('stream', ['stdout'])[0]
                if stage not in {'worker'} | {'test-' + t for t in task['tests']} or stream not in {'stdout', 'stderr'}:
                    raise OrchError('Invalid log selection')
                root = e.cfg.state / 'runs' / task_id
                file = root / stage / (stream + '.log')
                if not inside(file, root):
                    raise OrchError('Invalid log path')
                if not file.exists():
                    return self.reply(200, {'text': '', 'truncated': False, 'available': False})
                with file.open('rb') as log:
                    size = log.seek(0, 2)
                    log.seek(max(0, size - 65536))
                    text = log.read(65536).decode('utf-8', 'replace')
                return self.reply(200, {'text': text, 'truncated': size > 65536, 'available': True})
            if action in {'download/patch', 'download/manifest'}:
                exported = e.export(task_id)
                file = Path(exported[action.split('/')[1]])
                return self.reply(200, file.read_bytes(), 'application/octet-stream', file.name)
        else:
            if action == 'cancel' and not body:
                return self.reply(200, e.db.cancel(task_id))
            if action == 'review' and set(body) == {'verdict', 'patch_sha256', 'notes'}:
                return self.reply(200, e.record_review(task_id, **body))
            if action == 'export' and not body:
                return self.reply(200, e.export(task_id))
        return self.reply(404, {'error': 'Route or arguments not supported'})


def serve_web(engine, port=8765, run_workers=False, open_browser=False):
    with WebServer(engine, port) as server:
        try:
            if run_workers:
                from .runners import Runners
                server.runners = Runners(engine.cfg)
                server.runners.start()
            bridge = engine.cfg.state / 'terminal-bridge.json'
            bridge.write_text(json.dumps({'port': server.server_port, 'key': server.bridge_key, 'pid': os.getpid()}), encoding='utf-8')
            print(f'Dashboard: {server.origin}/#token={server.token}', flush=True)
            print('Local only. ' + ('Managed runners enabled.' if run_workers else 'Workers run separately.') + ' Ctrl+C to stop.', flush=True)
            if open_browser:
                import threading, webbrowser
                threading.Timer(.7, webbrowser.open, (f'{server.origin}/#token={server.token}',)).start()
            server.serve_forever(poll_interval=.25)
        finally:
            server.terminals.close()
            try:
                (engine.cfg.state / 'terminal-bridge.json').unlink()
            except OSError:
                pass
            if server.runners:
                server.runners.close()
