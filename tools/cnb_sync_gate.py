#!/usr/bin/env python3
"""Verify a degraded run's successful publication without expanding permissions.

Public API failures fail closed. Scheduled/manual synchronization is independent.
The triggering SHA identifies the build, not its later generated publication commit.
"""
import json
import os
from pathlib import Path
import re
import urllib.request

GEN_WORKFLOW = '生成规则集（Ozon / AI / 去广告）'
GEN_PATH = '.github/workflows/gen-rulesets.yml'
DOCS_WORKFLOW = '更新日志自动生成'


def jobs_allow_degraded_sync(run, jobs):
    if (run.get('name') != GEN_WORKFLOW or run.get('path') != GEN_PATH
            or run.get('conclusion') != 'failure' or run.get('status') != 'completed'):
        return False
    sha = run.get('head_sha', '')
    attempt = run.get('run_attempt')
    if not re.fullmatch('[0-9a-f]{40}', sha) or type(attempt) is not int or attempt <= 0:
        return False
    expected = {'gen': 'success', 'publish': 'success', 'source-health': 'failure'}
    if len(jobs) != len(expected) or {job.get('name') for job in jobs} != set(expected):
        return False
    return all(job.get('status') == 'completed'
               and job.get('conclusion') == expected[job['name']]
               and job.get('head_sha') == sha
               and job.get('run_id') == run['id']
               and job.get('run_attempt') == attempt for job in jobs)


def api_json(url):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'laincat-rules-source-health',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def should_sync(event_name, event, repository, fetch=api_json):
    if event_name != 'workflow_run':
        return True
    run = event['workflow_run']
    workflows = {GEN_WORKFLOW: GEN_PATH, DOCS_WORKFLOW: '.github/workflows/docs-watch.yml'}
    if run.get('name') not in workflows or run.get('path') != workflows[run['name']]:
        return False
    if run.get('conclusion') == 'success':
        return True
    if run.get('name') != GEN_WORKFLOW or run.get('conclusion') != 'failure':
        return False
    if event.get('repository', {}).get('full_name') != repository:
        return False
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('invalid repository')
    run_id, attempt = run.get('id'), run.get('run_attempt')
    if type(run_id) is not int or run_id <= 0:
        raise ValueError('invalid run ID')
    if type(attempt) is not int or attempt <= 0:
        raise ValueError('invalid run attempt')
    # A rerun can share the ID/SHA: pin the completed event's exact attempt.
    result = fetch(f'https://api.github.com/repos/{repository}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100')
    jobs = result['jobs']
    if result.get('total_count') != len(jobs):
        return False
    return jobs_allow_degraded_sync(run, jobs)


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    allowed = should_sync(os.environ['GITHUB_EVENT_NAME'], event, os.environ['GITHUB_REPOSITORY'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f"allowed={'true' if allowed else 'false'}\n")
    print('Mirror allowed: ' + str(allowed))


if __name__ == '__main__':
    main()
