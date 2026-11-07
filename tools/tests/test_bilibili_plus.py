"""Offline artifact/packaging tests; not an iOS playback validation."""
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILES = ROOT / 'Surge/Advertising/BilibiliPlus'
BASE = 'https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus'

class BilibiliPlusTests(unittest.TestCase):
    def test_manifest_hashes(self):
        lines = (FILES / 'Bilibili.Compatibility.SHA256SUMS').read_text().splitlines()
        self.assertEqual(len(lines), 4)
        for line in lines:
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256((FILES/name).read_bytes()).hexdigest(), digest, name)

    def test_boxjs_defaults(self):
        data=json.loads((FILES/'Bilibili.Compatibility.boxjs.json').read_text())
        self.assertEqual(len(data['apps']),1)
        settings={item['id']:item['val'] for item in data['apps'][0]['settings']}
        self.assertEqual(settings, {'laincat_bili_enabled':True,'laincat_bili_optimize':False,'laincat_bili_diagnostics':True})
        self.assertEqual(set(data['apps'][0]['keys']),set(settings))

    def test_module_nonoverlap_and_real_dependency(self):
        text=(FILES/'Bilibili.Compatibility.sgmodule').read_text()
        self.assertNotIn('example.invalid',text)
        self.assertIn('script-path='+BASE+'/Bilibili.Compatibility.js',text)
        lines=text.splitlines()
        original=next(x for x in lines if x.startswith('bilibili.protobuf.response ='))
        added=next(x for x in lines if x.startswith('bilibili.compat.playback ='))
        regex=lambda line:re.compile(re.search(r'pattern=(.*?),argument=',line).group(1))
        for host in ('grpc.biliapi.net','app.bilibili.com'):
            for endpoint in ('app.playurl.v1.PlayURL/PlayView','app.playerunite.v1.Player/PlayViewUnite','pgc.gateway.player.v2.PlayURL/PlayView'):
                url=f'https://{host}/bilibili.{endpoint}'
                self.assertIsNotNone(regex(added).fullmatch(url))
                self.assertIsNone(regex(original).fullmatch(url))
        self.assertIn('max-size=-1',original)
        self.assertIn('max-size=2097152',added)

    def test_original_surge_sections_and_parameters_preserved(self):
        with tarfile.open(FILES/'Bilibili.Compatibility.Source.tar.gz','r:gz') as archive:
            original=archive.extractfile('sparkle/release/surge/module/bilibili.sgmodule').read().decode()
        current=(FILES/'Bilibili.Compatibility.sgmodule').read_text()
        def sections(text):
            result={}; section=None
            for line in text.splitlines():
                if line.startswith('['): section=line; result[section]=[]
                elif section and line.strip(): result[section].append(line)
            return result
        old,new=sections(original),sections(current)
        for name in ('[Rule]','[Map Local]','[Body Rewrite]','[MITM]'):
            self.assertEqual(old[name],new[name],name)
        for prefix in ('#!arguments=','#!arguments-desc='):
            self.assertEqual(next(x for x in original.splitlines() if x.startswith(prefix)),next(x for x in current.splitlines() if x.startswith(prefix)))
        self.assertEqual(len(old['[Script]']),7)
        self.assertEqual(len(new['[Script]']),8)
        self.assertIn('BilibiliPlus',current)
        self.assertIn('原 B站 Surge 模块',current)
        self.assertIn('非完整移植',current)

    def test_source_complete_and_matches_published_artifacts(self):
        with tarfile.open(FILES/'Bilibili.Compatibility.Source.tar.gz','r:gz') as archive:
            names=set(archive.getnames())
            for name in ('build.mjs','package.py','tests/adapter.test.ts','sparkle/package-lock.json','sparkle/src/script/bilibili/protobuf/pcdn-adapter.ts','licenses/Sparkle-GPL-3.0.txt','licenses/Sukka-MIT.txt','licenses/BV-MIT.txt','THIRD_PARTY_LICENSES.txt'):
                self.assertIn(name,names)
            self.assertFalse(any(name.startswith('/') or '..' in Path(name).parts or 'node_modules' in Path(name).parts for name in names))
            for name in ('Bilibili.Compatibility.js','Bilibili.Compatibility.sgmodule','Bilibili.Compatibility.boxjs.json'):
                self.assertEqual(archive.extractfile('release/'+name).read(), (FILES/name).read_bytes())
            self.assertIn(b'tests 48',archive.extractfile('test-results.txt').read())

if __name__ == '__main__': unittest.main()
