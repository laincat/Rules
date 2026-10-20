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

    def test_surge_changelog_has_only_the_telegram_source(self):
        text = (ROOT / "Surge" / "Changelog" / "readme.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Surge Telegram 每周更新日志", text)
        self.assertIn("@SurgeTestFlightFeed", text)
        self.assertNotIn("appcast", text.lower())
        self.assertNotIn("GitHub Release", text)
        self.assertNotIn("App Store", text)

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
