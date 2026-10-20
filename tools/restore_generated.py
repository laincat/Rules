#!/usr/bin/env python3
"""Restore only regular generated data from an unprivileged build artifact."""
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

DIRECTORIES = (
    'Surge/Advertising',
    'Surge/Ruleset',
    'Mihomo/Advertising',
    'Mihomo/Ruleset',
    'Mihomo/Sukka',
)
FILES = ('DIFF.md', 'diff.json', 'Mihomo/config.yaml')


def restore(archive, root):
    root = Path(root)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if sum(m.size for m in members) > 200 * 1024 * 1024:
            raise ValueError('artifact too large')
        names = set()
        for member in members:
            path = PurePosixPath(member.name)
            name = member.name.rstrip('/')
            if path.is_absolute() or '..' in path.parts or name in names:
                raise ValueError('unsafe or duplicate artifact path')
            if not (member.isfile() or member.isdir()):
                raise ValueError('artifact links/devices are forbidden')
            if not (name in FILES or any(name == d or name.startswith(d + '/') for d in DIRECTORIES)):
                raise ValueError('unexpected artifact path')
            names.add(name)
        if not all(d in names for d in DIRECTORIES) or not all(f in names for f in FILES):
            raise ValueError('incomplete artifact')
        for d in DIRECTORIES:
            shutil.rmtree(root / d)
        tar.extractall(root, members=members, filter='data')


if __name__ == '__main__':
    restore(sys.argv[1], Path.cwd())
