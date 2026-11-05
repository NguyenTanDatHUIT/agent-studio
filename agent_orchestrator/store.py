from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import OrchError


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
            ''')

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
            db.execute('INSERT INTO tasks VALUES(?,?,?,NULL,0,?,?)',
                       (task['id'], 'queued', json.dumps(task), now(), now()))
        self.event(task['id'], 'queued', {'provider': task['provider']})

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
