"""Offline guards for independently sourced product documentation."""
from pathlib import Path
import importlib.util
import json
import re
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('docs_watch_structure', ROOT / 'tools/docs_watch.py')
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)

class DocumentationStructureTests(unittest.TestCase):
    def test_official_source_maps_are_product_specific(self):
        for product, host in [('Surge', 'manual.nssurge.com'), ('Mihomo', 'wiki.metacubex.one')]:
            folder = ROOT / product / 'Docs'
            source = json.loads((folder / 'sources.json').read_text())
            self.assertEqual(source['product'], product)
            self.assertEqual(set(source['chapters']), {p.name for p in folder.glob('0*.md')})
            for chapter, urls in source['chapters'].items():
                self.assertTrue(urls)
                for url in urls:
                    self.assertEqual(urlparse(url).hostname, host)
                    self.assertIn(url, (folder / chapter).read_text())

    def test_guides_do_not_depend_on_other_product(self):
        for product, other in [('Surge', 'Mihomo'), ('Mihomo', 'Surge')]:
            folder = ROOT / product / 'Docs'
            for page in list(folder.glob('0*.md')) + [folder / 'readme.md', folder / 'sources.md']:
                self.assertNotRegex(page.read_text(), '(?i)' + other)

    def test_local_navigation_targets_exist(self):
        for product in ['Surge', 'Mihomo']:
            for page in (ROOT / product / 'Docs').glob('*.md'):
                for target in re.findall(r'\]\(([^\s)]+)\)', page.read_text()):
                    if '://' in target or target.startswith('#'):
                        continue
                    path = target.split('#', 1)[0]
                    self.assertTrue((page.parent / path).exists(), f'{page}: missing {target}')

    def test_generated_state_preserves_markers_and_source_independence(self):
        for product in ['Surge', 'Mihomo']:
            folder = ROOT / product / 'Docs'
            state = json.loads((folder / 'upstream.json').read_text())
            rendered = watch.RENDERERS[product.lower()](state)
            for marker in ['<!-- AUTO-STATE:BEGIN -->', '<!-- AUTO-STATE:END -->']:
                self.assertEqual((folder / 'readme.md').read_text().count(marker), 1)
                self.assertEqual(rendered.count(marker), 1)
            self.assertNotIn('community-yamls', state.get('facts', {}))
            self.assertNotIn('community-yamls', state.get('sources', {}))
            self.assertNotIn('HenryChiao', rendered)
            self.assertNotIn('Mihomo' if product == 'Surge' else 'Surge', rendered)

    def test_mihomo_changelog_template_is_self_contained(self):
        log = {'releases':[{'tag':'v1.0', 'date':'2026-01-01', 'body':''}],
               'alpha':[{'sha':'abc', 'date':'2026-01-02', 'message':''}],
               'week_start':'2026-01-01'}
        result = watch.render_mihomo_changelog(log, {}, [])
        self.assertNotIn('Surge', result)
        self.assertNotIn('只有配置面', result)
        self.assertNotIn('按月', result)

    def test_yaml_examples_parse(self):
        import yaml
        for page in (ROOT / 'Mihomo/Docs').glob('*.md'):
            for block in re.findall(r'```ya?ml\n(.*?)\n```', page.read_text(), re.S):
                try:
                    yaml.safe_load(block)
                except yaml.YAMLError as exc:
                    self.fail(f'{page.name}: {exc}')

if __name__ == '__main__':
    unittest.main()

class ReleaseNoteNamesTests(unittest.TestCase):
    def test_names_keep_original_without_translation_request(self):
        pending = []
        output = watch.translate_block('# Tailscale\n**WireGuard**\n- Tailscale', {}, pending)
        self.assertFalse(pending)
        self.assertIn('**WireGuard**', output)
        self.assertNotIn('- WireGuard**', output)


class SourceMigrationTests(unittest.TestCase):
    def test_old_kb_source_retained_until_replacement_fetch_succeeds(self):
        key = "kb/surge-knowledge-base/index.md"
        old = {"pages": {key: "old-hash"}, "sources": {"page:" + key: {"ok": False}}}
        watch.retire_obsolete_sources("surge", old, {})
        self.assertIn(key, old["pages"])
        watch.retire_obsolete_sources("surge", old, {"kb/surge-knowledge-base/readme.md": "new-hash"})
        self.assertNotIn(key, old["pages"])
        self.assertNotIn("page:" + key, old["sources"])

    def test_retired_community_source_does_not_mask_official_failures(self):
        old = {"facts": {"community-yamls": {}, "metadocs": {}},
               "sources": {"community-yamls": {"ok": False}, "metadocs": {"ok": False}}}
        watch.retire_obsolete_sources("mihomo", old, {})
        self.assertNotIn("community-yamls", old["facts"])
        self.assertNotIn("community-yamls", old["sources"])
        self.assertFalse(old["sources"]["metadocs"]["ok"])
