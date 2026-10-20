#!/usr/bin/env python3
"""Load every generated Sukka provider in an isolated Mihomo core.

Unlike ``mihomo -t``, checking the running provider API detects classical rows
that the core warns about and silently discards. Only local provider copies are
used; the core has no proxy, DNS, or TUN listeners, no subscriptions, and a
temporary authenticated loopback controller. IP-ASN parsing may download the
official MetaCubeX ASN database unless --asn-mmdb supplies an existing copy.
This is a syntax/load check, not an ASN lookup or real-network routing test.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
from urllib.parse import urlparse
import urllib.request

import yaml

from gen_rulesets import SUKKA_RULE_ORDER


ROOT = Path(__file__).resolve().parents[1]
ASN_URL = "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb"
ASN_SIZE_LIMIT = 64 * 1024 * 1024


class ValidationError(RuntimeError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not let duplicate YAML keys hide a provider from validation."""


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValidationError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def read_yaml(path: Path):
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ValidationError(f"cannot read YAML {path}: {exc}") from exc


@dataclass(frozen=True)
class ProviderExpectation:
    behavior: str
    file_format: str
    count: int


def check_provider_counts(actual: dict, expected: dict[str, ProviderExpectation]) -> list[str]:
    """MRS stores input counts, which can exceed its optimized trie size."""
    problems = []
    for name, want in expected.items():
        got = actual.get(name)
        if not isinstance(got, dict):
            problems.append(f"{name}: provider missing")
            continue
        if str(got.get("behavior", "")).lower() != want.behavior:
            problems.append(f"{name}: behavior {got.get('behavior')!r} != {want.behavior}")
        if str(got.get("format", "")).lower().removesuffix("rule") != want.file_format:
            problems.append(f"{name}: format {got.get('format')!r} != {want.file_format}")
        count = got.get("ruleCount")
        if not isinstance(count, int) or isinstance(count, bool):
            problems.append(f"{name}: invalid ruleCount {count!r}")
        elif want.file_format == "mrs":
            if count < want.count:
                problems.append(f"{name}: loaded {count}, decoded MRS contains {want.count} rules")
        elif count != want.count:
            problems.append(f"{name}: loaded {count}, YAML contains {want.count} rules (rows skipped)")
    return problems


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise ValidationError("Sukka validation timed out")
    return left


def prepare_providers(example_path: Path, directory: Path, mihomo: Path,
                      deadline: float) -> tuple[dict, dict[str, ProviderExpectation], list[str]]:
    example = read_yaml(example_path)
    if not isinstance(example, dict) or not isinstance(example.get("rule-providers"), dict):
        raise ValidationError("example must contain a rule-providers mapping")
    providers = example["rule-providers"]
    if not providers:
        raise ValidationError("example has no providers")
    root = example_path.parent.resolve()
    local, expected, seen_paths = {}, {}, set()
    for index, (name, provider) in enumerate(providers.items()):
        if not isinstance(name, str) or not isinstance(provider, dict):
            raise ValidationError(f"invalid provider: {name!r}")
        behavior = provider.get("behavior")
        file_format = provider.get("format")
        if behavior not in {"domain", "classical", "ipcidr"}:
            raise ValidationError(f"{name}: unsupported behavior {behavior!r}")
        if file_format not in {"yaml", "mrs"} or (file_format == "mrs" and behavior == "classical"):
            raise ValidationError(f"{name}: unsupported format/behavior combination")
        path = provider.get("path")
        if not isinstance(path, str) or not path.startswith("./sukka/"):
            raise ValidationError(f"{name}: expected ./sukka/ provider path")
        relative = Path(path.removeprefix("./sukka/"))
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != "." + file_format:
            raise ValidationError(f"{name}: unsafe or inconsistent provider path {path!r}")
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValidationError(f"{name}: missing or unsafe provider file {relative}")
        if source in seen_paths:
            raise ValidationError(f"{name}: duplicate provider path {relative}")
        seen_paths.add(source)
        copy = directory / f"provider-{index}.{file_format}"
        shutil.copyfile(source, copy)
        if file_format == "yaml":
            document = read_yaml(copy)
            payload = document.get("payload") if isinstance(document, dict) else None
            if not isinstance(payload, list) or not payload or not all(
                    isinstance(row, str) and row.strip() for row in payload):
                raise ValidationError(f"{name}: payload must be a nonempty list of strings")
            count = len(payload)
        else:
            decoded = directory / f"decoded-{index}.txt"
            try:
                result = subprocess.run(
                    [str(mihomo), "convert-ruleset", behavior, "mrs", str(copy), str(decoded)],
                    capture_output=True, text=True, timeout=_remaining(deadline),
                )
            except subprocess.TimeoutExpired as exc:
                raise ValidationError(f"{name}: MRS decoding timed out") from exc
            if result.returncode or not decoded.is_file():
                raise ValidationError(f"{name}: MRS decoding failed: {(result.stderr or result.stdout)[-2000:]}")
            count = sum(bool(row.strip()) for row in decoded.read_text(encoding="utf-8").splitlines())
            if count == 0:
                raise ValidationError(f"{name}: decoded MRS is empty")
        local[name] = {"type": "file", "behavior": behavior, "format": file_format,
                       "path": "./" + copy.name}
        expected[name] = ProviderExpectation(behavior, file_format, count)

    artifacts = {path.resolve() for path in root.rglob("*")
                 if path.is_file() and path.suffix in {".yaml", ".mrs"}
                 and path.resolve() != example_path.resolve()}
    if any(not path.is_relative_to(root) for path in artifacts):
        raise ValidationError("artifact symlink points outside the Sukka directory")
    if artifacts != seen_paths:
        unreferenced = sorted(str(path.relative_to(root)) for path in artifacts - seen_paths)
        raise ValidationError(f"example does not reference all artifacts: {unreferenced}")

    rule_lines = example.get("rules")
    if not isinstance(rule_lines, list) or not all(isinstance(row, str) for row in rule_lines):
        raise ValidationError("example must contain a rules list")
    referenced = []
    for rule in rule_lines:
        parts = rule.split(",")
        if parts == ["MATCH", "DIRECT"]:
            continue
        if (len(parts) not in {3, 4} or parts[0] != "RULE-SET"
                or parts[1] not in expected or parts[2] != "DIRECT"
                or (len(parts) == 4 and parts[3] != "no-resolve")):
            raise ValidationError(f"unexpected example rule: {rule!r}")
        referenced.append(parts[1])
    if len(referenced) != len(set(referenced)) or set(referenced) != set(expected):
        raise ValidationError("example rules must reference every provider exactly once")

    order_index = {source: index for index, source in enumerate(SUKKA_RULE_ORDER)}
    source_by_provider = {}
    for name, provider in providers.items():
        relative = Path(provider["path"].removeprefix("./sukka/")).as_posix()
        source = relative.rsplit(".", 1)[0]
        if source.endswith(".Extra"):
            source = source.removesuffix(".Extra")
        source_by_provider[name] = source
    unknown = sorted({
        source for source in source_by_provider.values()
        if source not in order_index
    })
    if unknown:
        raise ValidationError(
            "example contains sources missing from SUKKA_RULE_ORDER: "
            + ", ".join(unknown)
        )
    expected_order = sorted(
        referenced,
        key=lambda name: (
            order_index[source_by_provider[name]],
            name.endswith("-extra"),
        ),
    )
    if referenced != expected_order:
        raise ValidationError(
            "example rules do not follow SUKKA_RULE_ORDER: expected "
            + ", ".join(expected_order)
        )
    return local, expected, rule_lines


class HTTPSOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValidationError("ASN download redirected outside HTTPS")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_asn(destination: Path, deadline: float) -> None:
    """Download only the official prerequisite, before the DNS-disabled core."""
    opener = urllib.request.build_opener(HTTPSOnlyRedirect())
    temporary = destination.with_suffix(".part")
    try:
        with opener.open(ASN_URL, timeout=_remaining(deadline)) as response:
            if response.status != 200:
                raise ValidationError(f"ASN database download returned HTTP {response.status}")
            if urlparse(response.geturl()).scheme != "https":
                raise ValidationError("ASN download requires HTTPS")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > ASN_SIZE_LIMIT:
                raise ValidationError("ASN database exceeds size limit")
            size = 0
            with temporary.open("wb") as output:
                while True:
                    _remaining(deadline)
                    chunk = response.read1(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > ASN_SIZE_LIMIT:
                        raise ValidationError("ASN database exceeds size limit")
                    output.write(chunk)
            if size == 0:
                raise ValidationError("ASN database download is empty")
        _remaining(deadline)
        temporary.replace(destination)
    except (OSError, ValueError) as exc:
        raise ValidationError(f"official ASN database download failed: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def prepare_asn(providers: dict, directory: Path, asn_mmdb: Path | None,
                deadline: float) -> None:
    needs_asn = any(
        re.search(r"(?:^|[,(])\s*(?:SRC-)?IP-ASN\s*,", row, re.I)
        for provider in providers.values()
        if provider["behavior"] == "classical" and provider["format"] == "yaml"
        for row in read_yaml(directory / provider["path"])["payload"]
    )
    if not needs_asn:
        return
    destination = directory / "ASN.mmdb"
    if asn_mmdb is not None:
        if not asn_mmdb.is_file():
            raise ValidationError(f"ASN database missing: {asn_mmdb}")
        shutil.copyfile(asn_mmdb, destination)
    else:
        fetch_asn(destination, deadline)


def isolated_config(providers: dict, rules: list[str], port: int, secret: str) -> dict:
    return {
        "mode": "rule", "log-level": "info", "allow-lan": False,
        "port": 0, "socks-port": 0, "mixed-port": 0, "redir-port": 0, "tproxy-port": 0,
        "external-controller": f"127.0.0.1:{port}", "secret": secret,
        "dns": {"enable": False}, "tun": {"enable": False}, "listeners": [],
        "geo-auto-update": False,
        "geox-url": {key: "http://127.0.0.1:1/disabled"
                     for key in ("geoip", "geosite", "mmdb", "asn")},
        "rule-providers": providers, "rules": rules,
    }


def validate(example: Path, mihomo: Path, timeout: float = 30,
             asn_mmdb: Path | None = None) -> dict:
    if timeout <= 0:
        raise ValidationError("timeout must be positive")
    mihomo = mihomo.resolve()
    if not mihomo.is_file():
        raise ValidationError(f"mihomo executable missing: {mihomo}")
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(prefix="sukka-core-validation-") as tmp:
        directory = Path(tmp)
        providers, expected, rule_lines = prepare_providers(example.resolve(), directory, mihomo, deadline)
        prepare_asn(providers, directory, asn_mmdb, deadline)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        secret = secrets.token_urlsafe(24)
        config = directory / "config.json"
        config.write_text(json.dumps(isolated_config(
            providers, rule_lines, port, secret)), encoding="utf-8")
        request = urllib.request.Request(f"http://127.0.0.1:{port}/providers/rules",
                                         headers={"Authorization": "Bearer " + secret})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        log_path = directory / "core.log"
        problems = ["controller did not become ready"]
        with log_path.open("w", encoding="utf-8") as output:
            process = subprocess.Popen([str(mihomo), "-d", str(directory), "-f", str(config)],
                                       stdout=output, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        with opener.open(request, timeout=min(1, _remaining(deadline))) as response:
                            actual = json.load(response).get("providers")
                        if not isinstance(actual, dict):
                            raise ValidationError("invalid provider API response")
                        problems = check_provider_counts(actual, expected)
                        if not problems:
                            return {"providers": len(expected),
                                    "loaded_rules": sum(actual[name]["ruleCount"] for name in expected),
                                    "yaml_providers": sum(w.file_format == "yaml" for w in expected.values()),
                                    "mrs_providers": sum(w.file_format == "mrs" for w in expected.values())}
                    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                        pass
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
                output.flush()
                logs = log_path.read_text(encoding="utf-8", errors="replace")[-5000:]
                raise ValidationError("Sukka provider validation failed: " + "; ".join(problems) + "\n" + logs)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mihomo", required=True, type=Path)
    parser.add_argument("--example", type=Path, default=ROOT / "Mihomo/Sukka/example.yaml")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--asn-mmdb", type=Path, help="existing official ASN database for offline validation")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.example, args.mihomo, args.timeout, args.asn_mmdb), ensure_ascii=False))
    except (ValidationError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
