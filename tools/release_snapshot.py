#!/usr/bin/env python3
"""Build or fetch a hash-verified coherent rolling-release snapshot.

The manifest is uploaded last. A partially updated rolling release fails closed.
Downloads use immutable asset IDs; no mutable filename URL is trusted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

MANIFEST = 'snapshot-manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(directory, source):
    if not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('invalid source SHA')
    files = {f.name: sha(f.read_bytes()) for f in sorted(directory.iterdir())
             if f.is_file() and f.name != MANIFEST}
    manifest = {'schema': 1, 'source_sha': source, 'files': files}
    (directory / MANIFEST).write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    return manifest


def validate(manifest, assets):
    if manifest.get('schema') != 1 or not re.fullmatch(r'[0-9a-f]{40}', manifest.get('source_sha', '')):
        raise ValueError('invalid snapshot manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('empty manifest')
    for name, digest in files.items():
        if Path(name).name != name or name in ('.', '..', MANIFEST) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid asset entry')
        if name not in assets or assets[name].get('digest') != 'sha256:' + digest:
            raise ValueError('release is incomplete or changed: ' + name)


def gh_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint]))


def download(repo, asset, destination):
    with destination.open('wb') as f:
        subprocess.run(['gh', 'api', f'repos/{repo}/releases/assets/{asset["id"]}',
                        '-H', 'Accept: application/octet-stream'], stdout=f, check=True)


def fetch(directory, repo):
    release = gh_json(f'repos/{repo}/releases/tags/latest')
    assets = {a['name']: a for a in release['assets']}
    if MANIFEST not in assets:
        raise ValueError('snapshot manifest not yet published; retry after generator succeeds')
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError('snapshot directory must be empty')
    download(repo, assets[MANIFEST], directory / MANIFEST)
    raw = (directory / MANIFEST).read_bytes()
    if assets[MANIFEST].get('digest') != 'sha256:' + sha(raw):
        raise ValueError('manifest digest mismatch')
    manifest = json.loads(raw)
    validate(manifest, assets)
    for name, digest in manifest['files'].items():
        if name.endswith('.tar.gz'):
            continue
        download(repo, assets[name], directory / name)
        if sha((directory / name).read_bytes()) != digest:
            raise ValueError('asset digest mismatch: ' + name)
    latest = gh_json(f'repos/{repo}/releases/tags/latest')
    current = {a['name']: a for a in latest['assets']}
    if current.get(MANIFEST, {}).get('id') != assets[MANIFEST]['id']:
        raise ValueError('snapshot changed during download; retry')
    validate(manifest, current)
    print('Verified snapshot source: ' + manifest['source_sha'])
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['build', 'fetch'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('--source')
    parser.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY'))
    args = parser.parse_args()
    if args.mode == 'build':
        build(args.directory, args.source)
    else:
        fetch(args.directory, args.repo)
