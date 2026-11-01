"""Independent orchestration checks for coherent whole-AI bootstrap reuse."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules
from source_cache import SourceCache, SourceUnavailableError


class BootstrapReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = SourceCache(self.root / 'cache')
        self.assets = {name: ('unchanged old ' + name).encode() for name in
                       ('AI.list', 'AI.Extra.list', 'AI.mrs', 'AI.Extra.yaml')}
        self.args = SimpleNamespace(write=True, mihomo='mihomo', report=None,
                                    published_baseline=str(self.root / 'baseline'))
        self.compiled = []
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for field, path in [('SURGE_OUT', 'Surge/Ruleset'), ('MIHOMO_OUT', 'Mihomo/Ruleset'),
                            ('SURGE_ADS_OUT', 'Surge/Advertising'), ('MIHOMO_ADS_OUT', 'Mihomo/Advertising')]:
            directory = self.root / path
            directory.mkdir(parents=True)
            self.stack.enter_context(patch.object(rules, field, directory))
        self.stack.enter_context(patch.object(rules, 'SOURCE_CACHE', self.cache))
        self.stack.enter_context(patch.object(rules, 'BUILD_TIME', '2030-01-01 00:00:00'))
        self.ozon = rules.RuleSet()
        self.ozon.exact.add('fresh-ozon.example.com')
        self.stack.enter_context(patch.object(rules, 'build_ozon', return_value=self.ozon))
        shards = {shard.key: self.ozon for shard in rules.SKK_ADS_SHARDS}
        self.stack.enter_context(patch.object(rules, 'build_ads', return_value=shards))
        def compile_fake(mihomo, name, text, destination):
            self.compiled.append(name)
            destination.write_bytes(('fresh binary ' + name).encode())
        self.stack.enter_context(patch.object(rules, 'convert_mrs', side_effect=compile_fake))
        self.load = self.stack.enter_context(patch('published_ai.load_published_ai', return_value=(
            self.assets, {'source_sha': 'a' * 40, 'files': {name: 'b' * 64 for name in self.assets}})))

    def ai_path(self, name):
        return (rules.SURGE_OUT if name.endswith('.list') else rules.MIHOMO_OUT) / name

    def test_bootstrap_keeps_four_exact_assets_and_refreshes_other_groups(self):
        def unavailable(mihomo):
            self.cache.get(rules.SRC_METACUBEX_AI, lambda: b'candidate not used')
            raise SourceUnavailableError('Kelee unavailable and no raw cache')
        with patch.object(rules, 'build_ai', side_effect=unavailable):
            self.assertEqual(rules.generate(self.args), 0)
        for name, data in self.assets.items():
            self.assertEqual(self.ai_path(name).read_bytes(), data)
        self.assertNotIn('AI', self.compiled)
        self.assertIn('Ozon', self.compiled)
        self.assertTrue(any(name.startswith('Advertising.') for name in self.compiled))
        self.assertIn('fresh-ozon.example.com', (rules.SURGE_OUT / 'Ozon.list').read_text())
        self.assertNotIn(rules.SRC_METACUBEX_AI, self.cache.pending)
        report = self.cache.report(True)
        self.assertEqual(report['components'][0]['freshness'], 'unknown')
        self.assertTrue(all(s['used'] is False and s['freshness'] == 'unknown' for s in report['sources']))
        self.cache.commit()
        self.assertEqual(list(self.cache.directory.glob('*.json')), [])

    def test_bad_baseline_aborts_before_output_changes(self):
        for name, data in self.assets.items():
            self.ai_path(name).write_bytes(data)
        self.load.side_effect = ValueError('invalid baseline digest')
        with patch.object(rules, 'build_ai', side_effect=SourceUnavailableError('offline')):
            with self.assertRaisesRegex(ValueError, 'invalid baseline'):
                rules.generate(self.args)
        self.assertEqual(self.compiled, [])
        self.assertFalse((rules.SURGE_OUT / 'Ozon.list').exists())
        for name, data in self.assets.items():
            self.assertEqual(self.ai_path(name).read_bytes(), data)

    def test_missing_baseline_does_not_replace_with_empty_ai(self):
        self.args.published_baseline = None
        with patch.object(rules, 'build_ai', side_effect=SourceUnavailableError('offline')):
            with self.assertRaises(SourceUnavailableError):
                rules.generate(self.args)
        self.load.assert_not_called()
        self.assertEqual(self.compiled, [])

    def test_internal_failure_is_not_hidden_by_component_reuse(self):
        with patch.object(rules, 'build_ai', side_effect=RuntimeError('internal bug')):
            with self.assertRaisesRegex(RuntimeError, 'internal bug'):
                rules.generate(self.args)
        self.load.assert_not_called()
        self.assertEqual(self.cache.report(False)['components'], [])

    def test_recovered_ai_is_built_fresh_without_baseline(self):
        with patch.object(rules, 'build_ai', return_value=self.ozon):
            self.assertEqual(rules.generate(self.args), 0)
        self.load.assert_not_called()
        self.assertIn('AI', self.compiled)
        self.assertIn('fresh-ozon.example.com', (rules.SURGE_OUT / 'AI.list').read_text())
        self.assertEqual(self.cache.report(True)['components'], [])

    def test_native_kelee_failure_preserves_source_unavailable_type(self):
        process = MagicMock()
        process.poll.return_value = 1
        with patch.object(rules.subprocess, 'Popen', return_value=process):
            with self.assertRaises(SourceUnavailableError):
                rules.fetch_kelee_with_mihomo('mihomo')


if __name__ == '__main__':
    unittest.main()
