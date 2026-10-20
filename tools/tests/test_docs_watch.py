"""Offline regression tests for the two automatic weekly changelogs."""

from pathlib import Path
import datetime
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from unittest.mock import patch


_SPEC = importlib.util.spec_from_file_location(
    "docs_watch",
    str(Path(__file__).resolve().parents[1] / "docs_watch.py"),
)
docs_watch = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(docs_watch)


def recent_date(days_ago: int = 1) -> str:
    return (
        docs_watch.now_utc().date() - datetime.timedelta(days=days_ago)
    ).isoformat()


class ConsoleEncodingTests(unittest.TestCase):
    def test_gbk_console_does_not_abort_collection(self):
        output = io.BytesIO()
        console = io.TextIOWrapper(output, encoding="gbk", newline="\n")
        with patch.object(docs_watch.sys, "stdout", console):
            docs_watch.log("✓ 已更新")
        console.flush()
        self.assertEqual(
            output.getvalue().decode("gbk"),
            "\\u2713 已更新\n",
        )


class SourceTests(unittest.TestCase):
    def test_surge_feed_keeps_latest_posts_and_markdown(self):
        html = b"""
        <div data-post="SurgeTestFlightFeed/10">
          <div class="tgme_widget_message_text js-message_text">
            <b>Beta Updates</b><br/>
            Use <code>block-quic=adaptive</code> and
            <a href="https://example.com/guide">read the guide</a>.
          </div>
          <time datetime="2026-10-13T15:01:42Z"></time>
        </div>
        <div data-post="SurgeTestFlightFeed/11">
          <div class="tgme_widget_message_text">Newest</div>
          <time datetime="2026-10-14T09:00:00Z"></time>
        </div>
        """
        with patch.object(docs_watch, "http_get", return_value=html):
            posts = docs_watch.surge_tg_posts(limit=2)
        self.assertEqual([post["id"] for post in posts], ["11", "10"])
        self.assertIn("# Beta Updates", posts[1]["text"])
        self.assertIn("`block-quic=adaptive`", posts[1]["text"])
        self.assertIn(
            "[read the guide](https://example.com/guide)",
            posts[1]["text"],
        )
        self.assertEqual(posts[1]["date"], "2026-10-13")

    def test_surge_feed_without_messages_is_a_failed_fetch(self):
        with patch.object(docs_watch, "http_get", return_value=b"<html></html>"):
            self.assertIsNone(docs_watch.surge_tg_posts())

    def test_surge_feed_pages_until_the_week_boundary(self):
        def page(post_id, date):
            return (
                '<div data-post="SurgeTestFlightFeed/%d">'
                '<div class="tgme_widget_message_text">Post</div>'
                '<time datetime="%sT00:00:00Z"></time>'
                "</div>" % (post_id, date)
            ).encode()

        first = page(100, recent_date(1)) + page(99, recent_date(2))
        second = page(98, "2020-01-01")

        def fetch(url):
            return second if "before=99" in url else first

        with patch.object(docs_watch, "http_get", side_effect=fetch) as call:
            posts = docs_watch.surge_tg_posts()
        self.assertEqual(
            [post["id"] for post in posts],
            ["100", "99", "98"],
        )
        self.assertEqual(call.call_count, 2)

    def test_mihomo_alpha_parser_uses_first_message_line_and_link(self):
        sha = "a" * 40
        response = json.dumps([{
            "sha": sha,
            "html_url": "https://github.com/MetaCubeX/mihomo/commit/" + sha,
            "commit": {
                "message": "fix: close listener\n\nLonger explanation",
                "committer": {"date": "2026-10-13T12:02:16Z"},
            },
        }]).encode()
        with patch.object(docs_watch, "http_get", return_value=response):
            commits = docs_watch.mihomo_alpha_commits()
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["sha"], "aaaaaaa")
        self.assertEqual(commits[0]["date"], "2026-10-13")
        self.assertEqual(commits[0]["message"], "fix: close listener")
        self.assertIn("/commit/" + sha, commits[0]["url"])

    def test_invalid_github_payload_is_a_failed_fetch(self):
        with patch.object(docs_watch, "http_get", return_value=b'{"message":"bad"}'):
            self.assertIsNone(docs_watch.mihomo_alpha_commits())

    def test_seven_day_window_is_inclusive(self):
        now = datetime.datetime(2026, 10, 20, 12, tzinfo=datetime.timezone.utc)
        items = [
            {"date": "2026-10-13"},
            {"date": "2026-10-12"},
            {"date": None},
        ]
        self.assertEqual(
            docs_watch.within_week(items, now),
            [{"date": "2026-10-13"}],
        )


class AutoTranslationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "translations.json"
        self.original = {
            "entries": [{"en": "Known", "zh": "已有译文"}],
            "note": "preserve metadata",
        }
        self.path.write_text(
            json.dumps(self.original, ensure_ascii=False),
            encoding="utf-8",
        )

    def response(self, content, finish_reason="stop"):
        return io.BytesIO(json.dumps({
            "choices": [{
                "finish_reason": finish_reason,
                "message": {"content": content},
            }],
        }).encode())

    def test_api_preserves_literals_and_sends_no_credentials(self):
        source = (
            "Fix `behavior: classical` in v1.19.32: "
            "https://example.com/a"
        )
        with patch.object(
            docs_watch.urllib.request,
            "urlopen",
            return_value=self.response(
                "修复 __RULES_KEEP_0__，版本 __RULES_KEEP_1__："
                "__RULES_KEEP_2__"
            ),
        ) as call:
            translated = docs_watch.index_translate(source)
        self.assertEqual(
            translated,
            "修复 `behavior: classical`，版本 v1.19.32："
            "https://example.com/a",
        )
        request = call.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, docs_watch.TRANSLATE_URL)
        self.assertFalse(request.has_header("Authorization"))
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])

    def test_invalid_translation_is_rejected(self):
        for output, reason in (
            ("Fix only", "stop"),
            ("修复 __RULES_KEEP_0__ __RULES_KEEP_0__", "stop"),
            ("修复 __RULES_KEEP_9__", "stop"),
            ("修复 __RULES_KEEP_0__\n额外说明", "stop"),
            ("修复 __RULES_KEEP_0__，新增 https://evil.example", "stop"),
            ("修复 __RULES_KEEP_0__", "length"),
        ):
            with self.subTest(output=output):
                with patch.object(
                    docs_watch.urllib.request,
                    "urlopen",
                    return_value=self.response(output, reason),
                ):
                    with self.assertRaises(ValueError):
                        docs_watch.index_translate("Fix `test-url`")

    def test_literal_only_source_never_calls_api(self):
        with patch.object(docs_watch.urllib.request, "urlopen") as call:
            self.assertEqual(
                docs_watch.index_translate("https://example.com/a"),
                "https://example.com/a",
            )
        call.assert_not_called()

    def test_bold_product_name_is_not_treated_as_a_bullet(self):
        pending = []
        self.assertEqual(
            docs_watch.translate_block("**WireGuard**", {}, pending),
            ["**WireGuard**"],
        )
        self.assertEqual(pending, [])

    def test_cache_reuses_entries_and_preserves_metadata(self):
        with patch.object(
            docs_watch,
            "index_translate",
            return_value="修复问题",
        ) as call:
            self.assertEqual(
                docs_watch.fill_translations(
                    self.tmp.name,
                    ["Known", "Fix issue", "Fix issue"],
                ),
                1,
            )
            self.assertEqual(
                docs_watch.fill_translations(
                    self.tmp.name,
                    ["Fix issue"],
                ),
                0,
            )
        call.assert_called_once()
        cached = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(cached["entries"][0], self.original["entries"][0])
        self.assertEqual(cached["note"], self.original["note"])
        self.assertEqual(
            cached["entries"][1]["provider"],
            "Index-Translate",
        )

    def test_service_outage_keeps_catalog_unchanged(self):
        original = self.path.read_bytes()
        error = urllib.error.HTTPError("", 429, "", {}, None)
        self.addCleanup(error.close)
        with patch.object(docs_watch, "index_translate", side_effect=error):
            self.assertEqual(
                docs_watch.fill_translations(
                    self.tmp.name,
                    ["Fix issue"],
                ),
                0,
            )
        self.assertEqual(self.path.read_bytes(), original)

    def test_bad_catalog_is_never_overwritten(self):
        self.path.write_text("{broken", encoding="utf-8")
        with patch.object(docs_watch, "index_translate") as call:
            self.assertEqual(
                docs_watch.fill_translations(
                    self.tmp.name,
                    ["Fix issue"],
                ),
                0,
            )
        call.assert_not_called()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{broken")


class RenderingTests(unittest.TestCase):
    def test_surge_render_is_telegram_only_and_translated(self):
        pending = []
        catalog = {
            "Beta Updates": "测试版更新",
            "Fix issue": "修复问题",
        }
        text = docs_watch.render_surge_changelog(
            [{
                "id": "42",
                "date": recent_date(),
                "url": "https://t.me/SurgeTestFlightFeed/42",
                "text": "# Beta Updates\n- Fix issue",
            }],
            catalog,
            pending,
        )
        self.assertIn("### 测试版更新", text)
        self.assertIn("- 修复问题", text)
        self.assertNotIn("appcast", text)
        self.assertNotIn("GitHub Release", text)
        self.assertEqual(pending, [])

    def test_mihomo_render_groups_alpha_commits(self):
        pending = []
        catalog = {
            "fix: close listener": "修复：关闭监听器",
            "feat: add option": "新功能：增加选项",
        }
        text = docs_watch.render_mihomo_changelog(
            [{
                "sha": "aaaaaaa",
                "full_sha": "a" * 40,
                "date": recent_date(),
                "url": "https://example.com/a",
                "message": "fix: close listener",
            }, {
                "sha": "bbbbbbb",
                "full_sha": "b" * 40,
                "date": recent_date(),
                "url": "https://example.com/b",
                "message": "feat: add option",
            }],
            catalog,
            pending,
        )
        self.assertIn("## 本周概览", text)
        self.assertIn("- 新功能：1 条", text)
        self.assertIn("- 修复：1 条", text)
        self.assertIn("修复：关闭监听器", text)
        self.assertIn("新功能：增加选项", text)
        self.assertNotIn("GitHub Releases", text)
        self.assertEqual(pending, [])


class WriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "readme.md"
        self.path.write_text("# old\n", encoding="utf-8")
        self.catalog = Path(self.tmp.name) / "translations.json"
        self.catalog.write_text(
            json.dumps({
                "entries": [{
                    "en": "fix: close listener",
                    "zh": "修复：关闭监听器",
                }],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_source_failure_preserves_existing_changelog(self):
        result = docs_watch.write_changelog(
            self.tmp.name,
            "mihomo",
            None,
            dry_run=False,
        )
        self.assertIn("跳过", result)
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            "# old\n",
        )

    def test_healthy_source_updates_changelog(self):
        result = docs_watch.write_changelog(
            self.tmp.name,
            "mihomo",
            [{
                "sha": "aaaaaaa",
                "full_sha": "a" * 40,
                "date": recent_date(),
                "url": "https://example.com/a",
                "message": "fix: close listener",
            }],
            dry_run=False,
        )
        self.assertEqual(result, "已更新")
        self.assertIn(
            "修复：关闭监听器",
            self.path.read_text(encoding="utf-8"),
        )

    def test_dry_run_does_not_call_translation_or_write(self):
        with patch.object(docs_watch, "index_translate") as translate:
            result = docs_watch.write_changelog(
                self.tmp.name,
                "mihomo",
                [{
                    "sha": "aaaaaaa",
                    "full_sha": "a" * 40,
                    "date": recent_date(),
                    "url": "https://example.com/a",
                    "message": "fix: untranslated",
                }],
                dry_run=True,
            )
        self.assertEqual(result, "已更新")
        translate.assert_not_called()
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            "# old\n",
        )


class ProcessTests(unittest.TestCase):
    def test_fetch_failure_is_nonzero(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(docs_watch, "TARGETS", {"surge": directory}), \
                patch.object(docs_watch, "surge_tg_posts", return_value=None), \
                patch.object(docs_watch, "log"):
            self.assertEqual(
                docs_watch.process("surge"),
                (False, False),
            )

    def test_successful_no_change_is_healthy(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(docs_watch, "TARGETS", {"mihomo": directory}), \
                patch.object(docs_watch, "mihomo_alpha_commits", return_value=[]), \
                patch.object(docs_watch, "write_changelog", return_value="未变化"), \
                patch.object(docs_watch, "log"):
            self.assertEqual(
                docs_watch.process("mihomo"),
                (True, False),
            )

    def test_invalid_cli_target_fails(self):
        with patch.object(
            docs_watch.sys,
            "argv",
            ["docs_watch.py", "--target", "invalid"],
        ), patch.object(docs_watch, "log"):
            self.assertEqual(docs_watch.main(), 2)


if __name__ == "__main__":
    unittest.main()
