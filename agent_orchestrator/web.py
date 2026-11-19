"""Authenticated loopback dashboard, backed by the same Engine as CLI/MCP."""
from __future__ import annotations

import base64
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.request
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .config import OrchError, inside
from .gemini_bridge import GeminiBridgeHub, WorkspaceExecutor
from . import mcp_server
from .terminals import TERMINAL_AGENTS, Terminals
from .engine import task_lock
from .gitops import ID

ASSETS = Path(__file__).with_name('web_assets')
_TTS_CACHE: dict[str, bytes] = {}


def get_tts_audio(text: str) -> bytes | None:
    text = text.strip()[:200]
    if not text:
        return None
    if text in _TTS_CACHE:
        return _TTS_CACHE[text]
    try:
        url = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=vi&q=' + quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(_TTS_CACHE) < 100:
                    _TTS_CACHE[text] = data
                return data
    except Exception:
        pass
    return None


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
        # Gemini Web bridge: a separate key, only for the browser extension and the queue worker. The file lets a worker
        # running in another process reach this server; it is removed on close.
        self.gemini_bridge = GeminiBridgeHub(engine.cfg, self.terminals)
        self.terminals.gemini_bridge = self.gemini_bridge
        self.gemini_bridge_file = engine.cfg.state / 'gemini-bridge.json'
        self.gemini_bridge_file.write_text(json.dumps({'port': self.server_port, 'key': self.gemini_bridge.key}), encoding='utf-8')
        # MCP server token — dùng token cố định từ config nếu có, ngược lại tự sinh mỗi lần khởi động
        fixed = engine.cfg.mcp_fixed_token() if hasattr(engine.cfg, 'mcp_fixed_token') else None
        self.mcp_token = fixed if fixed else secrets.token_urlsafe(32)
        self.mcp_server_file = engine.cfg.state / 'mcp-server.json'
        self.mcp_server_file.write_text(json.dumps({'port': self.server_port, 'token': self.mcp_token}), encoding='utf-8')

    def server_close(self):
        try:
            self.gemini_bridge_file.unlink()
        except OSError:
            pass
        try:
            self.mcp_server_file.unlink()
        except OSError:
            pass
        super().server_close()


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
        if getattr(self, '_gemini_cors', False):
            self.cors_gemini()
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; media-src 'self' data: blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def do_OPTIONS(self):
        # CORS preflight only for the Gemini extension routes; everything else stays same-origin only.
        if urlsplit(self.path).path.startswith('/api/gemini-bridge/') and self.headers.get('Host') == self.server.authority:
            self._gemini_cors = True
            self.send_response(204)
            self.cors_gemini()
            self.send_header('Content-Length', '0')
            self.send_header('Connection', 'close')
            self.end_headers()
            return
        # MCP endpoints accept cross-origin preflight (token required on actual request).
        if urlsplit(self.path).path.startswith('/api/mcp/'):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Content-Length', '0')
            self.send_header('Connection', 'close')
            self.end_headers()
            return
        self.send_response(405)
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()

    def cors_gemini(self):
        origin = self.headers.get('Origin', '')
        if origin.startswith(('chrome-extension://', 'moz-extension://')):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Gemini-Bridge-Key')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def gemini_ext(self, url, mutation):
        """Routes for the browser extension and the queue worker. Authenticated only by the bridge key."""
        hub = self.server.gemini_bridge
        if not hmac.compare_digest(self.headers.get('X-Gemini-Bridge-Key', '').encode(), hub.key.encode()):
            return self.reply(401, {'error': 'Bridge key required'})
        if not self.server.engine.cfg.provider_enabled('gemini_web'):
            return self.reply(403, {'error': 'gemini_web is disabled in the owner config'})
        parts = [unquote(x) for x in url.path.strip('/').split('/')][2:]
        query = parse_qs(url.query)

        def q(name, default=''):
            return query.get(name, [default])[0]
        if parts == ['poll'] and not mutation:
            item = hub.poll_next_prompt(q('client_id', 'ext')[:64], q('tab_id') or None, q('url')[:400], float(q('wait', '8') or 8))
            return self.reply(200, item)
        if parts == ['reply'] and mutation:
            body = self.read_json()
            if body is None:
                return
            return self.reply(200, hub.submit_reply(str(body.get('prompt_id', '')), str(body.get('text') or ''),
                                                    str(body.get('url') or ''), body.get('error') or None,
                                                    body.get('blocks'), str(body.get('debug_html') or '')))
        if parts == ['jobs'] and mutation:
            body = self.read_json()
            if body is None:
                return
            return self.reply(200, hub.create_worker_job(str(body.get('worktree', '')), body.get('allow_paths') or [],
                                                         str(body.get('prompt', '')), body.get('resume')))
        if len(parts) == 2 and parts[0] == 'jobs' and not mutation:
            return self.reply(200, hub.get_worker_job(parts[1], float(q('wait', '0') or 0)))
        if len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'cancel' and mutation:
            if self.read_json() is None:
                return
            return self.reply(200, hub.cancel_worker_job(parts[1]))
        return self.reply(404, {'error': 'Route not found'})

    def read_json(self):
        """Parse the JSON object body. Replies and returns None for transport-level problems."""
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.reply(400, {'error': 'JSON body required'})
            return None
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 200_000:
            to_drain = min(length, 1_000_000)
            try:
                while to_drain > 0:
                    chunk = self.rfile.read(min(to_drain, 65536))
                    if not chunk:
                        break
                    to_drain -= len(chunk)
            except Exception:
                pass
            self.reply(413, {'error': 'Request body limit: 200 KB'})
            return None
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise OrchError('Incomplete request body')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise OrchError('JSON object required')
        return body

    def handle_request(self, mutation):
        self.close_connection = True
        try:
            if self.path.startswith('/api/mcp/'):
                self._handle_mcp()
                return
            if self.headers.get('Host') != self.server.authority:
                return self.reply(403, {'error': 'Invalid Host'})
            url = urlsplit(self.path)
            if url.path.startswith('/api/gemini-bridge/') and url.path not in {'/api/gemini-bridge/status', '/api/gemini-bridge/toggle'}:
                # The extension origin (chrome-extension://...) is cross-site by design; it is gated by the bridge key instead.
                ext_origin = self.headers.get('Origin', '')
                if ext_origin and not ext_origin.startswith(('chrome-extension://', 'moz-extension://')):
                    return self.reply(403, {'error': 'Cross-origin access denied'})
                self._gemini_cors = True
                return self.gemini_ext(url, mutation)
            origin = self.headers.get('Origin')
            if (origin and origin != self.server.origin) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': 'Cross-origin access denied'})
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/icons.js': ('icons.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8'),
                      '/vendor/xterm.js': ('vendor/xterm.js', 'text/javascript; charset=utf-8'),
                      '/vendor/addon-fit.js': ('vendor/addon-fit.js', 'text/javascript; charset=utf-8'),
                      '/vendor/addon-webgl.js': ('vendor/addon-webgl.js', 'text/javascript; charset=utf-8'),
                      '/vendor/xterm.css': ('vendor/xterm.css', 'text/css; charset=utf-8')}
            if not mutation and url.path in static:
                name, mime = static[url.path]
                return self.reply(200, (ASSETS / name).read_bytes(), mime)
            if url.path.startswith('/api/bridge/'):
                if not hmac.compare_digest(self.headers.get('X-Bridge-Key', '').encode(), self.server.bridge_key.encode()):
                    return self.reply(401, {'error': 'Bridge key required'})
                terminals, parts = self.server.terminals, [unquote(x) for x in url.path.strip('/').split('/')]
                if mutation:
                    # The only writes the bridge allows: Agent 0 opening an interactive agent terminal, typing one line into one,
                    # and closing a terminal it opened itself.
                    # Agent 0's own tool list does not auto-approve them, so Claude Code asks the owner every time.
                    if parts == ['api', 'bridge', 'terminals', 'open']:
                        body = self.read_json()
                        if body is None:
                            return
                        if set(body) != {'provider'}:
                            raise OrchError('Expected only provider')
                        return self.reply(200, terminals.open_agent(body['provider']))
                    if len(parts) == 5 and parts[2] == 'terminals' and parts[4] == 'input':
                        body = self.read_json()
                        if body is None:
                            return
                        if set(body) != {'text'}:
                            raise OrchError('Expected only text')
                        return self.reply(200, terminals.send(parts[3], body['text']))
                    if len(parts) == 5 and parts[2] == 'terminals' and parts[4] == 'close':
                        body = self.read_json()
                        if body is None:
                            return
                        if body:
                            raise OrchError('Không nhận tham số')
                        return self.reply(200, terminals.close_opened(parts[3]))
                    return self.reply(401, {'error': 'Bridge is read-only except opening a terminal, terminal input and closing a terminal Agent 0 opened'})
                if parts == ['api', 'bridge', 'terminals']:
                    return self.reply(200, terminals.snapshot())
                if len(parts) == 4 and parts[2] == 'terminals':
                    query_params = parse_qs(url.query)
                    chars = int(query_params.get('chars', ['6000'])[0])
                    clean_flag = query_params.get('clean', ['0'])[0].lower() in {'1', 'true'}
                    return self.reply(200, terminals.tail(parts[3], chars=chars, clean=clean_flag))
                return self.reply(404, {'error': 'Route not found'})
            expected = ('Bearer ' + self.server.token).encode()
            auth = self.headers.get('Authorization', '').encode()
            query_token = parse_qs(url.query).get('token', [''])[0].encode()
            if not hmac.compare_digest(auth, expected) and not (query_token and hmac.compare_digest(query_token, self.server.token.encode())):
                return self.reply(401, {'error': 'Mở liên kết Dashboard có token trong terminal máy chủ.'})
            body = {}
            if mutation:
                if origin != self.server.origin:
                    return self.reply(403, {'error': 'Same-origin POST required'})
                body = self.read_json()
                if body is None:
                    return
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

    def _handle_mcp(self):
        """Handle all /api/mcp/* requests (Bearer token auth, CORS-open)."""
        try:
            # Send CORS header on all responses
            path = urlsplit(self.path).path  # e.g. /api/mcp/tools/list
            path_parts = [p for p in path.strip('/').split('/') if p][2:]  # strip "api", "mcp"
            # Bearer token check
            auth = self.headers.get('Authorization', '')
            expected = 'Bearer ' + self.server.mcp_token
            if not hmac.compare_digest(auth.encode('utf-8'), expected.encode('utf-8')):
                body = json.dumps({'error': 'MCP token không hợp lệ hoặc thiếu Authorization header.'}, ensure_ascii=False).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)
                return
            # Parse JSON body (optional for GET-like tools/list)
            request_body: dict = {}
            content_length = int(self.headers.get('Content-Length', '0') or '0')
            if content_length > 0:
                if content_length > 200_000:
                    raw_body = json.dumps({'error': 'Body quá lớn (tối đa 200 KB).'}, ensure_ascii=False).encode('utf-8')
                    self.send_response(413)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(raw_body)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(raw_body)
                    return
                raw = self.rfile.read(content_length)
                try:
                    request_body = json.loads(raw)
                    if not isinstance(request_body, dict):
                        request_body = {}
                except (ValueError, TypeError):
                    request_body = {}
            # Build executor using repo from engine config
            cfg = self.server.engine.cfg
            executor = WorkspaceExecutor(cfg.repo, allow_paths=cfg.mcp_allow_paths() if hasattr(cfg, 'mcp_allow_paths') else None)
            status_code, response = mcp_server.handle_mcp(path_parts, request_body, executor)
            resp_bytes = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(resp_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(resp_bytes)
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({'error': f'Lỗi MCP nội bộ: {exc}'}, ensure_ascii=False).encode('utf-8')
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(err)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(err)
            except Exception:  # noqa: BLE001
                pass

    def route(self, path, query, body, mutation):
        e = self.server.engine
        if path == '/api/tts' and not mutation:
            q = query.get('q', [''])[0].strip()
            if not q:
                raise OrchError('Missing q parameter')
            audio = get_tts_audio(q)
            if audio is None:
                return self.reply(503, {'error': 'TTS service unavailable'})
            return self.reply(200, audio, mime='audio/mpeg')
        if path == '/api/runners' and not mutation:
            return self.reply(200, {'managed': self.server.runners is not None,
                                   'providers': self.server.runners.snapshot() if self.server.runners else {}})
        if path == '/api/terminals' and not mutation:
            return self.reply(200, self.server.terminals.snapshot())
        if path == '/api/gemini-bridge/status' and not mutation:
            hub = self.server.gemini_bridge
            return self.reply(200, {**hub.status_snapshot(), 'pair': f'{self.server.origin}|{hub.key}'})
        if path == '/api/gemini-bridge/toggle' and mutation:
            if set(body) != {'enabled'} or type(body['enabled']) is not bool:
                raise OrchError('Expected only enabled (true/false)')
            # In memory only: the owner config file is never rewritten by the dashboard.
            provider = e.cfg.data.setdefault('providers', {}).setdefault(
                'gemini_web', {'command': [], 'model': 'gemini-web', 'max_turns': 12})
            provider['enabled'] = body['enabled']
            return self.reply(200, self.server.gemini_bridge.status_snapshot())
        if path == '/api/conversations' and not mutation:
            try:
                limit = int(query.get('limit', ['50'])[0])
            except (ValueError, TypeError):
                raise OrchError("limit must be 1..200")
            provider = query.get('provider', [None])[0] or None
            q = query.get('q', [None])[0] or None
            return self.reply(200, self.server.terminals.with_live_state(e.db.conversation_list(limit=limit, provider=provider, q=q)))
        if path == '/api/chat' and not mutation:
            return self.reply(200, self.server.terminals.chat_status())
        if path == '/api/chat/new' and mutation:
            if not set(body) <= {'confirm', 'cols', 'rows'} or body.get('confirm') is not True:
                raise OrchError('Cần {"confirm": true} để bắt đầu cuộc trò chuyện mới')
            cols, rows = max(20, min(int(body.get('cols', 100)), 400)), max(5, min(int(body.get('rows', 30)), 200))
            return self.reply(200, self.server.terminals.new_chat(cols=cols, rows=rows))
        if path == '/api/conversations/delete-all' and mutation:
            if body != {'confirm': True}:
                raise OrchError('Cần {"confirm": true} để xóa toàn bộ lịch sử')
            return self.reply(200, self.server.terminals.delete_all_conversations())
        if path.startswith('/api/conversations/'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[1] == 'conversations' and parts[3] == 'delete' and mutation:
                if body:
                    raise OrchError('Không nhận tham số')
                return self.reply(200, self.server.terminals.delete_conversation(parts[2]))
            if len(parts) == 4 and parts[1] == 'conversations' and parts[3] == 'transcript' and not mutation:
                cid = parts[2]
                try:
                    after = int(query.get('after', ['0'])[0])
                    limit = int(query.get('limit', ['200'])[0])
                except (ValueError, TypeError):
                    raise OrchError("Invalid after or limit parameter")
                return self.reply(200, self.server.terminals.read_transcript(cid, after=after, limit=limit))
            if len(parts) == 4 and parts[1] == 'conversations' and parts[3] == 'resume' and mutation:
                cid = parts[2]
                cols = int(body.get('cols', 100)) if body else 100
                rows = int(body.get('rows', 30)) if body else 30
                return self.reply(200, self.server.terminals.resume_conversation(cid, cols=cols, rows=rows))
            if len(parts) == 3 and parts[1] == 'conversations' and not mutation:
                cid = parts[2]
                return self.reply(200, self.server.terminals.with_live_state(e.db.conversation_get(cid)))
        if path == '/api/terminals/open' and mutation:
            if not set(body) <= {'kind', 'provider', 'task_id', 'cols', 'rows', 'repo'} or 'kind' not in body:
                raise OrchError('Expected kind, optional provider, task_id, repo, cols and rows')
            return self.reply(200, self.server.terminals.open(body['kind'], body.get('provider'), body.get('task_id'), body.get('cols', 100),
                                                              body.get('rows', 30), repo=body.get('repo')))
        if path == '/api/terminals/stream' and not mutation:
            cursors = {}
            for item in query.get('c', [''])[0].split(',')[:40]:
                sid, _, after = item.partition(':')
                if sid and after.isdigit():
                    cursors[sid] = int(after)
            return self.reply(200, self.server.terminals.stream(cursors, min(float(query.get('wait', ['0'])[0]), 8)))
        if path.startswith('/api/terminals/'):
            parts = path.split('/')
            if len(parts) == 5 and parts[4] in {'output', 'input', 'resize', 'close', 'notify-done'}:
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
                if mutation and parts[4] == 'notify-done' and not body:
                    return self.reply(200, self.server.terminals.notify_done(parts[3]))
            return self.reply(404, {'error': 'Route or arguments not supported'})
        if path == '/api/agent0' and not mutation:
            return self.reply(200, agent0_status(e.cfg.state))
        if path == '/api/browse/native' and mutation:
            initial = str(body.get('initial') or e.cfg.repo or '').strip()
            picker_script = (
                "import tkinter as tk; from tkinter import filedialog; "
                "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
                f"folder = filedialog.askdirectory(initialdir={json.dumps(initial)}, title='Chọn thư mục mã nguồn dự án'); "
                "root.destroy(); print(folder)"
            )
            chosen = ""
            try:
                proc = subprocess.run(
                    [sys.executable, '-c', picker_script],
                    capture_output=True, text=True, timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if proc.returncode == 0:
                    chosen = proc.stdout.strip()
            except Exception:
                pass
            if not chosen and os.name == 'nt':
                ps_cmd = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "$f.Description = 'Chọn thư mục mã nguồn dự án'; "
                    f"if ('{initial}' -and (Test-Path '{initial}')) {{ $f.SelectedPath = '{initial}' }}; "
                    "$top = New-Object System.Windows.Forms.Form; $top.TopMost = $true; "
                    "if ($f.ShowDialog($top) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
                )
                try:
                    proc = subprocess.run(
                        ['powershell', '-NoProfile', '-STA', '-Command', ps_cmd],
                        capture_output=True, text=True, timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if proc.returncode == 0:
                        chosen = proc.stdout.strip()
                except Exception:
                    pass
            return self.reply(200, {'path': chosen, 'cancelled': not chosen})
        if path == '/api/browse' and not mutation:
            target = unquote(query.get('path', [''])[0]).strip()
            if not target:
                drives = [f"{d}:\\" for d in 'CDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{d}:\\")]
                return self.reply(200, {'current': '', 'parent': None, 'dirs': drives})
            target_path = Path(target).resolve()
            if not target_path.is_dir():
                raise OrchError(f'Thư mục không tồn tại: {target}')
            dirs = []
            try:
                for entry in os.scandir(target_path):
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.') and not entry.name.startswith('$'):
                        dirs.append(entry.name)
            except OSError as err:
                raise OrchError(f'Không thể đọc thư mục: {err}')
            parent = str(target_path.parent) if target_path.parent != target_path else None
            return self.reply(200, {'current': str(target_path), 'parent': parent, 'dirs': sorted(dirs, key=str.lower)})
        if path == '/api/repo':
            if not mutation:
                return self.reply(200, {'repo': str(e.cfg.repo), 'base_ref': e.cfg.data.get('base_ref', 'HEAD'), 'repos': list(e.cfg.repos)})
            if not isinstance(body, dict) or not body.get('path'):
                raise OrchError('Cần cung cấp path của thư mục')
            raw = str(body['path']).strip()
            p = Path(raw).resolve()
            if not p.is_dir():
                raise OrchError(f'Thư mục không tồn tại: {raw}')
            e.cfg.repo = p
            e.cfg.data['repo'] = str(p)
            e.cfg.repos['default'] = p
            e.gits = {}
            agent0 = None
            if hasattr(self.server, 'terminals') and self.server.terminals:
                self.server.terminals.cfg = e.cfg
                # Agent 0's folder and MCP tools were fixed when it started; reopen it on the new repo.
                agent0 = self.server.terminals.restart_agent0()
            return self.reply(200, {'ok': True, 'repo': str(p), 'name': p.name, 'base_ref': e.cfg.data.get('base_ref', 'HEAD'),
                                    'agent0_restarted': agent0 is not None})
        if path == '/api/repo/folders' and not mutation:
            root = e.cfg.repo
            ignored = {'.git', '.claude', '.codex', '.github', '.venv', '.runtime', '.local-run', '__pycache__', 'node_modules', 'bin', 'obj', 'dist', 'build'}
            folders = []
            try:
                for base, dirnames, _ in os.walk(root):
                    dirnames[:] = [d for d in dirnames if d.lower() not in ignored and not d.startswith('.')]
                    rel = Path(base).relative_to(root).as_posix()
                    if rel != '.':
                        folders.append(rel)
                    if len(rel.split('/')) >= 4:
                        dirnames.clear()
                    if len(folders) >= 200:
                        break
            except OSError:
                pass
            return self.reply(200, {'repo': str(root), 'folders': sorted(folders)})
        if path == '/api/config' and not mutation:
            from .roles import role_choices
            return self.reply(200, {'repo': str(e.cfg.repo), 'base_ref': e.cfg.data.get('base_ref', 'HEAD'),
                                   'demo': e.cfg.data.get('demo') is True,
                                   'execution_enabled': e.cfg.data.get('acknowledge_local_execution') is True,
                                   'providers': {k: e.cfg.provider_enabled(k) for k in e.cfg.data.get('providers', {}) if k in {'claude', 'codex', 'gemini_web'}},
                                   'terminal_agents': [k for k in TERMINAL_AGENTS if e.cfg.provider_enabled(k)],
                                   'repos': list(e.cfg.repos),
                                   'roles': role_choices(),
                                   'tests': list(e.cfg.data.get('tests', {}))})
        if path == '/api/workflows':
            if not mutation:
                return self.reply(200, e.workflows(all_chats=query.get('scope', [''])[0] == 'all'))
            if not {'steps'} <= set(body) <= {'steps', 'title', 'require_approval'}:
                raise OrchError('Expected steps (optional title, require_approval)')
            return self.reply(201, e.plan(body['steps'], body.get('title'), body.get('require_approval', False)))
        match = re.fullmatch(r'/api/workflows/([0-9a-f]{12})(/cancel)?', path)
        if match:
            if mutation and match[2] and not body:
                return self.reply(200, e.cancel_workflow(match[1]))
            if not mutation and not match[2]:
                return self.reply(200, e.workflow(match[1]))
            return self.reply(404, {'error': 'Route or arguments not supported'})
        if path == '/api/agents' and not mutation:
            return self.reply(200, e.agents_overview())
        if path == '/api/settings':
            if not mutation:
                return self.reply(200, {'default_remember': e.default_remember(), 'notify_agent0': bool(e.db.setting('notify_agent0', True))})
            if len(body) != 1 or set(body) - {'default_remember', 'notify_agent0'} or not all(isinstance(v, bool) for v in body.values()):
                raise OrchError('Expected default_remember or notify_agent0 (true or false)')
            for key, value in body.items():
                e.db.set_setting(key, value)
            return self.reply(200, {'default_remember': e.default_remember(), 'notify_agent0': bool(e.db.setting('notify_agent0', True))})
        if path.startswith('/api/orchestration-rules'):
            from . import rules as orch_rules
            from .roles import catalog_with_content
            repos = list(e.cfg.repos.values())

            def rules_view():
                data, markdown, unknown = orch_rules.current(e.cfg, e.db)
                try:
                    orch_rules.sync_roles(e.cfg, data['params'])
                except OSError:
                    pass
                rdir = orch_rules.roles_dir(e.cfg, data['params'])
                agent0 = self.server.terminals.sessions.get('agent0')
                return {'params': data['params'], 'texts': data['texts'], 'default': orch_rules.defaults(), 'preview': markdown,
                        'unknown_variables': unknown, 'digest': orch_rules.digest(markdown), 'variables': list(orch_rules.VARIABLES),
                        'roles_dir': str(rdir), 'roles': catalog_with_content(rdir),
                        'applied_digest': e.db.setting(orch_rules.APPLIED_KEY, None),
                        'agent0_running': bool(agent0 is not None and getattr(agent0, 'alive', False)),
                        'text_limit': orch_rules.TEXT_LIMIT, 'history': [{'time': h.get('time')} for h in orch_rules.history(e.db)]}
            def rules_saved():
                markdown = orch_rules.current(e.cfg, e.db)[1]
                self.server.terminals.rules_changed(orch_rules.digest(markdown))

            sub = path[len('/api/orchestration-rules'):]
            if sub == '' and not mutation:
                return self.reply(200, rules_view())
            if sub == '' and mutation:
                orch_rules.save(e.db, body, repos)
                rules_saved()
                return self.reply(200, rules_view())
            if sub == '/preview' and mutation:
                candidate = orch_rules.validate(body, repos)
                markdown, unknown = orch_rules.render(e.cfg, candidate)
                return self.reply(200, {'preview': markdown, 'unknown_variables': unknown})
            if sub == '/reset' and mutation and not body:
                orch_rules.reset(e.db)
                rules_saved()
                return self.reply(200, rules_view())
            if sub == '/restart-agent0' and mutation and not body:
                info = self.server.terminals.restart_agent0()
                return self.reply(200, {'restarted': info is not None})
            if sub == '/history' and not mutation:
                return self.reply(200, orch_rules.history(e.db))
            if sub == '/restore' and mutation and set(body) == {'index'}:
                orch_rules.restore(e.db, body['index'], repos)
                rules_saved()
                return self.reply(200, rules_view())
            return self.reply(404, {'error': 'Route or arguments not supported'})
        match = re.fullmatch(r'/api/agents/(\d{1,9})/settings', path)
        if match and mutation:
            # Whitelisted keys only; add new per-agent options here and in the dashboard's settingDefs list.
            if set(body) != {'remember_context'} or not isinstance(body['remember_context'], bool):
                raise OrchError('Expected only remember_context (true or false)')
            if e.db.agent_get(int(match[1])) is None:
                raise OrchError(f'Không có agent {match[1]}')
            e.db.agent_setting(int(match[1]), 'remember_context', body['remember_context'])
            return self.reply(200, {'agent': int(match[1]), 'remember_context': body['remember_context']})
        if path == '/api/tasks':
            if mutation:
                if not {'prompt', 'allow_paths', 'tests'} <= set(body) <= {'provider', 'prompt', 'allow_paths', 'tests', 'agent', 'remember', 'repo', 'role'}:
                    raise OrchError('Expected prompt, allow_paths, tests and provider or agent (optional remember, role)')
                return self.reply(201, e.enqueue(body.get('provider'), body['prompt'], body['allow_paths'], body['tests'],
                                                 agent=body.get('agent'), remember=body.get('remember'), repo=body.get('repo'),
                                                 role=body.get('role')))
            return self.reply(200, [e.db.get(row['id']) for row in e.db.list(limit=200, all_chats=query.get('scope', [''])[0] == 'all')])
        if path == '/api/activity' and not mutation:
            return self.reply(200, e.db.activity(40, all_chats=query.get('scope', [''])[0] == 'all'))
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
                live = {'worker'} | {'test-' + t for t in task['tests']}
                archived = re.fullmatch(r'(.+)-r\d{1,3}', stage)  # logs of earlier rounds: worker-r1, test-x-r1
                if (stage not in live and not (archived and archived[1] in live)) or stream not in {'stdout', 'stderr'}:
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
    # Every run of the tool is a new chat, so numbered agents start again at 1. Work still running from a previous
    # run keeps its numbers (reset_chat refuses), and the user can start a new chat later from the dashboard.
    try:
        engine.db.reset_chat()
    except (OrchError, sqlite3.Error):
        pass
    with WebServer(engine, port) as server:
        try:
            if run_workers:
                from .runners import Runners
                server.runners = Runners(engine.cfg)
                server.runners.start()
            server.terminals.start_monitor(lambda: server.runners.snapshot() if server.runners else {})
            bridge = engine.cfg.state / 'terminal-bridge.json'
            bridge.write_text(json.dumps({'port': server.server_port, 'key': server.bridge_key, 'pid': os.getpid()}), encoding='utf-8')
            print(f'Dashboard: {server.origin}/#token={server.token}', flush=True)
            print('Local only. ' + ('Managed runners enabled.' if run_workers else 'Workers run separately.') + ' Ctrl+C to stop.', flush=True)
            print(f'MCP Server: {server.origin}/api/mcp/  Token: {server.mcp_token}', flush=True)
            if open_browser:
                import threading
                from .browser import open_dashboard
                threading.Timer(.7, open_dashboard, (f'{server.origin}/#token={server.token}',)).start()
            server.serve_forever(poll_interval=.25)
        finally:
            server.terminals.close()
            try:
                (engine.cfg.state / 'terminal-bridge.json').unlink()
            except OSError:
                pass
            if server.runners:
                server.runners.close()
