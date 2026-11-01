"""Per-URL latest validated input snapshots; promote only after the build succeeds."""
from __future__ import annotations
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

MAX_BYTES = 32 * 1024 * 1024


def public_error(error):
    """Release reports must not disclose local runner filenames."""
    if isinstance(error, OSError):
        return type(error).__name__ + ': ' + (error.strerror or 'I/O failure')
    return re.sub(r"(?<![A-Za-z0-9:/])(?:/(?:tmp|home|workspace|private|var|Users|runner|mnt)/|[A-Za-z]:[\\/])[^\s\"'<>]+",
                  '<local-path>', str(error))


class SourceValidationError(ValueError):
    """Expected input error, not an internal generator bug."""


class SourceUnavailableError(RuntimeError):
    """Neither fresh input nor a valid prior snapshot is available."""


class SourceCache:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.pending = {}
        self.values = {}
        self.sources = {}
        self.components = []

    def path(self, url):
        return self.directory / (hashlib.sha256(url.encode()).hexdigest() + '.json')

    def _read(self, url):
        path = self.path(url)
        if path.stat().st_size > MAX_BYTES * 2:
            raise ValueError('oversized cache entry')
        entry = json.loads(path.read_text(encoding='utf-8'))
        if type(entry['version']) is not int or entry['version'] != 1 or entry['url'] != url:
            raise ValueError('cache identity/version mismatch')
        if datetime.fromisoformat(entry['last_success']).tzinfo is None:
            raise ValueError('cache timestamp lacks timezone')
        packed = base64.b64decode(entry['data'], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            data = stream.read(MAX_BYTES + 1)
        if not data or len(data) > MAX_BYTES:
            raise ValueError('empty or oversized cached source')
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('cache checksum mismatch')
        return data, entry

    def get(self, url, loader, validator=None):
        if url in self.values:
            return self.values[url]
        error = None
        try:
            data = loader()
            if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES:
                raise ValueError('empty, oversized or non-binary source')
        except Exception as failure:
            error = failure
        if error is None and validator:
            try:
                validator(data)
            except SourceValidationError as failure:
                error = failure
        if error is not None:
            cache_error = None
            try:
                data, entry = self._read(url)
            except Exception as failure:
                cache_error = failure
            if cache_error is None and validator:
                try:
                    validator(data)
                except SourceValidationError as failure:
                    cache_error = failure
            if cache_error is not None:
                self.sources[url] = {'url': url, 'status': 'unavailable',
                                     'error': public_error(error), 'cache_error': public_error(cache_error)}
                raise SourceUnavailableError(
                    f'{url}: source failed ({public_error(error)}); no valid last-good cache '
                    f'({public_error(cache_error)}); refusing incomplete publication') from error
            self.sources[url] = {key: entry[key] for key in ('url', 'sha256', 'last_success')}
            self.sources[url].update(status='stale', error=public_error(error))
            print(f"[source-stale] {url}: using last-good {entry['last_success']} "
                  f"sha256={entry['sha256']} after source failure", file=sys.stderr)
        else:
            entry = {'version': 1, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(),
                     'last_success': datetime.now(timezone.utc).isoformat(),
                     'data': base64.b64encode(gzip.compress(data, mtime=0)).decode('ascii')}
            self.pending[url] = entry
            self.sources[url] = {key: entry[key] for key in ('url', 'sha256', 'last_success')}
            self.sources[url]['status'] = 'fresh'
        self.values[url] = data
        return data

    def commit(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        for url, entry in self.pending.items():
            path = self.path(url)
            temporary = path.with_suffix('.tmp')
            try:
                temporary.write_text(json.dumps(entry, ensure_ascii=False) + '\n', encoding='utf-8')
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

    def reuse_component(self, urls, metadata):
        for url in urls:
            self.pending.pop(url, None)
            source = self.sources.setdefault(url, {'url': url, 'status': 'unknown'})
            source.update(used=False, freshness='unknown')
        self.components.append(metadata)

    def report(self, success):
        return {'success': success, 'sources': list(self.sources.values()), 'components': self.components}
