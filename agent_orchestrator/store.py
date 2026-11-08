from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import OrchError

# A finished task can be continued (another round in the same worktree) from these states.
CONTINUABLE = {'awaiting_review', 'changes_requested', 'failed', 'approved'}
ACTIVE = ('queued', 'running')
NOTIFY = {'awaiting_review', 'failed', 'cancelled'}  # outcomes that Agent 0 should hear about


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root):
        self.file = root / 'queue.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks(
                  id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL,
                  result TEXT, cancel INTEGER NOT NULL DEFAULT 0,
                  created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT,
                  time TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);
                -- Numbered agents ("codex 1", "claude 2"). AUTOINCREMENT: one global counter, never reused,
                -- shared by interactive terminals and queue workers, safe across the web and MCP processes.
                CREATE TABLE IF NOT EXISTS agents(
                  n INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, kind TEXT NOT NULL,
                  settings TEXT NOT NULL DEFAULT '{}', session_id TEXT, thread_task TEXT, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                -- Workflows: a plan of steps. A step waits until the steps it depends on have finished.
                CREATE TABLE IF NOT EXISTS workflows(
                  id TEXT PRIMARY KEY, title TEXT NOT NULL, require_approval INTEGER NOT NULL DEFAULT 0,
                  cancelled INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS steps(
                  wf TEXT NOT NULL, key TEXT NOT NULL, seq INTEGER NOT NULL, status TEXT NOT NULL,
                  spec TEXT NOT NULL, task_id TEXT, note TEXT, PRIMARY KEY(wf, key));
                -- Short plain-text notices for Agent 0 (ids and statuses only, never worker text).
                CREATE TABLE IF NOT EXISTS notices(
                  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, text TEXT NOT NULL);
            ''')
            if 'agent' not in {r['name'] for r in db.execute('PRAGMA table_info(tasks)')}:
                try:
                    db.execute('ALTER TABLE tasks ADD COLUMN agent INTEGER')
                except sqlite3.OperationalError:
                    pass  # another process migrated first

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.file, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, task_id, kind, data):
        with self.connect() as db:
            db.execute('INSERT INTO events(task_id,time,kind,data) VALUES(?,?,?,?)',
                       (task_id, now(), kind, json.dumps(data, ensure_ascii=False)))

    def add(self, task):
        with self.connect() as db:
            db.execute('INSERT INTO tasks(id,status,payload,result,cancel,created,updated,agent) VALUES(?,?,?,NULL,0,?,?,?)',
                       (task['id'], 'queued', json.dumps(task), now(), now(), task.get('agent')))
        self.event(task['id'], 'queued', {'provider': task['provider'], 'round': task.get('round', 1)})

    def get(self, task_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
        if row is None:
            raise OrchError("Unknown task")
        return {**json.loads(row['payload']), 'status': row['status'],
                'cancel_requested': bool(row['cancel']),
                'result': json.loads(row['result']) if row['result'] else None,
                'created': row['created'], 'updated': row['updated']}

    def list(self, limit=50):
        if type(limit) is not int or not 1 <= limit <= 200:
            raise OrchError("limit must be 1..200")
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                'SELECT id,status,created,updated FROM tasks ORDER BY created DESC LIMIT ?', (limit,))]

    def claim(self, provider=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,payload FROM tasks WHERE status='queued' AND cancel=0 ORDER BY created").fetchall()
            for row in rows:
                if provider is None or json.loads(row['payload'])['provider'] == provider:
                    db.execute("UPDATE tasks SET status='running',updated=? WHERE id=?", (now(), row['id']))
                    return row['id']
        return None

    def finish(self, task_id, status, result):
        with self.connect() as db:
            db.execute('UPDATE tasks SET status=?,result=?,updated=? WHERE id=?',
                       (status, json.dumps(result, ensure_ascii=False), now(), task_id))
        self.event(task_id, status, result)
        if status in NOTIFY:
            try:
                p = self.get(task_id)
                if p.get('agent'):
                    self.notice(f"Agent {p['agent']} ({p['provider']}) · task {task_id[:8]} (vòng {p.get('round', 1)}): {status}")
            except OrchError:
                pass

    def notice(self, text):
        with self.connect() as db:
            db.execute('INSERT INTO notices(time,text) VALUES(?,?)', (now(), text[:300]))

    def notices_after(self, after):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,text FROM notices WHERE id>? ORDER BY id LIMIT 50', (after,))]

    def last_notice(self):
        with self.connect() as db:
            return db.execute('SELECT COALESCE(MAX(id),0) FROM notices').fetchone()[0]

    # ---- workflows ------------------------------------------------------------------------------------
    def wf_create(self, wf_id, title, require_approval, steps):
        with self.connect() as db:
            db.execute('INSERT INTO workflows(id,title,require_approval,created) VALUES(?,?,?,?)',
                       (wf_id, title, int(require_approval), now()))
            for seq, (key, spec) in enumerate(steps):
                db.execute("INSERT INTO steps(wf,key,seq,status,spec) VALUES(?,?,?,'waiting',?)",
                           (wf_id, key, seq, json.dumps(spec, ensure_ascii=False)))

    def wf_steps(self, wf_id):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM steps WHERE wf=? ORDER BY seq', (wf_id,)).fetchall()
        return [{**dict(r), 'spec': json.loads(r['spec'])} for r in rows]

    def wf_list(self, limit=30):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM workflows ORDER BY created DESC LIMIT ?', (limit,)).fetchall()
        return [{**dict(r), 'require_approval': bool(r['require_approval']), 'cancelled': bool(r['cancelled'])} for r in rows]

    def wf_get(self, wf_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM workflows WHERE id=?', (wf_id,)).fetchone()
        if row is None:
            raise OrchError("Unknown workflow")
        return {**dict(row), 'require_approval': bool(row['require_approval']), 'cancelled': bool(row['cancelled'])}

    def step_set(self, wf_id, key, expect, status, task_id=None, note=None):
        """Atomic transition: only succeeds when the step is still in one of the `expect` states
        (the web server and the CLI runner may both evaluate the same workflow)."""
        with self.connect() as db:
            marks = ','.join('?' * len(expect))
            cur = db.execute(f'UPDATE steps SET status=?, task_id=COALESCE(?,task_id), note=? WHERE wf=? AND key=? AND status IN ({marks})',
                             (status, task_id, note, wf_id, key, *expect))
            return cur.rowcount == 1

    def wf_cancel(self, wf_id):
        self.wf_get(wf_id)
        with self.connect() as db:
            db.execute('UPDATE workflows SET cancelled=1 WHERE id=?', (wf_id,))
            db.execute("UPDATE steps SET status='cancelled', note='Workflow bị hủy' WHERE wf=? AND status IN ('waiting','blocked')", (wf_id,))

    def cancel(self, task_id):
        self.get(task_id)
        with self.connect() as db:
            db.execute("UPDATE tasks SET cancel=1, status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END, updated=? WHERE id=?",
                       (now(), task_id))
        self.event(task_id, 'cancel_requested', {})
        return self.get(task_id)

    def events(self, task_id, after=0):
        self.get(task_id)
        with self.connect() as db:
            return [dict(r) | {'data': json.loads(r['data'])} for r in db.execute(
                'SELECT * FROM events WHERE task_id=? AND seq>? ORDER BY seq LIMIT 100', (task_id, after))]

    def last_event_seq(self, task_id):
        with self.connect() as db:
            return db.execute('SELECT COALESCE(MAX(seq),0) FROM events WHERE task_id=?', (task_id,)).fetchone()[0]

    def requeue(self, task_id, make_payload):
        """Another round of the same task: same worktree, branch and id. Atomic, only from a finished state."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,payload,result FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise OrchError("Unknown task")
            if row['status'] not in CONTINUABLE:
                raise OrchError(f"Task đang ở trạng thái {row['status']}; chưa thể làm tiếp")
            payload = make_payload(json.loads(row['payload']), json.loads(row['result']) if row['result'] else {}, row['status'])
            db.execute("UPDATE tasks SET status='queued', payload=?, result=NULL, cancel=0, updated=? WHERE id=?",
                       (json.dumps(payload), now(), task_id))
        self.event(task_id, 'queued', {'provider': payload['provider'], 'round': payload['round'], 'continued': True})
        return self.get(task_id)

    # ---- numbered agents and owner settings ------------------------------------------------------------
    @staticmethod
    def _agent(row):
        return {**dict(row), 'settings': json.loads(row['settings'] or '{}')}

    def agent_new(self, provider, kind, settings=None):
        with self.connect() as db:
            return db.execute('INSERT INTO agents(provider,kind,settings,created) VALUES(?,?,?,?)',
                              (provider, kind, json.dumps(settings or {}), now())).lastrowid

    def agent_get(self, n):
        with self.connect() as db:
            row = db.execute('SELECT * FROM agents WHERE n=?', (n,)).fetchone()
        return self._agent(row) if row else None

    def agent_list(self):
        with self.connect() as db:
            return [self._agent(r) for r in db.execute('SELECT * FROM agents ORDER BY n')]

    def agent_update(self, n, **fields):
        if set(fields) - {'session_id', 'thread_task'}:
            raise OrchError("Unsupported agent field")
        if fields:
            with self.connect() as db:
                db.execute('UPDATE agents SET ' + ','.join(f'{k}=?' for k in fields) + ' WHERE n=?', (*fields.values(), n))

    def agent_setting(self, n, key, value):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT settings FROM agents WHERE n=?', (n,)).fetchone()
            if row is None:
                raise OrchError(f"Không có agent {n}")
            settings = json.loads(row['settings'] or '{}')
            settings[key] = value
            db.execute('UPDATE agents SET settings=? WHERE n=?', (json.dumps(settings), n))

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row['value']) if row else default

    def set_setting(self, key, value):
        with self.connect() as db:
            db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       (key, json.dumps(value)))

    def agent_active(self):
        """Tasks currently queued/running that belong to a numbered agent (one row per task)."""
        with self.connect() as db:
            rows = db.execute("SELECT id,agent,status,payload FROM tasks WHERE agent IS NOT NULL AND status IN ('queued','running')").fetchall()
        return [{'task_id': r['id'], 'agent': r['agent'], 'status': r['status'], 'round': json.loads(r['payload']).get('round', 1)} for r in rows]
