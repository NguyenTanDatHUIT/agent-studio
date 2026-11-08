"""Which browser the dashboard opens in: Chrome by default, system default as fallback, owner override by env var."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_orchestrator import browser

URL = 'http://127.0.0.1:8765/#token=abc'


class OpenDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='browser-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(browser.ENV, None)
        self.fake_chrome = self.tmp / 'chrome.exe'
        self.fake_chrome.write_text('', encoding='utf-8')

    def run_open(self, chrome=True, popen_error=None):
        with mock.patch.object(browser, 'find_chrome', return_value=str(self.fake_chrome) if chrome else None), \
             mock.patch.object(browser.subprocess, 'Popen', side_effect=popen_error) as popen, \
             mock.patch.object(browser.webbrowser, 'open') as default_open:
            result = browser.open_dashboard(URL)
        return result, popen, default_open

    def test_chrome_is_used_by_default_and_gets_the_url_as_one_argument(self):
        result, popen, default_open = self.run_open()
        self.assertEqual(result, str(self.fake_chrome))
        self.assertEqual(popen.call_args.args[0], [str(self.fake_chrome), URL])  # a list: no shell, no splitting
        default_open.assert_not_called()

    def test_without_chrome_the_system_default_browser_is_used(self):
        result, popen, default_open = self.run_open(chrome=False)
        self.assertIsNone(result)
        popen.assert_not_called()
        default_open.assert_called_once_with(URL)

    def test_default_override_wins_even_when_chrome_exists(self):
        os.environ[browser.ENV] = 'default'
        _, popen, default_open = self.run_open()
        popen.assert_not_called()
        default_open.assert_called_once_with(URL)

    def test_explicit_chrome_setting_behaves_like_the_default(self):
        os.environ[browser.ENV] = 'Chrome'
        result, _, default_open = self.run_open()
        self.assertEqual(result, str(self.fake_chrome))
        default_open.assert_not_called()

    def test_override_with_an_executable_path(self):
        other = self.tmp / 'other.exe'
        other.write_text('', encoding='utf-8')
        os.environ[browser.ENV] = f'"{other}"'
        result, popen, _ = self.run_open()
        self.assertEqual((result, popen.call_args.args[0]), (str(other), [str(other), URL]))

    def test_unusable_override_never_runs_anything(self):
        for bad in ('notepad', 'cmd.exe', r'..\x.exe', str(self.tmp / 'missing.exe'), str(self.tmp), str(self.tmp / 'a.bat')):
            (self.tmp / 'a.bat').write_text('', encoding='utf-8')
            os.environ[browser.ENV] = bad
            result, popen, default_open = self.run_open()
            self.assertIsNone(result, bad)
            popen.assert_not_called()
            default_open.assert_called_once_with(URL)

    def test_failure_to_launch_falls_back_to_the_default_browser(self):
        result, popen, default_open = self.run_open(popen_error=OSError('boom'))
        self.assertIsNone(result)
        popen.assert_called_once()
        default_open.assert_called_once_with(URL)

    def test_find_chrome_looks_in_the_program_files_folders(self):
        root = self.tmp / 'pf'
        exe = root / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
        exe.parent.mkdir(parents=True)
        exe.write_text('', encoding='utf-8')
        with mock.patch.dict(os.environ, {'ProgramFiles': str(root), 'ProgramFiles(x86)': '', 'LocalAppData': ''}):
            self.assertEqual(browser.find_chrome(), str(exe))
        with mock.patch.dict(os.environ, {'ProgramFiles': str(self.tmp / 'none'), 'ProgramFiles(x86)': '', 'LocalAppData': ''}), \
             mock.patch.dict('sys.modules', {'winreg': None}):
            self.assertIsNone(browser.find_chrome())


if __name__ == '__main__':
    unittest.main()
