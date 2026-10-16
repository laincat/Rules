"""Offline checks of tracked Surge files; not a substitute for the Surge engine."""
from pathlib import Path
import fnmatch
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules

ROOT = Path(__file__).resolve().parents[2]
DOMAINSETS = {"AI.list", "Ozon.list", "Advertising.Reject.list", "Advertising.RejectExtra.list"}


def active(path):
    return [s.strip() for s in path.read_text().splitlines()
            if s.strip() and not s.lstrip().startswith(("#", ";", "//"))]


def hongguo_policy(host):
    for line in active(ROOT / "Surge/Advertising/HongGuo.sgmodule"):
        if line.startswith("["):
            continue
        kind, pattern, policy = line.split(",")
        match = (kind == "DOMAIN" and host == pattern
                 or kind == "DOMAIN-SUFFIX" and (host == pattern or host.endswith("." + pattern))
                 or kind == "DOMAIN-WILDCARD" and fnmatch.fnmatchcase(host, pattern))
        if match:
            return policy
    return None


class SurgeArtifactTests(unittest.TestCase):
    def test_hongguo_ads_reject_before_cdn_fallback(self):
        for part in ("reading-ad", "bd-daily-reading-ad", "se-daily-reading-ad", "se-sjy-daily-reading-ad"):
            for prefix in ("v1", "v6", "v99"):
                with self.subTest(part=part, prefix=prefix):
                    self.assertEqual(hongguo_policy(f"{prefix}-{part}.qznovelvod.com"), "REJECT")

    def test_hongguo_playback_images_and_api_remain_direct(self):
        for host in ("v1-reading-video.qznovelvod.com", "v6-reading-videocdn.qznovelvod.com",
                     "n98-v-readingvideo.qznovelvod.com", "other.qznovelvod.com",
                     "audio-fq-tts.fqnovelvod.com", "p3-novel.byteimg.com",
                     "p3-ad-sign.byteimg.com", "p3-tt.byteimg.com",
                     "api5-normal.fqnovel.com", "api5-normal-lq.fqnovel.com"):
            with self.subTest(host=host):
                self.assertEqual(hongguo_policy(host), "DIRECT")
        self.assertEqual(hongguo_policy("p4-ad-sign.byteimg.com"), "REJECT")
        self.assertIsNone(hongguo_policy("v1-reading-ad.qznovelvod.com.example.org"))

    def test_nodrop_precedes_generic_reject_but_not_drop(self):
        text = (ROOT / "Surge/Advertising/Advertising.sgmodule").read_text()
        self.assertLess(text.index("Advertising.Drop.list"), text.index("Advertising.NoDrop.list"))
        for name in ("Reject", "RejectExtra", "NonIP"):
            self.assertLess(text.index("Advertising.NoDrop.list"), text.index(f"Advertising.{name}.list"))

    def test_hongguo_named_exceptions_not_rejected_by_prematching_shards(self):
        # Concrete hosts only; this does not prove all wildcard intersections empty.
        hosts = ('p3-tt.byteimg.com', 'p3-ad-sign.byteimg.com',
                 'n98-v-readingvideo.qznovelvod.com',
                 'v6-reading-video.qznovelvod.com', 'p3-novel.byteimg.com',
                 'api5-normal.fqnovel.com', 'audio-fq-tts.fqnovelvod.com')
        for path in sorted((ROOT / "Surge/Advertising").glob("*.list")):
            if path.name == "Advertising.IP.list":
                continue
            for line in active(path):
                if path.name in DOMAINSETS:
                    kind, value = ('DOMAIN-SUFFIX', line[1:]) if line.startswith('.') else ('DOMAIN', line)
                else:
                    parts = line.split(',')
                    kind, value = parts[:2]
                for host in hosts:
                    hit = (kind == 'DOMAIN' and host == value
                           or kind == 'DOMAIN-SUFFIX' and (host == value or host.endswith('.' + value))
                           or kind == 'DOMAIN-KEYWORD' and value in host
                           or kind == 'DOMAIN-WILDCARD' and fnmatch.fnmatchcase(host, value))
                    self.assertFalse(hit, f"{host} blocked by {path.name}: {line}")

    def test_all_list_formats_and_duplicates(self):
        paths = sorted((ROOT / "Surge").rglob("*.list"))
        self.assertEqual(len(paths), 14)
        for path in paths:
            with self.subTest(path=path):
                lines = active(path)
                self.assertEqual(len(lines), len(set(lines)))
                for line in lines:
                    if path.name in DOMAINSETS:
                        self.assertEqual(rules.normalize_domain(line.lstrip(".")), line.lstrip("."))
                    else:
                        self.assertRegex(line, r"^(DOMAIN(?:-SUFFIX|-KEYWORD|-WILDCARD)?|IP-CIDR6?|IP-ASN|AND|OR|NOT|PROCESS-NAME|URL-REGEX),")

    def test_local_module_references_exist_and_have_correct_format(self):
        modules = sorted((ROOT / "Surge").rglob("*.sgmodule"))
        self.assertEqual(len(modules), 12)
        for path in modules:
            for line in active(path):
                match = re.match(r"(RULE-SET|DOMAIN-SET),\s*https://raw.githubusercontent.com/laincat/Rules/main/([^, ]+)", line)
                if match:
                    target = ROOT / match[2]
                    self.assertTrue(target.is_file(), str(target))
                    self.assertEqual(match[1], "DOMAIN-SET" if target.name in DOMAINSETS else "RULE-SET")

    def test_domainset_artifacts_respect_whitelist_snapshot(self):
        whitelist = rules.parse_skk_whitelist((Path(__file__).parent / "fixtures/skk_whitelist.ts").read_text())
        for name in ("Advertising.Reject.list", "Advertising.RejectExtra.list"):
            rs = rules.RuleSet()
            rules.parse_sukka_domainset((ROOT / "Surge/Advertising" / name).read_text(), rs)
            before = (set(rs.exact), set(rs.suffix))
            rules.filter_ads_domains(rs, set(), whitelist=whitelist | rules.LOCAL_ADS_WHITELIST)
            self.assertEqual(before, (rs.exact, rs.suffix), name)


if __name__ == "__main__":
    unittest.main()
