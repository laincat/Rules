"""Offline last-good snapshot failure, recovery and native provider tests."""
from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules
from source_cache import SourceCache, SourceValidationError, SourceUnavailableError, public_error

URL = 'https://example.com/rules?dataset=ai'
GOOD = b'DOMAIN,working.example.com\n'


def offline():
    raise RuntimeError('upstream EOF')


class SourceCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache_dir = self.root / 'cache'

    def seed(self, url=URL, data=GOOD):
        cache = SourceCache(self.cache_dir)
        cache.get(url, lambda: data)
        cache.commit()
        return cache.path(url)

    def test_fallback_keeps_bytes_timestamp_and_digest(self):
        path = self.seed()
        before = path.read_bytes()
        cache = SourceCache(self.cache_dir)
        self.assertEqual(cache.get(URL, offline), GOOD)
        cache.commit()
        self.assertEqual(path.read_bytes(), before)
        source = cache.report(True)['sources'][0]
        self.assertEqual(source['status'], 'stale')
        self.assertEqual(source['last_success'], json.loads(before)['last_success'])
        self.assertEqual(source['sha256'], json.loads(before)['sha256'])

    def test_missing_cache_reports_unavailable_and_fails_closed(self):
        cache = SourceCache(self.cache_dir)
        with self.assertRaisesRegex(SourceUnavailableError, 'no valid last-good cache'):
            cache.get(URL, offline)
        self.assertEqual(cache.report(False)['sources'][0]['status'], 'unavailable')
        self.assertFalse(self.cache_dir.exists())

    def test_corrupt_cache_preserves_evidence(self):
        path = self.seed()
        valid = json.loads(path.read_text())
        corruptions = ['not JSON', json.dumps({**valid, 'sha256': '0' * 64}),
                       json.dumps({**valid, 'url': URL + 'wrong'}),
                       json.dumps({**valid, 'version': 999}),
                       json.dumps({**valid, 'data': 'not-base64!'}),
                       json.dumps({**valid, 'last_success': 'invalid'})]
        for content in corruptions:
            with self.subTest(content=content[:50]):
                path.write_text(content)
                cache = SourceCache(self.cache_dir)
                with self.assertRaises(SourceUnavailableError):
                    cache.get(URL, offline)
                self.assertEqual(path.read_text(), content)
                self.assertEqual(cache.sources[URL]['status'], 'unavailable')

    def test_empty_response_does_not_replace_good_snapshot(self):
        path = self.seed()
        before = path.read_bytes()
        cache = SourceCache(self.cache_dir)
        self.assertEqual(cache.get(URL, lambda: b''), GOOD)
        cache.commit()
        self.assertEqual(path.read_bytes(), before)

    def test_semantically_invalid_response_falls_back_and_revalidates_cache(self):
        path = self.seed()
        before = path.read_bytes()
        checked = []
        def validate(data):
            checked.append(data)
            if data != GOOD:
                raise SourceValidationError('invalid rules')
        cache = SourceCache(self.cache_dir)
        self.assertEqual(cache.get(URL, lambda: b'<html>error</html>', validate), GOOD)
        self.assertEqual(checked, [b'<html>error</html>', GOOD])
        cache.commit()
        self.assertEqual(path.read_bytes(), before)

    def test_semantically_invalid_cache_cannot_be_used(self):
        self.seed()
        def reject(data):
            raise SourceValidationError('outdated or invalid schema')
        cache = SourceCache(self.cache_dir)
        with self.assertRaises(SourceUnavailableError):
            cache.get(URL, offline, reject)
        self.assertEqual(cache.sources[URL]['status'], 'unavailable')

    def test_internal_validator_bug_is_not_silently_masked(self):
        self.seed()
        def bug(data):
            raise TypeError('programming error')
        cache = SourceCache(self.cache_dir)
        with self.assertRaises(TypeError):
            cache.get(URL, lambda: GOOD, bug)
        self.assertFalse(cache.pending)

    def test_recovery_updates_only_after_commit(self):
        path = self.seed()
        before = path.read_bytes()
        fresh = b'DOMAIN,recovered.example.com\n'
        cache = SourceCache(self.cache_dir)
        self.assertEqual(cache.get(URL, lambda: fresh), fresh)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(cache.sources[URL]['status'], 'fresh')
        cache.commit()
        self.assertEqual(SourceCache(self.cache_dir).get(URL, offline), fresh)

    def test_url_query_is_part_of_cache_identity(self):
        self.seed()
        with self.assertRaises(SourceUnavailableError):
            SourceCache(self.cache_dir).get(URL.replace('ai', 'other'), offline)

    def test_repeated_consumers_share_single_snapshot(self):
        cache = SourceCache(self.cache_dir)
        loader = MagicMock(return_value=GOOD)
        self.assertEqual(cache.get(URL, loader), GOOD)
        self.assertEqual(cache.get(URL, loader), GOOD)
        loader.assert_called_once()

    def test_component_reuse_cancels_raw_candidate_promotion(self):
        path = self.seed()
        before = path.read_bytes()
        cache = SourceCache(self.cache_dir)
        cache.get(URL, lambda: b'DOMAIN,new.example.com\n')
        metadata = {'name': 'AI', 'status': 'stale', 'source_sha': 'a' * 40}
        cache.reuse_component([URL], metadata)
        cache.commit()
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(cache.sources[URL]['used'])
        self.assertEqual(cache.report(True)['components'], [metadata])

    def test_failed_build_never_promotes_candidates(self):
        path = self.seed()
        before = path.read_bytes()
        report = self.root / 'status.json'
        def fail(_args):
            rules.SOURCE_CACHE.get(URL, lambda: b'DOMAIN,new.example.com\n')
            raise RuntimeError('later parser rejected build')
        with patch.object(sys, 'argv', ['gen_rulesets.py', '--write',
                '--source-cache', str(self.cache_dir), '--source-report', str(report)]), \
                patch.object(rules, 'generate', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'rejected build'):
                rules.main()
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(json.loads(report.read_text())['success'])
        self.assertIsNone(rules.SOURCE_CACHE)

    def test_real_missing_source_aborts_before_publication_writes(self):
        published = self.root / 'AI.list'
        published.write_bytes(GOOD)
        report = self.root / 'status.json'
        with patch.object(sys, 'argv', ['gen_rulesets.py', '--write',
                '--source-cache', str(self.cache_dir), '--source-report', str(report)]), \
                patch.object(rules, 'SURGE_OUT', self.root), \
                patch.object(rules, '_fetch', side_effect=RuntimeError('upstream EOF')), \
                patch.object(rules, 'write_with_stamp') as write, \
                patch.object(rules, 'convert_mrs') as compile_mrs:
            with self.assertRaises(SourceUnavailableError):
                rules.main()
        self.assertEqual(published.read_bytes(), GOOD)
        write.assert_not_called()
        compile_mrs.assert_not_called()
        self.assertFalse(self.cache_dir.exists())

    def test_dry_run_does_not_promote_candidates(self):
        path = self.seed()
        before = path.read_bytes()
        def generate(_args):
            rules.SOURCE_CACHE.get(URL, lambda: b'DOMAIN,new.example.com\n')
            return 0
        with patch.object(sys, 'argv', ['gen_rulesets.py', '--source-cache', str(self.cache_dir)]), \
                patch.object(rules, 'generate', side_effect=generate):
            self.assertEqual(rules.main(), 0)
        self.assertEqual(path.read_bytes(), before)

    def test_successful_write_promotes_candidates(self):
        self.seed()
        fresh = b'DOMAIN,new.example.com\n'
        def generate(_args):
            rules.SOURCE_CACHE.get(URL, lambda: fresh)
            return 0
        with patch.object(sys, 'argv', ['gen_rulesets.py', '--write',
                '--source-cache', str(self.cache_dir)]), \
                patch.object(rules, 'generate', side_effect=generate):
            self.assertEqual(rules.main(), 0)
        self.assertEqual(SourceCache(self.cache_dir).get(URL, offline), fresh)

    def test_native_partial_failure_uses_only_failed_provider_cache(self):
        old_loon = ''.join(f'DOMAIN,old{i}.example.com\n' for i in range(150))
        fresh_clash = ''.join(f'DOMAIN,new{i}.example.com\n' for i in range(150))
        path = self.seed(rules.SRC_KELEE_LOON_AI, old_loon.encode())
        before = path.read_bytes()
        cache = SourceCache(self.cache_dir)
        process = MagicMock()
        process.poll.side_effect = [None, 1]
        def start(command, **kwargs):
            directory = Path(command[2])
            (directory / 'clash.txt').write_text(fresh_clash)
            kwargs['stdout'].write('loon download: EOF\n')
            return process
        response = io.BytesIO(json.dumps({'providers': {
            'clash': {'ruleCount': 150}, 'loon': {'ruleCount': 0}}}).encode())
        with patch.object(rules, 'SOURCE_CACHE', cache), \
                patch.object(rules.subprocess, 'Popen', side_effect=start), \
                patch.object(rules.urllib.request, 'urlopen', return_value=response), \
                patch.object(rules.time, 'sleep'):
            self.assertEqual(rules.fetch_kelee_with_mihomo('mihomo'), (fresh_clash, old_loon))
        self.assertEqual(cache.sources[rules.SRC_KELEE_AI]['status'], 'fresh')
        self.assertEqual(cache.sources[rules.SRC_KELEE_LOON_AI]['status'], 'stale')
        cache.commit()
        self.assertEqual(path.read_bytes(), before)
        process.terminate.assert_called_once()
        process.wait.assert_called_once()

    def test_native_missing_cache_does_not_drop_provider(self):
        cache = SourceCache(self.cache_dir)
        process = MagicMock()
        process.poll.return_value = 1
        with patch.object(rules, 'SOURCE_CACHE', cache), \
                patch.object(rules.subprocess, 'Popen', return_value=process):
            with self.assertRaises(SourceUnavailableError):
                rules.fetch_kelee_with_mihomo('mihomo')
        self.assertEqual(cache.sources[rules.SRC_KELEE_AI]['status'], 'unavailable')
        self.assertEqual(cache.sources[rules.SRC_KELEE_LOON_AI]['status'], 'unavailable')
        process.terminate.assert_called_once()

    def test_public_error_omits_private_runner_paths(self):
        for error in [FileNotFoundError(2, 'No such file', '/home/runner/cache'),
                      RuntimeError('failed at /workspace/private/cache')]:
            self.assertNotIn('/home/runner', public_error(error))
            self.assertNotIn('/workspace/private', public_error(error))


if __name__ == '__main__':
    unittest.main()
