"""Offline fallback visibility, artifact safety, and exact-attempt mirror checks."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cnb_sync_gate as gate
import restore_generated
import source_status


class SourceStatusTests(unittest.TestCase):
    def test_stale_is_visible_and_escaped(self):
        markdown, attention = source_status.render({'success': True, 'sources': [
            {'url': 'https://example/a|b', 'status': 'stale', 'last_success': '2026-10-29T00:00:00Z',
             'sha256': 'a' * 64, 'error': '<script>\nEOF'}]})
        self.assertTrue(attention)
        for text in ('沿用旧数据', '2026-10-29T00:00:00Z', '&lt;script&gt;<br>EOF', 'a&#124;b'):
            self.assertIn(text, markdown)

    def test_fresh_recovery_and_missing_cache(self):
        markdown, attention = source_status.render({'success': True, 'sources': [{'url': 'u', 'status': 'fresh'}]})
        self.assertFalse(attention)
        self.assertIn('新数据 1', markdown)
        markdown, attention = source_status.render({'success': False, 'sources': [
            {'url': 'u', 'status': 'unavailable', 'error': 'EOF', 'cache_error': 'missing'}]})
        self.assertTrue(attention)
        self.assertIn('保留上一次发布', markdown)
        self.assertIn('missing', markdown)
        self.assertIn('无可用数据（未用于产物）', markdown)

    def test_whole_ai_reuse_is_successful_but_freshness_unknown(self):
        report = {'success': True, 'sources': [
            {'url': status, 'status': status, 'used': False, 'freshness': 'unknown'}
            for status in ('fresh', 'unavailable', 'unknown')],
            'components': [{'name': 'AI', 'status': 'reused', 'source_sha': 'a' * 40,
                            'files': {'AI.list': 'b' * 64}, 'reason': 'EOF', 'freshness': 'unknown'}]}
        markdown, attention = source_status.render(report)
        self.assertTrue(attention)
        self.assertNotIn('本轮生成失败', markdown)
        for text in ('生成结果：成功', '未混入本轮候选数据', '逐来源新鲜度未知', '未使用候选', 'AI.list', 'a' * 40, 'b' * 64):
            self.assertIn(text, markdown)
        self.assertTrue(source_status.render(dict(report, sources=[]))[1])

    def test_baseline_failure_does_not_expose_partial_directory(self):
        workflow = (Path(__file__).resolve().parents[2] / '.github/workflows/gen-rulesets.yml').read_text()
        section = workflow.split('        id: baseline\n', 1)[1].split('      - name: 生成规则集', 1)[0]
        script = '\n'.join(line[10:] for line in section.split('        run: |\n', 1)[1].splitlines())
        for status in (0, 1):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                binary = root / 'bin'
                binary.mkdir()
                python = binary / 'python'
                python.write_text('#!/bin/sh\necho simulated-fetch\nexit ' + str(status) + '\n')
                python.chmod(0o755)
                output, summary = root / 'output', root / 'summary'
                output.touch(); summary.touch()
                env = dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'], RUNNER_TEMP=tmp,
                           GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
                subprocess.run(['bash', '-c', script], env=env, check=True, capture_output=True)
                self.assertEqual('path=' in output.read_text(), status == 0)
                if status:
                    self.assertIn('已禁用整组 AI 基线回退', summary.read_text())

    def test_safe_complete_snapshot_restores_cache_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root / 'snapshot.tar'; dest = root / 'dest'; dest.mkdir()
            for directory in restore_generated.DIRECTORIES:
                (dest / directory).mkdir(parents=True)
                (dest / directory / 'old').write_text('last-good')
            with tarfile.open(archive, 'w') as tar:
                for directory in restore_generated.DIRECTORIES:
                    item = tarfile.TarInfo(directory); item.type = tarfile.DIRTYPE; tar.addfile(item)
                for name in (*restore_generated.FILES, '.source-cache/source.json'):
                    data = b'{"validated": true}'
                    item = tarfile.TarInfo(name); item.size = len(data); tar.addfile(item, io.BytesIO(data))
            restore_generated.restore(archive, dest)
            self.assertTrue((dest / 'source-status.md').exists())
            with tarfile.open(archive, 'w') as tar:
                tar.addfile(tarfile.TarInfo('.source-cache/../escape'), io.BytesIO(b''))
            with self.assertRaises(ValueError):
                restore_generated.restore(archive, dest)
            self.assertEqual((dest / '.source-cache/source.json').read_bytes(), b'{"validated": true}')


class SyncGateTests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 42, 'run_attempt': 2, 'name': gate.GEN_WORKFLOW, 'path': gate.GEN_PATH,
                    'status': 'completed', 'conclusion': 'failure', 'head_sha': 'a' * 40}
        self.jobs = [{'name': name, 'run_id': 42, 'run_attempt': 2, 'head_sha': 'a' * 40,
                      'status': 'completed', 'conclusion': conclusion}
                     for name, conclusion in [('gen', 'success'), ('publish', 'success'), ('source-health', 'failure')]]
        self.event = {'workflow_run': self.run, 'repository': {'full_name': 'laincat/Rules'}}

    def test_degraded_successful_publication(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {'total_count': 3, 'jobs': self.jobs}
        self.assertTrue(gate.should_sync('workflow_run', self.event, 'laincat/Rules', fetch))
        self.assertIn('/runs/42/attempts/2/jobs?per_page=100', calls[0])

    def test_gen_or_publish_failure_cannot_sync(self):
        for name in ('gen', 'publish'):
            jobs = [dict(job, conclusion='failure') if job['name'] == name else job for job in self.jobs]
            self.assertFalse(gate.jobs_allow_degraded_sync(self.run, jobs))

    def test_unrelated_run_commit_attempt_workflow_rejected(self):
        for field, value in [('name', 'other'), ('path', 'other.yml')]:
            self.assertFalse(gate.jobs_allow_degraded_sync(dict(self.run, **{field: value}), self.jobs))
        for field, value in [('run_id', 43), ('head_sha', 'b' * 40), ('run_attempt', 3)]:
            self.assertFalse(gate.jobs_allow_degraded_sync(self.run, [dict(job, **{field: value}) for job in self.jobs]))
        self.assertFalse(gate.jobs_allow_degraded_sync(self.run, self.jobs + [dict(self.jobs[0], name='other')]))
        self.assertFalse(gate.should_sync('workflow_run', {'workflow_run': dict(self.run, name='other', conclusion='success')}, 'laincat/Rules'))

    def test_missing_invalid_attempt_cannot_fetch(self):
        for attempt in (None, 0, -1, '2', True):
            run = dict(self.run, run_attempt=attempt)
            self.assertFalse(gate.jobs_allow_degraded_sync(run, self.jobs))
            with self.assertRaisesRegex(ValueError, 'invalid run attempt'):
                gate.should_sync('workflow_run', dict(self.event, workflow_run=run), 'laincat/Rules',
                                 lambda url: self.fail('unbounded attempt requested'))

    def test_later_attempt_same_run_and_sha_rejected(self):
        self.assertFalse(gate.should_sync('workflow_run', self.event, 'laincat/Rules',
                         lambda url: {'total_count': 3, 'jobs': [dict(job, run_attempt=3) for job in self.jobs]}))

    def test_incomplete_api_and_network_errors_fail_closed(self):
        self.assertFalse(gate.should_sync('workflow_run', self.event, 'laincat/Rules',
                                         lambda url: {'total_count': 4, 'jobs': self.jobs}))
        def unavailable(url):
            raise OSError('API unavailable')
        with self.assertRaises(OSError):
            gate.should_sync('workflow_run', self.event, 'laincat/Rules', unavailable)

    def test_success_and_schedule_unchanged(self):
        self.assertTrue(gate.should_sync('schedule', {}, 'laincat/Rules'))
        self.assertTrue(gate.should_sync('workflow_run', {'workflow_run': dict(self.run, conclusion='success')}, 'laincat/Rules'))


if __name__ == '__main__':
    unittest.main()
