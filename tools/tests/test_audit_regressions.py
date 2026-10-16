"""Offline regression coverage for the 2026-10-16 follow-up audit."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import docs_watch
import gen_diff
import publish_cnb_release as cnb
import release_snapshot as snapshot
ROOT = Path(__file__).resolve().parents[2]


class AuditTests(unittest.TestCase):
    def test_partial_source_failure_retains_fact_and_alerts(self):
        old = {'facts': {'config-yaml': {'value': 'hash', 'changed_at': 'old'}},
               'sources': {'config-yaml': {'ok': True, 'last_success': 'yesterday'}}}
        state = docs_watch.merge_state(old, {'release': 'same'}, {}, {'release', 'config-yaml'})
        self.assertEqual(state['facts']['config-yaml'], old['facts']['config-yaml'])
        self.assertEqual(state['sources']['config-yaml']['last_success'], 'yesterday')
        self.assertTrue(any('config-yaml' in s for s in docs_watch.attention_reasons(old, state, [], [], '已更新')))
        recovered = docs_watch.merge_state(state, {'release': 'same', 'config-yaml': 'hash'}, {}, {'release', 'config-yaml'})
        self.assertFalse(docs_watch.attention_reasons(state, recovered, [], [], '已更新'))

    def test_equal_size_binary_change_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'x.mrs').write_bytes(b'new')
            with patch.object(gen_diff, 'ROOT', root), patch.object(gen_diff, 'TEXT_FILES', []), \
                 patch.object(gen_diff, 'BINARY_FILES', ['x.mrs']), \
                 patch.object(gen_diff.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'old')), \
                 patch.object(sys, 'argv', ['gen_diff.py']):
                gen_diff.main()
            result = json.loads((root / 'diff.json').read_text())
            self.assertTrue(result['files']['x.mrs']['binary_changed'])
            self.assertIn('未计算条目差异', (root / 'DIFF.md').read_text())

    def test_api_and_upload_boundaries(self):
        for url in ['http://api.cnb.cool/x', 'https://evil.example/x', 'https://api.cnb.cool.evil/x',
                    'https://user@api.cnb.cool/x', 'https://api.cnb.cool:8443/x']:
            with self.assertRaises(ValueError):
                cnb.secure_url(url, api=True)
        cnb.secure_url('https://api.cnb.cool/x', api=True)
        cnb.secure_url('https://bucket.cos.ap-guangzhou.myqcloud.com/x')
        with self.assertRaises(ValueError):
            cnb.secure_url('https://myqcloud.com.evil/x')
        with self.assertRaises(ValueError):
            cnb.NoRedirect().redirect_request(None, None, 307, '', {}, 'https://evil.example/')

    def test_snapshot_rejects_mixed_revision_and_unsafe_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'x.list').write_bytes(b'one')
            manifest = snapshot.build(root, 'a' * 40)
            assets = {'x.list': {'digest': 'sha256:' + hashlib.sha256(b'one').hexdigest()}}
            snapshot.validate(manifest, assets)
            assets['x.list']['digest'] = 'sha256:' + hashlib.sha256(b'two').hexdigest()
            with self.assertRaises(ValueError):
                snapshot.validate(manifest, assets)
            manifest['files'] = {'../escape': 'a' * 64}
            with self.assertRaises(ValueError):
                snapshot.validate(manifest, {})

    def test_workflow_guards(self):
        gen = (ROOT / '.github/workflows/gen-rulesets.yml').read_text()
        self.assertNotIn('--jq --arg', gen)
        self.assertIn('sha256sum --check --strict', gen)
        self.assertIn('needs: gen', gen)
        self.assertIn('persist-credentials: false', gen)
        docs = (ROOT / '.github/workflows/docs-watch.yml').read_text()
        self.assertIn('if: always() &&', docs)
        self.assertIn('git rebase origin/main', docs)
        sync = (ROOT / '.github/workflows/sync-cnb.yml').read_text()
        self.assertIn('ref: main', sync)
        self.assertIn('--force-with-lease=', sync)
        self.assertIn('release_snapshot.py fetch', sync)
        for workflow in (ROOT / '.github/workflows').glob('*.yml'):
            for line in workflow.read_text().splitlines():
                if 'uses: actions/' in line:
                    self.assertRegex(line, r'@[0-9a-f]{40}')

    def test_release_digest_function_unchanged_and_missing(self):
        workflow = (ROOT / '.github/workflows/gen-rulesets.yml').read_text()
        start = workflow.index('          digest() {')
        end = workflow.index('\n          uploads=()', start)
        function = '\n'.join(line[10:] for line in workflow[start:end].splitlines())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'release.json'
            path.write_text(json.dumps({'assets': [{'name': 'x.list', 'digest': 'sha256:' + 'a' * 64}]}))
            script = 'set -euo pipefail\nrelease_json="$1"\n' + function + '\n[ "$(digest x.list)" = "' + 'a' * 64 + '" ]\n[ -z "$(digest missing.list)" ]\n'
            subprocess.run(['bash', '-c', script, 'test', str(path)], check=True)

    def test_artifact_tar_preserves_paths_and_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, dest = root / 'source', root / 'dest'
            (source / 'Mihomo/Ruleset').mkdir(parents=True)
            dest.mkdir()
            (source / 'Mihomo/Ruleset/.hidden').write_text('metadata')
            (source / 'Mihomo/Ruleset/x.mrs').write_bytes(b'\x00\xff')
            archive = root / 'generated-rules.tar'
            subprocess.run(['tar', '-cf', str(archive), 'Mihomo/Ruleset'], cwd=source, check=True)
            subprocess.run(['tar', '-xf', str(archive)], cwd=dest, check=True)
            self.assertEqual((dest / 'Mihomo/Ruleset/.hidden').read_text(), 'metadata')
            self.assertEqual((dest / 'Mihomo/Ruleset/x.mrs').read_bytes(), b'\x00\xff')

    def test_snapshot_rejects_manifest_replacement_after_download(self):
        data = b'one'
        manifest = {'schema': 1, 'source_sha': 'a' * 40, 'files': {'x.list': snapshot.sha(data)}}
        raw = json.dumps(manifest).encode()
        assets = [{'id': 1, 'name': snapshot.MANIFEST, 'digest': 'sha256:' + snapshot.sha(raw)},
                  {'id': 2, 'name': 'x.list', 'digest': 'sha256:' + snapshot.sha(data)}]
        second = [dict(assets[0], id=3), assets[1]]
        def download(repo, asset, dest):
            dest.write_bytes(raw if asset['name'] == snapshot.MANIFEST else data)
        with tempfile.TemporaryDirectory() as tmp, patch.object(snapshot, 'download', side_effect=download), \
             patch.object(snapshot, 'gh_json', side_effect=[{'assets': assets}, {'assets': second}]):
            with self.assertRaisesRegex(ValueError, 'changed during download'):
                snapshot.fetch(Path(tmp), 'owner/repo')

    def test_rebase_preserves_concurrent_docs_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL)
            git('init', '-q', '-b', 'main')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            (root / 'rule.list').write_text('old')
            (root / 'docs.md').write_text('old docs')
            git('add', '.')
            git('commit', '-qm', 'base')
            git('checkout', '-qb', 'generated')
            (root / 'rule.list').write_text('new')
            git('commit', '-qam', 'rules')
            git('checkout', 'main')
            (root / 'docs.md').write_text('concurrent docs')
            git('commit', '-qam', 'docs')
            git('checkout', 'generated')
            git('rebase', 'main')
            self.assertEqual((root / 'docs.md').read_text(), 'concurrent docs')
            self.assertEqual((root / 'rule.list').read_text(), 'new')

    def test_privileged_restore_rejects_symlink_artifact(self):
        import tarfile
        import restore_generated
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.tar'
            with tarfile.open(archive, 'w') as tar:
                link = tarfile.TarInfo('DIFF.md')
                link.type = tarfile.SYMTYPE
                link.linkname = '.git/config'
                tar.addfile(link)
            with self.assertRaisesRegex(ValueError, 'links/devices'):
                restore_generated.restore(archive, tmp)

    def test_approved_routing_preserves_drop_and_lan_tun(self):
        config = (ROOT / 'Mihomo/config.yaml').read_text()
        self.assertIn('allow-lan: true', config)
        self.assertIn('tun:\n  enable: true', config)
        self.assertIn('RULE-SET,adblock-drop,REJECT-DROP', config)
        self.assertIn('RULE-SET,adblock,🛡️ 广告拦截', config)
        self.assertIn('RULE-SET,ozon,🇷🇺 Ozon', config)
        self.assertIn('proxies: [REJECT, DIRECT]', config)
        self.assertIn('name: "🇷🇺 Ozon", type: select, proxies: [DIRECT,', config)
