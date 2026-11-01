"""Independent regressions for successful HTTP carrying unusable source data."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules
from source_cache import SourceCache


class SemanticFallbackReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'cache'
        self.url = rules.SRC_METACUBEX_AI
        self.good = ''.join(f'DOMAIN,valid{i}.example.com\n' for i in range(101)).encode()

    def seed(self, url=None, data=None):
        url = url or self.url
        cache = SourceCache(self.directory)
        cache.get(url, lambda: self.good if data is None else data)
        cache.commit()
        return cache.path(url)

    def test_valid_http_truncated_source_falls_back_and_reports_stale(self):
        path = self.seed()
        before = path.read_bytes()
        cache = SourceCache(self.directory)
        with patch.object(rules, 'SOURCE_CACHE', cache), \
                patch.object(rules, '_fetch', return_value='DOMAIN,truncated.example.com\n'):
            self.assertEqual(rules.fetch(self.url), self.good.decode())
        self.assertEqual(cache.sources[self.url]['status'], 'stale')
        self.assertTrue(cache.sources[self.url]['error'])
        cache.commit()
        self.assertEqual(path.read_bytes(), before)

    def test_malformed_json_and_wrong_schema_use_own_last_good(self):
        url = rules.OZON_PLIST_DOMAINS
        good = json.dumps({'ozon': [f'ozon{i}.example.com' for i in range(51)]}).encode()
        path = self.seed(url, good)
        before = path.read_bytes()
        for bad in ('{invalid-json', '[]', '{}', '{"ozon": null}'):
            with self.subTest(bad=bad):
                cache = SourceCache(self.directory)
                with patch.object(rules, 'SOURCE_CACHE', cache), \
                        patch.object(rules, '_fetch', return_value=bad):
                    self.assertEqual(rules.fetch(url), good.decode())
                self.assertEqual(cache.sources[url]['status'], 'stale')
                cache.commit()
                self.assertEqual(path.read_bytes(), before)

    def test_semantically_invalid_source_without_cache_is_unavailable(self):
        cache = SourceCache(self.directory)
        with patch.object(rules, 'SOURCE_CACHE', cache), \
                patch.object(rules, '_fetch', return_value='DOMAIN,truncated.example.com\n'):
            with self.assertRaises(RuntimeError):
                rules.fetch(self.url)
        self.assertEqual(cache.sources[self.url]['status'], 'unavailable')
        self.assertFalse(self.directory.exists())

    def test_old_cache_must_satisfy_current_semantic_validation(self):
        path = self.seed(data=b'DOMAIN,old-invalid.example.com\n')
        before = path.read_bytes()
        cache = SourceCache(self.directory)
        with patch.object(rules, 'SOURCE_CACHE', cache), \
                patch.object(rules, '_fetch', side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):
                rules.fetch(self.url)
        self.assertEqual(cache.sources[self.url]['status'], 'unavailable')
        self.assertEqual(path.read_bytes(), before)

    def test_unsupported_kelee_logical_scope_preserves_prior_source(self):
        url = rules.SRC_KELEE_LOON_AI
        good = ''.join(f'DOMAIN,valid{i}.example.com\n' for i in range(151)).encode()
        path = self.seed(url, good)
        before = path.read_bytes()
        bad = good.decode() + 'AND,((DOMAIN-KEYWORD,unaudited),(DOMAIN-SUFFIX,example.com))\n'
        cache = SourceCache(self.directory)
        with patch.object(rules, 'SOURCE_CACHE', cache), patch.object(rules, '_fetch', return_value=bad):
            self.assertEqual(rules.fetch(url), good.decode())
        self.assertEqual(cache.sources[url]['status'], 'stale')
        self.assertIn('unaudited', cache.sources[url]['error'])
        cache.commit()
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_mrs_decoder_input_uses_prior_binary(self):
        url = rules.SRC_CATS_MIHOMO_MRS
        good = b'previous validated binary'
        path = self.seed(url, good)
        before = path.read_bytes()
        decoded = ''.join(f'valid{i}.example.com\n' for i in range(10001))
        seen = []
        def decode(mihomo, source, payload):
            seen.append(payload)
            if payload != good:
                raise RuntimeError('invalid MRS source header')
            return decoded
        cache = SourceCache(self.directory)
        with patch.object(rules, 'SOURCE_CACHE', cache), patch.object(rules, 'SOURCE_MIHOMO', 'mihomo'), \
                patch.object(rules, '_fetch_bytes', return_value=b'invalid binary'), \
                patch.object(rules, 'decode_mrs_domains', side_effect=decode):
            self.assertEqual(rules.fetch_bytes(url), good)
        self.assertEqual(seen, [b'invalid binary', good])
        self.assertEqual(cache.sources[url]['status'], 'stale')
        cache.commit()
        self.assertEqual(path.read_bytes(), before)

    def test_internal_validator_errors_abort_instead_of_hiding_with_cache(self):
        path = self.seed()
        before = path.read_bytes()
        for error in (NameError('bug'), AttributeError('bug'), OSError('broken tool')):
            with self.subTest(error=type(error).__name__):
                cache = SourceCache(self.directory)
                with patch.object(rules, 'SOURCE_CACHE', cache), \
                        patch.object(rules, '_fetch', return_value=self.good.decode()), \
                        patch.object(rules, '_validate_source_payload', side_effect=error):
                    with self.assertRaises(type(error)):
                        rules.fetch(self.url)
                self.assertFalse(cache.pending)
                self.assertNotIn(self.url, cache.values)
                self.assertEqual(path.read_bytes(), before)

    def test_recovery_promotion_waits_for_successful_overall_build(self):
        path = self.seed()
        before = path.read_bytes()
        recovered = ''.join(f'DOMAIN,recovered{i}.example.com\n' for i in range(102))
        report = self.root / 'status.json'
        argv = ['gen_rulesets.py', '--write', '--source-cache', str(self.directory),
                '--source-report', str(report)]
        def failure(args):
            self.assertEqual(rules.fetch(self.url), recovered)
            raise RuntimeError('internal compiler failure')
        def success(args):
            self.assertEqual(rules.fetch(self.url), recovered)
            self.assertEqual(path.read_bytes(), before)
            return 0
        with patch.object(sys, 'argv', argv), patch.object(rules, '_fetch', return_value=recovered):
            with patch.object(rules, 'generate', side_effect=failure):
                with self.assertRaisesRegex(RuntimeError, 'internal compiler failure'):
                    rules.main()
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(json.loads(report.read_text())['success'])
            with patch.object(rules, 'generate', side_effect=success):
                self.assertEqual(rules.main(), 0)
        self.assertEqual(SourceCache(self.directory)._read(self.url)[0], recovered.encode())
        status = json.loads(report.read_text())
        self.assertTrue(status['success'])
        self.assertEqual(status['sources'][0]['status'], 'fresh')


if __name__ == '__main__':
    unittest.main()
