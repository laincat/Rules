"""Published bootstrap requires provenance, safe files and cross-client parity."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import published_ai


class PublishedAITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshot = self.root / 'snapshot'
        self.snapshot.mkdir()
        self.mihomo = self.root / 'mihomo'
        self.mihomo.touch()
        self.domains = ['.suffix.example.com'] + [f'd{i}.example.com' for i in range(150)]
        self.extra = ['DOMAIN-KEYWORD,openai', 'IP-CIDR,1.2.3.0/24,no-resolve',
                      'IP-CIDR6,2001:db8::/32,no-resolve', 'IP-ASN,399358,no-resolve',
                      'AND,((DOMAIN-KEYWORD,antigravity-auto-updater-),(DOMAIN-SUFFIX,run.app))']
        self.assets = {'AI.list': ('# original timestamp\n' + '\n'.join(self.domains)).encode(),
                       'AI.Extra.list': '\n'.join(self.extra).encode(),
                       'AI.Extra.yaml': ('payload:\n' + '\n'.join('  - ' + x for x in self.extra)).encode(),
                       'AI.mrs': b'fake binary validated by mocked core', 'other.asset': b'complete snapshot'}
        for name, data in self.assets.items():
            (self.snapshot / name).write_bytes(data)
        self.manifest = {'schema': 1, 'source_sha': 'a' * 40,
                         'files': {name: hashlib.sha256(data).hexdigest() for name, data in self.assets.items()}}
        self.write_manifest()

    def write_manifest(self):
        (self.snapshot / published_ai.MANIFEST).write_text(json.dumps(self.manifest))

    def change(self, name, data):
        (self.snapshot / name).write_bytes(data)
        self.manifest['files'][name] = hashlib.sha256(data).hexdigest()
        self.write_manifest()

    def convert(self, command, **kwargs):
        self.assertEqual(command[1:4], ['convert-ruleset', 'domain', 'mrs'])
        self.assertEqual(Path(command[4]).read_bytes(), self.assets['AI.mrs'])
        text = '\n'.join('+' + d if d.startswith('.') else d for d in self.domains)
        Path(command[5]).write_text(text)
        return subprocess.CompletedProcess(command, 0, '', '')

    def load(self):
        with patch.object(published_ai.subprocess, 'run', side_effect=self.convert):
            return published_ai.load_published_ai(self.snapshot, self.mihomo)

    def test_complete_snapshot_returns_original_bytes_and_provenance(self):
        files, metadata = self.load()
        self.assertEqual(files, {name: self.assets[name] for name in published_ai.AI_FILES})
        self.assertEqual(metadata, {'source_sha': 'a' * 40,
                         'files': {name: self.manifest['files'][name] for name in published_ai.AI_FILES}})

    def test_non_ai_missing_or_corrupt_asset_rejects_entire_snapshot(self):
        (self.snapshot / 'other.asset').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.load()
        (self.snapshot / 'other.asset').unlink()
        with self.assertRaisesRegex(ValueError, 'missing or unsafe'):
            self.load()

    def test_missing_ai_group_member_rejected(self):
        del self.manifest['files']['AI.mrs']
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'complete AI group'):
            self.load()

    def test_unsafe_names_symlinks_and_unexpected_files_rejected(self):
        for name in ('../escape', '..\\escape', '/absolute', '\x00bad'):
            self.manifest['files'][name] = '0' * 64
            self.write_manifest()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'unsafe'):
                self.load()
            del self.manifest['files'][name]
        self.write_manifest()
        target = self.snapshot / 'other.asset'
        target.unlink()
        target.symlink_to(self.mihomo)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            self.load()
        target.unlink()
        target.write_bytes(self.assets['other.asset'])
        (self.snapshot / 'unexpected').touch()
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            self.load()

    def test_invalid_manifest_version_and_source_sha_rejected(self):
        for field, value in [('schema', 2), ('schema', True), ('source_sha', 'main')]:
            with self.subTest(field=field, value=value):
                original = self.manifest[field]
                self.manifest[field] = value
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, 'manifest'):
                    self.load()
                self.manifest[field] = original

    def test_domain_semantic_mismatch_rejected_even_with_valid_hashes(self):
        self.change('AI.list', self.assets['AI.list'] + b'\nnew.example.com')
        with self.assertRaisesRegex(ValueError, 'domain formats disagree'):
            self.load()

    def test_small_invalid_duplicate_domainset_rejected(self):
        for data, error in [(b'example.com\n', 'too small'),
                (self.assets['AI.list'] + b'\nhttps://example.com/path', 'invalid published'),
                (self.assets['AI.list'] + b'\nd0.example.com', 'duplicate')]:
            self.change('AI.list', data)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.load()

    def test_extra_semantic_mismatch_rejected_even_with_valid_hashes(self):
        self.change('AI.Extra.yaml', b'payload:\n - DOMAIN-KEYWORD,different\n')
        with self.assertRaisesRegex(ValueError, 'Extra formats disagree'):
            self.load()

    def test_unknown_or_overbroad_extra_rules_rejected(self):
        for rule in ['URL-REGEX,.*', 'IP-CIDR,0.0.0.0/0,PROXY',
                     'AND,((DOMAIN-KEYWORD,ai),(DOMAIN-SUFFIX,com))']:
            with self.subTest(rule=rule):
                self.change('AI.Extra.list', rule.encode())
                with self.assertRaisesRegex(ValueError, 'invalid or duplicate'):
                    self.load()

    def test_malformed_yaml_rejected(self):
        for text in ['payload: []', 'payload:\nDOMAIN-KEYWORD,openai', '# comments only']:
            with self.subTest(text=text):
                self.change('AI.Extra.yaml', text.encode())
                with self.assertRaises(ValueError):
                    self.load()

    def test_mihomo_missing_or_decode_failure_rejected(self):
        with self.assertRaisesRegex(ValueError, 'mihomo executable required'):
            published_ai.load_published_ai(self.snapshot, None)
        with patch.object(published_ai.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 1, '', 'invalid MRS')):
            with self.assertRaisesRegex(ValueError, 'decode failed'):
                published_ai.load_published_ai(self.snapshot, self.mihomo)


if __name__ == '__main__':
    unittest.main()
