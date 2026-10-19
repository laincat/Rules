"""Offline tests for the Sukka -> Mihomo generation chain."""

from pathlib import Path
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_rulesets as rules  # noqa: E402


class SukkaGenerationTests(unittest.TestCase):
    @staticmethod
    def parsed(directory, suffix=(), exact=(), classical=(), ip_cidrs=(),
               resolved_ip_cidrs=()):
        parsed = rules.SukkaRules()
        parsed.suffix.update(suffix)
        parsed.exact.update(exact)
        parsed.classical.update(classical)
        parsed.ip_cidrs.update({value: True for value in ip_cidrs})
        parsed.ip_cidrs.update({value: False for value in resolved_ip_cidrs})
        return parsed

    def grouped(self, overrides):
        return {
            spec.file_base: overrides.get(
                spec.file_base,
                self.parsed(spec.directory),
            )
            for spec in rules.SUKKA_LISTS
        }

    def test_parser_filters_marker_and_classifies_supported_rules(self):
        parsed = rules.parse_sukka_list(
            "\n".join([
                "# metadata",
                f"DOMAIN,{next(iter(rules.SUKKA_MARKER_DOMAINS))}",
                "DOMAIN-SUFFIX,Example.COM",
                "DOMAIN-SUFFIX,sptkh1_tc.taiwanmobile.com",
                "DOMAIN,unifi",
                "DOMAIN-KEYWORD,video",
                "DOMAIN-WILDCARD,*.media.example.com",
                "PROCESS-NAME,com.example.video",
                "USER-AGENT,ExampleOS/*",
                r"URL-REGEX,^http://example\.com/video",
                "IP-CIDR,192.0.2.0/24,no-resolve",
                "IP-CIDR,198.51.100.0/24",
                "IP-ASN,64500",
            ]),
            "non_ip",
        )
        self.assertEqual(
            parsed.suffix,
            {"example.com", "sptkh1_tc.taiwanmobile.com"},
        )
        self.assertEqual(parsed.exact, set())
        self.assertIn("DOMAIN,unifi", parsed.classical)
        self.assertIn("DOMAIN-KEYWORD,video", parsed.classical)
        self.assertIn("PROCESS-NAME,com.example.video", parsed.classical)
        self.assertEqual(parsed.ip_cidrs, {
            "192.0.2.0/24": True,
            "198.51.100.0/24": False,
        })
        self.assertNotIn(
            "IP-CIDR,192.0.2.0/24,no-resolve",
            parsed.classical,
        )
        self.assertEqual(
            parsed.ignored,
            {"URL-REGEX": 1, "USER-AGENT": 1},
        )
        self.assertTrue(parsed.exact.isdisjoint(rules.SUKKA_MARKER_DOMAINS))

    def test_clash_domainset_does_not_broaden_subdomain_only_patterns(self):
        parsed = rules.parse_sukka_list(
            "exact.example\n+.suffix.example\n", "domainset",
        )
        self.assertEqual(parsed.exact, {"exact.example"})
        self.assertEqual(parsed.suffix, {"suffix.example"})
        with self.assertRaisesRegex(RuntimeError, "subdomain-only"):
            rules.parse_sukka_list(".suffix.example\n", "domainset")

    def test_bare_cidr_does_not_invent_no_resolve(self):
        parsed = rules.parse_sukka_list("192.0.2.0/24\n", "ip")
        self.assertEqual(parsed.ip_cidrs, {"192.0.2.0/24": False})

    def test_threshold_and_behavior_plan(self):
        grouped = self.grouped({
            "domainset/speedtest": self.parsed(
                "domainset",
                suffix={f"speed{i}.example" for i in range(101)},
            ),
            "domainset/game-download": self.parsed(
                "domainset", exact={f"g{i}.example" for i in range(100)},
            ),
            "non_ip/stream": self.parsed(
                "non_ip",
                suffix={f"stream{i}.example" for i in range(100)},
                classical={"PROCESS-NAME,stream-app"},
            ),
            "non_ip/global": self.parsed(
                "non_ip",
                suffix={f"global{i}.example" for i in range(101)},
                ip_cidrs={"203.0.113.0/24"},
            ),
            "ip/china_ip": self.parsed(
                "ip",
                ip_cidrs={
                    f"192.0.{i // 256}.{i % 256}/32"
                    for i in range(101)
                },
            ),
            "ip/stream": self.parsed(
                "ip",
                ip_cidrs={f"198.51.{i // 256}.{i % 256}/32" for i in range(101)},
                classical={"IP-ASN,64500"},
            ),
            "ip/telegram": self.parsed(
                "ip",
                ip_cidrs={"203.0.113.0/24", "2001:db8::/32"},
            ),
            "ip/cdn": self.parsed(
                "ip",
                resolved_ip_cidrs={"198.51.100.0/24"},
            ),
            "ip/teleproto": self.parsed(
                "ip",
                ip_cidrs={"203.0.113.0/24"},
                resolved_ip_cidrs={"198.51.100.0/24"},
            ),
        })
        artifacts = rules.plan_sukka_artifacts(grouped)
        by_repo_path = {
            artifact.repo_path: artifact for artifact in artifacts
        }

        self.assertNotIn(
            "Mihomo/Sukka/domainset/speedtest.yaml",
            by_repo_path,
        )
        speed = by_repo_path["Mihomo/Sukka/domainset/speedtest.mrs"]
        self.assertEqual(
            (speed.behavior, speed.file_format),
            ("domain", "mrs"),
        )

        game = by_repo_path["Mihomo/Sukka/domainset/game-download.yaml"]
        self.assertEqual(
            (game.behavior, game.file_format),
            ("domain", "yaml"),
        )

        stream_main = by_repo_path["Mihomo/Sukka/non_ip/stream.mrs"]
        stream_extra = by_repo_path[
            "Mihomo/Sukka/non_ip/stream.Extra.yaml"
        ]
        self.assertEqual(stream_main.behavior, "domain")
        self.assertEqual(stream_extra.behavior, "classical")

        global_extra = by_repo_path[
            "Mihomo/Sukka/non_ip/global.Extra.yaml"
        ]
        global_payload = yaml.safe_load(rules.render_sukka_artifact(
            global_extra, grouped["non_ip/global"], ["test"]
        ))["payload"]
        self.assertEqual(
            global_payload,
            ["IP-CIDR,203.0.113.0/24,no-resolve"],
        )

        china = by_repo_path["Mihomo/Sukka/ip/china_ip.mrs"]
        self.assertEqual(
            (china.behavior, china.file_format),
            ("ipcidr", "mrs"),
        )
        self.assertNotIn(
            "Mihomo/Sukka/ip/china_ip.yaml",
            by_repo_path,
        )

        stream_ip = by_repo_path["Mihomo/Sukka/ip/stream.mrs"]
        stream_ip_extra = by_repo_path[
            "Mihomo/Sukka/ip/stream.Extra.yaml"
        ]
        self.assertEqual(
            (stream_ip.behavior, stream_ip.file_format),
            ("ipcidr", "mrs"),
        )
        self.assertEqual(
            (stream_ip_extra.behavior, stream_ip_extra.file_format),
            ("classical", "yaml"),
        )
        extra = yaml.safe_load(rules.render_sukka_artifact(
            stream_ip_extra, grouped["ip/stream"], ["test"]
        ))
        self.assertEqual(extra["payload"], ["IP-ASN,64500"])

        telegram = by_repo_path["Mihomo/Sukka/ip/telegram.yaml"]
        self.assertEqual(
            (telegram.behavior, telegram.file_format),
            ("ipcidr", "yaml"),
        )
        self.assertTrue(telegram.no_resolve)

        cdn = by_repo_path["Mihomo/Sukka/ip/cdn.yaml"]
        self.assertEqual(
            (cdn.behavior, cdn.file_format, cdn.no_resolve),
            ("ipcidr", "yaml", False),
        )

        mixed = by_repo_path["Mihomo/Sukka/ip/teleproto.yaml"]
        self.assertEqual(
            (mixed.behavior, mixed.file_format, mixed.no_resolve),
            ("classical", "yaml", False),
        )
        mixed_payload = yaml.safe_load(rules.render_sukka_artifact(
            mixed, grouped["ip/teleproto"], ["test"]
        ))["payload"]
        self.assertEqual(mixed_payload, [
            "IP-CIDR,198.51.100.0/24",
            "IP-CIDR,203.0.113.0/24,no-resolve",
        ])

    def test_split_keeps_classical_fallback_domains(self):
        # These nine live Sukka direct.txt rules are intentionally stored in
        # classical rather than the normalized public-domain trie buckets.
        local_rules = {
            "DOMAIN,unifi",
            *{"DOMAIN-SUFFIX," + value for value in (
                "lan", "m2m", "home", "bogon", "local", "router",
                "internal", "localdomain",
            )},
        }
        source = "\n".join([
            *sorted(local_rules),
            *(f"DOMAIN-SUFFIX,site{i}.example" for i in range(101)),
            "DOMAIN-KEYWORD,example",
            "PROCESS-NAME,LocalSend",
        ])
        parsed = rules.parse_sukka_list(source, "non_ip")
        self.assertTrue(local_rules.issubset(parsed.classical))
        artifacts = rules.plan_sukka_artifacts(self.grouped({
            "non_ip/direct": parsed,
        }))
        main, extra = artifacts
        self.assertEqual(main.behavior, "domain")
        self.assertTrue(extra.is_extra)
        extra_payload = yaml.safe_load(rules.render_sukka_artifact(
            extra, parsed, ["test"],
        ))["payload"]
        self.assertTrue(local_rules.issubset(extra_payload))
        self.assertEqual(set(extra_payload), parsed.classical)
        # The split must preserve exactly the original supported rule set.
        trie_rules = {
            "DOMAIN-SUFFIX," + line[2:] if line.startswith("+.")
            else "DOMAIN," + line
            for line in rules.render_sukka_mrs_src(parsed, "domain").splitlines()
        }
        self.assertEqual(trie_rules | set(extra_payload), set(parsed.yaml_lines()))
        self.assertTrue(trie_rules.isdisjoint(extra_payload))

    def test_split_keeps_single_label_global_suffixes(self):
        # Public-suffix protection in the general normalizer must not erase
        # Sukka's intentional global routing rules for entire TLDs.
        tld_rules = {"DOMAIN-SUFFIX," + tld for tld in ("ai", "hk", "uk", "us")}
        parsed = rules.parse_sukka_list("\n".join([
            *sorted(tld_rules),
            *(f"DOMAIN,global{i}.example" for i in range(101)),
        ]), "non_ip")
        artifacts = rules.plan_sukka_artifacts(self.grouped({
            "non_ip/global": parsed,
        }))
        extra = next(artifact for artifact in artifacts if artifact.is_extra)
        payload = yaml.safe_load(rules.render_sukka_artifact(
            extra, parsed, ["test"],
        ))["payload"] or []
        self.assertEqual(set(payload), tld_rules)

    def test_fallback_domains_survive_threshold_crossing(self):
        fallback = {"DOMAIN,unifi", "DOMAIN-SUFFIX,local", "DOMAIN-SUFFIX,jp"}
        for count in (100, 101):
            with self.subTest(count=count):
                parsed = rules.parse_sukka_list("\n".join([
                    *sorted(fallback),
                    *(f"DOMAIN,host{i}.example" for i in range(count - 3)),
                ]), "non_ip")
                artifacts = rules.plan_sukka_artifacts(self.grouped({
                    "non_ip/direct": parsed,
                }))
                self.assertEqual(len(artifacts), 1 if count == 100 else 2)
                restored = set()
                for artifact in artifacts:
                    if artifact.file_format == "mrs":
                        restored.update("DOMAIN," + value for value in parsed.exact)
                    else:
                        restored.update(yaml.safe_load(rules.render_sukka_artifact(
                            artifact, parsed, ["test"],
                        ))["payload"] or [])
                self.assertEqual(restored, set(parsed.yaml_lines()))

    def test_example_is_single_line_and_keeps_directory_order(self):
        artifacts = [
            rules.SukkaArtifact(
                spec=rules.SukkaList(
                    "domainset", "cdn", "domainset/cdn.conf", 1, "cdn"
                ),
                relative="domainset/cdn.mrs",
                behavior="domain",
                file_format="mrs",
                provider_id="sukka-domainset-cdn",
            ),
            rules.SukkaArtifact(
                spec=rules.SukkaList(
                    "non_ip", "cdn", "non_ip/cdn.conf", 1, "cdn"
                ),
                relative="non_ip/cdn.yaml",
                behavior="classical",
                file_format="yaml",
                provider_id="sukka-non-ip-cdn",
            ),
            rules.SukkaArtifact(
                spec=rules.SukkaList(
                    "ip", "lan", "ip/lan.conf", 1, "lan"
                ),
                relative="ip/lan.yaml",
                behavior="ipcidr",
                file_format="yaml",
                provider_id="sukka-ip-lan",
                no_resolve=True,
            ),
        ]
        text = rules.render_sukka_example(artifacts, ["skk-clash"])
        provider_lines = [
            line for line in text.splitlines()
            if line.startswith("  sukka-")
        ]
        self.assertEqual(len(provider_lines), 3)
        self.assertTrue(
            all(line.rstrip().endswith("}") for line in provider_lines)
        )
        rule_lines = [
            line for line in text.splitlines()
            if line.startswith("  - RULE-SET,")
        ]
        self.assertEqual(
            [line.split(",")[1] for line in rule_lines],
            [
                "sukka-domainset-cdn",
                "sukka-non-ip-cdn",
                "sukka-ip-lan",
            ],
        )
        self.assertEqual(
            [",".join(line.split(",")[2:]) for line in rule_lines],
            ["DIRECT", "DIRECT", "DIRECT,no-resolve"],
        )

    def test_source_and_scope(self):
        stream = next(
            spec for spec in rules.SUKKA_LISTS
            if spec.file_base == "non_ip/stream"
        )
        self.assertEqual(
            stream.url,
            "https://ruleset.skk.moe/Clash/non_ip/stream.txt",
        )
        bases = {spec.file_base for spec in rules.SUKKA_LISTS}
        self.assertIn("non_ip/apple_cn", bases)
        self.assertIn("non_ip/apple_services", bases)
        self.assertIn("non_ip/cloudmounter", bases)
        self.assertIn("non_ip/telegram", bases)
        self.assertIn("ip/stream_biliintl", bases)
        self.assertNotIn("non_ip/ai", bases)
        self.assertNotIn("non_ip/apple_intelligence", bases)
        self.assertNotIn("ip/ai", bases)
        self.assertNotIn("domainset/clash_fake_ip_filter", bases)
        self.assertNotIn("non_ip/apple_cdn", bases)
        self.assertNotIn("non_ip/global_plus", bases)
        self.assertFalse(any(name.startswith("non_ip/my_") for name in bases))
        self.assertFalse(any(
            name.startswith(
                ("domainset/reject", "non_ip/reject", "ip/reject")
            )
            for name in bases
        ))

    def test_source_order_matches_sukka_generation_order(self):
        expected = [
            "domainset/speedtest",
            "domainset/cdn",
            "domainset/apple_cdn",
            "domainset/download",
            "domainset/game-download",
            "domainset/icloud_private_relay",
            "non_ip/sogouinput",
            "non_ip/cdn",
            "non_ip/stream_us",
            "non_ip/stream_eu",
            "non_ip/stream_jp",
            "non_ip/stream_kr",
            "non_ip/stream_hk",
            "non_ip/stream_tw",
            "non_ip/stream_biliintl",
            "non_ip/stream",
            "non_ip/telegram",
            "non_ip/apple_services",
            "non_ip/apple_cn",
            "non_ip/microsoft_cdn",
            "non_ip/microsoft",
            "non_ip/neteasemusic",
            "non_ip/download",
            "non_ip/lan",
            "non_ip/domestic_cdn",
            "non_ip/domestic",
            "non_ip/direct",
            "non_ip/cloudmounter",
            "non_ip/global",
            "non_ip/gitlab",
            "ip/stream_us",
            "ip/stream_eu",
            "ip/stream_jp",
            "ip/stream_kr",
            "ip/stream_hk",
            "ip/stream_tw",
            "ip/stream_biliintl",
            "ip/stream",
            "ip/telegram",
            "ip/telegram_asn",
            "ip/teleproto",
            "ip/apple_services",
            "ip/neteasemusic",
            "ip/download",
            "ip/lan",
            "ip/domestic",
            "ip/cdn",
            "ip/china_ip",
            "ip/china_ip_ipv6",
        ]
        self.assertEqual(
            [spec.file_base for spec in rules.SUKKA_LISTS],
            expected,
        )

    def test_generated_example_references_real_files(self):
        example = yaml.safe_load(
            (ROOT / "Mihomo/Sukka/example.yaml").read_text(encoding="utf-8")
        )
        providers = example["rule-providers"]
        self.assertTrue(providers)
        self.assertEqual(example["rules"][-1], "MATCH,DIRECT")

        expected_provider_order = []
        for spec in rules.SUKKA_LISTS:
            base_id = (
                "sukka-"
                + spec.file_base.replace("/", "-").replace("_", "-").lower()
            )
            for provider_id in (base_id, base_id + "-extra"):
                if provider_id not in providers:
                    continue
                expected_provider_order.append(provider_id)
        self.assertEqual(list(providers), expected_provider_order)

        directory_order = {"domainset": 0, "non_ip": 1, "ip": 2}
        seen = []
        referenced = set()
        for name, provider in providers.items():
            relative = provider["path"].removeprefix("./sukka/")
            path = ROOT / "Mihomo/Sukka" / relative
            self.assertTrue(path.exists(), (name, path))
            referenced.add(relative)
            self.assertEqual(
                provider["format"],
                "mrs" if path.suffix == ".mrs" else "yaml",
            )
            directory_order_value = directory_order[relative.split("/")[0]]
            seen.append(directory_order_value)
            rule = next(
                item for item in example["rules"]
                if item.startswith("RULE-SET," + name + ",")
            )
            if relative in {
                "ip/china_ip.mrs",
                "ip/china_ip_ipv6.mrs",
                "ip/cdn.yaml",
                "ip/lan.yaml",
            }:
                self.assertFalse(rule.endswith(",no-resolve"), rule)
        self.assertEqual(seen, sorted(seen))
        actual = {
            path.relative_to(ROOT / "Mihomo/Sukka").as_posix()
            for path in (ROOT / "Mihomo/Sukka").rglob("*")
            if path.is_file()
            and path.suffix in {".yaml", ".mrs"}
            and path.name != "example.yaml"
        }
        self.assertEqual(actual, referenced)

    def test_text_only_write_requires_existing_mrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            present = Path(tmp) / "present.mrs"
            present.write_bytes(b"mrs")
            rules.require_existing_mrs([present])
            with self.assertRaisesRegex(RuntimeError, "缺失.*missing"):
                rules.require_existing_mrs([
                    present,
                    Path(tmp) / "missing.mrs",
                ])


if __name__ == "__main__":
    unittest.main()
