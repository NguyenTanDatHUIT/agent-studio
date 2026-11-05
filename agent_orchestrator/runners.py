"""Explicit web-owned foreground runners. No shell or detached model processes."""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from .config import OrchError
from .engine import Engine
from .readiness import probe


class Runners:
    def __init__(self, config):
        self.config = config
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.threads = []
        self.states = {}

    def update(self, provider, **fields):
        with self.lock:
            self.states.setdefault(provider, {}).update(fields, heartbeat=datetime.now(timezone.utc).isoformat())

    def snapshot(self):
        with self.lock:
            return {name: dict(value) for name, value in self.states.items()}

    def start(self):
        self.config.execution_allowed()
        providers = [p for p in ('claude', 'codex') if self.config.data.get('providers', {}).get(p, {}).get('command')]
        if not providers or not self.config.data.get('tests'):
            raise OrchError('Configure at least one provider and a functional test profile before starting runners')
        for provider in providers:
            checked = probe(self.config, provider)
            if not checked['compatible']:
                raise OrchError(f'{provider} CLI is unavailable/incompatible: {checked}')
        for provider in providers:
            self.update(provider, status='starting', error=None)
            thread = threading.Thread(target=self.loop, args=(provider,), name='runner-' + provider)
            self.threads.append(thread)
            thread.start()
        return self

    def loop(self, provider):
        try:
            engine = Engine(self.config)
            while not self.stop_event.is_set():
                self.update(provider, status='polling')
                task = engine.work_once(provider, cancelled=self.stop_event.is_set,
                                        on_claim=lambda task_id: self.update(provider, status='busy', task_id=task_id))
                self.update(provider, status='idle', task_id=None,
                            last_task=task['id'] if task else self.snapshot()[provider].get('last_task'))
                self.stop_event.wait(.5 if task else 1)
        except Exception as exc:
            self.update(provider, status='error', error=str(exc)[:1000])
        finally:
            if self.snapshot()[provider]['status'] != 'error':
                self.update(provider, status='stopped', task_id=None)

    def close(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join()
