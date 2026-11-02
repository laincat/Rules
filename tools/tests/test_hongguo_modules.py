"""Offline HongGuo model checks; not Surge-engine, merged-profile or device tests."""
from collections import deque
from pathlib import Path
import fnmatch
import hashlib
import itertools
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "Surge/Advertising"
SOURCE_BLOB = "04ee3209cabae4c9f05ac34b7df289aa1cdd56eb"
REMOVED = (
    ("DOMAIN-WILDCARD,v*-reading-videocdn*.qznovelvod.com,DIRECT",
     "DOMAIN-WILDCARD,v*-reading-video*.qznovelvod.com,DIRECT"),
    ("DOMAIN-WILDCARD,*-fq-tts.fqnovelvod.com,DIRECT",
     "DOMAIN-SUFFIX,fqnovelvod.com,DIRECT"),
    ("DOMAIN-WILDCARD,ads*-normal-lq.zijieapi.com,REJECT",
     "DOMAIN-WILDCARD,ads*-normal-*.zijieapi.com,REJECT"),
    ("DOMAIN-WILDCARD,v*-bd-daily-reading-ad.qznovelvod.com,REJECT",
     "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com,REJECT"),
    ("DOMAIN-WILDCARD,v*-se-daily-reading-ad.qznovelvod.com,REJECT",
     "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com,REJECT"),
    ("DOMAIN-WILDCARD,v*-se-sjy-daily-reading-ad.qznovelvod.com,REJECT",
     "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com,REJECT"),
)
EXPECTED = {
    "v3-reading-video.qznovelvod.com": "DIRECT",
    "v3-reading-videocdn.qznovelvod.com": "DIRECT",
    "v1-reading-video-reading-ad.qznovelvod.com": "DIRECT",
    "n98-v-readingvideo.qznovelvod.com": "DIRECT",
    "v6-reading-ad.qznovelvod.com": "REJECT",
    "v6-bd-daily-reading-ad.qznovelvod.com": "REJECT",
    "v6-se-daily-reading-ad.qznovelvod.com": "REJECT",
    "v6-se-sjy-daily-reading-ad.qznovelvod.com": "REJECT",
    "v6-normal.qznovelvod.com": "DIRECT",
    "qznovelvod.com": "DIRECT",
    "voice-fq-tts.fqnovelvod.com": "DIRECT",
    "fqnovelvod.com": "DIRECT",
    "p3-ad-sign.byteimg.com": "DIRECT",
    "p6-ad-sign.byteimg.com": "REJECT",
    "p3-tt.byteimg.com": "DIRECT",
    "p6-novel.byteimg.com": "DIRECT",
    "api5-normal.fqnovel.com": "DIRECT",
    "api3-normal-lq.fqnovel.com": "DIRECT",
    "api5-normal-sinfonlinea.fqnovel.com": None,
    "ads5-normal.zijieapi.com": "REJECT",
    "ads3-normal-lq.zijieapi.com": "REJECT",
    "ads3-normal-lf.zijieapi.com": "REJECT",
    "ads-normal-other.zijieapi.com": "REJECT",
    "ads3-normality.zijieapi.com": None,
    "api-access.pangolin-sdk-toutiao2.com": "REJECT",
    "log-api.pangolin-sdk-toutiao-extra.com": "REJECT",
    "pangolin-sdk-toutiao2.com": None,
    "business.pangolin-sdk-toutiao2.com": None,
    "praisewindow-sinfonlinea.ugsdk.cn": "REJECT",
    "praisewindow.ugsdk.cn": "REJECT",
    "praisewindow-other.ugsdk.cn": None,
    "reading-tracking.fqnovel.com": None,
    "rtlog3-applog.fqnovel.com": None,
    "rtlog5-applog-lq.fqnovel.com": "REJECT",
    "isaas.ecombdapi.com": None,
    "webcast.amemv.com": None,
    "example.com": None,
}


def sections(text):
    result = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            if current in result:
                raise ValueError("duplicate section: " + current)
            result[current] = []
        elif current is None:
            raise ValueError("entry outside a section")
        else:
            result[current].append(line)
    return result


def rules(text):
    result = []
    for line in sections(text)["Rule"]:
        kind, pattern, policy_name = line.split(",")
        if kind not in {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-WILDCARD"}:
            raise ValueError("unsupported model rule: " + kind)
        result.append((kind, pattern, policy_name))
    return result


def matches(rule, host):
    kind, pattern, _ = rule
    host = host.lower().removesuffix(".")
    if kind == "DOMAIN":
        return host == pattern
    if kind == "DOMAIN-SUFFIX":
        return host == pattern or host.endswith("." + pattern)
    return fnmatch.fnmatchcase(host, pattern)


def policy(rule_list, host):
    return next((r[2] for r in rule_list if matches(r, host)), None)


def globs(rule):
    kind, pattern, _ = rule
    return (pattern, "*." + pattern) if kind == "DOMAIN-SUFFIX" else (pattern,)


def closure(patterns, states):
    result = set(states)
    work = list(states)
    while work:
        branch, index = work.pop()
        if index < len(patterns[branch]) and patterns[branch][index] == "*":
            next_state = (branch, index + 1)
            if next_state not in result:
                result.add(next_state)
                work.append(next_state)
    return frozenset(result)


def advance(patterns, states, char):
    out = set()
    for branch, index in states:
        pattern = patterns[branch]
        if index < len(pattern):
            if pattern[index] == "*":
                out.add((branch, index))
            elif pattern[index] == char:
                out.add((branch, index + 1))
    return closure(patterns, out)


def accepts(patterns, states):
    return any(index == len(patterns[branch]) for branch, index in states)


def inclusion(narrow, wide):
    """Finite-state proof for literal/* patterns, including dots matched by *."""
    literal_chars = set("".join(narrow + wide)) - {"*"}
    if literal_chars & set("?[]#"):
        raise ValueError("proof supports only literal/* patterns")
    # Every nonliteral character is equivalent to the fresh representative '#'.
    alphabet = sorted(literal_chars | {"#"})
    start = tuple(closure(p, [(i, 0) for i in range(len(p))]) for p in (narrow, wide))
    work = deque([start])
    seen = {start}
    while work:
        a, b = work.popleft()
        if accepts(narrow, a) and not accepts(wide, b):
            return False
        for char in alphabet:
            na = advance(narrow, a, char)
            if not na:
                continue
            state = (na, advance(wide, b, char))
            if state not in seen:
                seen.add(state)
                work.append(state)
    return True


def hosts_for(rule):
    kind, pattern, _ = rule
    if kind == "DOMAIN":
        return [pattern, "x." + pattern, pattern + ".other.example"]
    if kind == "DOMAIN-SUFFIX":
        return [pattern, "x." + pattern, "a.b." + pattern, pattern + ".other.example", "evil" + pattern]
    pieces = pattern.split("*")
    words = ["", "0", "3", "5", "12", "x", "-lq", "-lf", "x.y",
             "-reading-video", "-reading-videocdn", "-se-sjy-daily"]
    out = []
    for replacements in itertools.product(words, repeat=len(pieces) - 1):
        value = pieces[0] + "".join(a + b for a, b in zip(replacements, pieces[1:]))
        if all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
               for label in value.split(".")):
            out.extend([value, value.upper(), value + ".", value + ".other.example"])
    return out


def original_text(candidate):
    """Reconstruct the pinned prior text only in memory; no legacy module is shipped.

    The Git blob assertion below prevents a changed candidate from inventing a
    different baseline. These six lines are test inputs, never deployable output.
    """
    anchors = [wide for _, wide in REMOVED]
    anchors[1] = "DOMAIN,n98-v-readingvideo.qznovelvod.com,DIRECT"
    text = candidate
    # Reverse iteration preserves the order of removals sharing one anchor.
    for (removed, _), anchor in reversed(list(zip(REMOVED, anchors))):
        assert text.count(anchor + "\n") == 1
        text = text.replace(anchor + "\n", anchor + "\n" + removed + "\n")
    return text


class HongGuoModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_text = (MODULES / "HongGuo.sgmodule").read_text(encoding="utf-8")
        cls.original = original_text(cls.main_text)
        cls.old = rules(cls.original)
        cls.new = rules(cls.main_text)

    def test_baseline_and_only_six_removals_in_original_order(self):
        original = self.original.encode("utf-8")
        blob = hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest()
        self.assertEqual(blob, SOURCE_BLOB)
        removed = {tuple(narrow.split(",")) for narrow, _ in REMOVED}
        self.assertEqual((len(self.old), len(self.new), len(removed)), (51, 45, 6))
        self.assertEqual(self.new, [r for r in self.old if r not in removed])

    def test_each_removed_rule_is_covered_earlier_with_same_policy(self):
        for narrow_line, wide_line in REMOVED:
            with self.subTest(rule=narrow_line):
                narrow, wide = tuple(narrow_line.split(",")), tuple(wide_line.split(","))
                self.assertLess(self.old.index(wide), self.old.index(narrow))
                self.assertEqual(wide[2], narrow[2])
                self.assertIn(wide, self.new)
                self.assertTrue(inclusion(globs(narrow), globs(wide)))

    def test_inclusion_proof_rejects_counterexamples(self):
        self.assertTrue(inclusion(("a*",), ("*",)))
        self.assertFalse(inclusion(("*",), ("a*",)))
        self.assertFalse(inclusion(("p3-ad-sign.byteimg.com",), ("p6-ad-sign.byteimg.com",)))
        with self.assertRaises(ValueError):
            inclusion(("a?",), ("*",))

    def test_regressions_and_generated_host_differential(self):
        self.assertEqual(len(EXPECTED), 37)
        for host, expected in EXPECTED.items():
            with self.subTest(host=host):
                self.assertEqual(policy(self.old, host), expected)
                self.assertEqual(policy(self.new, host), expected)
        hosts = set(EXPECTED)
        for rule in self.old:
            hosts.update(hosts_for(rule))
        self.assertGreater(len(hosts), 3000)
        for host in sorted(hosts):
            self.assertEqual(policy(self.old, host), policy(self.new, host), host)

    def test_regressions_detect_unsafe_mutations(self):
        no_exception = [r for r in self.new if r != ("DOMAIN", "p3-ad-sign.byteimg.com", "DIRECT")]
        self.assertNotEqual(policy(no_exception, "p3-ad-sign.byteimg.com"), EXPECTED["p3-ad-sign.byteimg.com"])
        broad_qz = [("DOMAIN-SUFFIX", "qznovelvod.com", "DIRECT")] + self.new
        self.assertNotEqual(policy(broad_qz, "v6-reading-ad.qznovelvod.com"), "REJECT")
        broad_pangolin = [("DOMAIN-WILDCARD", "*pangolin-sdk-toutiao*.com", "REJECT")] + self.new
        self.assertIsNotNone(policy(broad_pangolin, "business.pangolin-sdk-toutiao2.com"))

    def test_diagnostic_is_standalone_and_mitm_is_narrow_and_appended(self):
        text = (MODULES / "HongGuo.Diagnostic.sgmodule").read_text(encoding="utf-8")
        main, diagnostic = sections(self.main_text), sections(text)
        self.assertEqual(set(main), {"Rule"})
        self.assertEqual(set(diagnostic), {"Rule", "Script", "MITM"})
        self.assertEqual(rules(text), self.new)
        for content in (self.main_text, text):
            for field in ("name", "desc", "homepage"):
                self.assertRegex(content, rf"(?m)^#!{field}\s*=\s*\S")
        self.assertEqual(len(diagnostic["MITM"]), 1)
        key, value = map(str.strip, diagnostic["MITM"][0].split("=", 1))
        self.assertEqual(key, "hostname")
        self.assertTrue(value.startswith("%APPEND% "))
        hosts = [h.strip() for h in value.removeprefix("%APPEND%").split(",")]
        expected_hosts = {f"api{n}-normal{suffix}.fqnovel.com" for n in (3, 5) for suffix in ("", "-lq")}
        self.assertEqual(len(hosts), 4)
        self.assertEqual(set(hosts), expected_hosts)
        self.assertEqual(len(diagnostic["Script"]), 1)
        parameters = diagnostic["Script"][0].split("=", 1)[1]
        parts = [tuple(map(str.strip, part.split("=", 1))) for part in parameters.split(",")]
        settings = dict(parts)
        self.assertEqual(len(settings), len(parts))
        for key, value in {
            "type": "http-response", "requires-body": "true", "max-size": "262144", "timeout": "2",
            "script-path": "https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/HongGuo.Diagnostic.js",
        }.items():
            self.assertEqual(settings[key], value)
        pattern = re.compile(settings["pattern"])
        endpoint = "/novel/player/video_detail/v1/"
        for host in expected_hosts:
            for query in ("", "?example=synthetic"):
                self.assertIsNotNone(pattern.search("https://" + host + endpoint + query))
        for url in (
            "https://api5-normal.fqnovel.com.evil.example" + endpoint,
            "https://api9-normal.fqnovel.com" + endpoint,
            "https://api5-normal-lf.fqnovel.com" + endpoint,
            "https://api5-normal.fqnovel.com" + endpoint + "extra",
            "https://api5-normal.fqnovel.com/novel/player/video_model/v1/",
            "https://user:pass@api5-normal.fqnovel.com" + endpoint,
            "http://api5-normal.fqnovel.com" + endpoint,
        ):
            self.assertIsNone(pattern.search(url), url)

    def test_javascript_synthetic_cases(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for diagnostic script regression tests")
        result = subprocess.run(
            [node, str(Path(__file__).with_name("hongguo_diagnostic.test.cjs"))],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
