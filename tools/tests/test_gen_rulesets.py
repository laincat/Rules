"""Offline regression tests for domain cleaning and advertising safeguards."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules  # noqa: E402


PSL_TEXT = """
// ===BEGIN ICANN DOMAINS===
com
org
uk
co.uk
ck
*.ck
!www.ck
// ===END ICANN DOMAINS===
// ===BEGIN PRIVATE DOMAINS===
github.io
// ===END PRIVATE DOMAINS===
"""


class DomainNormalizationTests(unittest.TestCase):
    def test_case_trailing_dot_and_idna_are_normalized(self):
        cases = {
            "Ads.Example.COM.": "ads.example.com",
            "b\u00fccher.example": "xn--bcher-kva.example",
            "XN--BCHER-KVA.Example.": "xn--bcher-kva.example",
            "xn--fa-hia.de": "xn--fa-hia.de",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(rules.normalize_domain(value), expected)

    def test_ip_literals_and_invalid_labels_are_rejected(self):
        invalid = [
            "", "localhost", "127.0.0.1", "0.0.0.0", "2001:db8::1",
            "[2001:db8::1]", "-ads.example.com", "ads-.example.com",
            "ads..example.com", "_ads.example.com", "*.example.com",
            "https://ads.example.com", "ads.example.com/path",
            "ads.example.com:443", "ads example.com", "a" * 64 + ".com",
            ".".join(["a" * 63] * 4), "ads.example.com..",
            "foo.123", "999.1.2.3",
        ]
        for value in invalid:
            with self.subTest(value=value):
                self.assertIsNone(rules.normalize_domain(value))

    def test_classical_parser_cannot_emit_ip_as_domain(self):
        rs = rules.RuleSet()
        rs.add_classical(
            "DOMAIN,127.0.0.1\n"
            "DOMAIN-SUFFIX,0.0.0.0\n"
            "DOMAIN,Ads.Example.COM.\n"
            "DOMAIN-SUFFIX,b\u00fccher.example\n"
        )
        self.assertEqual(rs.exact, {"ads.example.com"})
        self.assertEqual(rs.suffix, {"xn--bcher-kva.example"})

    def test_domainset_parsers_keep_exact_and_suffix_semantics(self):
        cats = rules.RuleSet()
        rules.parse_cats_domainset(
            "127.0.0.1\n.Ads.Example.COM.\nb\u00fccher.example\n", cats
        )
        self.assertEqual(
            cats.suffix, {"ads.example.com", "xn--bcher-kva.example"}
        )
        sukka = rules.RuleSet()
        rules.parse_sukka_domainset(
            "0.0.0.0\n.Ads.Example.COM.\nb\u00fccher.example\n", sukka
        )
        self.assertEqual(sukka.suffix, {"ads.example.com"})
        self.assertEqual(sukka.exact, {"xn--bcher-kva.example"})

    def test_cats_surge_keeps_platform_specific_rules_separate(self):
        domains = rules.RuleSet()
        keywords = rules.RuleSet()
        counts = rules.parse_cats_surge(
            "# comment\n"
            "DOMAIN-SUFFIX,Ads.Example.COM.\n"
            "DOMAIN-WILDCARD,*.ad.example.com\n"
            "DOMAIN-KEYWORD,adsense\n"
            "PROCESS-NAME,ignored\n",
            domains,
            keywords,
        )
        self.assertEqual(counts["suffix"], 1)
        self.assertEqual(counts["wildcard"], 1)
        self.assertEqual(counts["keyword"], 1)
        self.assertEqual(counts["unsupported"], 1)
        self.assertEqual(domains.suffix, {"ads.example.com"})
        self.assertEqual(keywords.keyword, {"adsense"})
        self.assertEqual(domains.wildcards, {"*.ad.example.com"})

    def test_cats_surge_arbitrary_wildcards_are_preserved_verbatim(self):
        domains = rules.RuleSet()
        keywords = rules.RuleSet()
        counts = rules.parse_cats_surge(
            "DOMAIN-WILDCARD,*-ad.byteimg.com\n"
            "DOMAIN-WILDCARD,163487*.example.com\n",
            domains,
            keywords,
        )
        self.assertEqual(counts["wildcard"], 2)
        self.assertEqual(domains.wildcards,
                         {"*-ad.byteimg.com", "163487*.example.com"})


class PublicSuffixTests(unittest.TestCase):
    def setUp(self):
        self.psl = rules.PublicSuffixList.from_text(PSL_TEXT)

    def test_icann_and_private_suffixes_are_protected(self):
        for domain in ["com", "co.uk", "github.io"]:
            with self.subTest(domain=domain):
                self.assertTrue(self.psl.is_public_suffix(domain))
        for domain in ["example.com", "ads.example.co.uk", "ads.github.io"]:
            with self.subTest(domain=domain):
                self.assertFalse(self.psl.is_public_suffix(domain))

    def test_wildcard_and_exception_rules(self):
        self.assertTrue(self.psl.is_public_suffix("ads.ck"))
        self.assertFalse(self.psl.is_public_suffix("www.ck"))
        self.assertFalse(self.psl.is_public_suffix("tracking.ads.ck"))
        self.assertFalse(self.psl.is_public_suffix("tracking.www.ck"))

    def test_ads_drop_public_suffixes_but_keep_individual_tenants(self):
        rs = rules.RuleSet()
        rs.suffix.update({
            "com", "co.uk", "github.io", "ads.ck", "www.ck",
            "ads.github.io", "ads.example.co.uk", "tracking.ads.ck",
        })
        with patch.dict(rules.ADS_NEVER_BLOCK_SUFFIX, {}, clear=True):
            with patch.dict(rules.ADS_NEVER_BLOCK_EXACT, {}, clear=True):
                rules.filter_ads_domains(rs, set(), public_suffixes=self.psl)
        self.assertEqual(
            rs.suffix,
            {"www.ck", "ads.github.io", "ads.example.co.uk", "tracking.ads.ck"},
        )


class AdvertisingProtectionTests(unittest.TestCase):
    def setUp(self):
        self.suffix_patch = patch.dict(
            rules.ADS_NEVER_BLOCK_SUFFIX, {}, clear=True
        )
        self.exact_patch = patch.dict(
            rules.ADS_NEVER_BLOCK_EXACT, {}, clear=True
        )
        self.suffix_patch.start()
        self.exact_patch.start()
        self.addCleanup(self.suffix_patch.stop)
        self.addCleanup(self.exact_patch.stop)

    def test_parent_suffix_cannot_override_protected_child(self):
        rs = rules.RuleSet()
        rs.suffix.update({"example.com", "ads.example.com"})
        rs.exact.update({"pay.example.com", "tracking.example.com"})
        rules.filter_ads_domains(rs, {"pay.example.com"})
        self.assertEqual(rs.suffix, {"ads.example.com"})
        self.assertEqual(rs.exact, {"tracking.example.com"})

    def test_suffix_protection_covers_descendants_and_ancestors(self):
        rules.ADS_NEVER_BLOCK_SUFFIX["pay.example.com"] = "payment service"
        rs = rules.RuleSet()
        rs.suffix.update({
            "example.com", "pay.example.com", "api.pay.example.com",
            "ads.example.com",
        })
        rs.exact.update({"api.pay.example.com", "tracking.example.com"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"ads.example.com"})
        self.assertEqual(rs.exact, {"tracking.example.com"})

    def test_exact_protection_does_not_release_other_subdomains(self):
        rules.ADS_NEVER_BLOCK_EXACT["pay.example.com"] = "payment endpoint"
        rs = rules.RuleSet()
        rs.suffix.update({"example.com", "ads.pay.example.com"})
        rs.exact.update({"pay.example.com", "api.pay.example.com"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"ads.pay.example.com"})
        self.assertEqual(rs.exact, {"api.pay.example.com"})

    def test_filters_run_before_redundancy_removal(self):
        rs = rules.RuleSet()
        rs.suffix.update({"example.com", "ads.example.com"})
        rs.exact.update({"safe.example.com", "metrics.example.com"})
        rules.filter_ads_domains(rs, {"safe.example.com"})
        self.assertEqual(rs.suffix, {"ads.example.com"})
        self.assertEqual(rs.exact, {"metrics.example.com"})

    def test_final_cleaning_still_removes_redundant_entries(self):
        rs = rules.RuleSet()
        rs.suffix.update({"ads.example.com", "sub.ads.example.com"})
        rs.exact.update({"adserver.ads.example.com", "tracking.example.com"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"ads.example.com"})
        self.assertEqual(rs.exact, {"tracking.example.com"})

    def test_keywords_cannot_match_protected_domains(self):
        rules.ADS_NEVER_BLOCK_SUFFIX["alipay.com"] = "payment service"
        rules.ADS_NEVER_BLOCK_EXACT["safe.example.com"] = "required endpoint"
        rs = rules.RuleSet()
        rs.keyword.update({"alipay", "safe.example", "checkout", "-advert"})
        rules.filter_ads_keywords(rs, {"checkout.example.com"})
        self.assertEqual(rs.keyword, {"-advert"})

    def test_tco_remains_protected_without_upstream_allowlist(self):
        rules.ADS_NEVER_BLOCK_SUFFIX["t.co"] = "X link redirects"
        rs = rules.RuleSet()
        rs.suffix.update({"t.co", "co", "ads.example.com"})
        rs.exact.update({"t.co", "link.t.co"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"ads.example.com"})
        self.assertEqual(rs.exact, set())


class SourceValidationTests(unittest.TestCase):
    def test_rules_and_json_responses_are_accepted(self):
        cases = [
            ("# Source\n.ads.example.com\n", "text/plain"),
            ("DOMAIN-SUFFIX,ads.example.com\n", ""),
            ('{"example.com": ["api.example.com"]}', "application/json"),
        ]
        for text, content_type in cases:
            with self.subTest(content_type=content_type):
                rules.validate_source_text(
                    "https://example.com/list", text, content_type
                )

    def test_empty_html_and_corrupt_utf8_responses_are_rejected(self):
        cases = [
            ("", "text/plain"),
            (" \r\n\t", "text/plain"),
            ("<!DOCTYPE html><html><body>Denied</body></html>", "text/plain"),
            ("<html><body>Login required</body></html>", ""),
            ("ads.example.com\n", "text/html; charset=utf-8"),
            ("ads.exa\ufffdmple.com\n", "text/plain"),
        ]
        for text, content_type in cases:
            with self.subTest(text=text, content_type=content_type):
                with self.assertRaises((ValueError, RuntimeError)):
                    rules.validate_source_text(
                        "https://example.com/list", text, content_type
                    )


class FetchTests(unittest.TestCase):
    @staticmethod
    def response(body, content_type="text/plain"):
        response = MagicMock()
        response.__enter__.return_value = response
        response.headers = {"Content-Type": content_type}
        response.read.return_value = body
        return response

    def test_utf8_bom_is_removed_before_parsing(self):
        response = self.response(b"\xef\xbb\xbf.ads.example.com\n")
        with patch.object(rules.urllib.request, "urlopen", return_value=response):
            self.assertEqual(
                rules.fetch("https://example.com/list"), ".ads.example.com\n"
            )

    def test_html_response_fails_immediately_without_retry(self):
        response = self.response(b"<html><body>Login</body></html>")
        with patch.object(
            rules.urllib.request, "urlopen", return_value=response
        ) as request:
            with patch.object(rules.time, "sleep") as sleep:
                with self.assertRaises(RuntimeError):
                    rules.fetch("https://example.com/list", tries=3)
        request.assert_called_once()
        sleep.assert_not_called()

    def test_invalid_utf8_does_not_become_a_partial_rule_list(self):
        response = self.response(b".ads.example.com\n.bad\xff.example.com\n")
        with patch.object(
            rules.urllib.request, "urlopen", return_value=response
        ) as request:
            with patch.object(rules.time, "sleep") as sleep:
                with self.assertRaises(RuntimeError):
                    rules.fetch("https://example.com/list", tries=3)
        request.assert_called_once()
        sleep.assert_not_called()


class MrsPublicationTests(unittest.TestCase):
    def test_failed_compiler_cannot_overwrite_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            dst = Path(directory) / "Advertising.mrs"
            dst.write_bytes(b"previous-working-artifact")

            def failed_compile(command, **kwargs):
                Path(command[-1]).write_bytes(b"partial-output")
                return subprocess.CompletedProcess(
                    command, 1, stdout="", stderr="conversion failed"
                )

            with patch.object(rules.subprocess, "run", side_effect=failed_compile):
                with self.assertRaises(RuntimeError):
                    rules.convert_mrs("mihomo", "Advertising", "+.ads.example.com\n", dst)
            self.assertEqual(dst.read_bytes(), b"previous-working-artifact")

    def test_success_status_without_valid_output_preserves_artifact(self):
        for output in [None, b""]:
            with self.subTest(output=output):
                with tempfile.TemporaryDirectory() as directory:
                    dst = Path(directory) / "Advertising.mrs"
                    dst.write_bytes(b"previous-working-artifact")

                    def compile_without_output(command, **kwargs):
                        if output is not None:
                            Path(command[-1]).write_bytes(output)
                        return subprocess.CompletedProcess(
                            command, 0, stdout="", stderr=""
                        )

                    with patch.object(
                        rules.subprocess, "run", side_effect=compile_without_output
                    ):
                        with self.assertRaises(RuntimeError):
                            rules.convert_mrs(
                                "mihomo", "Advertising", "+.ads.example.com\n", dst
                            )
                    self.assertEqual(dst.read_bytes(), b"previous-working-artifact")

    def test_valid_compilation_replaces_artifact_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            dst = Path(directory) / "Advertising.mrs"
            dst.write_bytes(b"previous-working-artifact")

            def successful_compile(command, **kwargs):
                self.assertEqual(dst.read_bytes(), b"previous-working-artifact")
                Path(command[-1]).write_bytes(b"new-working-artifact")
                self.assertEqual(dst.read_bytes(), b"previous-working-artifact")
                return subprocess.CompletedProcess(
                    command, 0, stdout="", stderr=""
                )

            with patch.object(rules.subprocess, "run", side_effect=successful_compile):
                rules.convert_mrs("mihomo", "Advertising", "+.ads.example.com\n", dst)
            self.assertEqual(dst.read_bytes(), b"new-working-artifact")


class AdShardTests(unittest.TestCase):
    """分片架构：SKK 骨架 + Cats/AWA 增量补充分片。"""

    def test_shard_keys_and_strategies_match_skk(self):
        self.assertEqual(
            [s.key for s in rules.SKK_ADS_SHARDS],
            ["domainset_reject", "domainset_extra", "non_ip_drop",
             "non_ip_nodrop", "non_ip", "ip"],
        )
        # Surge 侧保留 REJECT-DROP / REJECT-NO-DROP 语义
        strategies = {s.key: s.drop for s in rules.SKK_ADS_SHARDS}
        self.assertEqual(strategies["non_ip_drop"], "REJECT-DROP")
        self.assertEqual(strategies["non_ip_nodrop"], "REJECT-NO-DROP")
        # Mihomo 没有这两种策略，统一降级为 REJECT（与 SKK 自身一致）
        mihomo = {s.key: s.mihomo for s in rules.SKK_ADS_SHARDS}
        self.assertEqual(mihomo["non_ip_drop"], "REJECT-DROP")
        self.assertEqual(mihomo["non_ip_nodrop"], "REJECT")
        self.assertEqual(mihomo["ip"], "REJECT")

    def test_skk_shard_parser_handles_both_syntaxes(self):
        rs = rules.RuleSet()
        text = (
            "# $ meta_title demo\n"
            ".ads.example.com\n"
            "exact.example.net\n"
            "DOMAIN-KEYWORD,tracker\n"
            "DOMAIN-WILDCIXX,broken\n"
            "DOMAIN-SUFFIX,cdn.example.org,no-resolve\n"
            "IP-CIDR,1.2.3.0/24,no-resolve\n"
        )
        n = rules.parse_skk_shard(text, rs)
        self.assertIn("ads.example.com", rs.suffix)
        self.assertIn("exact.example.net", rs.exact)
        self.assertIn("cdn.example.org", rs.suffix)
        self.assertIn("tracker", rs.keyword)
        self.assertIn(("IP-CIDR", "1.2.3.0/24"), rs.ips)
        self.assertEqual(n, 5)

    def test_cats_and_awa_only_fill_gaps_left_by_skk(self):
        """SKK 已覆盖的条目不得被重复计入补充分片。"""
        skk = rules.RuleSet()
        skk.suffix.update({"shared.example.com", "skk.example.com"})
        covered = skk.suffix | skk.exact
        incoming = rules.RuleSet()
        incoming.suffix.update({"shared.example.com", "cats.example.com"})
        increment = {s for s in incoming.suffix if s not in covered}
        self.assertEqual(increment, {"cats.example.com"})

    def test_drop_shard_keeps_telemetry_endpoints(self):
        """drop 层只放行 SKK 点名的子域，不动受保护的主域。

        保护表的本意是「整域拦截会伤用户」；但 drop 层语义相反：静默丢包
        （非 RST）不会让客户端立刻报错，且 SKK 逐条挑选过。
        """
        # 受保护主域：整域拦截会伤推送，build_ads 因此让 drop 层豁免保护表。
        self.assertIn("jpush.cn", rules.ADS_NEVER_BLOCK_SUFFIX)
        self.assertIn("getui.com", rules.ADS_NEVER_BLOCK_SUFFIX)
        # SKK 实际收录的是这些子域，它们不在保护表里，必须原样保留。
        self.assertNotIn("jpush.io", rules.ADS_NEVER_BLOCK_SUFFIX)
        self.assertNotIn("getui.net", rules.ADS_NEVER_BLOCK_SUFFIX)
        rs = rules.RuleSet()
        rs.suffix.update({"jpush.io", "getui.net", "ads.example.com"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"jpush.io", "getui.net", "ads.example.com"})

    def test_protected_root_is_removed_even_in_a_shaped_set(self):
        """保护表在普通分片里照常生效（drop 层豁免不等于全局失效）。"""
        rules.ADS_NEVER_BLOCK_SUFFIX["jpush.cn"] = "audit 极光推送"
        rs = rules.RuleSet()
        rs.suffix.update({"jpush.cn", "jpush.io"})
        rules.filter_ads_domains(rs, set())
        self.assertEqual(rs.suffix, {"jpush.io"})


class BuildGuardTests(unittest.TestCase):
    def test_repeated_domainset_rows_cannot_satisfy_minimum_size(self):
        """重复的**有效**行也不能满足 SKK 分片的健康下限。

        旧版测的是 Cats 源；现在 Cats 只做增量、骨架来自 SKK 分片，所以这条
        断言的防线要落在真正把关条目数的那一层。

        注意旧版用例写的是 `DOMAIN-SUFFIX,.example.org` —— 前导点让它成为
        **非法**规则，失败原因和"重复行凑数"无关。这里改用前导点的裸域名
        形式（domainset 语法），保证每行都合法。
        """
        cats_surge = "DOMAIN-SUFFIX,.example.org\n" * 20000
        # 6 个分片 × 100 行 = 600 < 100000 下限。全部是同一个域名，
        # 唯一值只有 1 条，靠重复行永远不可能满足下限。
        skk_stub = ".dup.example.org\n" * 100
        with patch.object(rules, "fetch", side_effect=lambda url: (
            skk_stub if url.startswith(rules.SRC_SUKKA_SURGE) else cats_surge)):
            with self.assertRaisesRegex(RuntimeError, "skk domainset_reject"):
                rules.build_ads()

    def test_comment_only_awa_source_cannot_pass_health_check(self):
        cats_surge = "".join(f"DOMAIN-SUFFIX,ad{i}.example.org\n" for i in range(10000))
        skk_stub = "".join(f".skk{i}.example.org\n" for i in range(150000))

        def pick(url):
            if url == rules.SRC_AWA_SURGE:
                return "  # comment\n" * 1000
            if url.startswith(rules.SRC_SUKKA_SURGE):
                return skk_stub
            return cats_surge

        with patch.object(rules, "fetch", side_effect=pick):
            with self.assertRaisesRegex(RuntimeError, "awavenue parsed rules"):
                rules.build_ads()

    def test_unchanged_crlf_artifact_preserves_original_timestamp_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Advertising.list"
            original = b"# stamp: 2026-01-01\r\n.ads.example.com\r\n"
            target.write_bytes(original)
            rendered = "# stamp: NEW_STAMP\n.ads.example.com\n"
            with patch.object(rules, "BUILD_TIME", "NEW_STAMP"):
                with patch.object(rules, "_existing_time", return_value="2026-01-01"):
                    self.assertFalse(rules.write_with_stamp(target, rendered, "2026-01-02"))
            self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
