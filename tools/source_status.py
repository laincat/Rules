#!/usr/bin/env python3
"""Render source freshness separately from successful degraded generation."""
import argparse
import html
import json
from pathlib import Path


def cell(value):
    return html.escape(str(value or '—')).replace('|', '&#124;').replace('\r', '').replace('\n', '<br>')


def render(report):
    sources = report['sources']
    components = report.get('components', [])
    if not isinstance(sources, list) or not isinstance(components, list):
        raise ValueError('invalid source/component status list')
    counts = dict.fromkeys(('fresh', 'stale', 'unavailable', 'unknown'), 0)
    for source in sources:
        if source.get('status') not in counts:
            raise ValueError('invalid source status')
        counts[source['status']] += 1
    reused = [component for component in components if component.get('status') == 'reused']
    attention = bool(counts['stale'] or counts['unavailable'] or reused)
    lines = ['## 上游来源状态', '']
    if reused:
        lines += ['**整组应急回退：AI 产物完整沿用已校验的上一份发布，未混入本轮候选数据；逐来源新鲜度未知。请仓库所有者决定如何处理失效来源。**', '']
    elif counts['unavailable'] and not report.get('success'):
        lines += ['**来源不可用且无有效缓存：本轮生成失败，保留上一次发布。**', '']
    elif counts['stale']:
        lines += ['**正在沿用上一次校验通过的数据；以下来源已失效，请仓库所有者决定修复、替换或继续等待。**', '']
    else:
        lines += ['本轮已读取的来源均为新获取数据。', '']
    lines += [f"生成结果：{'成功' if report.get('success') else '失败，未发布本轮构建'}。",
              f"本轮来源获取尝试（候选未必用于产物）：新数据 {counts['fresh']}，沿用旧数据 {counts['stale']}，不可用 {counts['unavailable']}，未尝试/未知 {counts['unknown']}。", '',
              '| 来源 URL | 获取状态 | 本轮产物使用情况 | 最近成功获取（UTC） | SHA-256 | 错误 |',
              '|---|---|---|---|---|---|']
    labels = {'fresh': '新数据', 'stale': '**失效，沿用旧数据**',
              'unavailable': '**不可用，无有效缓存**', 'unknown': '未尝试；来源新鲜度未知'}
    for source in sorted(sources, key=lambda item: item['url']):
        error = source.get('error', '')
        if source.get('cache_error'):
            error += ' / cache: ' + str(source['cache_error'])
        if source.get('used') is False:
            used = '未使用候选；整组旧发布中的逐来源新鲜度未知'
        elif source['status'] in ('unavailable', 'unknown'):
            used = '无可用数据（未用于产物）'
        else:
            used = '使用本轮选择的数据'
        lines.append('| ' + ' | '.join([cell(source['url']), labels[source['status']], used,
                     cell(source.get('last_success')), cell(source.get('sha256')), cell(error)]) + ' |')
    for component in reused:
        lines += ['', '### 整组沿用：' + cell(component.get('name')),
                  '- 基线发布提交：`' + cell(component.get('source_sha')) + '`',
                  '- 逐来源新鲜度：**未知**（发布产物不能反推出单个来源的历史数据）',
                  '- 原因：' + cell(component.get('reason')), '',
                  '| 原样沿用文件 | SHA-256 |', '|---|---|']
        for name, digest in sorted(component.get('files', {}).items()):
            lines.append('| ' + cell(name) + ' | ' + cell(digest) + ' |')
    lines += ['', '原始状态见 `source-status.json`。缓存时间不会因回退而刷新；来源恢复后自动使用新数据。', '']
    return '\n'.join(lines), attention


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--markdown', type=Path, required=True)
    parser.add_argument('--summary', type=Path)
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    markdown, attention = render(json.loads(args.report.read_text(encoding='utf-8')))
    args.markdown.write_text(markdown, encoding='utf-8')
    if args.summary:
        with args.summary.open('a', encoding='utf-8') as stream:
            stream.write(markdown)
    if args.github_output:
        with args.github_output.open('a', encoding='utf-8') as stream:
            stream.write(f"needs_attention={'true' if attention else 'false'}\n")
    if attention:
        print('::warning::上游来源已失效。详见来源状态报告；有效旧数据继续使用，由仓库所有者决定处置。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
