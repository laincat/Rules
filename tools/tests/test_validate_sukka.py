"""Offline tests, plus real-core integration tests when MIHOMO is supplied."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_sukka as validator


class ValidationTests(unittest.TestCase):
    def test_yaml_count_must_be_exact(self):
        want = {"test": validator.ProviderExpectation("classical", "yaml", 2)}
        got = {"test": {"behavior": "Classical", "format": "YamlRule", "ruleCount": 1}}
        self.assertIn("rows skipped", validator.check_provider_counts(got, want)[0])
        got["test"]["ruleCount"] = 2
        self.assertEqual(validator.check_provider_counts(got, want), [])

    def test_mrs_count_can_exceed_optimized_trie_size(self):
        want = {"test": validator.ProviderExpectation("ipcidr", "mrs", 2)}
        got = {"test": {"behavior": "IPCIDR", "format": "MrsRule", "ruleCount": 3}}
        self.assertEqual(validator.check_provider_counts(got, want), [])
        got["test"]["ruleCount"] = 1
        self.assertIn("decoded MRS contains 2", validator.check_provider_counts(got, want)[0])

    def test_missing_and_wrong_behavior_are_rejected(self):
        want = {"test": validator.ProviderExpectation("domain", "yaml", 1)}
        self.assertIn("provider missing", validator.check_provider_counts({}, want)[0])
        got = {"test": {"behavior": "Classical", "format": "Yaml", "ruleCount": 1}}
        self.assertIn("behavior", validator.check_provider_counts(got, want)[0])

    def test_core_configuration_has_no_traffic_listeners(self):
        config = validator.isolated_config({}, ["MATCH,DIRECT"], 12345, "test-secret")
        self.assertEqual(config["external-controller"], "127.0.0.1:12345")
        self.assertEqual(config["secret"], "test-secret")
        for key in ("port", "socks-port", "mixed-port", "redir-port", "tproxy-port"):
            self.assertEqual(config[key], 0)
        self.assertFalse(config["dns"]["enable"])
        self.assertFalse(config["tun"]["enable"])
        self.assertFalse(config["allow-lan"])
        self.assertFalse(config["geo-auto-update"])
        self.assertEqual(config["listeners"], [])
        self.assertNotIn("proxy-providers", config)
        self.assertTrue(all(url.startswith("http://127.0.0.1:") for url in config["geox-url"].values()))

    @staticmethod
    def make_example(root, payload=None, path="./sukka/non_ip/cdn.yaml"):
        provider = {"type": "http", "url": "https://must-not-be-contacted.invalid/test",
                    "behavior": "classical", "format": "yaml", "path": path}
        example = {"rule-providers": {"test": provider},
                   "rules": ["RULE-SET,test,DIRECT", "MATCH,DIRECT"]}
        example_path = root / "example.yaml"
        example_path.write_text(yaml.safe_dump(example), encoding="utf-8")
        if payload is not None:
            (root / "non_ip").mkdir(exist_ok=True)
            (root / "non_ip/cdn.yaml").write_text(yaml.safe_dump({"payload": payload}), encoding="utf-8")
        return example_path

    def test_missing_path_fails_before_starting_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = self.make_example(root)
            with self.assertRaisesRegex(validator.ValidationError, "missing or unsafe provider"):
                validator.prepare_providers(example, root, Path("unused"), time.monotonic() + 5)

    def test_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = self.make_example(root, path="./sukka/../outside.yaml")
            with self.assertRaisesRegex(validator.ValidationError, "unsafe or inconsistent"):
                validator.prepare_providers(example, root, Path("unused"), time.monotonic() + 5)

    def test_duplicate_yaml_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text("payload: []\npayload: []\n", encoding="utf-8")
            with self.assertRaisesRegex(validator.ValidationError, "duplicate YAML key"):
                validator.read_yaml(path)

    def test_file_copy_preserves_payload_and_strips_remote_settings(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as dest:
            root = Path(tmp)
            example = self.make_example(root, ["DOMAIN,example.com"])
            local, expected, _ = validator.prepare_providers(
                example, Path(dest), Path("unused"), time.monotonic() + 5)
            self.assertEqual(local["test"]["type"], "file")
            self.assertNotIn("url", local["test"])
            self.assertEqual(expected["test"].count, 1)
            self.assertEqual((Path(dest) / "provider-0.yaml").read_bytes(),
                             (root / "non_ip/cdn.yaml").read_bytes())

    def test_example_rule_order_is_checked_independently_of_providers(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as dest:
            root = Path(tmp)
            providers = {
                "domain": {
                    "behavior": "domain",
                    "format": "yaml",
                    "path": "./sukka/domainset/cdn.yaml",
                },
                "non-ip": {
                    "behavior": "classical",
                    "format": "yaml",
                    "path": "./sukka/non_ip/cdn.yaml",
                },
                "ip": {
                    "behavior": "ipcidr",
                    "format": "yaml",
                    "path": "./sukka/ip/lan.yaml",
                },
            }
            for relative in (
                "domainset/cdn.yaml",
                "non_ip/cdn.yaml",
                "ip/lan.yaml",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    yaml.safe_dump({"payload": ["DOMAIN,example.com"]}),
                    encoding="utf-8",
                )
            example = {
                "rule-providers": providers,
                "rules": [
                    "RULE-SET,ip,DIRECT",
                    "RULE-SET,domain,DIRECT",
                    "RULE-SET,non-ip,DIRECT",
                    "MATCH,DIRECT",
                ],
            }
            example_path = root / "example.yaml"
            example_path.write_text(
                yaml.safe_dump(example),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                validator.ValidationError,
                "do not follow SUKKA_RULE_ORDER",
            ):
                validator.prepare_providers(
                    example_path,
                    Path(dest),
                    Path("unused"),
                    time.monotonic() + 5,
                )

    def test_unreferenced_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as dest:
            root = Path(tmp)
            example = self.make_example(root, ["DOMAIN,example.com"])
            (root / "non_ip/stale.yaml").write_text("payload: [DOMAIN,stale.example]\n")
            with self.assertRaisesRegex(validator.ValidationError, "does not reference all artifacts"):
                validator.prepare_providers(example, Path(dest), Path("unused"), time.monotonic() + 5)

    def test_asn_download_is_only_needed_for_asn_rules_including_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = {"test": {"behavior": "classical", "format": "yaml", "path": "./test.yaml"}}
            for row, needed in [("DOMAIN,example.com", False), ("IP-ASN,64500", True),
                                ("AND,((NETWORK,TCP),(IP-ASN,64500))", True)]:
                with self.subTest(row=row), patch.object(validator, "fetch_asn") as fetch:
                    (root / "test.yaml").write_text(yaml.safe_dump({"payload": [row]}))
                    validator.prepare_asn(provider, root, None, time.monotonic() + 5)
                    self.assertEqual(fetch.called, needed)

    def test_asn_cache_avoids_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "test.yaml").write_text(yaml.safe_dump({"payload": ["IP-ASN,64500"]}))
            cache = root / "cache.mmdb"
            cache.write_bytes(b"existing database")
            provider = {"test": {"behavior": "classical", "format": "yaml", "path": "./test.yaml"}}
            with patch.object(validator, "fetch_asn") as fetch:
                validator.prepare_asn(provider, root, cache, time.monotonic() + 5)
                fetch.assert_not_called()
            self.assertEqual((root / "ASN.mmdb").read_bytes(), cache.read_bytes())

    def test_asn_download_failure_is_actionable_and_leaves_no_file(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(validator.urllib.request, "build_opener") as build:
            build.return_value.open.side_effect = urllib.error.URLError("unreachable")
            destination = Path(tmp) / "ASN.mmdb"
            with self.assertRaisesRegex(validator.ValidationError, "official ASN database download failed"):
                validator.fetch_asn(destination, time.monotonic() + 5)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".part").exists())

    def test_asn_redirect_cannot_downgrade_https(self):
        with self.assertRaisesRegex(validator.ValidationError, "outside HTTPS"):
            validator.HTTPSOnlyRedirect().redirect_request(None, None, 302, "", {}, "http://example.com/asn")

    def test_asn_download_checks_status_empty_body_size_and_timeout(self):
        for status, chunks, error in [(503, [], "HTTP 503"), (200, [b""], "is empty"),
                                      (200, [b"too large"], "size limit")]:
            with self.subTest(status=status, chunks=chunks), tempfile.TemporaryDirectory() as tmp, \
                    patch.object(validator.urllib.request, "build_opener") as build, \
                    patch.object(validator, "ASN_SIZE_LIMIT", 4):
                response = build.return_value.open.return_value.__enter__.return_value
                response.status = status
                response.geturl.return_value = validator.ASN_URL
                response.headers = {}
                response.read1.side_effect = chunks
                destination = Path(tmp) / "ASN.mmdb"
                with self.assertRaisesRegex(validator.ValidationError, error):
                    validator.fetch_asn(destination, time.monotonic() + 5)
                timeout = build.return_value.open.call_args.kwargs["timeout"]
                self.assertGreater(timeout, 0)
                self.assertLessEqual(timeout, 5)
                self.assertFalse(destination.exists())
                self.assertFalse(destination.with_suffix(".part").exists())

    def test_expired_asn_download_deadline_prevents_network_request(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(validator.urllib.request, "build_opener") as build:
            with self.assertRaisesRegex(validator.ValidationError, "timed out"):
                validator.fetch_asn(Path(tmp) / "ASN.mmdb", time.monotonic() - 1)
            build.return_value.open.assert_not_called()


@unittest.skipUnless(os.environ.get("MIHOMO"), "set MIHOMO to run isolated core integration tests")
class CoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.core = Path(os.environ["MIHOMO"]).resolve()
        self.asn = Path(os.environ["MIHOMO_ASN"]).resolve() if os.environ.get("MIHOMO_ASN") else None

    def test_real_core_accepts_classical_and_asn(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = ValidationTests.make_example(Path(tmp), ["DOMAIN,example.com", "IP-ASN,64500"])
            result = validator.validate(example, self.core, timeout=30, asn_mmdb=self.asn)
            self.assertEqual(result["loaded_rules"], 2)

    def test_real_core_rejects_silently_skipped_classical_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = ValidationTests.make_example(Path(tmp), ["DOMAIN,example.com", "INVALID-RULE,broken"])
            with self.assertRaisesRegex(validator.ValidationError, "loaded 1, YAML contains 2"):
                validator.validate(example, self.core, timeout=1)

    def test_real_core_rejects_corrupt_mrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "domainset").mkdir()
            (root / "domainset/cdn.mrs").write_bytes(b"not an MRS")
            example = {"rule-providers": {"test": {"behavior": "domain", "format": "mrs",
                                                   "path": "./sukka/domainset/cdn.mrs"}},
                       "rules": ["RULE-SET,test,DIRECT", "MATCH,DIRECT"]}
            path = root / "example.yaml"
            path.write_text(yaml.safe_dump(example), encoding="utf-8")
            with self.assertRaisesRegex(validator.ValidationError, "MRS decoding failed"):
                validator.validate(path, self.core, timeout=5)

    def test_real_core_accepts_mrs_with_overlapping_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ip").mkdir()
            source = root / "source.txt"
            source.write_text("192.0.2.0/25\n192.0.2.128/25\n", encoding="utf-8")
            subprocess.run([str(self.core), "convert-ruleset", "ipcidr", "text",
                            str(source), str(root / "ip/cdn.mrs")], check=True, capture_output=True, timeout=5)
            example = {"rule-providers": {"test": {"behavior": "ipcidr", "format": "mrs",
                                                   "path": "./sukka/ip/cdn.mrs"}},
                       "rules": ["RULE-SET,test,DIRECT,no-resolve", "MATCH,DIRECT"]}
            path = root / "example.yaml"
            path.write_text(json.dumps(example), encoding="utf-8")
            self.assertEqual(validator.validate(path, self.core, timeout=5)["loaded_rules"], 2)


if __name__ == "__main__":
    unittest.main()
