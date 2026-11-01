"""Revalidate a complete published snapshot before whole-AI bootstrap fallback.

The caller must obtain the directory through release_snapshot.fetch(), which
checks immutable GitHub asset IDs, digests and the upload-last manifest. This
helper never downloads data or treats aggregate outputs as per-source inputs.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import tempfile

from rule_validation import normalize_domain, validate_source_text

AI_FILES = ('AI.list', 'AI.Extra.list', 'AI.mrs', 'AI.Extra.yaml')
MANIFEST = 'snapshot-manifest.json'


def _body(data, name):
    text = data.decode('utf-8-sig')
    validate_source_text(name, text)
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def _domains(lines, prefix):
    result = set()
    for line in lines:
        suffix = line.startswith(prefix)
        domain = line[len(prefix):] if suffix else line
        if normalize_domain(domain) != domain:
            raise ValueError('invalid published AI domain')
        rule = ('suffix' if suffix else 'exact', domain)
        if rule in result:
            raise ValueError('duplicate published AI domain')
        result.add(rule)
    if len(result) <= 120:
        raise ValueError('published AI domain baseline is too small')
    return result


def _extra(lines):
    # Avoid permissive parsers that silently discard unsupported syntax.
    from gen_rulesets import KELEE_LOGICAL_PAIRS, normalize_wildcard
    result = set()
    for line in lines:
        parts = line.split(',')
        kind = parts[0]
        if kind == 'AND':
            match = re.fullmatch(r'AND,\(\(DOMAIN-KEYWORD,([a-z0-9._-]+)\),'
                                 r'\(DOMAIN-SUFFIX,([a-z0-9.-]+)\)\)', line)
            valid = bool(match and match.groups() in KELEE_LOGICAL_PAIRS)
        elif kind == 'DOMAIN-KEYWORD':
            valid = len(parts) == 2 and bool(re.fullmatch(r'[a-z0-9._-]+', parts[1]))
        elif kind == 'DOMAIN-WILDCARD':
            valid = len(parts) == 2 and normalize_wildcard(parts[1]) == parts[1]
        elif kind in ('IP-CIDR', 'IP-CIDR6'):
            valid = len(parts) == 3 and parts[2] == 'no-resolve'
            if valid:
                try:
                    network = ipaddress.ip_network(parts[1], strict=True)
                    valid = (network.version == (4 if kind == 'IP-CIDR' else 6)
                             and str(network) == parts[1])
                except ValueError:
                    valid = False
        elif kind == 'IP-ASN':
            valid = (len(parts) == 3 and parts[2] == 'no-resolve'
                     and parts[1].isdigit() and 0 < int(parts[1]) <= 4294967295)
        else:
            valid = False
        if not valid or line in result:
            raise ValueError('invalid or duplicate published AI Extra rule')
        result.add(line)
    if not result:
        raise ValueError('empty published AI Extra baseline')
    return result


def load_published_ai(directory, mihomo):
    """Return unchanged four-file AI bytes and source_sha/files-hash metadata.

    Reject incomplete/corrupt snapshots and cross-format semantic drift. This
    represents a visibly stale whole group, not reconstructed upstream inputs.
    """
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('published snapshot is not a regular directory')
    manifest_path = directory / MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('missing or unsafe snapshot manifest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or type(manifest.get('schema')) is not int
            or manifest['schema'] != 1
            or not isinstance(manifest.get('source_sha'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', manifest['source_sha'])):
        raise ValueError('invalid snapshot manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files or not set(AI_FILES) <= files.keys():
        raise ValueError('snapshot lacks complete AI group')
    assets = {}
    for name, digest in files.items():
        if (not isinstance(name, str) or '/' in name or '\\' in name or '\x00' in name
                or name in ('', '.', '..', MANIFEST)
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('unsafe snapshot asset entry')
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or unsafe snapshot asset')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('snapshot asset digest mismatch')
        if name in AI_FILES:
            assets[name] = data
    if {p.name for p in directory.iterdir()} != set(files) | {MANIFEST}:
        raise ValueError('unexpected files in published snapshot')
    surge_domains = _domains(_body(assets['AI.list'], 'AI.list'), '.')
    surge_extra = _extra(_body(assets['AI.Extra.list'], 'AI.Extra.list'))
    yaml_lines = _body(assets['AI.Extra.yaml'], 'AI.Extra.yaml')
    if (not yaml_lines or yaml_lines[0] != 'payload:'
            or not all(line.startswith('- ') for line in yaml_lines[1:])):
        raise ValueError('invalid published AI Extra YAML payload')
    if _extra([line[2:] for line in yaml_lines[1:]]) != surge_extra:
        raise ValueError('published AI Extra formats disagree')
    if not mihomo or not Path(mihomo).is_file():
        raise ValueError('mihomo executable required to verify published AI.mrs')
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / 'AI.mrs'
        output = Path(temporary) / 'AI.txt'
        source.write_bytes(assets['AI.mrs'])
        result = subprocess.run(
            [str(Path(mihomo).resolve()), 'convert-ruleset', 'domain', 'mrs', str(source), str(output)],
            capture_output=True, text=True, timeout=60)
        if result.returncode or not output.is_file():
            raise ValueError('published AI.mrs decode failed')
        if _domains(_body(output.read_bytes(), 'AI.mrs'), '+.') != surge_domains:
            raise ValueError('published AI domain formats disagree')
    return assets, {'source_sha': manifest['source_sha'],
                    'files': {name: files[name] for name in AI_FILES}}
