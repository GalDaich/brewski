"""Regression tests: fake brew only; no packages, sudo, or real passwords.

Run: python3 -m unittest discover -s tests -v
The script fixture changes only the lock path, to avoid touching user state.
PTY/process tests require normal macOS process and terminal access.
"""
import itertools
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'bin/brewski'
MOCK = r'''
import json, os, subprocess, sys, time, signal
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['TEST_LOG'], 'a') as f:
    f.write(json.dumps({'args': args, 'no_autoremove': os.getenv('HOMEBREW_NO_AUTOREMOVE'), 'greedy': os.getenv('HOMEBREW_UPGRADE_GREEDY')}) + '\n')
mode = os.getenv('TEST_MODE', '')
if mode == 'hang' and args == ['update']:
    child = subprocess.Popen(['/bin/sleep', '60'])
    Path(os.environ['TEST_PID']).write_text(str(child.pid))
    def terminate(sig, frame):
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: pass
        sys.exit(128 + sig)
    signal.signal(signal.SIGTERM, terminate)
    child.wait()
if mode == 'self-upgrade' and args[:2] == ['upgrade', '--formula']:
    Path(os.environ['TEST_SCRIPT']).unlink()
if mode == 'self-upgrade' and args[:2] == ['upgrade', '--cask']:
    # Headless input should fail gracefully inside the surviving snapshot,
    # rather than fail to execute a script removed by the earlier upgrade.
    result = subprocess.run([os.environ['SUDO_ASKPASS'], 'Password:'], capture_output=True, text=True)
    assert result.returncode == 1, result
    assert 'no terminal is available' in result.stderr, result.stderr
    assert result.stdout == '', result.stdout
if mode == 'outdated' and args[0] == 'outdated':
    print('example (1.0) < 2.0 [pinned]')
if ' '.join(args) == os.getenv('TEST_FAIL'):
    sys.exit(7)
'''

class BrewskiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='brewski-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.tmp = self.root / 'runtime with spaces'
        self.tmp.mkdir()
        self.lock = self.root / 'lock'
        self.script = self.root / 'brewski'
        source = SOURCE.read_text()
        old = 'LOCK_DIR="${HOME}/Library/Caches/brewski"'
        self.assertEqual(source.count(old), 1)
        self.script.write_text(source.replace(old, 'LOCK_DIR="' + str(self.lock) + '"'))
        self.script.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('HOMEBREW_', 'BREWSKI_'))}
        self.env.update(PATH=str(self.bin) + ':/usr/bin:/bin:/usr/sbin:/sbin',
                        TMPDIR=str(self.tmp), TERM='xterm', NO_COLOR='1',
                        TEST_LOG=str(self.root/'log'), TEST_PID=str(self.root/'pid'),
                        TEST_SCRIPT=str(self.script), BREWSKI_RUNTIME_DIR=str(self.tmp))
        self.stub('brew', '#!' + sys.executable + '\n' + MOCK)
        self.stub('osascript', '#!/bin/sh\nexit 1\n')
        self.stub('terminal-notifier', '#!/bin/sh\nexit 1\n')
        (self.tmp/'last-sudo-notify').write_text(str(int(time.time())))

    def stub(self, name, text):
        target = self.bin/name
        target.write_text(text)
        target.chmod(0o755)

    def run_script(self, *args, **env):
        return subprocess.run([str(self.script), *args], env={**self.env, **env},
                              capture_output=True, text=True, start_new_session=True, timeout=15)

    def calls(self):
        p = self.root/'log'
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def assert_clean(self):
        self.assertEqual(list(self.tmp.glob('brewski-run.*')), [])

    def test_options(self):
        flags = ['--autoremove', '--greedy', '--no-quit', '--diagnostics']
        for enabled in itertools.product([False, True], repeat=4):
            with self.subTest(enabled=enabled):
                (self.root/'log').write_text('')
                args = [flag for flag, yes in zip(flags, enabled) if yes]
                r = self.run_script(*args, HOMEBREW_UPGRADE_GREEDY='1', HOMEBREW_NO_AUTOREMOVE='1')
                self.assertEqual(r.returncode, 0, r.stderr)
                calls = self.calls()
                commands = [c['args'] for c in calls]
                self.assertIn(['autoremove'] if enabled[0] else ['autoremove', '--dry-run'], commands)
                cask = next(c for c in commands if c[:2] == ['upgrade', '--cask'])
                self.assertEqual('--greedy' in cask, enabled[1])
                self.assertEqual('--no-quit' in cask, enabled[2])
                self.assertEqual(['config'] in commands, enabled[3])
                self.assertEqual(commands[1 if not enabled[3] else 2], commands[-1])
                for call in calls:
                    if call['args'][0] in ('upgrade', 'cleanup'):
                        self.assertEqual(call['no_autoremove'], '1')
                self.assert_clean()

    def test_cli_without_brew(self):
        (self.bin/'brew').unlink()
        for args, code in [(('--help',), 0), (('--version',), 0), (('--bad',), 2), (('--', 'bad'), 2)]:
            with self.subTest(args=args):
                r = self.run_script(*args)
                self.assertEqual(r.returncode, code, r.stderr)
        self.assertFalse(self.lock.exists())
        self.assertEqual(self.calls(), [])
        self.assertIn('0.1.0-dev', self.run_script('--version').stdout)
        self.assertEqual(self.run_script().returncode, 1)

    def test_failure_policy(self):
        for command, code in [('update', 1), ('upgrade --formula --display-times --no-ask', 1), ('missing', 1), ('doctor', 0)]:
            with self.subTest(command=command):
                (self.root/'log').write_text('')
                r = self.run_script(TEST_FAIL=command)
                self.assertEqual(r.returncode, code, r.stderr)
                if command == 'update': self.assertEqual(len(self.calls()), 1)
                if command == 'doctor': self.assertIn('completed with 1 warning', r.stdout)
                self.assert_clean()

    def test_remaining_updates_are_warning(self):
        r = self.run_script(TEST_MODE='outdated')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Updates remain', r.stderr)
        self.assertIn('completed with 1 warning', r.stdout)
        self.assertNotIn('Final outdated-package check completed', r.stdout)

    def test_verification_failure_is_distinct(self):
        r = self.run_script(TEST_FAIL='outdated --verbose --greedy-auto-updates')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Could not verify remaining updates', r.stderr)
        self.assertIn('completed with 2 warning', r.stdout)

    def test_inherited_no_quit(self):
        r = self.run_script(HOMEBREW_NO_UPGRADE_QUIT_CASKS='1')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Quit apps:  no', r.stdout)
        cask = next(c['args'] for c in self.calls() if c['args'][:2] == ['upgrade', '--cask'])
        self.assertIn('--no-quit', cask)

    def test_self_upgrade(self):
        r = self.run_script(TEST_MODE='self-upgrade')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.script.exists())
        self.assert_clean()

    def test_early_setup_failure_cleans_runtime(self):
        self.stub('chmod', '#!/bin/sh\ncase "$2" in */brewski-run.*/*) exit 1;; esac\nexec /bin/chmod "$@"\n')
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn('snapshot', r.stderr)
        self.assert_clean()
        self.assertEqual(self.calls(), [])

    def start_hanging(self):
        f = open(self.root/'process-output', 'w')
        self.addCleanup(f.close)
        p = subprocess.Popen([str(self.script)], env={**self.env, 'TEST_MODE':'hang'}, stdout=f, stderr=f, start_new_session=True)
        def cleanup():
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait(timeout=5)
        self.addCleanup(cleanup)
        for _ in range(200):
            if (self.root/'pid').exists(): return p, int((self.root/'pid').read_text())
            time.sleep(.02)
        self.fail('fake brew did not start')

    def test_lock_across_tmpdirs_and_release(self):
        p, child = self.start_hanging()
        alt = self.root/'other-tmp'; alt.mkdir()
        r = self.run_script(TMPDIR=str(alt))
        self.assertEqual(r.returncode, 1)
        self.assertIn('run lock', r.stderr)
        p.terminate(); self.assertEqual(p.wait(timeout=8), 143)
        self.assertEqual(self.run_script().returncode, 0)

    def test_cancel_discovery_failure_preserves_runtime(self):
        self.stub('pgrep', '#!/bin/sh\nexit 2\n')
        p, child = self.start_hanging()
        p.terminate()
        self.assertEqual(p.wait(timeout=8), 143)
        self.assertEqual(len(list(self.tmp.glob('brewski-run.*'))), 1)
        self.assertIn('runtime files retained', (self.root/'process-output').read_text())

    def test_signals_stop_descendants(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig):
                (self.root/'pid').unlink(missing_ok=True)
                p, child = self.start_hanging()
                p.send_signal(sig)
                self.assertEqual(p.wait(timeout=8), 128 + sig)
                for _ in range(50):
                    try: os.kill(child, 0)
                    except ProcessLookupError: break
                    time.sleep(.02)
                else: self.fail('descendant survived cancellation')
                self.assert_clean()

    def password(self, fail='', sig=None):
        if fail:
            self.stub('stty', '#!/bin/sh\ncase "$1" in ' + fail + ') exit 1;; esac\nexec /bin/stty "$@"\n')
        # A separate stdout pipe verifies passwords never mix with prompts.
        read_fd, write_fd = os.pipe()
        pid, tty = pty.fork()
        if pid == 0:
            os.close(read_fd)
            os.dup2(write_fd, 1); os.close(write_fd)
            os.execve(str(self.script), [str(self.script), '--askpass-helper', 'Password:'], self.env)
        os.close(write_fd)
        output = b''; finished = False; wait_status = None
        try:
            end = time.monotonic() + 5
            while time.monotonic() < end:
                if select.select([tty], [], [], .05)[0]:
                    try:
                        chunk = os.read(tty, 8192)
                        if not chunk: break
                        output += chunk
                    except OSError: break
                if b'Password:' in output:
                    self.assertFalse(termios.tcgetattr(tty)[3] & termios.ECHO)
                    if sig: os.killpg(pid, sig)
                    else: os.write(tty, b'FAKE-test-password\n')
                    break
                done, wait_status = os.waitpid(pid, os.WNOHANG)
                if done: finished = True; break
            else: self.fail('password helper did not respond')
            if not finished:
                for _ in range(100):
                    # macOS can wait for pending PTY output to drain on exit.
                    if select.select([tty], [], [], .02)[0]:
                        try: output += os.read(tty, 8192)
                        except OSError: pass
                    done, wait_status = os.waitpid(pid, os.WNOHANG)
                    if done: finished = True; break
                    time.sleep(.02)
                self.assertTrue(finished, 'password helper hung')
            while select.select([tty], [], [], .05)[0]:
                try:
                    chunk = os.read(tty, 8192)
                    if not chunk: break
                    output += chunk
                except OSError: break
            self.assertTrue(termios.tcgetattr(tty)[3] & termios.ECHO, 'echo not restored')
            secret = os.read(read_fd, 8192)
            self.assertNotIn(b'FAKE-test-password', output)
            return os.waitstatus_to_exitcode(wait_status), output, secret
        finally:
            if not finished:
                try: os.killpg(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                os.waitpid(pid, 0)
            os.close(tty); os.close(read_fd)

    def test_password_success_and_restore(self):
        code, output, secret = self.password()
        self.assertEqual(code, 0, output)
        self.assertEqual(secret, b'FAKE-test-password\n')

    def test_password_stty_save_failure(self):
        code, output, secret = self.password(fail='-g')
        self.assertNotEqual(code, 0)
        self.assertNotIn(b'Password:', output)
        self.assertIn(b'refusing to read a password', output)
        self.assertEqual(secret, b'')

    def test_password_stty_disable_failure(self):
        code, output, secret = self.password(fail='-echo')
        self.assertNotEqual(code, 0)
        self.assertNotIn(b'Password:', output)
        self.assertIn(b'refusing to read a password', output)
        self.assertEqual(secret, b'')

    def test_password_signal_restore(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig):
                code, output, secret = self.password(sig=sig)
                self.assertNotEqual(code, 0)
                self.assertEqual(secret, b'')

if __name__ == '__main__':
    unittest.main()
