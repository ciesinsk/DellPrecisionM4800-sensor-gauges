"""Prüft Interpreter-Auswahl und Start über einen symbolischen Link."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class LauncherTests(unittest.TestCase):
    def test_interpreter_selection_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix='monitor test ') as temp:
            root = Path(temp)
            repo = root / 'repo'
            repo.mkdir()
            shutil.copy(Path(__file__).resolve().parents[1] / 'start.sh', repo / 'start.sh')
            launcher = root / 'bin' / 'cpu-monitor'
            launcher.parent.mkdir()
            launcher.symlink_to(repo / 'start.sh')
            interpreters = {}
            for name, path in (
                ('local', repo / '.venv/bin/python'),
                ('active', root / 'active/bin/python'),
                ('explicit', root / 'explicit/bin/python'),
            ):
                path.parent.mkdir(parents=True)
                path.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + '" "$@"\n')
                path.chmod(0o755)
                interpreters[name] = path
            env = {k: v for k, v in os.environ.items()
                   if k not in ('VIRTUAL_ENV', 'CPU_MONITOR_PYTHON')}
            for expected, additions in (
                ('local', {}),
                ('active', {'VIRTUAL_ENV': str(root / 'active')}),
                ('explicit', {'VIRTUAL_ENV': str(root / 'active'),
                              'CPU_MONITOR_PYTHON': str(interpreters['explicit'])}),
            ):
                with self.subTest(expected=expected):
                    result = subprocess.run([str(launcher), 'argument with spaces'],
                                            env={**env, **additions}, cwd=root,
                                            capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout.splitlines(),
                                     [expected, str(repo / 'cpu_monitor.py'), 'argument with spaces'])
            result = subprocess.run([str(launcher)],
                                    env={**env, 'CPU_MONITOR_PYTHON': str(root / 'missing')},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(root / 'missing'), result.stderr)


if __name__ == '__main__':
    unittest.main()
