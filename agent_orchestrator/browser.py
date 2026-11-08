"""Open the dashboard in the owner's preferred browser.

Default: Google Chrome when it is installed, otherwise the system default browser (the old behaviour).
Override with the environment variable AGENT_STUDIO_BROWSER:
  default        always use the system default browser
  chrome         Google Chrome (falls back to the system default if it is not installed)
  <path>.exe     that executable (an absolute path to an existing .exe)
"""
from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path

ENV = 'AGENT_STUDIO_BROWSER'


def find_chrome():
    """Path of chrome.exe, or None. Looks in the usual install folders, then the Windows App Paths registry."""
    roots = [os.environ.get(name) for name in ('ProgramFiles', 'ProgramFiles(x86)', 'LocalAppData')]
    for root in filter(None, roots):
        candidate = Path(root) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
        if candidate.is_file():
            return str(candidate)
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe') as key:
                    value = winreg.QueryValue(key, None)
                if value and Path(value).is_file():
                    return value
            except OSError:
                continue
    except ImportError:
        pass
    return None


def choose_browser(setting=None):
    """The executable to launch, or None for the system default browser."""
    setting = (os.environ.get(ENV, '') if setting is None else setting).strip()
    if setting.lower() == 'default':
        return None
    if setting and setting.lower() != 'chrome':
        path = Path(setting.strip('"'))
        if path.is_absolute() and path.suffix.lower() == '.exe' and path.is_file():
            return str(path)
        return None  # an unusable override must never run anything: use the system default
    return find_chrome()


def open_dashboard(url):
    """Open `url` in the chosen browser; fall back to the system default browser if that fails."""
    exe = choose_browser()
    if exe:
        try:
            subprocess.Popen([exe, url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            return exe
        except OSError:
            pass
    webbrowser.open(url)
    return None
