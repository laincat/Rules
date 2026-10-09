"""更新日志写入器的离线回归测试（不触网）。

守的是这条不变量：**任何一个主数据源抓取失败，都不得覆盖已有的 changelog.md**。
线上真实踩过一次死角 —— 判据写成 `not releases and not alpha`，
于是「Alpha 抓成功、发布列表抓失败」时页面照样重写，
把整张「正式版历史」表清空。这类失败是静默的：页面不会报错，只是少了一半内容。
"""

from pathlib import Path
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch


_SPEC = importlib.util.spec_from_file_location(
    "docs_watch", str(Path(__file__).resolve().parents[1] / "docs_watch.py"))
docs_watch = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(docs_watch)


ORIGINAL = "# 原始内容\n\n不得被覆盖。\n"


class ConsoleEncodingTests(unittest.TestCase):
    def test_gbk_console_does_not_abort_collection(self):
        output = io.BytesIO()
        console = io.TextIOWrapper(output, encoding="gbk", newline="\n")
        with patch.object(docs_watch.sys, "stdout", console):
            docs_watch.log("✓ 与上次记录一致")
        console.flush()
        self.assertEqual(output.getvalue().decode("gbk"),
                         "\\u2713 与上次记录一致\n")


class AutoTranslationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "translations.json"
        self.original = {"entries": [{"en": "Known", "zh": "已有译文"}],
                         "note": "preserve metadata"}
        self.path.write_text(json.dumps(self.original), encoding="utf-8")

    def _response(self, content, finish_reason="stop"):
        return io.BytesIO(json.dumps({
            "choices": [{"finish_reason": finish_reason,
                         "message": {"content": content}}]}).encode())

    def test_api_preserves_literals_and_sends_no_credentials(self):
        source = "Fix `behavior: classical` in v1.19.32: https://example.com/a"
        with patch.object(docs_watch.urllib.request, "urlopen", return_value=self._response(
                "修复 __RULES_KEEP_0__，版本 __RULES_KEEP_1__：__RULES_KEEP_2__")) as call:
            translated = docs_watch.index_translate(source)
        self.assertEqual(translated,
                         "修复 `behavior: classical`，版本 v1.19.32：https://example.com/a")
        request = call.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, docs_watch.TRANSLATE_URL)
        self.assertFalse(request.has_header("Authorization"))
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])

    def test_invalid_outputs_are_rejected(self):
        for output, reason in (
                ("修复参数", "stop"),
                ("修复 __RULES_KEEP_0__ __RULES_KEEP_0__", "stop"),
                ("修复 __RULES_KEEP_9__", "stop"),
                ("Fix __RULES_KEEP_0__", "stop"),
                ("修复 __RULES_KEEP_0__\n额外说明", "stop"),
                ("修复 __RULES_KEEP_0__，新增 https://evil.example", "stop"),
                ("修复 __RULES_KEEP_0__", "length")):
            with self.subTest(output=output, reason=reason):
                with patch.object(docs_watch.urllib.request, "urlopen",
                                  return_value=self._response(output, reason)):
                    with self.assertRaises(ValueError):
                        docs_watch.index_translate("Fix `test-url`")

    def test_literal_only_source_needs_no_api(self):
        with patch.object(docs_watch.urllib.request, "urlopen") as call:
            self.assertEqual(docs_watch.index_translate("https://example.com/a"),
                             "https://example.com/a")
        call.assert_not_called()

    def test_cache_reuses_entries_deduplicates_and_keeps_metadata(self):
        with patch.object(docs_watch, "index_translate", return_value="修复问题") as call:
            self.assertEqual(docs_watch.fill_translations(
                self.tmp.name, ["Known", "Fix issue", "Fix issue"]), 1)
            self.assertEqual(docs_watch.fill_translations(self.tmp.name, ["Fix issue"]), 0)
        call.assert_called_once()
        cached = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(cached["entries"][0], self.original["entries"][0])
        self.assertEqual(cached["note"], self.original["note"])
        self.assertEqual(cached["entries"][1]["provider"], "Index-Translate")

    def test_service_outage_keeps_catalog_unchanged(self):
        original = self.path.read_bytes()
        error = urllib.error.HTTPError("", 429, "", {}, None)
        self.addCleanup(error.close)
        with patch.object(docs_watch, "index_translate",
                          side_effect=error):
            self.assertEqual(docs_watch.fill_translations(self.tmp.name, ["Fix issue"]), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_bad_catalog_is_never_overwritten(self):
        self.path.write_text("{broken", encoding="utf-8")
        with patch.object(docs_watch, "index_translate") as call:
            self.assertEqual(docs_watch.fill_translations(self.tmp.name, ["Fix issue"]), 0)
        call.assert_not_called()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{broken")

    def test_request_limit_leaves_remaining_items_for_next_run(self):
        with patch.object(docs_watch, "index_translate", return_value="修复问题") as call:
            self.assertEqual(docs_watch.fill_translations(
                self.tmp.name, ["Fix issue %d" % i for i in range(41)]), 40)
        self.assertEqual(call.call_count, 40)

    def test_deadline_prevents_further_calls(self):
        with patch.object(docs_watch.time, "monotonic", side_effect=[0, 121]), \
                patch.object(docs_watch, "index_translate") as call:
            self.assertEqual(docs_watch.fill_translations(self.tmp.name, ["Fix issue"]), 0)
        call.assert_not_called()

    def _changelog(self):
        return {
            "releases": [{"tag": "v1.19.32", "date": "2026-10-08", "body": "- Fix issue"}],
            "alpha": [{"sha": "abc1234", "date": "2026-10-08", "message": "Fix issue"}],
            "week_start": "2026-10-01", "generated_at": "2026-10-08T00:00:00Z"}

    def test_accepted_translation_reaches_changelog_and_clears_pending(self):
        changelog = self._changelog()
        with patch.object(docs_watch, "index_translate", return_value="修复问题"):
            docs_watch.write_changelog(self.tmp.name, "mihomo", changelog, False)
        self.assertEqual(changelog["pending"], [])
        self.assertIn("修复问题",
                      (Path(self.tmp.name) / "changelog.md").read_text(encoding="utf-8"))

    def test_rejected_translation_keeps_english_and_pending(self):
        original = self.path.read_bytes()
        changelog = self._changelog()
        with patch.object(docs_watch, "index_translate", side_effect=ValueError("bad output")):
            docs_watch.write_changelog(self.tmp.name, "mihomo", changelog, False)
        self.assertEqual(changelog["pending"], ["Fix issue"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn("Fix issue",
                      (Path(self.tmp.name) / "changelog.md").read_text(encoding="utf-8"))

    def test_dry_run_and_opt_out_make_no_translation_calls(self):
        original = self.path.read_bytes()
        with patch.object(docs_watch, "index_translate") as call:
            docs_watch.write_changelog(self.tmp.name, "mihomo", self._changelog(), True)
            self.assertFalse((Path(self.tmp.name) / "changelog.md").exists())
            docs_watch.write_changelog(
                self.tmp.name, "mihomo", self._changelog(), False, auto_translate=False)
        call.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)


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


class AttentionReportTests(unittest.TestCase):
    def test_routine_updates_need_no_attention(self):
        old = {"facts": {key: {"value": 1} for key in (
            "mac-beta", "mac-stable", "ios-stable", "tg-max-id",
            "release", "alpha", "alpha-ahead", "community-yamls")}}
        new = {"facts": {key: {"value": 2} for key in old["facts"]}}
        self.assertTrue(docs_watch.diff_facts(old, new))
        self.assertEqual(docs_watch.attention_reasons(old, new, [], [], "已更新"), [])

    def test_configuration_reference_changes_need_attention(self):
        for key in ("manual-digest", "manual-pages", "kb-digest", "kb-pages-en",
                    "kb-pages-zh", "config-yaml", "metadocs", "wiki"):
            with self.subTest(key=key):
                reasons = docs_watch.attention_reasons(
                    {"facts": {key: {"value": "old"}}},
                    {"facts": {key: {"value": "new"}}}, [], [], "已更新")
                self.assertEqual(len(reasons), 1)
                self.assertIn(key, reasons[0])

    def test_page_changes_and_unfinished_updates_need_attention(self):
        reasons = docs_watch.attention_reasons(
            {}, {}, ["manual/proxy.html"], ["Fix issue"],
            "跳过（本轮没抓到 releases，保留原文件）")
        self.assertEqual(len(reasons), 3)
        self.assertIn("manual/proxy.html", reasons[0])
        self.assertIn("releases", reasons[1])
        self.assertIn("1 条待译", reasons[2])

    def _run(self, collected, fail_on_change=False):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "upstream.json"
            state_path.write_text(json.dumps({
                "facts": {"alpha-ahead": {"value": 1, "changed_at": "old"}},
                "pages": {}, "generated_at": "old",
            }), encoding="utf-8")
            report_path = Path(directory) / "report.json"
            args = ["docs_watch.py", "--target", "mihomo", "--report", str(report_path)]
            if fail_on_change:
                args.append("--fail-on-change")
            with patch.object(docs_watch.sys, "argv", args), \
                    patch.object(docs_watch, "TARGETS", {"mihomo": directory}), \
                    patch.object(docs_watch, "ROOT", directory), \
                    patch.object(docs_watch, "mihomo_collect", return_value=collected), \
                    patch.object(docs_watch, "update_readme_block", return_value="未变化"), \
                    patch.object(docs_watch, "write_changelog", return_value="已更新"), \
                    patch.object(docs_watch, "log"):
                code = docs_watch.main()
            return (code, json.loads(report_path.read_text(encoding="utf-8")),
                    json.loads(state_path.read_text(encoding="utf-8")))

    def test_report_keeps_original_diff_after_baseline_is_written(self):
        for fail_on_change, expected_code in ((False, 0), (True, 1)):
            with self.subTest(fail_on_change=fail_on_change):
                code, report, state = self._run(
                    ({"alpha-ahead": 4}, {}, {}), fail_on_change)
                self.assertEqual(code, expected_code)
                self.assertEqual(state["facts"]["alpha-ahead"]["value"], 4)
                self.assertTrue(report["changed"])
                self.assertFalse(report["needs_attention"])
                self.assertEqual(report["targets"][0]["changes"], ["alpha-ahead: 1 -> 4"])
                self.assertEqual(report["targets"][0]["pending_count"], 0)

    def test_pending_translation_needs_attention_even_without_upstream_changes(self):
        code, report, _ = self._run(
            ({"alpha-ahead": 1}, {}, {"pending": ["Fix issue"]}))
        self.assertEqual(code, 0)
        self.assertFalse(report["changed"])
        self.assertTrue(report["needs_attention"])
        self.assertEqual(report["targets"][0]["pending_count"], 1)

    def test_total_collection_failure_is_reported_without_overwriting_state(self):
        code, report, state = self._run(({}, {}, {}))
        self.assertEqual(code, 0)
        self.assertFalse(report["changed"])
        self.assertTrue(report["needs_attention"])
        self.assertTrue(report["targets"][0]["attention_reasons"])
        self.assertEqual(state["facts"]["alpha-ahead"]["value"], 1)

    def test_report_requires_a_path(self):
        with patch.object(docs_watch.sys, "argv", ["docs_watch.py", "--report"]), \
                patch.object(docs_watch, "process") as process, \
                patch.object(docs_watch, "log"):
            self.assertEqual(docs_watch.main(), 2)
        process.assert_not_called()


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
