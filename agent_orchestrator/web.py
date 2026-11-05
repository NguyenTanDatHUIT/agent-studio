"""Authenticated loopback dashboard, backed by the same Engine as CLI/MCP."""
from __future__ import annotations

import hmac
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .config import OrchError, inside
from .engine import task_lock
from .gitops import ID

ASSETS = Path(__file__).with_name('web_assets')


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, engine, port=8765):
        if type(port) is not int or not 0 <= port <= 65535:
            raise OrchError('Port must be 0..65535')
        self.engine = engine
        self.runners = None
        self.token = secrets.token_urlsafe(32)
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
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if not mutation and url.path in static:
                name, mime = static[url.path]
                return self.reply(200, (ASSETS / name).read_bytes(), mime)
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
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError:
            self.reply(400, {'error': 'Local file unavailable. Check state and permissions.'})
        except Exception:
            self.reply(500, {'error': 'Internal dashboard error. Check local state.'})

    def route(self, path, query, body, mutation):
        e = self.server.engine
        if path == '/api/runners' and not mutation:
            return self.reply(200, {'managed': self.server.runners is not None,
                                   'providers': self.server.runners.snapshot() if self.server.runners else {}})
        if path == '/api/config' and not mutation:
            return self.reply(200, {'repo': str(e.cfg.repo), 'base_ref': e.cfg.data.get('base_ref', 'HEAD'),
                                   'demo': e.cfg.data.get('demo') is True,
                                   'execution_enabled': e.cfg.data.get('acknowledge_local_execution') is True,
                                   'providers': {k: bool(v.get('command')) for k, v in e.cfg.data.get('providers', {}).items() if k in {'claude', 'codex'}},
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


def serve_web(engine, port=8765, run_workers=False):
    with WebServer(engine, port) as server:
        try:
            if run_workers:
                from .runners import Runners
                server.runners = Runners(engine.cfg)
                server.runners.start()
            print(f'Dashboard: {server.origin}/#token={server.token}', flush=True)
            print('Local only. ' + ('Managed runners enabled.' if run_workers else 'Workers run separately.') + ' Ctrl+C to stop.', flush=True)
            server.serve_forever(poll_interval=.25)
        finally:
            if server.runners:
                server.runners.close()
