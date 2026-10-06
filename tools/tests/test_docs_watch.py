"""更新日志写入器的离线回归测试（不触网）。

守的是这条不变量：**任何一个主数据源抓取失败，都不得覆盖已有的 changelog.md**。
线上真实踩过一次死角 —— 判据写成 `not releases and not alpha`，
于是「Alpha 抓成功、发布列表抓失败」时页面照样重写，
把整张「正式版历史」表清空。这类失败是静默的：页面不会报错，只是少了一半内容。
"""

from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch


_SPEC = importlib.util.spec_from_file_location(
    "docs_watch", str(Path(__file__).resolve().parents[1] / "docs_watch.py"))
docs_watch = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(docs_watch)


ORIGINAL = "# 原始内容\n\n不得被覆盖。\n"


class ChangelogOverwriteGuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.path = os.path.join(self.dir, "changelog.md")
        Path(self.path).write_text(ORIGINAL, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _unchanged(self) -> bool:
        return Path(self.path).read_text(encoding="utf-8") == ORIGINAL

    def test_mihomo_releases_empty_but_alpha_present_keeps_file(self):
        # 这正是线上踩到的死角：两个源里坏了一个，页面却照样重写。
        result = docs_watch.write_changelog(
            self.dir, "mihomo",
            {"releases": [], "alpha": [{"sha": "abc1234", "date": "2026-10-02"}],
             "week_start": "2026-09-29"},
            dry_run=True)
        self.assertIn("跳过", result)
        self.assertTrue(self._unchanged(), "发布列表抓空时不得覆盖原文件")

    def test_mihomo_alpha_empty_but_releases_present_keeps_file(self):
        result = docs_watch.write_changelog(
            self.dir, "mihomo",
            {"releases": [{"tag": "v1.19.32", "date": "2026-09-30", "body": "x"}],
             "alpha": [], "week_start": "2026-09-29"},
            dry_run=True)
        self.assertIn("跳过", result)
        self.assertTrue(self._unchanged())

    def test_surge_appcast_empty_but_tg_present_keeps_file(self):
        result = docs_watch.write_changelog(
            self.dir, "surge",
            {"stable": [], "beta": [],
             "tg": [{"id": "1", "date": "2026-10-05", "text": "hi"}],
             "week_start": "2026-09-29"},
            dry_run=True)
        self.assertIn("跳过", result)
        self.assertTrue(self._unchanged())

    def test_missing_source_is_named_in_result(self):
        result = docs_watch.write_changelog(
            self.dir, "mihomo",
            {"releases": [], "alpha": [{"sha": "abc1234", "date": "2026-10-02"}]},
            dry_run=True)
        self.assertIn("releases", result)

    def test_tg_outage_does_not_block_rewrite(self):
        # TG 是第三方通道，长期不可达时不能把整页钉死在旧内容上。
        result = docs_watch.write_changelog(
            self.dir, "surge",
            {"stable": [{"version": "6.9.1", "build": "12290",
                         "date": "2026-09-10", "notes": "x"}],
             "beta": [{"version": "6.10.0", "build": "12430",
                       "date": "2026-10-05", "notes": "y"}],
             "tg": [], "week_start": "2026-09-29",
             "generated_at": "2026-10-06T00:00:00Z"},
            dry_run=False)
        self.assertEqual(result, "已更新")
        self.assertFalse(self._unchanged())

    def test_tg_outage_is_disclosed_on_page(self):
        # 抓不到公告时必须写明「不代表本周没有发布」，否则读者会误读。
        pending: list[str] = []
        text = docs_watch.render_surge_changelog(
            {"stable": [{"version": "6.9.1", "build": "12290",
                         "date": "2026-09-10", "notes": "x"}],
             "beta": [], "tg": [], "week_start": "2026-09-29",
             "generated_at": "2026-10-06T00:00:00Z"},
            {}, pending)
        self.assertIn("Telegram", text)
        self.assertIn("不代表", text)

    def test_all_sources_present_writes_file(self):
        result = docs_watch.write_changelog(
            self.dir, "mihomo",
            {"releases": [{"tag": "v1.19.32", "date": "2026-10-05", "body": "x"}],
             "alpha": [{"sha": "abc1234", "date": "2026-10-05",
                        "message": "fix: something"}],
             "week_start": "2026-09-29",
             "generated_at": "2026-10-06T00:00:00Z"},
            dry_run=True)
        self.assertEqual(result, "已更新")


class ProcessStatePreservationTests(unittest.TestCase):
    """抓取失败时连 marker 也不能动 —— 它是「上一版内容是什么」的唯一记录。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        Path(os.path.join(self.dir, "changelog.md")).write_text(
            "# 旧内容\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _run_process(self, target, log):
        state_path = os.path.join(self.dir, "upstream.json")
        Path(state_path).write_text(json.dumps({
            "changelog_marker": "v1.19.32|9f053c4|pend0",
            "facts": {}, "pages": {}, "generated_at": "2026-10-01T00:00:00Z",
        }), encoding="utf-8")
        # facts 必须非空：process() 开头有「本轮没采集到任何数据就保持原状」的早退，
        # 传空字典会走那条分支，测不到 changelog 这条路径。
        facts = {"release": {"value": {"tag": "v1.19.32"}, "changed_at": "2026-10-01T00:00:00Z"}}
        with patch.object(docs_watch, "TARGETS", {target: self.dir}), \
                patch.object(docs_watch, "ROOT", self.dir), \
                patch.object(docs_watch, "RENDERERS",
                             {target: lambda state: "<!-- AUTO-STATE:BEGIN -->x<!-- AUTO-STATE:END -->"}), \
                patch.object(docs_watch, "update_readme_block", return_value="未变化"), \
                patch.object(docs_watch, "surge_collect", return_value=(facts, {}, log)), \
                patch.object(docs_watch, "mihomo_collect", return_value=(facts, {}, log)):
            docs_watch.process(target, dry_run=False, fail_on_change=False)
        return json.loads(Path(state_path).read_text(encoding="utf-8"))

    def test_marker_survives_partial_fetch_failure(self):
        # releases 空、alpha 有 —— 正是线上踩到的组合。
        state = self._run_process("mihomo", {
            "releases": [], "alpha": [{"sha": "abc1234", "date": "2026-10-02"}],
            "week_start": "2026-09-29"})
        self.assertEqual(state["changelog_marker"], "v1.19.32|9f053c4|pend0")

    def test_marker_advances_when_fetch_is_healthy(self):
        state = self._run_process("mihomo", {
            "releases": [{"tag": "v1.19.33", "date": "2026-10-06", "body": "x"}],
            "alpha": [{"sha": "deadbee", "date": "2026-10-06", "message": "fix: y"}],
            "week_start": "2026-09-29"})
        # 只断言「版本|提交」这两段 —— 尾部是待译条数，取决于 fixtures 里
        # 有多少句没进 translations.json，跟本用例要守的语义无关。
        self.assertTrue(state["changelog_marker"].startswith("v1.19.33|deadbee|"))


if __name__ == "__main__":
    unittest.main()
