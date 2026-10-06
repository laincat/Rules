"""CNB Release 发布器的离线回归测试（不触网）。"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish_cnb_release as cnb  # noqa: E402


class StaleAssetCleanupTests(unittest.TestCase):
    """改名的旧附件必须从 CNB Release 删除，否则直链返回过期内容。"""

    def _run(self, existing):
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "Advertising.Drop.list"
            keep.write_text("DOMAIN-SUFFIX,x.example\n", encoding="utf-8")
            deleted: list[tuple[str, str]] = []

            def fake_delete(endpoint, slug, release_id, asset_id, name, token):
                deleted.append((name, asset_id))

            with patch.object(cnb, "release_assets", return_value=existing), \
                    patch.object(cnb, "get_release_by_tag",
                                 return_value={"id": "77", "assets": []}), \
                    patch.object(cnb, "upload_asset"), \
                    patch.object(cnb, "verify_published", return_value=[]), \
                    patch.object(cnb, "delete_asset", side_effect=fake_delete):
                argv = ["--files", str(keep), "--slug", "laincat/Rules",
                        "--token", "test-token"]
                with patch.object(sys, "argv", ["publish_cnb_release.py"] + argv):
                    rc = cnb.main()
            return rc, deleted

    def test_renamed_old_asset_is_deleted(self):
        existing = {
            "Advertising.Drop.list": {"id": "1", "hash_value": ""},
            "Advertising.Drop.rules": {"id": "2", "hash_value": "abc"},
        }
        rc, deleted = self._run(existing)
        self.assertEqual(rc, 0)
        self.assertEqual(deleted, [("Advertising.Drop.rules", "2")])

    def test_current_assets_are_never_deleted(self):
        existing = {
            "Advertising.Drop.list": {"id": "1", "hash_value": ""},
        }
        rc, deleted = self._run(existing)
        self.assertEqual(rc, 0)
        self.assertEqual(deleted, [])


if __name__ == "__main__":
    unittest.main()
