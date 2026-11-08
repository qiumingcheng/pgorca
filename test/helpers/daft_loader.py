"""Native ABI fixtures and live postmaster checks for daft_loader.sql."""
import argparse
import os
from pathlib import Path
import shlex
import stat
import subprocess


def fixture_directory():
    directory = Path(os.environ['PG_ORCA_LOADER_FIXTURE_DIR'])
    info = directory.lstat()
    if (not directory.is_absolute() or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise RuntimeError('loader fixtures require an owned private directory')
    return directory


def setup():
    directory = fixture_directory()
    root = Path(__file__).resolve().parents[2]
    include = Path(os.environ.get('PG_ORCA_DAFT_BRIDGE_INCLUDE_DIR',
                                  root.parent / 'daft/src/daft-pg-bridge/include'))
    compiler = shlex.split(os.environ.get('CC', 'cc'))
    source = root / 'test/fixtures/daft_loader_fixture.c'
    for name, definitions in (('missing_symbol', ['-DMISSING_SYMBOL_FIXTURE']),
                              ('abi_major_mismatch', [])):
        output = directory / (name + '.so')
        if output.exists() or output.is_symlink():
            raise RuntimeError('refusing to overwrite a loader fixture')
        subprocess.run(compiler + ['-shared', '-fPIC', '-Wall', '-Werror',
                                  '-I', str(include), *definitions,
                                  str(source), '-o', str(output)], check=True)
        output.chmod(0o600)
    if (directory / 'not_present.so').exists():
        raise RuntimeError('missing-library fixture unexpectedly exists')
    print('P0-006-C fixtures ready')


def assert_preload():
    backend = Path('/proc') / str(int(os.environ['PG_ORCA_LOADER_BACKEND_PID']))
    status = dict(line.split(':', 1) for line in (backend / 'status').read_text().splitlines())
    postmaster = Path('/proc') / str(int(status['PPid']))
    if backend.stat().st_uid != os.geteuid() or postmaster.stat().st_uid != os.geteuid():
        raise RuntimeError('loader check must inspect the current user server')
    mappings = (postmaster / 'maps').read_text()
    if 'pg_orca.so' not in mappings:
        raise RuntimeError('postmaster did not preload pg_orca')
    if any(name in mappings for name in ('libdaft_pg_bridge', 'missing_symbol.so',
                                         'abi_major_mismatch.so')):
        raise RuntimeError('postmaster mapped a Bridge library')
    if len(list((postmaster / 'task').iterdir())) != 1:
        raise RuntimeError('postmaster started extra threads during preload')
    print('P0-006-C postmaster preload isolation verified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'assert-preload'))
    action = parser.parse_args().action
    if action == 'setup':
        setup()
    else:
        assert_preload()
