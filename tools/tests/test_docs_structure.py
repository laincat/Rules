"""Structural guards for the replacement Changelog directories."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ChangelogStructureTests(unittest.TestCase):
    def test_legacy_docs_directories_are_gone(self):
        self.assertFalse((ROOT / "Surge" / "Docs").exists())
        self.assertFalse((ROOT / "Mihomo" / "Docs").exists())

    def test_each_changelog_directory_contains_only_generated_artifacts(self):
        for product in ("Surge", "Mihomo"):
            folder = ROOT / product / "Changelog"
            self.assertTrue(folder.is_dir())
            self.assertEqual(
                {path.name for path in folder.iterdir() if path.is_file()},
                {"readme.md", "translations.json"},
            )
            self.assertFalse(any(path.is_dir() for path in folder.iterdir()))

    def assert_surge_telegram_sources(self, text):
        lines = text.splitlines()
        self.assertIn("Surge Telegram 每周更新日志", text)
        self.assertIn(
            "> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。",
            lines,
        )

        # Check the generated announcement headings, not the announcement text.
        post_headings = [
            line for line in lines
            if line.startswith("## ") and line != "## 中文翻译"
        ]
        if not post_headings:
            self.assertIn("最近 7 天没有可用公告。", lines)
        for heading in post_headings:
            self.assertRegex(
                heading,
                r"^## \[#([0-9]+)\]\(https://t\.me/SurgeTestFlightFeed/\1\)"
                r" · (?:[0-9]{4}-[0-9]{2}-[0-9]{2}|日期未知)$",
            )

    def test_surge_changelog_has_only_the_telegram_source(self):
        text = (ROOT / "Surge" / "Changelog" / "readme.md").read_text(
            encoding="utf-8"
        )
        self.assert_surge_telegram_sources(text)

    def test_surge_announcement_can_mention_distribution_channels(self):
        self.assert_surge_telegram_sources(
            "# Surge Telegram 每周更新日志（自动生成）\n"
            "> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。\n"
            "## [#464](https://t.me/SurgeTestFlightFeed/464) · 2026-11-19\n"
            "### Surge iOS 已在 App Store 上架\n"
            "[在 App Store 下载](https://apps.apple.com/app/id1442620678)\n"
            "其他渠道：appcast 和 GitHub Release。\n"
            "## 中文翻译\n"
        )

    def test_surge_changelog_rejects_other_sources_and_mismatched_ids(self):
        header = (
            "# Surge Telegram 每周更新日志（自动生成）\n"
            "> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。\n"
        )
        for heading in (
            "## [#464](https://apps.apple.com/app/id1442620678) · 2026-11-19",
            "## [#464](https://t.me/OtherFeed/464) · 2026-11-19",
            "## [#464](https://t.me/SurgeTestFlightFeed/465) · 2026-11-19",
            "## GitHub Releases",
        ):
            with self.subTest(heading=heading), self.assertRaises(AssertionError):
                self.assert_surge_telegram_sources(header + heading)

    def test_surge_changelog_allows_empty_feed(self):
        self.assert_surge_telegram_sources(
            "# Surge Telegram 每周更新日志（自动生成）\n"
            "> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。\n"
            "最近 7 天没有可用公告。\n"
            "## 中文翻译\n"
        )

    def test_mihomo_changelog_has_only_alpha_commits(self):
        text = (ROOT / "Mihomo" / "Changelog" / "readme.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Mihomo Alpha 每周提交摘要", text)
        self.assertIn("MetaCubeX/mihomo/tree/Alpha", text)
        self.assertNotIn("GitHub Releases", text)
        self.assertNotIn("正式版历史", text)

    def test_repository_readmes_link_to_changelog_paths(self):
        for relative in ("Readme.md", "Surge/Readme.md", "Mihomo/Readme.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("Changelog/", text)
            self.assertNotIn("](Docs/", text)
            self.assertNotIn("](../Docs/", text)

    def test_no_markdown_link_targets_removed_docs(self):
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("](Docs/", text, str(path))
            self.assertNotIn("](../Docs/", text, str(path))


if __name__ == "__main__":
    unittest.main()
